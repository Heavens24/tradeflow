from django.contrib import admin
from django.utils import timezone

from .models import (
    Business,
    BusinessPublicProfile,
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


# =========================================================
# PUBLIC BUSINESS PROFILE
# =========================================================


@admin.register(BusinessPublicProfile)
class BusinessPublicProfileAdmin(
    admin.ModelAdmin
):
    """
    Public marketplace profile.

    Verification should be controlled through the dedicated
    BusinessVerification workflow rather than directly
    editing is_verified here.
    """

    list_display = (
        "business",
        "trade_category",
        "public_profile_enabled",
        "is_verified",
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


# =========================================================
# BUSINESS VERIFICATION
# =========================================================


@admin.register(BusinessVerification)
class BusinessVerificationAdmin(
    admin.ModelAdmin
):
    """
    TradeFlow platform verification review area.

    Only staff with Django Admin access can approve or reject
    verification applications.
    """

    list_display = (
        "business",
        "legal_business_name",
        "registration_type",
        "registration_number",
        "status",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
    )

    list_filter = (
        "status",
        "registration_type",
        "submitted_at",
        "reviewed_at",
    )

    search_fields = (
        "business__name",
        "legal_business_name",
        "registration_number",
        "contact_name",
        "contact_email",
        "contact_phone",
    )

    readonly_fields = (
        "business",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "created_at",
        "updated_at",
    )

    actions = (
        "approve_verification",
        "reject_verification",
    )


    fieldsets = (

        (
            "Business",
            {
                "fields": (
                    "business",
                    "legal_business_name",
                    "registration_type",
                    "registration_number",
                )
            },
        ),

        (
            "Contact",
            {
                "fields": (
                    "contact_name",
                    "contact_email",
                    "contact_phone",
                )
            },
        ),

        (
            "Supporting information",
            {
                "fields": (
                    "supporting_information",
                )
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
                )
            },
        ),

        (
            "System timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),

    )


    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """
        Record who performed the verification review when an
        administrator manually changes status.
        """

        if obj.status in (
            BusinessVerification.STATUS_VERIFIED,
            BusinessVerification.STATUS_REJECTED,
        ):

            obj.reviewed_by = (
                request.user
            )

            obj.reviewed_at = (
                timezone.now()
            )

        elif (
            obj.status
            == BusinessVerification.STATUS_PENDING
        ):

            obj.reviewed_by = None
            obj.reviewed_at = None


        super().save_model(
            request,
            obj,
            form,
            change,
        )


    @admin.action(
        description=(
            "Approve selected business verification(s)"
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
                BusinessVerification.STATUS_VERIFIED
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
        )


    @admin.action(
        description=(
            "Reject selected business verification(s)"
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
                BusinessVerification.STATUS_REJECTED
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


# =========================================================
# QUOTE ITEMS
# =========================================================


class QuoteItemInline(admin.TabularInline):
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

    inlines = [
        QuoteItemInline,
    ]


@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
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


# =========================================================
# INVOICE ITEMS / PAYMENTS
# =========================================================


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
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

    inlines = [
        InvoiceItemInline,
        PaymentInline,
    ]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
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


# =========================================================
# QUOTE REQUEST
# =========================================================


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
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