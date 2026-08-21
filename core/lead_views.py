from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
)
from django.db import transaction
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.views.decorators.http import (
    require_POST,
)

from .models import (
    Business,
    Customer,
    Quote,
    QuoteItem,
    QuoteRequest,
)


# =========================================================
# HELPERS
# =========================================================


def get_user_business(user):
    return Business.objects.filter(
        owner=user
    ).first()


# =========================================================
# QUOTE REQUEST INBOX
# =========================================================


@login_required
def quote_request_list(request):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    requests = QuoteRequest.objects.filter(
        business=business
    )

    if status_filter:
        requests = requests.filter(
            status=status_filter
        )

    return render(
        request,
        "core/quote_requests.html",
        {
            "business": business,
            "quote_requests": requests,
            "status_filter": status_filter,
            "status_choices": (
                QuoteRequest.STATUS_CHOICES
            ),
        },
    )


# =========================================================
# QUOTE REQUEST DETAIL
# =========================================================


@login_required
def quote_request_detail(
    request,
    request_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote_request = get_object_or_404(
        QuoteRequest.objects.select_related(
            "converted_customer",
            "converted_quote",
        ),
        id=request_id,
        business=business,
    )

    return render(
        request,
        "core/quote_request_detail.html",
        {
            "business": business,
            "quote_request": quote_request,
        },
    )


# =========================================================
# MARK CONTACTED
# =========================================================


@login_required
@require_POST
def quote_request_contacted(
    request,
    request_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote_request = get_object_or_404(
        QuoteRequest,
        id=request_id,
        business=business,
    )

    if (
        quote_request.status
        != QuoteRequest.STATUS_CONVERTED
    ):

        quote_request.status = (
            QuoteRequest.STATUS_CONTACTED
        )

        quote_request.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        messages.success(
            request,
            "Quote request marked as contacted.",
        )

    return redirect(
        "core:quote_request_detail",
        request_id=quote_request.id,
    )


# =========================================================
# CONVERT REQUEST → CUSTOMER + QUOTE
# =========================================================


@login_required
@require_POST
def quote_request_convert(
    request,
    request_id,
):
    business = get_user_business(
        request.user
    )

    if not business:
        return redirect(
            "core:business_setup"
        )

    quote_request = get_object_or_404(
        QuoteRequest,
        id=request_id,
        business=business,
    )


    if quote_request.converted_quote:

        messages.info(
            request,
            (
                "This request has already been "
                "converted to a quotation."
            ),
        )

        return redirect(
            "core:quote_detail",
            quote_id=(
                quote_request
                .converted_quote_id
            ),
        )


    with transaction.atomic():

        # -------------------------------------------------
        # MATCH EXISTING CUSTOMER
        # -------------------------------------------------

        customer_query = Q(
            phone__iexact=quote_request.phone
        )

        if quote_request.email:

            customer_query |= Q(
                email__iexact=(
                    quote_request.email
                )
            )


        customer = (
            Customer.objects.filter(
                customer_query,
                business=business,
            )
            .first()
        )


        # -------------------------------------------------
        # CREATE CUSTOMER IF REQUIRED
        # -------------------------------------------------

        if not customer:

            customer = Customer.objects.create(
                business=business,
                name=quote_request.customer_name,
                phone=quote_request.phone,
                email=quote_request.email,
                address=quote_request.location,
                notes=(
                    "Created automatically from "
                    "a TradeFlow public quote request."
                ),
            )


        # -------------------------------------------------
        # CREATE REAL TRADEFLOW QUOTE
        # -------------------------------------------------

        quote = Quote.objects.create(
            business=business,
            customer=customer,
            status=Quote.STATUS_DRAFT,
            notes=(
                "Created from public quote request.\n\n"
                f"Customer request:\n"
                f"{quote_request.description}"
            ),
        )


        # The owner reviews and prices this line item.
        QuoteItem.objects.create(
            quote=quote,
            description=(
                quote_request.description[:255]
            ),
            quantity=1,
            unit_price=0,
        )


        quote_request.status = (
            QuoteRequest.STATUS_CONVERTED
        )

        quote_request.converted_customer = (
            customer
        )

        quote_request.converted_quote = quote

        quote_request.save(
            update_fields=[
                "status",
                "converted_customer",
                "converted_quote",
                "updated_at",
            ]
        )


    messages.success(
        request,
        (
            "Quote request converted successfully. "
            "Review the quotation and enter the "
            "correct prices before sending it."
        ),
    )


    return redirect(
        "core:quote_edit",
        quote_id=quote.id,
    )