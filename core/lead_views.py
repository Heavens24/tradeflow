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
    """
    Return the business belonging to the authenticated user.
    """

    return Business.objects.filter(
        owner=user
    ).first()


def find_matching_customer(
    business,
    quote_request,
):
    """
    Safely look for an existing customer.

    A contact detail alone is not enough to match a person.

    We require the customer's name to match AND at least
    one contact field to match.

    This prevents a reused/shared phone number or email
    address from attaching a quote request to the wrong
    customer.
    """

    customer_name = (
        quote_request.customer_name
        or ""
    ).strip()

    phone = (
        quote_request.phone
        or ""
    ).strip()

    email = (
        quote_request.email
        or ""
    ).strip()


    if not customer_name:
        return None


    contact_query = Q()


    if phone:
        contact_query |= Q(
            phone__iexact=phone
        )


    if email:
        contact_query |= Q(
            email__iexact=email
        )


    if not phone and not email:
        return None


    return (
        Customer.objects.filter(
            business=business,
            name__iexact=customer_name,
        )
        .filter(
            contact_query
        )
        .first()
    )


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


    quote_requests = (
        QuoteRequest.objects.filter(
            business=business
        )
        .select_related(
            "converted_customer",
            "converted_quote",
        )
    )


    if status_filter:
        quote_requests = (
            quote_requests.filter(
                status=status_filter
            )
        )


    return render(
        request,
        "core/quote_requests.html",
        {
            "business": business,
            "quote_requests": quote_requests,
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
            (
                "Quote request marked "
                "as contacted."
            ),
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
    """
    Convert a public QuoteRequest into:

    1. An existing matching Customer, or a newly-created
       Customer.
    2. A normal TradeFlow draft Quote.
    3. A zero-priced QuoteItem containing the customer's
       original work description.

    Matching is deliberately strict so a phone number or
    email address cannot accidentally connect one person's
    enquiry to another customer's account.
    """

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


    # =====================================================
    # ALREADY CONVERTED
    # =====================================================

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


    # =====================================================
    # CONVERSION TRANSACTION
    # =====================================================

    with transaction.atomic():

        # -------------------------------------------------
        # FIND EXISTING CUSTOMER SAFELY
        # -------------------------------------------------

        customer = find_matching_customer(
            business,
            quote_request,
        )


        # -------------------------------------------------
        # CREATE CUSTOMER WHEN NO SAFE MATCH EXISTS
        # -------------------------------------------------

        if not customer:

            customer = Customer.objects.create(
                business=business,
                name=(
                    quote_request
                    .customer_name
                    .strip()
                ),
                phone=(
                    quote_request
                    .phone
                    .strip()
                ),
                email=(
                    quote_request
                    .email
                    .strip()
                ),
                address=(
                    quote_request
                    .location
                    .strip()
                ),
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
                "Created from public quote request."
                "\n\n"
                "Customer request:"
                "\n"
                f"{quote_request.description}"
            ),
        )


        # -------------------------------------------------
        # CREATE FIRST QUOTE ITEM
        # -------------------------------------------------
        #
        # Pricing stays at zero because the customer has
        # described the job but has not supplied a verified
        # business price.
        #
        # The business owner reviews and prices it manually.
        # -------------------------------------------------

        QuoteItem.objects.create(
            quote=quote,
            description=(
                quote_request
                .description[:255]
            ),
            quantity=1,
            unit_price=0,
        )


        # -------------------------------------------------
        # COMPLETE QUOTE REQUEST
        # -------------------------------------------------

        quote_request.status = (
            QuoteRequest.STATUS_CONVERTED
        )

        quote_request.converted_customer = (
            customer
        )

        quote_request.converted_quote = (
            quote
        )

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