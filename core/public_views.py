from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
)
from django.core import signing
from django.db import IntegrityError
from django.db.models import (
    Avg,
    Q,
)
from django.http import Http404
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .models import (
    Business,
    BusinessPublicProfile,
    BusinessReview,
    BusinessSubscription,
    Job,
)

from .public_forms import (
    PublicBusinessProfileForm,
    PublicBusinessReviewForm,
    PublicQuoteRequestForm,
)


# =========================================================
# REVIEW SECURITY
# =========================================================


REVIEW_TOKEN_SALT = (
    "tradeflow.business-review"
)

REVIEW_TOKEN_MAX_AGE = (
    60
    * 60
    * 24
    * 90
)


# =========================================================
# MARKETPLACE REPUTATION
# =========================================================


MARKETPLACE_PRIOR_RATING = 4.0

MARKETPLACE_PRIOR_WEIGHT = 5


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


def business_has_marketplace_access(business):
    """
    Return True only when the business currently has
    TradeFlow Pro access.

    Marketplace publication is a Pro feature.

    BusinessSubscription.has_pro_access remains the single
    source of truth for paid access, including billing-period
    and subscription-status rules.
    """

    try:
        subscription = business.subscription
    except BusinessSubscription.DoesNotExist:
        return False

    return subscription.has_pro_access


def make_review_token(job):
    """
    Create a signed review token for one TradeFlow job.

    The token contains only the internal job ID and is signed
    with Django's SECRET_KEY.

    A customer cannot safely change the job ID without
    invalidating the token.
    """

    return signing.dumps(
        {
            "job_id": job.pk,
        },
        salt=REVIEW_TOKEN_SALT,
    )


def get_job_from_review_token(token):
    """
    Resolve and validate a signed review token.

    Review links expire after REVIEW_TOKEN_MAX_AGE.

    Only completed jobs are returned.
    """

    try:

        payload = signing.loads(
            token,
            salt=REVIEW_TOKEN_SALT,
            max_age=REVIEW_TOKEN_MAX_AGE,
        )

    except signing.SignatureExpired:

        raise Http404(
            (
                "This review link has expired."
            )
        )

    except signing.BadSignature:

        raise Http404(
            (
                "This review link is invalid."
            )
        )


    job_id = payload.get(
        "job_id"
    )


    if not job_id:

        raise Http404(
            (
                "This review link is invalid."
            )
        )


    return get_object_or_404(
        Job.objects.select_related(
            "business",
            "customer",
        ),
        pk=job_id,
        status=Job.STATUS_COMPLETED,
    )


def marketplace_reputation(
    average_rating,
    review_count,
):
    """
    Return a weighted marketplace reputation score.

    A business with only one review should not automatically
    outrank a business that has consistently strong feedback
    across many completed TradeFlow jobs.

    The score therefore shrinks small review samples toward
    a neutral marketplace prior.

    Businesses with no approved reviews receive a score of
    zero rather than receiving an artificial public rating.
    """

    if (
        not review_count
        or average_rating is None
    ):
        return 0.0


    weighted_total = (
        float(average_rating)
        * review_count
    )

    prior_total = (
        MARKETPLACE_PRIOR_RATING
        * MARKETPLACE_PRIOR_WEIGHT
    )


    reputation = (
        weighted_total
        + prior_total
    ) / (
        review_count
        + MARKETPLACE_PRIOR_WEIGHT
    )


    return round(
        reputation,
        4,
    )


def marketplace_search_score(
    profile,
    query,
):
    """
    Give matching marketplace businesses a lightweight
    relevance score.

    This is used only after the normal database search has
    already removed unrelated businesses.

    Search relevance stays ahead of reputation whenever a
    customer explicitly enters a search query.
    """

    if not query:
        return 0


    query_value = (
        query
        .strip()
        .lower()
    )


    if not query_value:
        return 0


    business_name = (
        profile.business.name
        or ""
    ).lower()

    city = (
        profile.business.city
        or ""
    ).lower()

    headline = (
        profile.headline
        or ""
    ).lower()

    description = (
        profile.description
        or ""
    ).lower()

    services = (
        profile.services
        or ""
    ).lower()


    score = 0


    # -----------------------------------------------------
    # BUSINESS NAME
    # -----------------------------------------------------

    if business_name == query_value:

        score += 100

    elif business_name.startswith(
        query_value
    ):

        score += 70

    elif query_value in business_name:

        score += 50


    # -----------------------------------------------------
    # PUBLIC PROFILE CONTENT
    # -----------------------------------------------------

    if query_value in headline:

        score += 35


    if query_value in services:

        score += 30


    if query_value in description:

        score += 20


    if query_value in city:

        score += 10


    return score


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

    Marketplace ordering combines:

    - customer search relevance
    - TradeFlow verification
    - approved-review reputation
    - approved review volume
    - emergency availability

    Only approved reviews contribute to public marketplace
    ratings and ranking.
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
            "business",
            "business__subscription",
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
    # MARKETPLACE REPUTATION
    # =====================================================

    ranked_profiles = []


    for profile in profiles:

        if not business_has_marketplace_access(
            profile.business
        ):
            continue

        review_summary = (
            BusinessReview.objects
            .filter(
                business=profile.business,
                status=(
                    BusinessReview
                    .STATUS_APPROVED
                ),
            )
            .aggregate(
                average_rating=Avg(
                    "rating"
                ),
            )
        )


        review_count = (
            BusinessReview.objects
            .filter(
                business=profile.business,
                status=(
                    BusinessReview
                    .STATUS_APPROVED
                ),
            )
            .count()
        )


        average_rating = (
            review_summary.get(
                "average_rating"
            )
        )


        profile.marketplace_review_count = (
            review_count
        )


        profile.marketplace_average_rating = (
            average_rating
        )


        profile.marketplace_reputation_score = (
            marketplace_reputation(
                average_rating,
                review_count,
            )
        )


        profile.marketplace_search_score = (
            marketplace_search_score(
                profile,
                query,
            )
        )


        ranked_profiles.append(
            profile
        )


    # =====================================================
    # MARKETPLACE ORDERING
    # =====================================================

    if query:

        ranked_profiles.sort(
            key=lambda profile: (
                -profile.marketplace_search_score,
                -int(
                    bool(
                        profile.is_verified
                    )
                ),
                -profile.marketplace_reputation_score,
                -profile.marketplace_review_count,
                -int(
                    bool(
                        profile.emergency_callouts
                    )
                ),
                (
                    profile.business.name
                    or ""
                ).lower(),
            )
        )

    else:

        ranked_profiles.sort(
            key=lambda profile: (
                -int(
                    bool(
                        profile.is_verified
                    )
                ),
                -profile.marketplace_reputation_score,
                -profile.marketplace_review_count,
                -int(
                    bool(
                        profile.emergency_callouts
                    )
                ),
                (
                    profile.business.name
                    or ""
                ).lower(),
            )
        )


    # =====================================================
    # FILTER OPTIONS
    # =====================================================

    city_choices = sorted(
        {
            profile.business.city
            for profile in ranked_profiles
            if profile.business.city
        }
    )


    context = {
        "profiles": ranked_profiles,
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


    if not business_has_marketplace_access(
        business
    ):

        messages.info(
            request,
            (
                "Marketplace publishing is available "
                "with TradeFlow Pro. Upgrade to Pro "
                "to publish and manage your public "
                "business profile."
            ),
        )

        return redirect(
            "core:subscription"
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

    Only approved customer reviews are exposed publicly.

    Pending and rejected reviews remain private to the
    TradeFlow moderation workflow.
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


    if not business_has_marketplace_access(
        business
    ):
        raise Http404(
            "This business profile is not currently available."
        )


    # =====================================================
    # APPROVED CUSTOMER REVIEWS ONLY
    # =====================================================

    approved_reviews = (
        BusinessReview.objects
        .filter(
            business=business,
            status=(
                BusinessReview
                .STATUS_APPROVED
            ),
        )
        .select_related(
            "job",
            "customer",
        )
        .order_by(
            "-created_at"
        )
    )


    review_summary = (
        approved_reviews.aggregate(
            average_rating=Avg(
                "rating"
            )
        )
    )


    average_rating = (
        review_summary.get(
            "average_rating"
        )
    )


    review_count = (
        approved_reviews.count()
    )


    context = {
        "business": business,
        "profile": profile,
        "services": profile.service_list,
        "approved_reviews": approved_reviews,
        "average_rating": average_rating,
        "review_count": review_count,
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


    if not business_has_marketplace_access(
        business
    ):
        raise Http404(
            (
                "This business is not currently accepting "
                "TradeFlow Marketplace quote requests."
            )
        )


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

    if not business_has_marketplace_access(
        profile.business
    ):
        raise Http404(
            "This business profile is not currently available."
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


# =========================================================
# PUBLIC CUSTOMER REVIEW
# =========================================================


def public_review_submit(
    request,
    token,
):
    """
    Allow a customer to submit one review for a completed
    TradeFlow job using a signed review link.

    Security rules:

    - the customer does not choose a job
    - the customer does not choose a business
    - the customer does not choose customer identity
    - the token determines the completed job
    - the model derives business/customer from that job
    - only one review is allowed per job
    - every new review begins as Pending Review
    """

    job = get_job_from_review_token(
        token
    )

    business = job.business
    customer = job.customer


    profile = (
        BusinessPublicProfile.objects
        .filter(
            business=business
        )
        .first()
    )


    existing_review = (
        BusinessReview.objects
        .filter(
            job=job
        )
        .first()
    )


    # -----------------------------------------------------
    # ONE REVIEW PER JOB
    # -----------------------------------------------------

    if existing_review:

        return render(
            request,
            "core/review_success.html",
            {
                "business": business,
                "customer": customer,
                "job": job,
                "profile": profile,
                "review": existing_review,
                "already_submitted": True,
            },
        )


    # -----------------------------------------------------
    # SUBMIT REVIEW
    # -----------------------------------------------------

    if request.method == "POST":

        form = PublicBusinessReviewForm(
            request.POST
        )

        if form.is_valid():

            review = form.save(
                commit=False
            )

            review.job = job

            review.status = (
                BusinessReview
                .STATUS_PENDING
            )


            try:

                review.save()

            except IntegrityError:

                existing_review = (
                    BusinessReview.objects
                    .filter(
                        job=job
                    )
                    .first()
                )

                return render(
                    request,
                    "core/review_success.html",
                    {
                        "business": business,
                        "customer": customer,
                        "job": job,
                        "profile": profile,
                        "review": existing_review,
                        "already_submitted": True,
                    },
                )


            return redirect(
                "core:public_review_success",
                token=token,
            )

    else:

        form = (
            PublicBusinessReviewForm()
        )


    context = {
        "business": business,
        "customer": customer,
        "job": job,
        "profile": profile,
        "form": form,
    }


    return render(
        request,
        "core/review_submit.html",
        context,
    )


# =========================================================
# PUBLIC CUSTOMER REVIEW SUCCESS
# =========================================================


def public_review_success(
    request,
    token,
):
    """
    Confirmation page shown after a customer review is
    submitted.

    The same signed token is validated again before any
    review/job information is displayed.
    """

    job = get_job_from_review_token(
        token
    )

    review = get_object_or_404(
        BusinessReview,
        job=job,
    )

    profile = (
        BusinessPublicProfile.objects
        .filter(
            business=job.business
        )
        .first()
    )


    return render(
        request,
        "core/review_success.html",
        {
            "business": (
                job.business
            ),
            "customer": (
                job.customer
            ),
            "job": job,
            "profile": profile,
            "review": review,
            "already_submitted": False,
        },
    )