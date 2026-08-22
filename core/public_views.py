from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
)
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .models import (
    Business,
    BusinessPublicProfile,
)

from .public_forms import (
    PublicBusinessProfileForm,
    PublicQuoteRequestForm,
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


# =========================================================
# PUBLIC MARKETPLACE
# =========================================================


def marketplace(request):
    """
    Public TradeFlow marketplace directory.

    Only businesses that have deliberately published their
    public TradeFlow profile are eligible to appear.

    Private operational information is never queried or
    exposed here.
    """

    query = request.GET.get(
        "q",
        "",
    ).strip()

    trade_category = request.GET.get(
        "trade",
        "",
    ).strip()

    city = request.GET.get(
        "city",
        "",
    ).strip()

    emergency_only = (
        request.GET.get(
            "emergency",
            "",
        )
        == "1"
    )

    verified_only = (
        request.GET.get(
            "verified",
            "",
        )
        == "1"
    )


    profiles = (
        BusinessPublicProfile.objects
        .filter(
            public_profile_enabled=True
        )
        .select_related(
            "business"
        )
    )


    # =====================================================
    # TEXT SEARCH
    # =====================================================

    if query:

        profiles = profiles.filter(
            Q(
                business__name__icontains=query
            )
            | Q(
                business__city__icontains=query
            )
            | Q(
                headline__icontains=query
            )
            | Q(
                description__icontains=query
            )
            | Q(
                services__icontains=query
            )
        )


    # =====================================================
    # STRUCTURED FILTERS
    # =====================================================

    if trade_category:

        profiles = profiles.filter(
            trade_category=trade_category
        )


    if city:

        profiles = profiles.filter(
            business__city__iexact=city
        )


    if emergency_only:

        profiles = profiles.filter(
            emergency_callouts=True
        )


    if verified_only:

        profiles = profiles.filter(
            is_verified=True
        )


    # =====================================================
    # FILTER OPTIONS
    # =====================================================

    city_choices = (
        BusinessPublicProfile.objects
        .filter(
            public_profile_enabled=True
        )
        .exclude(
            business__city=""
        )
        .values_list(
            "business__city",
            flat=True,
        )
        .distinct()
        .order_by(
            "business__city"
        )
    )


    context = {
        "profiles": profiles,
        "query": query,
        "trade_category": trade_category,
        "city": city,
        "emergency_only": emergency_only,
        "verified_only": verified_only,
        "trade_choices": (
            BusinessPublicProfile.TRADE_CHOICES
        ),
        "city_choices": city_choices,
    }


    return render(
        request,
        "core/marketplace.html",
        context,
    )


# =========================================================
# OWNER PUBLIC PROFILE SETTINGS
# =========================================================


@login_required
def public_profile_settings(request):
    """
    Allow a TradeFlow business owner to configure their
    public mini-page and marketplace listing.

    This page is private and requires authentication.

    Verification status is intentionally not controlled by
    this form.
    """

    business = get_user_business(
        request.user
    )

    if not business:

        messages.warning(
            request,
            (
                "Please create your business "
                "profile first."
            ),
        )

        return redirect(
            "core:business_setup"
        )


    profile, created = (
        BusinessPublicProfile.objects
        .get_or_create(
            business=business
        )
    )


    if request.method == "POST":

        form = (
            PublicBusinessProfileForm(
                request.POST,
                instance=profile,
            )
        )

        if form.is_valid():

            profile = form.save()

            messages.success(
                request,
                (
                    "Public business profile "
                    "updated successfully."
                ),
            )

            return redirect(
                "core:public_profile_settings"
            )

    else:

        form = (
            PublicBusinessProfileForm(
                instance=profile
            )
        )


    context = {
        "business": business,
        "profile": profile,
        "form": form,
    }


    return render(
        request,
        "core/public_business_settings.html",
        context,
    )


# =========================================================
# PUBLIC BUSINESS MINI-PAGE
# =========================================================


def public_business_profile(
    request,
    slug,
):
    """
    Public read-only business mini-page.
    """

    profile = get_object_or_404(
        BusinessPublicProfile.objects
        .select_related(
            "business"
        ),
        slug=slug,
        public_profile_enabled=True,
    )

    business = profile.business

    context = {
        "business": business,
        "profile": profile,
        "services": profile.service_list,
    }

    return render(
        request,
        "core/public_business.html",
        context,
    )


# =========================================================
# PUBLIC REQUEST QUOTE
# =========================================================


def public_quote_request(
    request,
    slug,
):
    """
    Public customer quote-request form.

    The URL determines the target business. Customers cannot
    submit the request to another business by manipulating
    form data.
    """

    profile = get_object_or_404(
        BusinessPublicProfile.objects
        .select_related(
            "business"
        ),
        slug=slug,
        public_profile_enabled=True,
    )

    business = profile.business


    if request.method == "POST":

        form = PublicQuoteRequestForm(
            request.POST
        )

        if form.is_valid():

            quote_request = form.save(
                commit=False
            )

            quote_request.business = (
                business
            )

            quote_request.save()

            return redirect(
                "core:public_quote_request_success",
                slug=profile.slug,
            )

    else:

        form = PublicQuoteRequestForm()


    context = {
        "business": business,
        "profile": profile,
        "form": form,
    }


    return render(
        request,
        "core/request_quote.html",
        context,
    )


def public_quote_request_success(
    request,
    slug,
):
    """
    Public confirmation page shown after a successful quote
    request.
    """

    profile = get_object_or_404(
        BusinessPublicProfile.objects
        .select_related(
            "business"
        ),
        slug=slug,
        public_profile_enabled=True,
    )

    return render(
        request,
        "core/request_quote_success.html",
        {
            "business": (
                profile.business
            ),
            "profile": profile,
        },
    )