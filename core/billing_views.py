import calendar
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime
from decimal import Decimal
from urllib.parse import quote

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    Business,
    BusinessSubscription,
    EFTSubscriptionRequest,
    SubscriptionPayment,
)


logger = logging.getLogger(__name__)

PAYSTACK_API_BASE = "https://api.paystack.co"
PAYSTACK_TIMEOUT_SECONDS = 20


# =========================================================
# HELPERS
# =========================================================


def get_user_business(user):
    return Business.objects.filter(
        owner=user
    ).first()


def get_or_create_subscription(business):
    subscription, _ = (
        BusinessSubscription.objects.get_or_create(
            business=business
        )
    )

    return subscription


def paystack_is_ready():
    return bool(
        settings.PAYSTACK_ENABLED
        and settings.PAYSTACK_SECRET_KEY
        and settings.PAYSTACK_PRO_PLAN_CODE
        and settings.TRADEFLOW_PRO_PRICE_ZAR
        > Decimal("0.00")
    )


def expected_amount_minor():
    return int(
        (
            settings.TRADEFLOW_PRO_PRICE_ZAR
            * Decimal("100")
        ).quantize(
            Decimal("1")
        )
    )


def paystack_api_request(
    method,
    path,
    payload=None,
):
    """
    Make one authenticated server-to-server Paystack request.

    The Paystack secret key never leaves the backend.
    Requests is used instead of urllib so Paystack receives a
    normal server-side HTTP client signature.
    """

    if not settings.PAYSTACK_SECRET_KEY:
        raise RuntimeError(
            "Paystack secret key is not configured."
        )

    url = (
        PAYSTACK_API_BASE
        + path
    )

    headers = {
        "Authorization": (
            "Bearer "
            + settings.PAYSTACK_SECRET_KEY
        ),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "TradeFlow/1.0 PaystackClient",
    }

    try:
        response = requests.request(
            method=method.upper(),
            url=url,
            json=payload,
            headers=headers,
            timeout=PAYSTACK_TIMEOUT_SECONDS,
        )

    except requests.Timeout as exc:
        logger.warning(
            "Paystack request timed out path=%s",
            path,
        )

        raise RuntimeError(
            "TradeFlow could not connect to Paystack."
        ) from exc

    except requests.ConnectionError as exc:
        logger.warning(
            "Paystack connection error path=%s error=%s",
            path,
            exc,
        )

        raise RuntimeError(
            "TradeFlow could not connect to Paystack."
        ) from exc

    except requests.RequestException as exc:
        logger.warning(
            "Unexpected Paystack request error path=%s error=%s",
            path,
            exc,
        )

        raise RuntimeError(
            "TradeFlow could not connect to Paystack."
        ) from exc

    if not response.ok:
        logger.warning(
            "Paystack HTTP error status=%s body=%s",
            response.status_code,
            response.text[:500],
        )

        raise RuntimeError(
            "Paystack rejected the request."
        )

    try:
        result = response.json()

    except ValueError as exc:
        logger.warning(
            "Paystack returned non-JSON response status=%s body=%s",
            response.status_code,
            response.text[:500],
        )

        raise RuntimeError(
            "Paystack returned an invalid response."
        ) from exc

    if not result.get("status"):
        raise RuntimeError(
            result.get("message")
            or "Paystack request failed."
        )

    return result


def add_one_month(value):
    """
    Add one calendar month while preserving time and timezone.
    """

    year = value.year
    month = value.month + 1

    if month == 13:
        year += 1
        month = 1

    day = min(
        value.day,
        calendar.monthrange(
            year,
            month,
        )[1],
    )

    return value.replace(
        year=year,
        month=month,
        day=day,
    )


def generate_eft_reference(business):
    """Generate a short unique customer-facing EFT reference."""

    while True:
        token = secrets.token_hex(4).upper()
        reference = f"TFPRO-{business.pk}-{token}"

        if not EFTSubscriptionRequest.objects.filter(
            reference=reference
        ).exists():
            return reference


def get_eft_bank_details():
    """Return TradeFlow platform bank details from settings."""

    return {
        "bank_name": getattr(
            settings,
            "TRADEFLOW_EFT_BANK_NAME",
            "",
        ),
        "account_name": getattr(
            settings,
            "TRADEFLOW_EFT_ACCOUNT_NAME",
            "",
        ),
        "account_number": getattr(
            settings,
            "TRADEFLOW_EFT_ACCOUNT_NUMBER",
            "",
        ),
        "branch_code": getattr(
            settings,
            "TRADEFLOW_EFT_BRANCH_CODE",
            "",
        ),
        "account_type": getattr(
            settings,
            "TRADEFLOW_EFT_ACCOUNT_TYPE",
            "",
        ),
    }


def eft_is_ready():
    details = get_eft_bank_details()

    return bool(
        details["bank_name"]
        and details["account_name"]
        and details["account_number"]
        and settings.TRADEFLOW_PRO_PRICE_ZAR
        > Decimal("0.00")
    )


@transaction.atomic
def activate_manual_pro(eft_request, staff_user):
    """
    Approve one verified EFT payment and grant one calendar
    month of TradeFlow Pro. Approval is idempotent.
    """

    eft_request = (
        EFTSubscriptionRequest.objects.select_for_update()
        .select_related(
            "business",
            "subscription",
        )
        .get(
            pk=eft_request.pk
        )
    )

    if (
        eft_request.status
        == EFTSubscriptionRequest.STATUS_APPROVED
    ):
        return eft_request.subscription

    if (
        eft_request.status
        != EFTSubscriptionRequest.STATUS_PENDING_REVIEW
    ):
        raise ValueError(
            "Only pending EFT payments may be approved."
        )

    subscription = (
        BusinessSubscription.objects.select_for_update()
        .get(
            pk=eft_request.subscription_id
        )
    )

    now = timezone.now()
    period_start = now

    if (
        subscription.current_period_end
        and subscription.current_period_end > now
    ):
        period_start = subscription.current_period_end

    period_end = add_one_month(
        period_start
    )

    subscription.plan = (
        BusinessSubscription.PLAN_PRO
    )
    subscription.status = (
        BusinessSubscription.STATUS_ACTIVE
    )
    subscription.billing_provider = (
        BusinessSubscription.PROVIDER_MANUAL
    )

    if not subscription.started_at:
        subscription.started_at = now

    subscription.current_period_start = (
        period_start
    )
    subscription.current_period_end = (
        period_end
    )
    subscription.cancelled_at = None
    subscription.provider_reference = (
        eft_request.reference
    )
    subscription.save()

    eft_request.status = (
        EFTSubscriptionRequest.STATUS_APPROVED
    )
    eft_request.reviewed_by = staff_user
    eft_request.reviewed_at = now
    eft_request.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    return subscription


def parse_paystack_datetime(value):
    if not value:
        return None

    if isinstance(
        value,
        datetime,
    ):
        parsed = value
    else:
        parsed = parse_datetime(
            str(value)
        )

    if not parsed:
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed


def extract_customer_code(data):
    customer = data.get(
        "customer"
    )

    if isinstance(
        customer,
        dict,
    ):
        return (
            customer.get(
                "customer_code"
            )
            or customer.get(
                "code"
            )
            or ""
        )

    return (
        data.get(
            "customer_code"
        )
        or ""
    )


def extract_customer_email(data):
    customer = data.get(
        "customer"
    )

    if isinstance(
        customer,
        dict,
    ):
        return (
            customer.get(
                "email"
            )
            or ""
        ).strip().lower()

    return (
        data.get(
            "email"
        )
        or ""
    ).strip().lower()


def extract_subscription_code(data):
    direct = (
        data.get(
            "subscription_code"
        )
        or ""
    )

    if direct:
        return direct

    subscription = data.get(
        "subscription"
    )

    if isinstance(
        subscription,
        dict,
    ):
        return (
            subscription.get(
                "subscription_code"
            )
            or subscription.get(
                "code"
            )
            or ""
        )

    return ""


def metadata_business_id(data):
    metadata = data.get(
        "metadata"
    )

    if isinstance(
        metadata,
        str,
    ):
        try:
            metadata = json.loads(
                metadata
            )
        except Exception:
            metadata = {}

    if not isinstance(
        metadata,
        dict,
    ):
        return None

    business_id = metadata.get(
        "tradeflow_business_id"
    )

    try:
        return int(
            business_id
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def find_subscription_for_event(data):
    subscription_code = (
        extract_subscription_code(
            data
        )
    )

    if subscription_code:
        subscription = (
            BusinessSubscription.objects.filter(
                provider_subscription_code=(
                    subscription_code
                )
            )
            .select_related(
                "business"
            )
            .first()
        )

        if subscription:
            return subscription

    customer_code = (
        extract_customer_code(
            data
        )
    )

    if customer_code:
        subscription = (
            BusinessSubscription.objects.filter(
                provider_customer_code=(
                    customer_code
                )
            )
            .select_related(
                "business"
            )
            .first()
        )

        if subscription:
            return subscription

    business_id = metadata_business_id(
        data
    )

    if business_id:
        return (
            BusinessSubscription.objects.filter(
                business_id=business_id
            )
            .select_related(
                "business"
            )
            .first()
        )

    email = extract_customer_email(
        data
    )

    if email:
        return (
            BusinessSubscription.objects.filter(
                Q(
                    business__email__iexact=email
                )
                | Q(
                    business__owner__email__iexact=email
                )
            )
            .select_related(
                "business"
            )
            .first()
        )

    return None


def validate_charge_amount(data):
    try:
        amount = int(
            data.get(
                "amount"
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return False

    currency = str(
        data.get(
            "currency",
            "",
        )
    ).upper()

    return (
        amount
        == expected_amount_minor()
        and currency == "ZAR"
    )


@transaction.atomic
def apply_successful_charge(
    data,
    event_type="charge.success",
):
    """
    Idempotently activate/renew Pro after a verified Paystack
    charge.
    """

    reference = str(
        data.get(
            "reference",
            "",
        )
    ).strip()

    if not reference:
        raise ValueError(
            "Successful Paystack charge has no reference."
        )

    if not validate_charge_amount(
        data
    ):
        logger.error(
            "Rejected Paystack charge due to amount/currency mismatch "
            "reference=%s amount=%s currency=%s",
            reference,
            data.get("amount"),
            data.get("currency"),
        )

        payment = (
            SubscriptionPayment.objects.filter(
                reference=reference
            )
            .first()
        )

        if payment:
            payment.status = (
                SubscriptionPayment.STATUS_FAILED
            )
            payment.provider_message = (
                "Amount or currency did not match the TradeFlow Pro plan."
            )
            payment.last_event_type = event_type
            payment.save(
                update_fields=[
                    "status",
                    "provider_message",
                    "last_event_type",
                    "updated_at",
                ]
            )

        return False

    payment = (
        SubscriptionPayment.objects.select_for_update()
        .filter(
            reference=reference
        )
        .select_related(
            "business",
            "subscription",
        )
        .first()
    )

    subscription = None

    if payment:
        subscription = (
            BusinessSubscription.objects.select_for_update()
            .get(
                pk=(
                    payment.subscription_id
                )
            )
        )

    if not subscription:
        discovered = (
            find_subscription_for_event(
                data
            )
        )

        if not discovered:
            logger.error(
                "Could not map Paystack charge to a TradeFlow business "
                "reference=%s",
                reference,
            )
            return False

        subscription = (
            BusinessSubscription.objects.select_for_update()
            .get(
                pk=discovered.pk
            )
        )

    business = subscription.business

    customer_code = (
        extract_customer_code(
            data
        )
    )

    subscription_code = (
        extract_subscription_code(
            data
        )
    )

    provider_transaction_id = (
        data.get(
            "id"
        )
    )

    paid_at = (
        parse_paystack_datetime(
            data.get(
                "paid_at"
            )
            or data.get(
                "paidAt"
            )
        )
        or timezone.now()
    )

    amount_zar = (
        Decimal(
            int(
                data.get(
                    "amount"
                )
            )
        )
        / Decimal("100")
    )

    if not payment:
        payment = (
            SubscriptionPayment.objects.create(
                business=business,
                subscription=subscription,
                reference=reference,
                amount=amount_zar,
                currency="ZAR",
                provider_customer_code=(
                    customer_code
                ),
                provider_subscription_code=(
                    subscription_code
                ),
                last_event_type=event_type,
            )
        )

    if (
        payment.status
        == SubscriptionPayment.STATUS_SUCCESS
    ):
        return True

    # Use the later of paid_at or the current paid-through date
    # so an early/retried renewal never shortens existing access.
    period_start = paid_at

    if (
        subscription.current_period_end
        and subscription.current_period_end
        > period_start
    ):
        period_start = (
            subscription.current_period_end
        )

    period_end = add_one_month(
        period_start
    )

    subscription.plan = (
        BusinessSubscription.PLAN_PRO
    )
    subscription.status = (
        BusinessSubscription.STATUS_ACTIVE
    )
    subscription.billing_provider = (
        BusinessSubscription.PROVIDER_PAYSTACK
    )

    if not subscription.started_at:
        subscription.started_at = paid_at

    subscription.current_period_start = (
        period_start
    )
    subscription.current_period_end = (
        period_end
    )
    subscription.cancelled_at = None
    subscription.provider_reference = (
        reference
    )

    if customer_code:
        subscription.provider_customer_code = (
            customer_code
        )

    if subscription_code:
        subscription.provider_subscription_code = (
            subscription_code
        )

    subscription.save()

    payment.status = (
        SubscriptionPayment.STATUS_SUCCESS
    )
    payment.amount = amount_zar
    payment.currency = "ZAR"
    payment.provider_transaction_id = (
        provider_transaction_id
        or payment.provider_transaction_id
    )
    payment.provider_customer_code = (
        customer_code
        or payment.provider_customer_code
    )
    payment.provider_subscription_code = (
        subscription_code
        or payment.provider_subscription_code
    )
    payment.last_event_type = event_type
    payment.provider_message = (
        "Paystack payment verified successfully."
    )
    payment.paid_at = paid_at
    payment.save()

    return True


# =========================================================
# SUBSCRIPTION PAGE
# =========================================================


@login_required
def subscription_overview(request):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    subscription = (
        get_or_create_subscription(
            business
        )
    )

    recent_payments = (
        SubscriptionPayment.objects.filter(
            business=business
        )[:10]
    )

    recent_eft_requests = (
        EFTSubscriptionRequest.objects.filter(
            business=business
        )[:10]
    )

    email = (
        business.email
        or request.user.email
        or ""
    ).strip()

    context = {
        "business": business,
        "subscription": subscription,
        "recent_payments": recent_payments,
        "recent_eft_requests": recent_eft_requests,
        "paystack_ready": paystack_is_ready(),
        "eft_ready": eft_is_ready(),
        "payment_email": email,
        "pro_price": (
            settings.TRADEFLOW_PRO_PRICE_ZAR
        ),
    }

    return render(
        request,
        "core/subscription.html",
        context,
    )


# =========================================================
# MANUAL EFT CHECKOUT
# =========================================================


@login_required
@require_POST
def eft_checkout(request):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    subscription = (
        get_or_create_subscription(
            business
        )
    )

    if subscription.has_pro_access:
        messages.info(
            request,
            "Your TradeFlow Pro subscription is already active.",
        )
        return redirect(
            "core:subscription"
        )

    if not eft_is_ready():
        messages.error(
            request,
            "EFT payment details are not currently available.",
        )
        return redirect(
            "core:subscription"
        )

    existing = (
        EFTSubscriptionRequest.objects.filter(
            business=business,
            status__in=[
                EFTSubscriptionRequest.STATUS_AWAITING_PAYMENT,
                EFTSubscriptionRequest.STATUS_PENDING_REVIEW,
            ],
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    if existing:
        return redirect(
            "core:eft_payment",
            reference=existing.reference,
        )

    eft_request = (
        EFTSubscriptionRequest.objects.create(
            business=business,
            subscription=subscription,
            reference=generate_eft_reference(
                business
            ),
            amount=settings.TRADEFLOW_PRO_PRICE_ZAR,
            currency="ZAR",
        )
    )

    return redirect(
        "core:eft_payment",
        reference=eft_request.reference,
    )


@login_required
def eft_payment(request, reference):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    eft_request = (
        EFTSubscriptionRequest.objects.filter(
            business=business,
            reference=reference,
        )
        .select_related(
            "subscription"
        )
        .first()
    )

    if not eft_request:
        return HttpResponse(
            "EFT request not found.",
            status=404,
        )

    if request.method == "POST":
        if (
            eft_request.status
            != EFTSubscriptionRequest.STATUS_AWAITING_PAYMENT
        ):
            messages.warning(
                request,
                (
                    "This EFT request has already been "
                    "submitted for review."
                ),
            )
            return redirect(
                "core:eft_payment",
                reference=eft_request.reference,
            )

        payment_reference = (
            request.POST.get(
                "payment_reference",
                "",
            )
            .strip()
        )

        customer_note = (
            request.POST.get(
                "customer_note",
                "",
            )
            .strip()
        )

        if not payment_reference:
            messages.error(
                request,
                (
                    "Enter the payment reference or bank "
                    "transaction reference before submitting."
                ),
            )

        else:
            eft_request.customer_payment_reference = (
                payment_reference[:160]
            )
            eft_request.customer_note = (
                customer_note[:2000]
            )
            eft_request.status = (
                EFTSubscriptionRequest.STATUS_PENDING_REVIEW
            )
            eft_request.submitted_at = timezone.now()
            eft_request.save(
                update_fields=[
                    "customer_payment_reference",
                    "customer_note",
                    "status",
                    "submitted_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                (
                    "Your EFT payment has been submitted for "
                    "verification. Pro will activate after "
                    "TradeFlow confirms the payment."
                ),
            )
            return redirect(
                "core:subscription"
            )

    context = {
        "business": business,
        "eft_request": eft_request,
        "bank_details": get_eft_bank_details(),
    }

    return render(
        request,
        "core/eft_payment.html",
        context,
    )


# =========================================================
# STAFF EFT VERIFICATION
# =========================================================


def staff_required(user):
    return (
        user.is_authenticated
        and user.is_staff
    )


@login_required
@user_passes_test(
    staff_required
)
def eft_admin_list(request):
    pending_requests = (
        EFTSubscriptionRequest.objects.filter(
            status=(
                EFTSubscriptionRequest.STATUS_PENDING_REVIEW
            )
        )
        .select_related(
            "business",
            "subscription",
        )
        .order_by(
            "submitted_at"
        )
    )

    return render(
        request,
        "core/eft_admin_list.html",
        {
            "pending_requests": pending_requests,
        },
    )


@login_required
@user_passes_test(
    staff_required
)
@require_POST
def eft_admin_approve(
    request,
    request_id,
):
    eft_request = (
        EFTSubscriptionRequest.objects.filter(
            pk=request_id,
        )
        .select_related(
            "business",
            "subscription",
        )
        .first()
    )

    if not eft_request:
        return HttpResponse(
            "EFT request not found.",
            status=404,
        )

    try:
        subscription = activate_manual_pro(
            eft_request,
            request.user,
        )

    except ValueError as exc:
        messages.error(
            request,
            str(exc),
        )

    else:
        messages.success(
            request,
            (
                f"EFT approved. "
                f"{eft_request.business.name} now has "
                f"TradeFlow Pro until "
                f"{timezone.localtime(subscription.current_period_end):%d %b %Y}."
            ),
        )

    return redirect(
        "core:eft_admin_list"
    )


@login_required
@user_passes_test(
    staff_required
)
@require_POST
@transaction.atomic
def eft_admin_reject(
    request,
    request_id,
):
    eft_request = (
        EFTSubscriptionRequest.objects.select_for_update()
        .filter(
            pk=request_id,
        )
        .first()
    )

    if not eft_request:
        return HttpResponse(
            "EFT request not found.",
            status=404,
        )

    if (
        eft_request.status
        != EFTSubscriptionRequest.STATUS_PENDING_REVIEW
    ):
        messages.error(
            request,
            "Only pending EFT requests may be rejected.",
        )
        return redirect(
            "core:eft_admin_list"
        )

    eft_request.status = (
        EFTSubscriptionRequest.STATUS_REJECTED
    )
    eft_request.reviewed_by = request.user
    eft_request.reviewed_at = timezone.now()
    eft_request.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ]
    )

    messages.success(
        request,
        (
            f"EFT request for "
            f"{eft_request.business.name} was rejected."
        ),
    )

    return redirect(
        "core:eft_admin_list"
    )


# =========================================================
# INITIALIZE PAYSTACK CHECKOUT
# =========================================================


@login_required
@require_POST
def subscription_checkout(request):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    subscription = (
        get_or_create_subscription(
            business
        )
    )

    if subscription.has_pro_access:
        messages.info(
            request,
            "Your TradeFlow Pro subscription is already active.",
        )
        return redirect(
            "core:subscription"
        )

    if not paystack_is_ready():
        messages.warning(
            request,
            (
                "Online Pro checkout is not enabled yet. "
                "Manual / EFT activation remains available."
            ),
        )
        return redirect(
            "core:subscription"
        )

    email = (
        business.email
        or request.user.email
        or ""
    ).strip()

    if not email:
        messages.error(
            request,
            (
                "Add a business email address before starting "
                "a Paystack subscription."
            ),
        )
        return redirect(
            "core:business_setup"
        )

    callback_url = (
        request.build_absolute_uri(
            reverse(
                "core:subscription_callback"
            )
        )
    )

    payload = {
        "email": email,
        "amount": str(
            expected_amount_minor()
        ),
        "currency": "ZAR",
        "plan": (
            settings.PAYSTACK_PRO_PLAN_CODE
        ),
        "callback_url": callback_url,
        "metadata": json.dumps(
            {
                "tradeflow_business_id": (
                    business.id
                ),
                "tradeflow_subscription_id": (
                    subscription.id
                ),
                "product": "tradeflow_pro",
            }
        ),
    }

    try:
        result = paystack_api_request(
            "POST",
            "/transaction/initialize",
            payload,
        )

    except RuntimeError:
        logger.exception(
            "Could not initialize Paystack checkout business_id=%s",
            business.id,
        )

        messages.error(
            request,
            (
                "TradeFlow could not start the secure payment "
                "checkout. Please try again shortly."
            ),
        )

        return redirect(
            "core:subscription"
        )

    data = result.get(
        "data"
    ) or {}

    reference = str(
        data.get(
            "reference",
            "",
        )
    ).strip()

    authorization_url = str(
        data.get(
            "authorization_url",
            "",
        )
    ).strip()

    if (
        not reference
        or not authorization_url.startswith(
            "https://checkout.paystack.com/"
        )
    ):
        logger.error(
            "Invalid Paystack initialize response business_id=%s",
            business.id,
        )

        messages.error(
            request,
            "Paystack returned an invalid checkout response.",
        )

        return redirect(
            "core:subscription"
        )

    SubscriptionPayment.objects.update_or_create(
        reference=reference,
        defaults={
            "business": business,
            "subscription": subscription,
            "amount": (
                settings.TRADEFLOW_PRO_PRICE_ZAR
            ),
            "currency": "ZAR",
            "status": (
                SubscriptionPayment.STATUS_INITIALIZED
            ),
            "last_event_type": (
                "transaction.initialize"
            ),
        },
    )

    subscription.billing_provider = (
        BusinessSubscription.PROVIDER_PAYSTACK
    )
    subscription.provider_reference = (
        reference
    )
    subscription.save(
        update_fields=[
            "billing_provider",
            "provider_reference",
            "updated_at",
        ]
    )

    return redirect(
        authorization_url
    )


# =========================================================
# PAYSTACK CALLBACK
# =========================================================


def subscription_callback(request):
    """
    Browser return URL after Paystack checkout.

    The browser is never trusted as proof of payment. TradeFlow
    verifies the reference directly against Paystack before
    activating Pro.
    """

    reference = (
        request.GET.get(
            "reference"
        )
        or request.GET.get(
            "trxref"
        )
        or ""
    ).strip()

    if not reference:
        messages.warning(
            request,
            "No Paystack transaction reference was returned.",
        )
        return redirect(
            "core:subscription"
        )

    payment = (
        SubscriptionPayment.objects.filter(
            reference=reference
        )
        .first()
    )

    if not payment:
        logger.warning(
            "Unknown Paystack callback reference=%s",
            reference,
        )
        messages.error(
            request,
            "TradeFlow could not match this payment reference.",
        )
        return redirect(
            "core:subscription"
        )

    if not paystack_is_ready():
        messages.error(
            request,
            "Paystack verification is not currently available.",
        )
        return redirect(
            "core:subscription"
        )

    try:
        result = paystack_api_request(
            "GET",
            (
                "/transaction/verify/"
                + quote(
                    reference,
                    safe="",
                )
            ),
        )

    except RuntimeError:
        logger.exception(
            "Paystack verification failed reference=%s",
            reference,
        )
        messages.error(
            request,
            (
                "TradeFlow could not verify the payment yet. "
                "If payment succeeded, the secure webhook can "
                "still activate your subscription automatically."
            ),
        )
        return redirect(
            "core:subscription"
        )

    data = result.get(
        "data"
    ) or {}

    if data.get("status") != "success":
        payment.status = (
            SubscriptionPayment.STATUS_FAILED
        )
        payment.provider_message = str(
            data.get(
                "gateway_response"
            )
            or data.get(
                "status"
            )
            or "Payment was not successful."
        )[:500]
        payment.last_event_type = (
            "transaction.verify"
        )
        payment.save()

        messages.warning(
            request,
            (
                "The payment has not been confirmed as successful. "
                "Pro access was not activated."
            ),
        )
        return redirect(
            "core:subscription"
        )

    # Never allow metadata from Paystack to redirect the payment
    # to another business. The locally stored reference owns the
    # transaction; force that business ID into the verified data.
    metadata = data.get(
        "metadata"
    )

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    if not isinstance(metadata, dict):
        metadata = {}

    metadata[
        "tradeflow_business_id"
    ] = payment.business_id

    data["metadata"] = metadata

    activated = apply_successful_charge(
        data,
        event_type="transaction.verify",
    )

    if activated:
        messages.success(
            request,
            (
                "Payment confirmed. TradeFlow Pro is now active."
            ),
        )
    else:
        messages.error(
            request,
            (
                "Payment was received but TradeFlow could not "
                "activate Pro automatically. Please contact support."
            ),
        )

    return redirect(
        "core:subscription"
    )


# =========================================================
# PAYSTACK WEBHOOK
# =========================================================


@csrf_exempt
@require_POST
def paystack_webhook(request):
    """
    Receive signed Paystack events.

    Webhook authenticity is verified using HMAC SHA512 over the
    exact raw request body before any event is processed.
    """

    secret = settings.PAYSTACK_SECRET_KEY

    if not secret:
        logger.error(
            "Paystack webhook received but secret key is missing."
        )
        return HttpResponse(
            status=503
        )

    supplied_signature = (
        request.headers.get(
            "x-paystack-signature",
            "",
        )
    )

    expected_signature = hmac.new(
        secret.encode(
            "utf-8"
        ),
        request.body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(
        supplied_signature,
        expected_signature,
    ):
        logger.warning(
            "Rejected Paystack webhook with invalid signature."
        )
        return HttpResponse(
            status=400
        )

    try:
        event = json.loads(
            request.body.decode(
                "utf-8"
            )
        )
    except Exception:
        return HttpResponse(
            status=400
        )

    event_type = str(
        event.get(
            "event",
            "",
        )
    )
    data = event.get(
        "data"
    ) or {}

    try:
        if event_type == "charge.success":
            apply_successful_charge(
                data,
                event_type=event_type,
            )

        elif event_type == "subscription.create":
            subscription = (
                find_subscription_for_event(
                    data
                )
            )

            if subscription:
                customer_code = (
                    extract_customer_code(
                        data
                    )
                )
                subscription_code = (
                    extract_subscription_code(
                        data
                    )
                )

                if customer_code:
                    subscription.provider_customer_code = (
                        customer_code
                    )

                if subscription_code:
                    subscription.provider_subscription_code = (
                        subscription_code
                    )

                subscription.billing_provider = (
                    BusinessSubscription.PROVIDER_PAYSTACK
                )
                subscription.save()

        elif event_type == "invoice.payment_failed":
            subscription = (
                find_subscription_for_event(
                    data
                )
            )

            if subscription:
                subscription.status = (
                    BusinessSubscription.STATUS_PAST_DUE
                )
                subscription.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

        elif event_type == "subscription.not_renew":
            subscription = (
                find_subscription_for_event(
                    data
                )
            )

            if subscription:
                # Keep already-paid access until the current period
                # ends. Paystack later sends subscription.disable.
                subscription.cancelled_at = (
                    timezone.now()
                )
                subscription.save(
                    update_fields=[
                        "cancelled_at",
                        "updated_at",
                    ]
                )

        elif event_type == "subscription.disable":
            subscription = (
                find_subscription_for_event(
                    data
                )
            )

            if subscription:
                now = timezone.now()
                subscription.status = (
                    BusinessSubscription.STATUS_CANCELLED
                )
                subscription.cancelled_at = now

                if (
                    not subscription.current_period_end
                    or subscription.current_period_end > now
                ):
                    subscription.current_period_end = now

                subscription.save(
                    update_fields=[
                        "status",
                        "cancelled_at",
                        "current_period_end",
                        "updated_at",
                    ]
                )

    except Exception:
        logger.exception(
            "Failed processing Paystack webhook event=%s",
            event_type,
        )

        # Non-200 causes Paystack to retry the event.
        return HttpResponse(
            status=500
        )

    return HttpResponse(
        status=200
    )