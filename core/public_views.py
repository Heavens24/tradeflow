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
# HELPERS
# =========================================================


def get_user_business(user):
    """
    Return the business belonging to the authenticated user.
    """

    return Business.objects.filter(
        owner=user
    ).first()


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