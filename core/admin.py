from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Business,
    BusinessPublicProfile,
    BusinessReview,
    BusinessSubscription,
    BusinessVerification,
    Customer,
    Invoice,
    InvoiceItem,
    Job,
    Payment,
    Quote,
    QuoteItem,
    QuoteRequest,
)


# =========================================================
# TRADEFLOW ADMIN BRANDING
# =========================================================


admin.site.site_header = "TradeFlow Admin"
admin.site.site_title = "TradeFlow Admin"
admin.site.index_title = "Platform Operations"
admin.site.site_url = "/"


# =========================================================
# BUSINESS
# =========================================================


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "phone",
        "email",
        "city",
        "registration_number",
        "created_at",
    )

    search_fields = (
        "name",
        "owner__username",
        "phone",
        "email",
        "registration_number",
    )

    list_filter = (
        "city",
        "created_at",
    )

    ordering = (
        "name",
    )


# =========================================================
# BUSINESS SUBSCRIPTION
# =========================================================


@admin.register(BusinessSubscription)
class BusinessSubscriptionAdmin(
    admin.ModelAdmin
):
    """
    Platform subscription administration.

    TradeFlow administrators may manually activate paid
    access after EFT or manage provider-linked subscription
    records.

    Provider references are stored here so Paystack can be
    connected later without making Paystack the source of
    truth for application access.
    """

    list_display = (
        "business",
        "plan",
        "status_badge",
        "billing_provider",
        "access_badge",
        "current_period_end",
        "updated_at",
    )

    list_filter = (
        "plan",
        "status",
        "billing_provider",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "business__name",
        "business__owner__username",
        "business__email",
        "provider_customer_code",
        "provider_subscription_code",
        "provider_reference",
    )

    ordering = (
        "business__name",
    )

    list_per_page = 25

    readonly_fields = (
        "effective_status_display",
        "pro_access_display",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Business",
            {
                "fields": (
                    "business",
                ),
            },
        ),
        (
            "Subscription",
            {
                "fields": (
                    "plan",
                    "status",
                    "billing_provider",
                    "effective_status_display",
                    "pro_access_display",
                ),
            },
        ),
        (
            "Billing period",
            {
                "fields": (
                    "started_at",
                    "trial_ends_at",
                    "current_period_start",
                    "current_period_end",
                    "cancelled_at",
                ),
            },
        ),
        (
            "Payment provider",
            {
                "fields": (
                    "provider_customer_code",
                    "provider_subscription_code",
                    "provider_reference",
                ),
            },
        ),
        (
            "Internal notes",
            {
                "fields": (
                    "admin_notes",
                ),
            },
        ),
        (
            "System information",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(
        description="Status",
        ordering="status",
    )
    def status_badge(
        self,
        obj,
    ):
        effective_status = (
            obj.effective_status
        )

        if effective_status in (
            BusinessSubscription.STATUS_ACTIVE,
            BusinessSubscription.STATUS_TRIALING,
        ):
            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-success">'
                    '{}'
                    '</span>'
                ),
                obj.get_status_display(),
            )

        if (
            effective_status
            == BusinessSubscription.STATUS_PAST_DUE
        ):
            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-warning">'
                    '{}'
                    '</span>'
                ),
                "Past Due",
            )

        if effective_status in (
            BusinessSubscription.STATUS_CANCELLED,
            BusinessSubscription.STATUS_EXPIRED,
        ):
            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-danger">'
                    '{}'
                    '</span>'
                ),
                (
                    "Expired"
                    if effective_status
                    == BusinessSubscription.STATUS_EXPIRED
                    else "Cancelled"
                ),
            )

        return format_html(
            (
                '<span class="tf-status '
                'tf-status-muted">'
                '{}'
                '</span>'
            ),
            "Free",
        )

    @admin.display(
        description="Pro access",
        boolean=False,
    )
    def access_badge(
        self,
        obj,
    ):
        if obj.has_pro_access:
            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-success">'
                    '{}'
                    '</span>'
                ),
                "✓ Allowed",
            )

        return format_html(
            (
                '<span class="tf-status '
                'tf-status-muted">'
                '{}'
                '</span>'
            ),
            "No",
        )

    @admin.display(
        description="Effective status",
    )
    def effective_status_display(
        self,
        obj,
    ):
        labels = dict(
            BusinessSubscription.STATUS_CHOICES
        )

        return labels.get(
            obj.effective_status,
            obj.effective_status,
        )

    @admin.display(
        description="Current Pro access",
        boolean=True,
    )
    def pro_access_display(
        self,
        obj,
    ):
        return obj.has_pro_access


# =========================================================
# PUBLIC BUSINESS PROFILE
# =========================================================


@admin.register(BusinessPublicProfile)
class BusinessPublicProfileAdmin(
    admin.ModelAdmin
):
    """
    Public marketplace profile.

    Verification is controlled only through the dedicated
    BusinessVerification workflow.

    Business owners cannot make themselves verified.
    """

    list_display = (
        "business",
        "trade_category_display",
        "city_display",
        "publication_badge",
        "verification_badge",
        "emergency_callouts",
        "updated_at",
    )

    list_filter = (
        "public_profile_enabled",
        "is_verified",
        "trade_category",
        "emergency_callouts",
    )

    search_fields = (
        "business__name",
        "business__city",
        "headline",
        "services",
    )

    readonly_fields = (
        "is_verified",
        "created_at",
        "updated_at",
    )

    ordering = (
        "business__name",
    )


    # =====================================================
    # TRADE DISPLAY
    # =====================================================

    @admin.display(
        description="Trade",
        ordering="trade_category",
    )
    def trade_category_display(
        self,
        obj,
    ):
        return (
            obj.get_trade_category_display()
        )


    # =====================================================
    # CITY DISPLAY
    # =====================================================

    @admin.display(
        description="City",
        ordering="business__city",
    )
    def city_display(
        self,
        obj,
    ):
        return (
            obj.business.city
            or "—"
        )


    # =====================================================
    # PUBLICATION BADGE
    # =====================================================

    @admin.display(
        description="Published",
        ordering="public_profile_enabled",
    )
    def publication_badge(
        self,
        obj,
    ):

        if obj.public_profile_enabled:

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-success">'
                    '{}'
                    '</span>'
                ),
                "Published",
            )

        return format_html(
            (
                '<span class="tf-status '
                'tf-status-muted">'
                '{}'
                '</span>'
            ),
            "Hidden",
        )


    # =====================================================
    # VERIFICATION BADGE
    # =====================================================

    @admin.display(
        description="Verification",
        ordering="is_verified",
    )
    def verification_badge(
        self,
        obj,
    ):

        if obj.is_verified:

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-success">'
                    '{}'
                    '</span>'
                ),
                "✓ Verified",
            )

        return format_html(
            (
                '<span class="tf-status '
                'tf-status-muted">'
                '{}'
                '</span>'
            ),
            "Not verified",
        )


# =========================================================
# BUSINESS VERIFICATION
# =========================================================


@admin.register(BusinessVerification)
class BusinessVerificationAdmin(
    admin.ModelAdmin
):
    """
    TradeFlow platform verification review area.

    Business-submitted identity information becomes
    read-only in admin.

    Administrators review the information, write internal
    notes and approve or reject the application.

    Approval automatically synchronizes the public
    BusinessPublicProfile verification badge through the
    BusinessVerification model.
    """

    # =====================================================
    # CUSTOM REVIEW TEMPLATE
    # =====================================================

    change_form_template = (
        "admin/core/businessverification/"
        "change_form.html"
    )


    # =====================================================
    # LIST PAGE
    # =====================================================

    list_display = (
        "business",
        "trade_display",
        "city_display",
        "registration_type_display",
        "registration_number",
        "status_badge",
        "submitted_at",
        "reviewed_by",
        "review_application",
    )


    list_filter = (
        "status",
        "registration_type",
        "submitted_at",
        "reviewed_at",
    )


    search_fields = (
        "business__name",
        "business__city",
        "legal_business_name",
        "registration_number",
        "contact_name",
        "contact_email",
        "contact_phone",
    )


    ordering = (
        "status",
        "-submitted_at",
    )


    list_per_page = 25


    # =====================================================
    # READ-ONLY BUSINESS APPLICATION DATA
    # =====================================================

    readonly_fields = (
        "business",
        "legal_business_name",
        "registration_type",
        "registration_number",
        "contact_name",
        "contact_email",
        "contact_phone",
        "supporting_information",
        "status",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "created_at",
        "updated_at",
    )


    # =====================================================
    # BULK ACTIONS
    # =====================================================

    actions = (
        "approve_verification",
        "reject_verification",
    )


    # =====================================================
    # REVIEW FORM LAYOUT
    # =====================================================

    fieldsets = (

        (
            "Business identity",
            {
                "fields": (
                    "business",
                    "legal_business_name",
                    "registration_type",
                    "registration_number",
                ),
            },
        ),

        (
            "Contact information",
            {
                "fields": (
                    "contact_name",
                    "contact_email",
                    "contact_phone",
                ),
            },
        ),

        (
            "Supporting information",
            {
                "fields": (
                    "supporting_information",
                ),
            },
        ),

        (
            "TradeFlow review",
            {
                "fields": (
                    "status",
                    "admin_notes",
                    "submitted_at",
                    "reviewed_at",
                    "reviewed_by",
                ),
            },
        ),

        (
            "System information",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),

    )


    # =====================================================
    # PREVENT MANUAL APPLICATION CREATION
    # =====================================================

    def has_add_permission(
        self,
        request,
    ):
        """
        Verification applications originate from business
        owners.

        Platform administrators review applications but do
        not create them manually.
        """

        return False


    # =====================================================
    # TRADE
    # =====================================================

    @admin.display(
        description="Trade",
    )
    def trade_display(
        self,
        obj,
    ):

        try:

            profile = (
                obj.business.public_profile
            )

        except (
            BusinessPublicProfile
            .DoesNotExist
        ):

            return "—"


        return (
            profile
            .get_trade_category_display()
        )


    # =====================================================
    # CITY
    # =====================================================

    @admin.display(
        description="City",
        ordering="business__city",
    )
    def city_display(
        self,
        obj,
    ):

        return (
            obj.business.city
            or "—"
        )


    # =====================================================
    # REGISTRATION TYPE
    # =====================================================

    @admin.display(
        description="Registration type",
        ordering="registration_type",
    )
    def registration_type_display(
        self,
        obj,
    ):

        return (
            obj
            .get_registration_type_display()
        )


    # =====================================================
    # STATUS BADGE
    # =====================================================

    @admin.display(
        description="Status",
        ordering="status",
    )
    def status_badge(
        self,
        obj,
    ):

        if (
            obj.status
            == BusinessVerification
            .STATUS_VERIFIED
        ):

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-success">'
                    '{}'
                    '</span>'
                ),
                "✓ Verified",
            )


        if (
            obj.status
            == BusinessVerification
            .STATUS_PENDING
        ):

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-warning">'
                    '{}'
                    '</span>'
                ),
                "Pending Review",
            )


        if (
            obj.status
            == BusinessVerification
            .STATUS_REJECTED
        ):

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-danger">'
                    '{}'
                    '</span>'
                ),
                "Needs Information",
            )


        return format_html(
            (
                '<span class="tf-status '
                'tf-status-muted">'
                '{}'
                '</span>'
            ),
            "Not Submitted",
        )


    # =====================================================
    # REVIEW LINK
    # =====================================================

    @admin.display(
        description="Review",
    )
    def review_application(
        self,
        obj,
    ):

        url = reverse(
            (
                "admin:"
                "core_businessverification_change"
            ),
            args=[
                obj.pk,
            ],
        )


        return format_html(
            (
                '<a class="tf-review-link" '
                'href="{}">'
                'Review'
                '</a>'
            ),
            url,
        )


    # =====================================================
    # NORMAL ADMIN SAVE
    # =====================================================

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """
        Standard admin saves are used mainly for admin_notes.

        Application identity data and review status remain
        protected through readonly_fields and the dedicated
        approval/rejection workflow.
        """

        super().save_model(
            request,
            obj,
            form,
            change,
        )


    # =====================================================
    # DIRECT APPROVE / REJECT BUTTONS
    # =====================================================

    def response_change(
        self,
        request,
        obj,
    ):
        """
        Handle the custom Approve Business and Reject /
        Needs Information buttons from the verification
        review page.

        Django saves admin_notes before this method runs,
        so review notes are preserved.
        """

        # -------------------------------------------------
        # APPROVE
        # -------------------------------------------------

        if (
            "_approve_verification"
            in request.POST
        ):

            obj.status = (
                BusinessVerification
                .STATUS_VERIFIED
            )

            obj.reviewed_by = (
                request.user
            )

            obj.reviewed_at = (
                timezone.now()
            )

            obj.save()


            self.message_user(
                request,
                (
                    f"{obj.business.name} "
                    f"has been verified "
                    f"successfully."
                ),
                level=messages.SUCCESS,
            )


            return HttpResponseRedirect(
                request.path
            )


        # -------------------------------------------------
        # REJECT / NEEDS INFORMATION
        # -------------------------------------------------

        if (
            "_reject_verification"
            in request.POST
        ):

            obj.status = (
                BusinessVerification
                .STATUS_REJECTED
            )

            obj.reviewed_by = (
                request.user
            )

            obj.reviewed_at = (
                timezone.now()
            )

            obj.save()


            self.message_user(
                request,
                (
                    f"{obj.business.name}'s "
                    f"verification application "
                    f"has been marked as needing "
                    f"more information."
                ),
                level=messages.WARNING,
            )


            return HttpResponseRedirect(
                request.path
            )


        return super().response_change(
            request,
            obj,
        )


    # =====================================================
    # BULK APPROVE
    # =====================================================

    @admin.action(
        description=(
            "Approve selected business "
            "verification(s)"
        )
    )
    def approve_verification(
        self,
        request,
        queryset,
    ):

        count = 0


        for verification in queryset:

            verification.status = (
                BusinessVerification
                .STATUS_VERIFIED
            )

            verification.reviewed_by = (
                request.user
            )

            verification.reviewed_at = (
                timezone.now()
            )

            verification.save()

            count += 1


        self.message_user(
            request,
            (
                f"{count} business verification "
                f"application(s) approved."
            ),
            level=messages.SUCCESS,
        )


    # =====================================================
    # BULK REJECT
    # =====================================================

    @admin.action(
        description=(
            "Reject selected business "
            "verification(s)"
        )
    )
    def reject_verification(
        self,
        request,
        queryset,
    ):

        count = 0


        for verification in queryset:

            verification.status = (
                BusinessVerification
                .STATUS_REJECTED
            )

            verification.reviewed_by = (
                request.user
            )

            verification.reviewed_at = (
                timezone.now()
            )

            verification.save()

            count += 1


        self.message_user(
            request,
            (
                f"{count} business verification "
                f"application(s) rejected."
            ),
            level=messages.WARNING,
        )


# =========================================================
# BUSINESS REVIEW MODERATION
# =========================================================


@admin.register(BusinessReview)
class BusinessReviewAdmin(
    admin.ModelAdmin
):
    """
    TradeFlow customer-review moderation area.

    Reviews originate from completed TradeFlow jobs. Admins
    moderate submitted reviews but cannot create customer
    reviews manually.

    Trusted relationship fields and review content remain
    read-only here. Platform staff may add moderation notes
    and approve or reject submitted reviews.
    """

    # =====================================================
    # LIST PAGE
    # =====================================================

    list_display = (
        "customer_display_name",
        "business",
        "job",
        "rating_stars",
        "status_badge",
        "created_at",
        "moderated_by",
        "review_application",
    )

    list_filter = (
        "status",
        "rating",
        "created_at",
        "moderated_at",
    )

    search_fields = (
        "customer_display_name",
        "customer__name",
        "customer__phone",
        "customer__email",
        "business__name",
        "job__job_number",
        "job__title",
        "comment",
    )

    ordering = (
        "status",
        "-created_at",
    )

    list_per_page = 25

    # =====================================================
    # REVIEW FORM
    # =====================================================

    readonly_fields = (
        "business",
        "customer",
        "job",
        "customer_display_name",
        "rating",
        "comment",
        "status",
        "created_at",
        "updated_at",
        "moderated_at",
        "moderated_by",
    )

    fieldsets = (
        (
            "Completed TradeFlow job",
            {
                "fields": (
                    "business",
                    "customer",
                    "job",
                ),
            },
        ),
        (
            "Customer review",
            {
                "fields": (
                    "customer_display_name",
                    "rating",
                    "comment",
                    "created_at",
                ),
            },
        ),
        (
            "TradeFlow moderation",
            {
                "fields": (
                    "status",
                    "moderation_notes",
                    "moderated_at",
                    "moderated_by",
                ),
            },
        ),
        (
            "System information",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "updated_at",
                ),
            },
        ),
    )

    actions = (
        "approve_reviews",
        "reject_reviews",
    )

    # =====================================================
    # PREVENT MANUAL REVIEW CREATION
    # =====================================================

    def has_add_permission(
        self,
        request,
    ):
        """
        Customer reviews must originate from the TradeFlow
        completed-job review workflow, never from admin.
        """

        return False

    # =====================================================
    # STATUS BADGE
    # =====================================================

    @admin.display(
        description="Status",
        ordering="status",
    )
    def status_badge(
        self,
        obj,
    ):

        if (
            obj.status
            == BusinessReview.STATUS_APPROVED
        ):

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-success">'
                    '{}'
                    '</span>'
                ),
                "✓ Approved",
            )

        if (
            obj.status
            == BusinessReview.STATUS_REJECTED
        ):

            return format_html(
                (
                    '<span class="tf-status '
                    'tf-status-danger">'
                    '{}'
                    '</span>'
                ),
                "Rejected / Hidden",
            )

        return format_html(
            (
                '<span class="tf-status '
                'tf-status-warning">'
                '{}'
                '</span>'
            ),
            "Pending Review",
        )

    # =====================================================
    # STAR DISPLAY
    # =====================================================

    @admin.display(
        description="Rating",
        ordering="rating",
    )
    def rating_stars(
        self,
        obj,
    ):

        stars = (
            "★" * obj.rating
            + "☆" * (5 - obj.rating)
        )

        return format_html(
            '<strong title="{} out of 5">{}</strong>',
            obj.rating,
            stars,
        )

    # =====================================================
    # REVIEW LINK
    # =====================================================

    @admin.display(
        description="Moderate",
    )
    def review_application(
        self,
        obj,
    ):

        url = reverse(
            "admin:core_businessreview_change",
            args=[
                obj.pk,
            ],
        )

        return format_html(
            (
                '<a class="tf-review-link" '
                'href="{}">'
                'Review'
                '</a>'
            ),
            url,
        )

    # =====================================================
    # NORMAL ADMIN SAVE
    # =====================================================

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """
        Standard saves are used for moderation_notes only.

        Approval/rejection is performed through the dedicated
        moderation actions below so the moderator and time are
        always recorded together with the status change.
        """

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    # =====================================================
    # BULK APPROVE
    # =====================================================

    @admin.action(
        description=(
            "Approve selected customer review(s)"
        )
    )
    def approve_reviews(
        self,
        request,
        queryset,
    ):

        count = 0

        for review in queryset:

            review.status = (
                BusinessReview.STATUS_APPROVED
            )

            review.moderated_by = (
                request.user
            )

            review.moderated_at = (
                timezone.now()
            )

            review.save()

            count += 1

        self.message_user(
            request,
            (
                f"{count} customer review(s) "
                f"approved and made public."
            ),
            level=messages.SUCCESS,
        )

    # =====================================================
    # BULK REJECT
    # =====================================================

    @admin.action(
        description=(
            "Reject / hide selected customer review(s)"
        )
    )
    def reject_reviews(
        self,
        request,
        queryset,
    ):

        count = 0

        for review in queryset:

            review.status = (
                BusinessReview.STATUS_REJECTED
            )

            review.moderated_by = (
                request.user
            )

            review.moderated_at = (
                timezone.now()
            )

            review.save()

            count += 1

        self.message_user(
            request,
            (
                f"{count} customer review(s) "
                f"rejected and hidden."
            ),
            level=messages.WARNING,
        )


# =========================================================
# CUSTOMER
# =========================================================


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "business",
        "phone",
        "email",
        "created_at",
    )

    search_fields = (
        "name",
        "business__name",
        "phone",
        "email",
    )

    list_filter = (
        "created_at",
    )


# =========================================================
# QUOTE ITEM INLINE
# =========================================================


class QuoteItemInline(
    admin.TabularInline
):
    model = QuoteItem
    extra = 0


# =========================================================
# QUOTE
# =========================================================


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "quote_number",
        "business",
        "customer",
        "status",
        "issue_date",
        "apply_vat",
        "created_at",
    )

    list_filter = (
        "status",
        "apply_vat",
    )

    search_fields = (
        "quote_number",
        "business__name",
        "customer__name",
    )

    inlines = [
        QuoteItemInline,
    ]


# =========================================================
# QUOTE ITEM
# =========================================================


@admin.register(QuoteItem)
class QuoteItemAdmin(
    admin.ModelAdmin
):
    list_display = (
        "quote",
        "description",
        "quantity",
        "unit_price",
    )


# =========================================================
# JOB
# =========================================================


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "job_number",
        "business",
        "customer",
        "quote",
        "title",
        "status",
        "start_date",
        "due_date",
    )

    list_filter = (
        "status",
    )

    search_fields = (
        "job_number",
        "business__name",
        "customer__name",
        "title",
    )


# =========================================================
# INVOICE ITEM INLINE
# =========================================================


class InvoiceItemInline(
    admin.TabularInline
):
    model = InvoiceItem
    extra = 0


# =========================================================
# PAYMENT INLINE
# =========================================================


class PaymentInline(
    admin.TabularInline
):
    model = Payment
    extra = 0


# =========================================================
# INVOICE
# =========================================================


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "business",
        "customer",
        "job",
        "status",
        "issue_date",
        "due_date",
        "apply_vat",
    )

    list_filter = (
        "status",
        "apply_vat",
    )

    search_fields = (
        "invoice_number",
        "business__name",
        "customer__name",
    )

    inlines = [
        InvoiceItemInline,
        PaymentInline,
    ]


# =========================================================
# INVOICE ITEM
# =========================================================


@admin.register(InvoiceItem)
class InvoiceItemAdmin(
    admin.ModelAdmin
):
    list_display = (
        "invoice",
        "description",
        "quantity",
        "unit_price",
    )


# =========================================================
# PAYMENT
# =========================================================


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "amount",
        "payment_date",
        "method",
        "reference",
    )

    list_filter = (
        "method",
        "payment_date",
    )

    search_fields = (
        "invoice__invoice_number",
        "reference",
    )


# =========================================================
# QUOTE REQUEST
# =========================================================


@admin.register(QuoteRequest)
class QuoteRequestAdmin(
    admin.ModelAdmin
):
    list_display = (
        "customer_name",
        "business",
        "phone",
        "location",
        "urgency",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "urgency",
        "preferred_contact",
        "created_at",
    )

    search_fields = (
        "customer_name",
        "phone",
        "email",
        "business__name",
        "description",
    )