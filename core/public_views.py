from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
)
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
# OWNER PUBLIC PROFILE SETTINGS
# =========================================================


@login_required
def public_profile_settings(request):
    """
    Allow a TradeFlow business owner to configure their
    public mini-page.

    This page is private and requires authentication.
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