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
from django.utils import timezone
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


def whatsapp_digits(value):
    """
    Convert a phone number into a WhatsApp-compatible
    digits-only value.

    South African local numbers beginning with 0 are
    converted to country code 27.
    """

    digits = "".join(
        character
        for character in (
            value
            or ""
        )
        if character.isdigit()
    )


    if digits.startswith("0"):
        digits = (
            "27"
            + digits[1:]
        )


    return digits


def calculate_lead_priority(
    quote_request,
):
    """
    Calculate a lightweight operational lead-priority score.

    No priority is stored in the database. It is calculated
    from existing TradeFlow data each time the inbox loads.

    Signals:
    - customer urgency
    - new vs contacted status
    - how recently the lead arrived
    - completeness of job/contact information

    Converted and closed enquiries are deliberately removed
    from active-priority competition.
    """

    # -----------------------------------------------------
    # ALREADY HANDLED
    # -----------------------------------------------------

    if quote_request.status in (
        QuoteRequest.STATUS_CONVERTED,
        QuoteRequest.STATUS_CLOSED,
    ):

        return {
            "score": 0,
            "label": "Handled",
            "level": "handled",
        }


    score = 0


    # -----------------------------------------------------
    # URGENCY
    # -----------------------------------------------------

    if (
        quote_request.urgency
        == QuoteRequest.URGENCY_URGENT
    ):

        score += 60

    elif (
        quote_request.urgency
        == QuoteRequest.URGENCY_SOON
    ):

        score += 30

    else:

        score += 10


    # -----------------------------------------------------
    # WORKFLOW STATUS
    # -----------------------------------------------------

    if (
        quote_request.status
        == QuoteRequest.STATUS_NEW
    ):

        score += 25

    elif (
        quote_request.status
        == QuoteRequest.STATUS_CONTACTED
    ):

        score += 5


    # -----------------------------------------------------
    # LEAD FRESHNESS
    # -----------------------------------------------------

    now = timezone.now()

    age = (
        now
        - quote_request.created_at
    )

    age_hours = (
        age.total_seconds()
        / 3600
    )


    if age_hours <= 6:

        score += 20

    elif age_hours <= 24:

        score += 15

    elif age_hours <= 72:

        score += 10

    elif age.days <= 7:

        score += 5


    # -----------------------------------------------------
    # INFORMATION COMPLETENESS
    # -----------------------------------------------------

    if (
        quote_request.email
        or ""
    ).strip():

        score += 3


    if (
        quote_request.location
        or ""
    ).strip():

        score += 3


    if len(
        (
            quote_request.description
            or ""
        ).strip()
    ) >= 40:

        score += 4


    # -----------------------------------------------------
    # PRIORITY LABEL
    # -----------------------------------------------------

    if score >= 90:

        label = "Urgent"
        level = "urgent"

    elif score >= 65:

        label = "High"
        level = "high"

    elif score >= 40:

        label = "Medium"
        level = "medium"

    else:

        label = "Standard"
        level = "standard"


    return {
        "score": score,
        "label": label,
        "level": level,
    }


def decorate_quote_request(
    quote_request,
):
    """
    Add presentation-only lead intelligence to a
    QuoteRequest instance.

    Nothing is written to the database.
    """

    priority = calculate_lead_priority(
        quote_request
    )


    quote_request.lead_priority_score = (
        priority["score"]
    )

    quote_request.lead_priority_label = (
        priority["label"]
    )

    quote_request.lead_priority_level = (
        priority["level"]
    )


    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    age = (
        timezone.now()
        - quote_request.created_at
    )


    if age.days > 0:

        quote_request.lead_age_label = (
            f"{age.days} day"
            f"{'s' if age.days != 1 else ''} ago"
        )

    else:

        hours = int(
            age.total_seconds()
            / 3600
        )

        if hours > 0:

            quote_request.lead_age_label = (
                f"{hours} hour"
                f"{'s' if hours != 1 else ''} ago"
            )

        else:

            minutes = max(
                0,
                int(
                    age.total_seconds()
                    / 60
                ),
            )

            quote_request.lead_age_label = (
                f"{minutes} minute"
                f"{'s' if minutes != 1 else ''} ago"
            )


    quote_request.whatsapp_digits = (
        whatsapp_digits(
            quote_request.phone
        )
    )


    return quote_request


# =========================================================
# QUOTE REQUEST INBOX
# =========================================================


@login_required
def quote_request_list(request):
    """
    Private lead inbox for one TradeFlow business.

    Results are scoped to the authenticated business and
    prioritized using existing quote-request information.
    """

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


    urgency_filter = request.GET.get(
        "urgency",
        "",
    ).strip()


    query = request.GET.get(
        "q",
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


    # =====================================================
    # FILTERS
    # =====================================================

    if status_filter:

        quote_requests = (
            quote_requests.filter(
                status=status_filter
            )
        )


    if urgency_filter:

        quote_requests = (
            quote_requests.filter(
                urgency=urgency_filter
            )
        )


    if query:

        quote_requests = (
            quote_requests.filter(
                Q(
                    customer_name__icontains=query
                )
                | Q(
                    phone__icontains=query
                )
                | Q(
                    email__icontains=query
                )
                | Q(
                    location__icontains=query
                )
                | Q(
                    description__icontains=query
                )
            )
        )


    # =====================================================
    # PRIORITY DECORATION
    # =====================================================

    quote_requests = [
        decorate_quote_request(
            item
        )
        for item
        in quote_requests
    ]


    # =====================================================
    # PRIORITY SORT
    # =====================================================

    quote_requests.sort(
        key=lambda item: (
            (
                item.status
                in (
                    QuoteRequest.STATUS_CONVERTED,
                    QuoteRequest.STATUS_CLOSED,
                )
            ),
            -item.lead_priority_score,
            -item.created_at.timestamp(),
        )
    )


    # =====================================================
    # INBOX SUMMARY
    # =====================================================

    business_requests = (
        QuoteRequest.objects.filter(
            business=business
        )
    )


    new_count = (
        business_requests.filter(
            status=QuoteRequest.STATUS_NEW
        )
        .count()
    )


    contacted_count = (
        business_requests.filter(
            status=(
                QuoteRequest
                .STATUS_CONTACTED
            )
        )
        .count()
    )


    urgent_count = (
        business_requests.filter(
            urgency=(
                QuoteRequest
                .URGENCY_URGENT
            ),
        )
        .exclude(
            status__in=[
                QuoteRequest.STATUS_CONVERTED,
                QuoteRequest.STATUS_CLOSED,
            ]
        )
        .count()
    )


    return render(
        request,
        "core/quote_requests.html",
        {
            "business": business,
            "quote_requests": quote_requests,
            "status_filter": status_filter,
            "urgency_filter": urgency_filter,
            "query": query,
            "status_choices": (
                QuoteRequest.STATUS_CHOICES
            ),
            "urgency_choices": (
                QuoteRequest.URGENCY_CHOICES
            ),
            "new_count": new_count,
            "contacted_count": contacted_count,
            "urgent_count": urgent_count,
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


    decorate_quote_request(
        quote_request
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
        not in (
            QuoteRequest.STATUS_CONVERTED,
            QuoteRequest.STATUS_CLOSED,
        )
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


    if (
        quote_request.status
        == QuoteRequest.STATUS_CLOSED
    ):

        messages.warning(
            request,
            (
                "This quote request is closed "
                "and cannot be converted."
            ),
        )

        return redirect(
            "core:quote_request_detail",
            request_id=quote_request.id,
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