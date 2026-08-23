from django import template

from core.models import (
    Business,
    BusinessPublicProfile,
    BusinessReview,
    BusinessVerification,
    QuoteRequest,
)


register = template.Library()


@register.simple_tag
def tradeflow_admin_stats():
    """
    Platform-level statistics displayed on the
    TradeFlow administration home page.
    """

    return {

        "businesses": (
            Business.objects.count()
        ),

        "published_profiles": (
            BusinessPublicProfile.objects
            .filter(
                public_profile_enabled=True
            )
            .count()
        ),

        "verified_businesses": (
            BusinessVerification.objects
            .filter(
                status=(
                    BusinessVerification
                    .STATUS_VERIFIED
                )
            )
            .count()
        ),

        "pending_verifications": (
            BusinessVerification.objects
            .filter(
                status=(
                    BusinessVerification
                    .STATUS_PENDING
                )
            )
            .count()
        ),

        "rejected_verifications": (
            BusinessVerification.objects
            .filter(
                status=(
                    BusinessVerification
                    .STATUS_REJECTED
                )
            )
            .count()
        ),

        "new_quote_requests": (
            QuoteRequest.objects
            .filter(
                status=QuoteRequest.STATUS_NEW
            )
            .count()
        ),

        "total_quote_requests": (
            QuoteRequest.objects.count()
        ),

        # =================================================
        # CUSTOMER REVIEWS
        # =================================================

        "pending_reviews": (
            BusinessReview.objects
            .filter(
                status=(
                    BusinessReview
                    .STATUS_PENDING
                )
            )
            .count()
        ),

        "approved_reviews": (
            BusinessReview.objects
            .filter(
                status=(
                    BusinessReview
                    .STATUS_APPROVED
                )
            )
            .count()
        ),

        "rejected_reviews": (
            BusinessReview.objects
            .filter(
                status=(
                    BusinessReview
                    .STATUS_REJECTED
                )
            )
            .count()
        ),

        "total_reviews": (
            BusinessReview.objects.count()
        ),

    }