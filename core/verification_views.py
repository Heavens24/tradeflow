from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
)
from django.shortcuts import (
    redirect,
    render,
)
from django.utils import timezone

from .models import (
    Business,
    BusinessVerification,
)

from .verification_forms import (
    BusinessVerificationForm,
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
# BUSINESS VERIFICATION
# =========================================================


@login_required
def business_verification(request):
    """
    Allow a business owner to submit or resubmit a TradeFlow
    verification application.

    Business owners cannot approve themselves.

    Pending applications cannot be changed until reviewed.

    Verified applications remain read-only unless TradeFlow
    later revokes or changes their verification status.

    Rejected applications can be updated and resubmitted.
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


    verification, created = (
        BusinessVerification.objects
        .get_or_create(
            business=business,
            defaults={
                "legal_business_name": (
                    business.name
                ),
                "registration_number": (
                    business.registration_number
                ),
                "contact_name": (
                    request.user.get_full_name()
                    or request.user.username
                ),
                "contact_email": (
                    business.email
                    or request.user.email
                ),
                "contact_phone": (
                    business.phone
                ),
            },
        )
    )


    # =====================================================
    # SUBMISSION
    # =====================================================

    if request.method == "POST":

        if (
            verification.status
            == BusinessVerification.STATUS_PENDING
        ):

            messages.warning(
                request,
                (
                    "Your verification application "
                    "is already pending review."
                ),
            )

            return redirect(
                "core:business_verification"
            )


        if (
            verification.status
            == BusinessVerification.STATUS_VERIFIED
        ):

            messages.info(
                request,
                (
                    "Your business is already verified."
                ),
            )

            return redirect(
                "core:business_verification"
            )


        form = BusinessVerificationForm(
            request.POST,
            instance=verification,
        )


        if form.is_valid():

            verification = form.save(
                commit=False
            )

            verification.business = business

            verification.status = (
                BusinessVerification.STATUS_PENDING
            )

            verification.submitted_at = (
                timezone.now()
            )

            verification.reviewed_at = None
            verification.reviewed_by = None
            verification.admin_notes = ""

            verification.save()


            messages.success(
                request,
                (
                    "Your business verification "
                    "application has been submitted "
                    "for review."
                ),
            )


            return redirect(
                "core:business_verification"
            )


    else:

        form = BusinessVerificationForm(
            instance=verification
        )


    context = {
        "business": business,
        "verification": verification,
        "form": form,
    }


    return render(
        request,
        "core/business_verification.html",
        context,
    )