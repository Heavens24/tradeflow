import json
import os
from datetime import date
from decimal import Decimal
from urllib.parse import quote as urlquote

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.http import JsonResponse
from django.urls import reverse

from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from .forms import (
    BusinessForm,
    CustomerForm,
    InvoiceForm,
    InvoiceItemFormSet,
    JobForm,
    PaymentForm,
    QuoteForm,
    QuoteItemFormSet,
    TradeFlowLoginForm,
    TradeFlowRegistrationForm,
)

from .models import (
    AIUsage,
    Business,
    BusinessPublicProfile,
    BusinessReview,
    BusinessSubscription,
    Customer,
    Invoice,
    Job,
    Payment,
    Quote,
    QuoteRequest,
)

from .public_views import make_review_token


# =========================================================
# HELPERS
# =========================================================


def get_user_business(user):
    """
    Return the business owned by the logged-in user.

    TradeFlow currently uses one Business per Django user.
    """
    return Business.objects.filter(
        owner=user
    ).first()


def sync_invoice_status(invoice):
    """
    Keep invoice status synchronized with payments and due dates.

    Rules:
    - Cancelled invoices stay cancelled.
    - Fully paid invoices become Paid.
    - Any unpaid balance after the due date becomes Overdue.
    - Partial payments before the due date become Part Paid.
    - If a previously payment-derived/overdue status no longer applies
      and no payment remains, the invoice returns to Sent.
    - Draft and Sent invoices that are not overdue remain unchanged.
    """

    if invoice.status == Invoice.STATUS_CANCELLED:
        return

    total = invoice.total
    amount_paid = invoice.amount_paid
    balance_due = invoice.balance_due
    today = timezone.localdate()

    if (
        total > Decimal("0.00")
        and balance_due <= Decimal("0.00")
    ):
        new_status = Invoice.STATUS_PAID

    elif (
        invoice.due_date
        and invoice.due_date < today
        and balance_due > Decimal("0.00")
    ):
        new_status = Invoice.STATUS_OVERDUE

    elif amount_paid > Decimal("0.00"):
        new_status = Invoice.STATUS_PART_PAID

    elif invoice.status in [
        Invoice.STATUS_PAID,
        Invoice.STATUS_PART_PAID,
        Invoice.STATUS_OVERDUE,
    ]:
        new_status = Invoice.STATUS_SENT

    else:
        return

    if invoice.status != new_status:
        invoice.status = new_status

        invoice.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )


def get_statement_date_filter(request):
    """
    Read and validate optional customer statement date filters.
    Query parameters: from_date=YYYY-MM-DD and to_date=YYYY-MM-DD.
    """
    from_date_text = request.GET.get("from_date", "").strip()
    to_date_text = request.GET.get("to_date", "").strip()

    from_date = None
    to_date = None
    error = ""

    if from_date_text:
        try:
            from_date = date.fromisoformat(from_date_text)
        except ValueError:
            error = "Please enter a valid From date."

    if not error and to_date_text:
        try:
            to_date = date.fromisoformat(to_date_text)
        except ValueError:
            error = "Please enter a valid To date."

    if (
        not error
        and from_date
        and to_date
        and from_date > to_date
    ):
        error = "The From date cannot be later than the To date."

    if error:
        from_date = None
        to_date = None

    return {
        "from_date_text": from_date_text,
        "to_date_text": to_date_text,
        "from_date": from_date,
        "to_date": to_date,
        "error": error,
        "has_filter": bool(from_date or to_date),
    }


def apply_date_range(queryset, field_name, from_date=None, to_date=None):
    """
    Apply an optional inclusive date range to a queryset.
    """
    filters = {}

    if from_date:
        filters[f"{field_name}__gte"] = from_date

    if to_date:
        filters[f"{field_name}__lte"] = to_date

    if filters:
        queryset = queryset.filter(**filters)

    return queryset


# =========================================================
# AUTHENTICATION
# =========================================================


def home(request):
    """Send visitors to the correct TradeFlow starting page."""
    if not request.user.is_authenticated:
        return redirect("core:login")

    if not get_user_business(request.user):
        return redirect("core:business_setup")

    return redirect("core:dashboard")


def register_view(request):
    """Create a new TradeFlow user and begin business setup."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = TradeFlowRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            auth_login(request, user)

            messages.success(
                request,
                "Your TradeFlow account was created successfully. "
                "Now set up your business profile.",
            )

            return redirect("core:business_setup")
    else:
        form = TradeFlowRegistrationForm()

    return render(
        request,
        "core/register.html",
        {"form": form},
    )


def login_view(request):
    """Sign an existing TradeFlow user in."""
    if request.user.is_authenticated:
        if get_user_business(request.user):
            return redirect("core:dashboard")

        return redirect("core:business_setup")

    next_url = (
        request.POST.get("next")
        or request.GET.get("next")
        or ""
    )

    if request.method == "POST":
        form = TradeFlowLoginForm(
            request=request,
            data=request.POST,
        )

        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)

            messages.success(
                request,
                "Welcome back to TradeFlow.",
            )

            if (
                next_url
                and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                )
            ):
                return redirect(next_url)

            if not get_user_business(user):
                return redirect("core:business_setup")

            return redirect("core:dashboard")
    else:
        form = TradeFlowLoginForm(request=request)

    return render(
        request,
        "core/login.html",
        {
            "form": form,
            "next": next_url,
        },
    )


@login_required
def logout_view(request):
    """Confirm logout on GET and sign out on POST."""
    if request.method == "POST":
        auth_logout(request)

        messages.success(
            request,
            "You have been logged out successfully.",
        )

        return redirect("core:login")

    return render(
        request,
        "core/logout_confirm.html",
    )


# =========================================================
# DASHBOARD
# =========================================================


@login_required
def dashboard(request):
    business = get_user_business(
        request.user
    )

    customer_count = 0
    quote_count = 0
    new_quote_requests_count = 0
    active_job_count = 0

    overdue_invoice_count = 0
    overdue_amount = Decimal("0.00")

    outstanding_amount = Decimal("0.00")
    paid_this_month = Decimal("0.00")

    if business:
        customer_count = Customer.objects.filter(
            business=business
        ).count()

        quote_count = Quote.objects.filter(
            business=business
        ).count()

        new_quote_requests_count = QuoteRequest.objects.filter(
            business=business,
            status="new",
        ).count()

        active_job_count = (
            Job.objects.filter(
                business=business
            )
            .exclude(
                status__in=[
                    Job.STATUS_COMPLETED,
                    Job.STATUS_CANCELLED,
                ]
            )
            .count()
        )

        invoices = list(
            Invoice.objects.filter(
                business=business
            )
            .exclude(
                status=Invoice.STATUS_CANCELLED
            )
            .prefetch_related(
                "items",
                "payments",
            )
        )

        for invoice in invoices:
            sync_invoice_status(invoice)

        outstanding_amount = sum(
            (
                invoice.balance_due
                for invoice in invoices
            ),
            Decimal("0.00"),
        )

        overdue_invoices = [
            invoice
            for invoice in invoices
            if (
                invoice.status
                == Invoice.STATUS_OVERDUE
                and invoice.balance_due
                > Decimal("0.00")
            )
        ]

        overdue_invoice_count = len(
            overdue_invoices
        )

        overdue_amount = sum(
            (
                invoice.balance_due
                for invoice in overdue_invoices
            ),
            Decimal("0.00"),
        )

        today = timezone.localdate()

        payment_total = (
            Payment.objects.filter(
                invoice__business=business,
                payment_date__year=today.year,
                payment_date__month=today.month,
            )
            .aggregate(
                total=Sum("amount")
            )
            .get("total")
        )

        paid_this_month = (
            payment_total
            or Decimal("0.00")
        )

    context = {
        "business": business,
        "customer_count": customer_count,
        "quote_count": quote_count,
        "new_quote_requests_count": new_quote_requests_count,
        "active_job_count": active_job_count,
        "overdue_invoice_count": overdue_invoice_count,
        "overdue_amount": overdue_amount,
        "outstanding_amount": outstanding_amount,
        "paid_this_month": paid_this_month,
    }

    return render(
        request,
        "core/dashboard.html",
        context,
    )


# =========================================================
# BUSINESS
# =========================================================


@login_required
def business_setup(request):
    business = get_user_business(
        request.user
    )

    if request.method == "POST":
        form = BusinessForm(
            request.POST,
            instance=business,
        )

        if form.is_valid():
            saved_business = form.save(
                commit=False
            )

            saved_business.owner = (
                request.user
            )

            saved_business.save()

            messages.success(
                request,
                "Business profile saved successfully.",
            )

            return redirect(
                "core:dashboard"
            )

    else:
        form = BusinessForm(
            instance=business
        )

    context = {
        "form": form,
        "business": business,
    }

    return render(
        request,
        "core/business_setup.html",
        context,
    )


# =========================================================
# CUSTOMERS
# =========================================================


@login_required
def customer_list(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    customers = Customer.objects.filter(
        business=business
    )

    if query:
        customers = customers.filter(
            Q(name__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(address__icontains=query)
        )

    context = {
        "business": business,
        "customers": customers,
        "query": query,
    }

    return render(
        request,
        "core/customers.html",
        context,
    )


@login_required
def customer_create(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    if request.method == "POST":
        form = CustomerForm(
            request.POST
        )

        if form.is_valid():
            customer = form.save(
                commit=False
            )

            customer.business = business
            customer.save()

            messages.success(
                request,
                "Customer added successfully.",
            )

            return redirect(
                "core:customer_list"
            )

    else:
        form = CustomerForm()

    context = {
        "form": form,
        "business": business,
        "page_title": "Add Customer",
        "button_text": "Save Customer",
    }

    return render(
        request,
        "core/customer_form.html",
        context,
    )


@login_required
def customer_edit(
    request,
    customer_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    customer = get_object_or_404(
        Customer,
        id=customer_id,
        business=business,
    )

    if request.method == "POST":
        form = CustomerForm(
            request.POST,
            instance=customer,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Customer updated successfully.",
            )

            return redirect(
                "core:customer_list"
            )

    else:
        form = CustomerForm(
            instance=customer
        )

    context = {
        "form": form,
        "business": business,
        "customer": customer,
        "page_title": "Edit Customer",
        "button_text": "Save Changes",
    }

    return render(
        request,
        "core/customer_form.html",
        context,
    )


@login_required
def customer_delete(
    request,
    customer_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    customer = get_object_or_404(
        Customer,
        id=customer_id,
        business=business,
    )

    if request.method == "POST":
        customer_name = customer.name

        customer.delete()

        messages.success(
            request,
            f"{customer_name} was deleted successfully.",
        )

        return redirect(
            "core:customer_list"
        )

    context = {
        "business": business,
        "customer": customer,
    }

    return render(
        request,
        "core/customer_confirm_delete.html",
        context,
    )


@login_required
def customer_statement(
    request,
    customer_id,
):
    business = get_user_business(request.user)

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )
        return redirect("core:business_setup")

    customer = get_object_or_404(
        Customer,
        id=customer_id,
        business=business,
    )

    date_filter = get_statement_date_filter(request)
    from_date = date_filter["from_date"]
    to_date = date_filter["to_date"]

    all_invoices = list(
        Invoice.objects.filter(
            business=business,
            customer=customer,
        )
        .select_related("job", "quote")
        .prefetch_related("items", "payments")
    )

    for invoice in all_invoices:
        sync_invoice_status(invoice)

    current_balance = sum(
        (
            invoice.balance_due
            for invoice in all_invoices
            if invoice.status != Invoice.STATUS_CANCELLED
        ),
        Decimal("0.00"),
    )

    overdue_balance = sum(
        (
            invoice.balance_due
            for invoice in all_invoices
            if invoice.status == Invoice.STATUS_OVERDUE
        ),
        Decimal("0.00"),
    )

    quotes_queryset = (
        Quote.objects.filter(
            business=business,
            customer=customer,
        )
        .prefetch_related("items")
    )
    quotes_queryset = apply_date_range(
        quotes_queryset,
        "issue_date",
        from_date,
        to_date,
    )
    quotes = list(quotes_queryset)

    jobs_queryset = (
        Job.objects.filter(
            business=business,
            customer=customer,
        )
        .select_related("quote")
    )
    jobs_queryset = apply_date_range(
        jobs_queryset,
        "start_date",
        from_date,
        to_date,
    )
    jobs = list(jobs_queryset)

    invoices_queryset = (
        Invoice.objects.filter(
            business=business,
            customer=customer,
        )
        .select_related("job", "quote")
        .prefetch_related("items", "payments")
    )
    invoices_queryset = apply_date_range(
        invoices_queryset,
        "issue_date",
        from_date,
        to_date,
    )
    invoices = list(invoices_queryset)

    for invoice in invoices:
        sync_invoice_status(invoice)

    payments_queryset = (
        Payment.objects.filter(
            invoice__business=business,
            invoice__customer=customer,
        )
        .select_related("invoice")
    )
    payments_queryset = apply_date_range(
        payments_queryset,
        "payment_date",
        from_date,
        to_date,
    )
    payments = list(
        payments_queryset.order_by(
            "-payment_date",
            "-created_at",
        )
    )

    total_quoted = sum(
        (quote.total for quote in quotes),
        Decimal("0.00"),
    )

    total_invoiced = sum(
        (
            invoice.total
            for invoice in invoices
            if invoice.status != Invoice.STATUS_CANCELLED
        ),
        Decimal("0.00"),
    )

    total_paid = sum(
        (payment.amount for payment in payments),
        Decimal("0.00"),
    )

    context = {
        "business": business,
        "customer": customer,
        "quotes": quotes,
        "jobs": jobs,
        "invoices": invoices,
        "payments": payments,
        "total_quoted": total_quoted,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "current_balance": current_balance,
        "overdue_balance": overdue_balance,
        "from_date": date_filter["from_date_text"],
        "to_date": date_filter["to_date_text"],
        "has_date_filter": date_filter["has_filter"],
        "date_filter_error": date_filter["error"],
    }

    return render(
        request,
        "core/customer_statement.html",
        context,
    )


@login_required
def customer_statement_print(
    request,
    customer_id,
):
    business = get_user_business(request.user)

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )
        return redirect("core:business_setup")

    customer = get_object_or_404(
        Customer,
        id=customer_id,
        business=business,
    )

    date_filter = get_statement_date_filter(request)
    from_date = date_filter["from_date"]
    to_date = date_filter["to_date"]

    all_invoices = list(
        Invoice.objects.filter(
            business=business,
            customer=customer,
        )
        .select_related("job", "quote")
        .prefetch_related("items", "payments")
    )

    for invoice in all_invoices:
        sync_invoice_status(invoice)

    current_balance = sum(
        (
            invoice.balance_due
            for invoice in all_invoices
            if invoice.status != Invoice.STATUS_CANCELLED
        ),
        Decimal("0.00"),
    )

    overdue_balance = sum(
        (
            invoice.balance_due
            for invoice in all_invoices
            if invoice.status == Invoice.STATUS_OVERDUE
        ),
        Decimal("0.00"),
    )

    invoices_queryset = (
        Invoice.objects.filter(
            business=business,
            customer=customer,
        )
        .select_related("job", "quote")
        .prefetch_related("items", "payments")
    )
    invoices_queryset = apply_date_range(
        invoices_queryset,
        "issue_date",
        from_date,
        to_date,
    )
    invoices = list(invoices_queryset)

    for invoice in invoices:
        sync_invoice_status(invoice)

    payments_queryset = (
        Payment.objects.filter(
            invoice__business=business,
            invoice__customer=customer,
        )
        .select_related("invoice")
    )
    payments_queryset = apply_date_range(
        payments_queryset,
        "payment_date",
        from_date,
        to_date,
    )
    payments = list(
        payments_queryset.order_by(
            "-payment_date",
            "-created_at",
        )
    )

    total_invoiced = sum(
        (
            invoice.total
            for invoice in invoices
            if invoice.status != Invoice.STATUS_CANCELLED
        ),
        Decimal("0.00"),
    )

    total_paid = sum(
        (payment.amount for payment in payments),
        Decimal("0.00"),
    )

    context = {
        "business": business,
        "customer": customer,
        "invoices": invoices,
        "payments": payments,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "current_balance": current_balance,
        "overdue_balance": overdue_balance,
        "statement_date": timezone.localdate(),
        "from_date": date_filter["from_date_text"],
        "to_date": date_filter["to_date_text"],
        "has_date_filter": date_filter["has_filter"],
        "date_filter_error": date_filter["error"],
    }

    return render(
        request,
        "core/customer_statement_print.html",
        context,
    )



# =========================================================
# SIMPLE AI QUOTE / INVOICE ASSISTANT
# =========================================================


@login_required
@require_POST
def ai_document_assistant(request):
    """
    Generate review-first quote or invoice suggestions.

    AI access is subscription-gated and every outbound OpenAI
    attempt is reserved against a hard per-period allowance before
    the external API call is made.
    """

    AI_PRO_REQUEST_LIMIT = 100

    business = get_user_business(request.user)

    if not business:
        return JsonResponse(
            {
                "success": False,
                "error": "Please create your business profile first.",
            },
            status=400,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "error": "Invalid request data."},
            status=400,
        )

    document_type = str(
        payload.get("document_type", "quote")
    ).strip().lower()
    description = str(payload.get("description", "")).strip()

    if document_type not in {"quote", "invoice"}:
        return JsonResponse(
            {
                "success": False,
                "error": "Document type must be quote or invoice.",
            },
            status=400,
        )

    if not description:
        return JsonResponse(
            {
                "success": False,
                "error": "Describe the work before asking the AI assistant.",
            },
            status=400,
        )

    if len(description) > 3000:
        return JsonResponse(
            {
                "success": False,
                "error": "Please keep the work description under 3000 characters.",
            },
            status=400,
        )

    model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

    # Reserve one request while locking the subscription row. The
    # reservation happens before OpenAI is called, so simultaneous
    # requests cannot bypass the hard allowance.
    with transaction.atomic():
        subscription, _ = BusinessSubscription.objects.select_for_update().get_or_create(
            business=business
        )

        if not subscription.has_ai_access:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "AI Assistant is available on an active TradeFlow Pro plan. "
                        "Your current subscription does not have AI access."
                    ),
                    "code": "ai_subscription_required",
                },
                status=403,
            )

        if subscription.status == BusinessSubscription.STATUS_TRIALING:
            period_start = subscription.started_at or subscription.created_at
            period_end = subscription.trial_ends_at
        else:
            period_start = subscription.current_period_start
            period_end = subscription.current_period_end

        if not period_start or not period_end:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Your subscription billing period is incomplete. "
                        "Please contact TradeFlow support before using AI."
                    ),
                    "code": "ai_period_unavailable",
                },
                status=403,
            )

        used_requests = AIUsage.objects.filter(
            business=business,
            period_start=period_start,
            period_end=period_end,
        ).count()

        if used_requests >= AI_PRO_REQUEST_LIMIT:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "You have reached the AI request limit for this "
                        "subscription period."
                    ),
                    "code": "ai_limit_reached",
                    "limit": AI_PRO_REQUEST_LIMIT,
                    "used": used_requests,
                    "remaining": 0,
                },
                status=429,
            )

        usage_record = AIUsage.objects.create(
            business=business,
            subscription=subscription,
            document_type=document_type,
            model_name=model_name,
            status=AIUsage.STATUS_RESERVED,
            period_start=period_start,
            period_end=period_end,
        )

        used_after_reservation = used_requests + 1

    business_name = business.name or "the business"

    prompt = (
        "You are the Simple AI Quote / Invoice Assistant "
        "inside TradeFlow, a South African small-business "
        "operating system.\n\n"
        f"Business: {business_name}\n"
        f"Document type: {document_type}\n\n"
        "The business owner described the work as:\n"
        f"{description}\n\n"
        "Return a practical draft with 1 to 4 line items. "
        "Use South African rand pricing. Prices are only "
        "suggestions for the owner to review and edit. "
        "Do not claim that a suggested price is a verified "
        "supplier price. If the description does not give "
        "enough information for a sensible price, use 0 "
        "for that unit price rather than inventing certainty. "
        "Use short, professional line-item descriptions. "
        "Quantity must be greater than zero. "
        "Recommend VAT only when it is reasonable for the "
        "business owner to consider it; the owner will make "
        "the final decision. Notes should be concise and "
        "customer-friendly."
    )

    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number", "exclusiveMinimum": 0},
                        "unit_price": {"type": "number", "minimum": 0},
                    },
                    "required": ["description", "quantity", "unit_price"],
                    "additionalProperties": False,
                },
            },
            "apply_vat": {"type": "boolean"},
            "notes": {"type": "string"},
        },
        "required": ["items", "apply_vat", "notes"],
        "additionalProperties": False,
    }

    def mark_failed(category):
        AIUsage.objects.filter(pk=usage_record.pk).update(
            status=AIUsage.STATUS_FAILED,
            error_category=category,
            completed_at=timezone.now(),
        )

    try:
        client = OpenAI()
        response = client.responses.create(
            model=model_name,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "tradeflow_document_draft",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        suggestion = json.loads(response.output_text)

        response_usage = getattr(response, "usage", None)
        input_tokens = getattr(response_usage, "input_tokens", None)
        output_tokens = getattr(response_usage, "output_tokens", None)
        total_tokens = getattr(response_usage, "total_tokens", None)

        AIUsage.objects.filter(pk=usage_record.pk).update(
            status=AIUsage.STATUS_SUCCEEDED,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            completed_at=timezone.now(),
        )

    except AuthenticationError:
        mark_failed("authentication")
        return JsonResponse(
            {
                "success": False,
                "error": "TradeFlow AI is temporarily unavailable.",
            },
            status=503,
        )

    except PermissionDeniedError:
        mark_failed("permission_denied")
        return JsonResponse(
            {
                "success": False,
                "error": "TradeFlow AI is temporarily unavailable.",
            },
            status=503,
        )

    except RateLimitError as exc:
        error_text = str(exc).lower()
        category = (
            "provider_quota"
            if (
                "insufficient_quota" in error_text
                or "current quota" in error_text
                or "billing" in error_text
            )
            else "provider_rate_limit"
        )
        mark_failed(category)
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "TradeFlow AI is temporarily busy or unavailable. "
                    "Please try again later."
                ),
            },
            status=503,
        )

    except BadRequestError:
        mark_failed("bad_request")
        return JsonResponse(
            {
                "success": False,
                "error": "The AI request could not be processed.",
            },
            status=400,
        )

    except APIConnectionError:
        mark_failed("connection")
        return JsonResponse(
            {
                "success": False,
                "error": "TradeFlow could not connect to the AI service.",
            },
            status=503,
        )

    except APIStatusError:
        mark_failed("api_status")
        return JsonResponse(
            {
                "success": False,
                "error": "The AI service returned an error. Please try again.",
            },
            status=502,
        )

    except Exception:
        mark_failed("unexpected")
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "The AI assistant could not generate a suggestion right now. "
                    "Please try again."
                ),
            },
            status=502,
        )

    return JsonResponse(
        {
            "success": True,
            "suggestion": suggestion,
            "notice": (
                "AI prices are suggestions only. Review all quantities, "
                "prices, VAT and notes before saving."
            ),
            "usage": {
                "limit": AI_PRO_REQUEST_LIMIT,
                "used": used_after_reservation,
                "remaining": max(AI_PRO_REQUEST_LIMIT - used_after_reservation, 0),
                "period_end": period_end.isoformat(),
            },
        }
    )

# =========================================================
# QUOTES
# =========================================================


@login_required
def quote_list(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    quotes = (
        Quote.objects.filter(
            business=business
        )
        .select_related(
            "customer"
        )
        .prefetch_related(
            "items"
        )
    )

    if query:
        quotes = quotes.filter(
            Q(
                quote_number__icontains=query
            )
            | Q(
                customer__name__icontains=query
            )
            | Q(
                customer__phone__icontains=query
            )
        )

    context = {
        "business": business,
        "quotes": quotes,
        "query": query,
    }

    return render(
        request,
        "core/quotes.html",
        context,
    )


@login_required
def quote_create(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    if not Customer.objects.filter(
        business=business
    ).exists():

        messages.warning(
            request,
            "Add a customer before creating a quote.",
        )

        return redirect(
            "core:customer_create"
        )

    quote = Quote(
        business=business
    )

    if request.method == "POST":
        form = QuoteForm(
            request.POST,
            instance=quote,
            business=business,
        )

        formset = QuoteItemFormSet(
            request.POST,
            instance=quote,
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                quote = form.save(
                    commit=False
                )

                quote.business = business

                quote.customer = (
                    form.cleaned_data["customer"]
                )

                quote.status = (
                    form.cleaned_data["status"]
                )

                quote.issue_date = (
                    form.cleaned_data["issue_date"]
                )

                quote.expiry_date = (
                    form.cleaned_data["expiry_date"]
                )

                quote.apply_vat = (
                    form.cleaned_data["apply_vat"]
                )

                quote.notes = (
                    form.cleaned_data["notes"]
                )

                quote.save()

                formset.instance = quote
                formset.save()

            quote.refresh_from_db()

            messages.success(
                request,
                (
                    f"{quote.quote_number} "
                    "created successfully."
                ),
            )

            return redirect(
                "core:quote_detail",
                quote_id=quote.id,
            )

    else:
        form = QuoteForm(
            instance=quote,
            business=business,
        )

        formset = QuoteItemFormSet(
            instance=quote
        )

    context = {
        "business": business,
        "form": form,
        "formset": formset,
        "page_title": "Create Quote",
        "button_text": "Create Quote",
    }

    return render(
        request,
        "core/quote_form.html",
        context,
    )


@login_required
def quote_detail(
    request,
    quote_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote = get_object_or_404(
        Quote.objects
        .select_related(
            "customer",
            "business",
        )
        .prefetch_related(
            "items"
        ),
        id=quote_id,
        business=business,
    )

    existing_job = Job.objects.filter(
        quote=quote,
        business=business,
    ).first()

    context = {
        "business": business,
        "quote": quote,
        "existing_job": existing_job,
    }

    return render(
        request,
        "core/quote_detail.html",
        context,
    )


# =========================================================
# PRINT QUOTE
# =========================================================


@login_required
def quote_print(
    request,
    quote_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote = get_object_or_404(
        Quote.objects
        .select_related(
            "business",
            "customer",
        )
        .prefetch_related(
            "items"
        ),
        id=quote_id,
        business=business,
    )

    context = {
        "business": business,
        "quote": quote,
    }

    return render(
        request,
        "core/quote_print.html",
        context,
    )


@login_required
def quote_edit(
    request,
    quote_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote = get_object_or_404(
        Quote,
        id=quote_id,
        business=business,
    )

    if request.method == "POST":

        form = QuoteForm(
            request.POST,
            instance=quote,
            business=business,
        )

        formset = QuoteItemFormSet(
            request.POST,
            instance=quote,
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                updated_quote = form.save(
                    commit=False
                )

                updated_quote.business = business

                updated_quote.customer = (
                    form.cleaned_data["customer"]
                )

                updated_quote.status = (
                    form.cleaned_data["status"]
                )

                updated_quote.issue_date = (
                    form.cleaned_data["issue_date"]
                )

                updated_quote.expiry_date = (
                    form.cleaned_data["expiry_date"]
                )

                updated_quote.apply_vat = (
                    form.cleaned_data["apply_vat"]
                )

                updated_quote.notes = (
                    form.cleaned_data["notes"]
                )

                updated_quote.save()

                formset.instance = updated_quote
                formset.save()

            updated_quote.refresh_from_db()

            messages.success(
                request,
                (
                    f"{updated_quote.quote_number} "
                    "updated successfully. "
                    f"Status: "
                    f"{updated_quote.get_status_display()}."
                ),
            )

            return redirect(
                "core:quote_detail",
                quote_id=updated_quote.id,
            )

    else:
        form = QuoteForm(
            instance=quote,
            business=business,
        )

        formset = QuoteItemFormSet(
            instance=quote
        )

    context = {
        "business": business,
        "quote": quote,
        "form": form,
        "formset": formset,
        "page_title": (
            f"Edit {quote.quote_number}"
        ),
        "button_text": "Save Changes",
    }

    return render(
        request,
        "core/quote_form.html",
        context,
    )


@login_required
def quote_delete(
    request,
    quote_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote = get_object_or_404(
        Quote,
        id=quote_id,
        business=business,
    )

    if request.method == "POST":
        quote_number = (
            quote.quote_number
        )

        quote.delete()

        messages.success(
            request,
            (
                f"{quote_number} "
                "was deleted successfully."
            ),
        )

        return redirect(
            "core:quote_list"
        )

    context = {
        "business": business,
        "quote": quote,
    }

    return render(
        request,
        "core/quote_confirm_delete.html",
        context,
    )


# =========================================================
# JOBS
# =========================================================


@login_required
def job_list(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    jobs = (
        Job.objects.filter(
            business=business
        )
        .select_related(
            "customer",
            "quote",
        )
    )

    if query:
        jobs = jobs.filter(
            Q(
                job_number__icontains=query
            )
            | Q(
                title__icontains=query
            )
            | Q(
                customer__name__icontains=query
            )
            | Q(
                customer__phone__icontains=query
            )
        )

    if status_filter:
        jobs = jobs.filter(
            status=status_filter
        )

    context = {
        "business": business,
        "jobs": jobs,
        "query": query,
        "status_filter": status_filter,
        "status_choices": Job.STATUS_CHOICES,
    }

    return render(
        request,
        "core/jobs.html",
        context,
    )


@login_required
def job_create(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    if not Customer.objects.filter(
        business=business
    ).exists():

        messages.warning(
            request,
            "Add a customer before creating a job.",
        )

        return redirect(
            "core:customer_create"
        )

    if request.method == "POST":
        form = JobForm(
            request.POST,
            business=business,
        )

        if form.is_valid():
            job = form.save(
                commit=False
            )

            job.business = business
            job.save()

            job.refresh_from_db()

            messages.success(
                request,
                (
                    f"{job.job_number} "
                    "created successfully."
                ),
            )

            return redirect(
                "core:job_detail",
                job_id=job.id,
            )

    else:
        form = JobForm(
            business=business
        )

    context = {
        "business": business,
        "form": form,
        "page_title": "Create Job",
        "button_text": "Create Job",
        "from_quote": False,
    }

    return render(
        request,
        "core/job_form.html",
        context,
    )


@login_required
def quote_to_job(
    request,
    quote_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote = get_object_or_404(
        Quote.objects
        .select_related(
            "customer"
        )
        .prefetch_related(
            "items"
        ),
        id=quote_id,
        business=business,
    )

    existing_job = Job.objects.filter(
        quote=quote,
        business=business,
    ).first()

    if existing_job:

        messages.info(
            request,
            (
                f"{quote.quote_number} "
                "has already been converted to "
                f"{existing_job.job_number}."
            ),
        )

        return redirect(
            "core:job_detail",
            job_id=existing_job.id,
        )

    if quote.status != Quote.STATUS_ACCEPTED:

        messages.warning(
            request,
            (
                "Only an accepted quote can "
                "be converted into a job."
            ),
        )

        return redirect(
            "core:quote_detail",
            quote_id=quote.id,
        )

    item_descriptions = []

    for item in quote.items.all():

        item_descriptions.append(
            (
                f"{item.description} "
                f"(Qty: {item.quantity})"
            )
        )

    description = "\n".join(
        item_descriptions
    )

    job = Job(
        business=business,
        customer=quote.customer,
        quote=quote,
        title="",
        description=description,
        status=Job.STATUS_SCHEDULED,
    )

    if request.method == "POST":

        form = JobForm(
            request.POST,
            instance=job,
            business=business,
            from_quote=True,
        )

        if form.is_valid():

            with transaction.atomic():

                job = form.save(
                    commit=False
                )

                job.business = business
                job.customer = quote.customer
                job.quote = quote

                job.save()

            job.refresh_from_db()

            messages.success(
                request,
                (
                    f"{quote.quote_number} "
                    f"converted to "
                    f"{job.job_number} successfully."
                ),
            )

            return redirect(
                "core:job_detail",
                job_id=job.id,
            )

    else:

        form = JobForm(
            instance=job,
            business=business,
            from_quote=True,
        )

    context = {
        "business": business,
        "form": form,
        "quote": quote,
        "page_title": (
            f"Convert "
            f"{quote.quote_number} "
            f"to Job"
        ),
        "button_text": "Create Job",
        "from_quote": True,
    }

    return render(
        request,
        "core/job_form.html",
        context,
    )


@login_required
def job_detail(
    request,
    job_id,
):
    """
    Display one TradeFlow job.

    Completed jobs also expose the secure customer-review
    request workflow to the business owner.

    Review links are generated with the same signed-token
    system used by the public customer review endpoint.
    """

    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    job = get_object_or_404(
        Job.objects.select_related(
            "customer",
            "quote",
            "business",
        ),
        id=job_id,
        business=business,
    )

    existing_invoice = (
        Invoice.objects.filter(
            job=job,
            business=business,
        )
        .select_related(
            "customer",
            "quote",
        )
        .first()
    )

    existing_review = (
        BusinessReview.objects
        .filter(
            job=job,
            business=business,
        )
        .first()
    )

    public_profile = (
        BusinessPublicProfile.objects
        .filter(
            business=business,
            public_profile_enabled=True,
        )
        .first()
    )

    review_url = ""
    review_whatsapp_url = ""

    if (
        job.status == Job.STATUS_COMPLETED
        and not existing_review
    ):
        review_token = make_review_token(
            job
        )

        review_path = reverse(
            "core:public_review_submit",
            kwargs={
                "token": review_token,
            },
        )

        review_url = (
            request.build_absolute_uri(
                review_path
            )
        )

        phone_digits = "".join(
            character
            for character
            in (
                job.customer.phone
                or ""
            )
            if character.isdigit()
        )

        if (
            phone_digits.startswith("0")
            and len(phone_digits) >= 10
        ):
            phone_digits = (
                "27"
                + phone_digits[1:]
            )

        review_message = (
            f"Hi {job.customer.name}, "
            f"thank you for choosing "
            f"{business.name}. "
            f"We'd appreciate your feedback "
            f"on the work completed for "
            f"{job.job_number}.\n\n"
            f"Please leave your TradeFlow "
            f"review here:\n"
            f"{review_url}"
        )

        encoded_message = urlquote(
            review_message
        )

        if phone_digits:
            review_whatsapp_url = (
                "https://wa.me/"
                f"{phone_digits}"
                "?text="
                f"{encoded_message}"
            )
        else:
            review_whatsapp_url = (
                "https://wa.me/"
                "?text="
                f"{encoded_message}"
            )

    context = {
        "business": business,
        "job": job,
        "existing_invoice": existing_invoice,
        "existing_review": existing_review,
        "public_profile": public_profile,
        "review_url": review_url,
        "review_whatsapp_url": (
            review_whatsapp_url
        ),
    }

    return render(
        request,
        "core/job_detail.html",
        context,
    )


@login_required
@require_POST
def job_status_action(
    request,
    job_id,
    action,
):
    """
    Move a job through the controlled TradeFlow lifecycle.

    Allowed transitions:

    Scheduled -> In Progress
    In Progress -> Completed

    The job must belong to the authenticated business.
    """

    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    job = get_object_or_404(
        Job,
        id=job_id,
        business=business,
    )

    if action == "start":

        if (
            job.status
            != Job.STATUS_SCHEDULED
        ):
            messages.warning(
                request,
                (
                    f"{job.job_number} cannot be "
                    "started from its current status."
                ),
            )

            return redirect(
                "core:job_detail",
                job_id=job.id,
            )

        job.status = (
            Job.STATUS_IN_PROGRESS
        )

        job.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                f"{job.job_number} is now "
                "In Progress."
            ),
        )

        return redirect(
            "core:job_detail",
            job_id=job.id,
        )

    if action == "complete":

        if (
            job.status
            != Job.STATUS_IN_PROGRESS
        ):
            messages.warning(
                request,
                (
                    f"{job.job_number} cannot be "
                    "completed from its current status."
                ),
            )

            return redirect(
                "core:job_detail",
                job_id=job.id,
            )

        job.status = (
            Job.STATUS_COMPLETED
        )

        job.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        messages.success(
            request,
            (
                f"{job.job_number} has been "
                "marked as Completed."
            ),
        )

        return redirect(
            "core:job_detail",
            job_id=job.id,
        )

    messages.error(
        request,
        "Invalid job action.",
    )

    return redirect(
        "core:job_detail",
        job_id=job.id,
    )


@login_required
def job_edit(
    request,
    job_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    job = get_object_or_404(
        Job.objects.select_related(
            "customer",
            "quote",
        ),
        id=job_id,
        business=business,
    )

    from_quote = bool(
        job.quote
    )

    if request.method == "POST":

        form = JobForm(
            request.POST,
            instance=job,
            business=business,
            from_quote=from_quote,
        )

        if form.is_valid():

            with transaction.atomic():

                updated_job = form.save(
                    commit=False
                )

                updated_job.business = business

                if updated_job.quote:
                    updated_job.customer = (
                        updated_job.quote.customer
                    )

                updated_job.save()

            updated_job.refresh_from_db()

            messages.success(
                request,
                (
                    f"{updated_job.job_number} "
                    "updated successfully."
                ),
            )

            return redirect(
                "core:job_detail",
                job_id=updated_job.id,
            )

    else:

        form = JobForm(
            instance=job,
            business=business,
            from_quote=from_quote,
        )

    context = {
        "business": business,
        "job": job,
        "form": form,
        "page_title": (
            f"Edit {job.job_number}"
        ),
        "button_text": "Save Changes",
        "from_quote": from_quote,
    }

    return render(
        request,
        "core/job_form.html",
        context,
    )


@login_required
def job_delete(
    request,
    job_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    job = get_object_or_404(
        Job,
        id=job_id,
        business=business,
    )

    if request.method == "POST":

        job_number = (
            job.job_number
        )

        job.delete()

        messages.success(
            request,
            (
                f"{job_number} "
                "was deleted successfully."
            ),
        )

        return redirect(
            "core:job_list"
        )

    context = {
        "business": business,
        "job": job,
    }

    return render(
        request,
        "core/job_confirm_delete.html",
        context,
    )


# =========================================================
# INVOICES
# =========================================================


@login_required
def invoice_list(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    query = request.GET.get(
        "q",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    invoices = (
        Invoice.objects.filter(
            business=business
        )
        .select_related(
            "customer",
            "job",
            "quote",
        )
        .prefetch_related(
            "items",
            "payments",
        )
    )

    for invoice in invoices:
        sync_invoice_status(invoice)

    invoices = (
        Invoice.objects.filter(
            business=business
        )
        .select_related(
            "customer",
            "job",
            "quote",
        )
        .prefetch_related(
            "items",
            "payments",
        )
    )

    if query:
        invoices = invoices.filter(
            Q(
                invoice_number__icontains=query
            )
            | Q(
                customer__name__icontains=query
            )
            | Q(
                customer__phone__icontains=query
            )
        )

    if status_filter:
        invoices = invoices.filter(
            status=status_filter
        )

    context = {
        "business": business,
        "invoices": invoices,
        "query": query,
        "status_filter": status_filter,
        "status_choices": Invoice.STATUS_CHOICES,
    }

    return render(
        request,
        "core/invoices.html",
        context,
    )


@login_required
def invoice_create(request):
    business = get_user_business(
        request.user
    )

    if not business:
        messages.warning(
            request,
            "Please create your business profile first.",
        )

        return redirect(
            "core:business_setup"
        )

    if not Customer.objects.filter(
        business=business
    ).exists():

        messages.warning(
            request,
            "Add a customer before creating an invoice.",
        )

        return redirect(
            "core:customer_create"
        )

    invoice = Invoice(
        business=business
    )

    if request.method == "POST":

        form = InvoiceForm(
            request.POST,
            instance=invoice,
            business=business,
        )

        formset = InvoiceItemFormSet(
            request.POST,
            instance=invoice,
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                invoice = form.save(
                    commit=False
                )

                invoice.business = business
                invoice.save()

                formset.instance = invoice
                formset.save()

            invoice.refresh_from_db()

            messages.success(
                request,
                (
                    f"{invoice.invoice_number} "
                    "created successfully."
                ),
            )

            return redirect(
                "core:invoice_detail",
                invoice_id=invoice.id,
            )

    else:

        form = InvoiceForm(
            instance=invoice,
            business=business,
        )

        formset = InvoiceItemFormSet(
            instance=invoice
        )

    context = {
        "business": business,
        "form": form,
        "formset": formset,
        "page_title": "Create Invoice",
        "button_text": "Create Invoice",
        "from_job": False,
    }

    return render(
        request,
        "core/invoice_form.html",
        context,
    )


@login_required
def job_to_invoice(
    request,
    job_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    job = get_object_or_404(
        Job.objects
        .select_related(
            "customer",
            "quote",
        )
        .prefetch_related(
            "quote__items"
        ),
        id=job_id,
        business=business,
    )

    existing_invoice = Invoice.objects.filter(
        business=business,
        job=job,
    ).first()

    if existing_invoice:

        messages.info(
            request,
            (
                f"{job.job_number} already has "
                f"{existing_invoice.invoice_number}."
            ),
        )

        return redirect(
            "core:invoice_detail",
            invoice_id=existing_invoice.id,
        )

    if (
        job.status
        != Job.STATUS_COMPLETED
    ):
        messages.warning(
            request,
            (
                f"{job.job_number} must be "
                "completed before an invoice "
                "can be created."
            ),
        )

        return redirect(
            "core:job_detail",
            job_id=job.id,
        )

    invoice = Invoice(
        business=business,
        customer=job.customer,
        job=job,
        quote=job.quote,
        status=Invoice.STATUS_DRAFT,
        due_date=job.due_date,
    )

    if job.quote:
        invoice.apply_vat = (
            job.quote.apply_vat
        )

    initial_items = []

    if job.quote:

        for quote_item in job.quote.items.all():

            initial_items.append(
                {
                    "description": (
                        quote_item.description
                    ),
                    "quantity": (
                        quote_item.quantity
                    ),
                    "unit_price": (
                        quote_item.unit_price
                    ),
                }
            )

    else:

        initial_items.append(
            {
                "description": job.title,
                "quantity": 1,
                "unit_price": 0,
            }
        )

    if request.method == "POST":

        form = InvoiceForm(
            request.POST,
            instance=invoice,
            business=business,
            from_job=True,
        )

        formset = InvoiceItemFormSet(
            request.POST,
            instance=invoice,
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                invoice = form.save(
                    commit=False
                )

                invoice.business = business
                invoice.customer = job.customer
                invoice.job = job
                invoice.quote = job.quote

                invoice.save()

                formset.instance = invoice
                formset.save()

            invoice.refresh_from_db()

            messages.success(
                request,
                (
                    f"{job.job_number} converted "
                    f"to {invoice.invoice_number} "
                    "successfully."
                ),
            )

            return redirect(
                "core:invoice_detail",
                invoice_id=invoice.id,
            )

    else:

        form = InvoiceForm(
            instance=invoice,
            business=business,
            from_job=True,
        )

        formset = InvoiceItemFormSet(
            instance=invoice,
            initial=initial_items,
        )

    context = {
        "business": business,
        "job": job,
        "form": form,
        "formset": formset,
        "page_title": (
            f"Create Invoice from "
            f"{job.job_number}"
        ),
        "button_text": "Create Invoice",
        "from_job": True,
    }

    return render(
        request,
        "core/invoice_form.html",
        context,
    )


@login_required
def invoice_detail(
    request,
    invoice_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    invoice = get_object_or_404(
        Invoice.objects
        .select_related(
            "business",
            "customer",
            "job",
            "quote",
        )
        .prefetch_related(
            "items",
            "payments",
        ),
        id=invoice_id,
        business=business,
    )

    sync_invoice_status(
        invoice
    )

    invoice.refresh_from_db()

    context = {
        "business": business,
        "invoice": invoice,
    }

    return render(
        request,
        "core/invoice_detail.html",
        context,
    )


# =========================================================
# PRINT INVOICE
# =========================================================


@login_required
def invoice_print(
    request,
    invoice_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    invoice = get_object_or_404(
        Invoice.objects
        .select_related(
            "business",
            "customer",
            "job",
            "quote",
        )
        .prefetch_related(
            "items",
            "payments",
        ),
        id=invoice_id,
        business=business,
    )

    sync_invoice_status(
        invoice
    )

    invoice.refresh_from_db()

    context = {
        "business": business,
        "invoice": invoice,
    }

    return render(
        request,
        "core/invoice_print.html",
        context,
    )


@login_required
def invoice_edit(
    request,
    invoice_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "job",
            "customer",
        ),
        id=invoice_id,
        business=business,
    )

    from_job = bool(
        invoice.job
    )

    if request.method == "POST":

        form = InvoiceForm(
            request.POST,
            instance=invoice,
            business=business,
            from_job=from_job,
        )

        formset = InvoiceItemFormSet(
            request.POST,
            instance=invoice,
        )

        if (
            form.is_valid()
            and formset.is_valid()
        ):

            with transaction.atomic():

                updated_invoice = form.save(
                    commit=False
                )

                updated_invoice.business = business

                if updated_invoice.job:
                    updated_invoice.customer = (
                        updated_invoice.job.customer
                    )

                updated_invoice.save()

                formset.instance = updated_invoice
                formset.save()

            updated_invoice.refresh_from_db()

            sync_invoice_status(
                updated_invoice
            )

            messages.success(
                request,
                (
                    f"{updated_invoice.invoice_number} "
                    "updated successfully."
                ),
            )

            return redirect(
                "core:invoice_detail",
                invoice_id=updated_invoice.id,
            )

    else:

        form = InvoiceForm(
            instance=invoice,
            business=business,
            from_job=from_job,
        )

        formset = InvoiceItemFormSet(
            instance=invoice
        )

    context = {
        "business": business,
        "invoice": invoice,
        "form": form,
        "formset": formset,
        "page_title": (
            f"Edit {invoice.invoice_number}"
        ),
        "button_text": "Save Changes",
        "from_job": from_job,
    }

    return render(
        request,
        "core/invoice_form.html",
        context,
    )


@login_required
def invoice_delete(
    request,
    invoice_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        business=business,
    )

    if request.method == "POST":

        invoice_number = (
            invoice.invoice_number
        )

        invoice.delete()

        messages.success(
            request,
            (
                f"{invoice_number} "
                "was deleted successfully."
            ),
        )

        return redirect(
            "core:invoice_list"
        )

    context = {
        "business": business,
        "invoice": invoice,
    }

    return render(
        request,
        "core/invoice_confirm_delete.html",
        context,
    )


# =========================================================
# PAYMENTS
# =========================================================


@login_required
def payment_list(request):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    payments = (
        Payment.objects.filter(
            invoice__business=business
        )
        .select_related(
            "invoice",
            "invoice__customer",
        )
    )

    context = {
        "business": business,
        "payments": payments,
    }

    return render(
        request,
        "core/payments.html",
        context,
    )


@login_required
def payment_create(
    request,
    invoice_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    invoice = get_object_or_404(
        Invoice.objects
        .select_related(
            "customer"
        )
        .prefetch_related(
            "items",
            "payments",
        ),
        id=invoice_id,
        business=business,
    )

    if (
        invoice.status
        == Invoice.STATUS_CANCELLED
    ):
        messages.warning(
            request,
            (
                "Payments cannot be recorded "
                "against a cancelled invoice."
            ),
        )

        return redirect(
            "core:invoice_detail",
            invoice_id=invoice.id,
        )

    if invoice.balance_due <= Decimal("0.00"):

        messages.info(
            request,
            (
                f"{invoice.invoice_number} "
                "has already been paid in full."
            ),
        )

        return redirect(
            "core:invoice_detail",
            invoice_id=invoice.id,
        )

    if request.method == "POST":

        form = PaymentForm(
            request.POST,
            invoice=invoice,
        )

        if form.is_valid():

            with transaction.atomic():

                payment = form.save(
                    commit=False
                )

                payment.invoice = invoice
                payment.save()

                sync_invoice_status(
                    invoice
                )

            messages.success(
                request,
                (
                    f"Payment of "
                    f"R{payment.amount:.2f} "
                    "recorded successfully."
                ),
            )

            return redirect(
                "core:invoice_detail",
                invoice_id=invoice.id,
            )

    else:

        form = PaymentForm(
            invoice=invoice,
            initial={
                "amount": (
                    invoice.balance_due
                ),
            },
        )

    context = {
        "business": business,
        "invoice": invoice,
        "form": form,
    }

    return render(
        request,
        "core/payment_form.html",
        context,
    )


@login_required
def payment_delete(
    request,
    payment_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    payment = get_object_or_404(
        Payment.objects.select_related(
            "invoice"
        ),
        id=payment_id,
        invoice__business=business,
    )

    invoice = payment.invoice

    if request.method == "POST":

        payment.delete()

        invoice.refresh_from_db()

        sync_invoice_status(
            invoice
        )

        messages.success(
            request,
            "Payment deleted successfully.",
        )

        return redirect(
            "core:invoice_detail",
            invoice_id=invoice.id,
        )

    context = {
        "business": business,
        "payment": payment,
        "invoice": invoice,
    }

    return render(
        request,
        "core/payment_confirm_delete.html",
        context,
    )