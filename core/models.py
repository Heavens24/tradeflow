from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


# =========================================================
# BUSINESS
# =========================================================


class Business(models.Model):
    owner = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="business",
    )

    name = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField(
        blank=True
    )

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        default="Bloemfontein",
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True,
    )

    # =====================================================
    # TAX / VAT DETAILS
    # =====================================================

    vat_number = models.CharField(
        max_length=100,
        blank=True,
    )

    # =====================================================
    # BANKING DETAILS
    # =====================================================

    bank_name = models.CharField(
        max_length=100,
        blank=True,
    )

    bank_account_name = models.CharField(
        max_length=150,
        blank=True,
    )

    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
    )

    bank_branch_code = models.CharField(
        max_length=30,
        blank=True,
    )

    bank_account_type = models.CharField(
        max_length=50,
        blank=True,
    )

    # =====================================================
    # DEFAULT CUSTOMER DOCUMENT TERMS
    # =====================================================

    default_quote_terms = models.TextField(
        blank=True,
    )

    default_invoice_terms = models.TextField(
        blank=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Business"
        verbose_name_plural = "Businesses"

    def __str__(self):
        return self.name


# =========================================================
# CUSTOMER
# =========================================================


class Customer(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="customers",
    )

    name = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=20
    )

    email = models.EmailField(
        blank=True
    )

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


# =========================================================
# QUOTE
# =========================================================


class Quote(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (
            STATUS_DRAFT,
            "Draft",
        ),
        (
            STATUS_SENT,
            "Sent",
        ),
        (
            STATUS_ACCEPTED,
            "Accepted",
        ),
        (
            STATUS_DECLINED,
            "Declined",
        ),
        (
            STATUS_EXPIRED,
            "Expired",
        ),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="quotes",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="quotes",
    )

    quote_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    issue_date = models.DateField(
        default=timezone.localdate,
    )

    expiry_date = models.DateField(
        blank=True,
        null=True,
    )

    apply_vat = models.BooleanField(
        default=False
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            self.quote_number
            or f"Quote {self.pk}"
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        super().save(
            *args,
            **kwargs,
        )

        if not self.quote_number:
            self.quote_number = (
                f"Q-{self.pk:05d}"
            )

            Quote.objects.filter(
                pk=self.pk
            ).update(
                quote_number=self.quote_number
            )

    @property
    def subtotal(self):
        return sum(
            (
                item.line_total
                for item in self.items.all()
            ),
            Decimal("0.00"),
        )

    @property
    def vat_amount(self):
        if not self.apply_vat:
            return Decimal("0.00")

        return (
            self.subtotal
            * Decimal("0.15")
        ).quantize(
            Decimal("0.01")
        )

    @property
    def total(self):
        return (
            self.subtotal
            + self.vat_amount
        )


# =========================================================
# QUOTE ITEMS
# =========================================================


class QuoteItem(models.Model):
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="items",
    )

    description = models.CharField(
        max_length=255
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description

    @property
    def line_total(self):
        return (
            self.quantity
            * self.unit_price
        ).quantize(
            Decimal("0.01")
        )


# =========================================================
# JOB
# =========================================================


class Job(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (
            STATUS_SCHEDULED,
            "Scheduled",
        ),
        (
            STATUS_IN_PROGRESS,
            "In Progress",
        ),
        (
            STATUS_COMPLETED,
            "Completed",
        ),
        (
            STATUS_CANCELLED,
            "Cancelled",
        ),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="jobs",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="jobs",
    )

    quote = models.OneToOneField(
        Quote,
        on_delete=models.SET_NULL,
        related_name="job",
        blank=True,
        null=True,
    )

    job_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
    )

    start_date = models.DateField(
        blank=True,
        null=True,
    )

    due_date = models.DateField(
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            self.job_number
            or f"Job {self.pk}"
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        super().save(
            *args,
            **kwargs,
        )

        if not self.job_number:
            self.job_number = (
                f"J-{self.pk:05d}"
            )

            Job.objects.filter(
                pk=self.pk
            ).update(
                job_number=self.job_number
            )


# =========================================================
# BUSINESS REVIEWS
# =========================================================


class BusinessReview(models.Model):
    """
    Customer review tied to a real completed TradeFlow job.

    Trust rules:
    - one review per job
    - the reviewed business comes from the job
    - the reviewing customer comes from the job
    - only completed jobs are eligible
    - public visibility is controlled by moderation status

    Public marketplace pages should use only reviews whose
    status is STATUS_APPROVED.
    """

    # =====================================================
    # MODERATION STATUS
    # =====================================================

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (
            STATUS_PENDING,
            "Pending review",
        ),
        (
            STATUS_APPROVED,
            "Approved / public",
        ),
        (
            STATUS_REJECTED,
            "Rejected / hidden",
        ),
    ]

    # =====================================================
    # RATING
    # =====================================================

    RATING_CHOICES = [
        (1, "1 star"),
        (2, "2 stars"),
        (3, "3 stars"),
        (4, "4 stars"),
        (5, "5 stars"),
    ]

    # =====================================================
    # TRUSTED RELATIONSHIPS
    # =====================================================

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="business_reviews",
    )

    job = models.OneToOneField(
        Job,
        on_delete=models.CASCADE,
        related_name="review",
    )

    # =====================================================
    # CUSTOMER REVIEW CONTENT
    # =====================================================

    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
    )

    comment = models.TextField(
        blank=True,
        max_length=2000,
    )

    customer_display_name = models.CharField(
        max_length=150,
        blank=True,
        help_text=(
            "Snapshot of the customer name shown with the "
            "review. It is filled automatically from the job."
        ),
    )

    # =====================================================
    # TRADEFLOW MODERATION
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    moderation_notes = models.TextField(
        blank=True,
    )

    moderated_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    moderated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="moderated_business_reviews",
        blank=True,
        null=True,
    )

    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =====================================================
    # MODEL OPTIONS
    # =====================================================

    class Meta:
        ordering = [
            "-created_at",
        ]

        verbose_name = "Business Review"
        verbose_name_plural = "Business Reviews"

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(rating__gte=1)
                    & models.Q(rating__lte=5)
                ),
                name="business_review_rating_1_to_5",
            ),
        ]

    # =====================================================
    # DISPLAY
    # =====================================================

    def __str__(self):
        return (
            f"{self.customer_display_name or self.customer.name} "
            f"→ {self.business.name} "
            f"({self.rating}/5)"
        )

    # =====================================================
    # TRUST VALIDATION
    # =====================================================

    def clean(self):
        """
        Protect review integrity at model level.

        The job is authoritative for both the business and
        customer, and only completed jobs may be reviewed.
        """

        super().clean()

        if not self.job_id:
            return

        if self.job.status != Job.STATUS_COMPLETED:
            raise ValidationError(
                {
                    "job": (
                        "Only completed jobs can receive "
                        "customer reviews."
                    )
                }
            )

        if (
            self.business_id
            and self.business_id != self.job.business_id
        ):
            raise ValidationError(
                {
                    "business": (
                        "The review business must match the "
                        "business that completed the job."
                    )
                }
            )

        if (
            self.customer_id
            and self.customer_id != self.job.customer_id
        ):
            raise ValidationError(
                {
                    "customer": (
                        "The review customer must match the "
                        "customer attached to the job."
                    )
                }
            )

    # =====================================================
    # SAVE PROTECTION
    # =====================================================

    def save(
        self,
        *args,
        **kwargs,
    ):
        """
        Derive trusted relationship fields from the job.

        This prevents callers from assigning a review to a
        different business or customer through submitted data.
        """

        if self.job_id:
            self.business_id = self.job.business_id
            self.customer_id = self.job.customer_id

            if not self.customer_display_name:
                self.customer_display_name = (
                    self.job.customer.name
                )

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    @property
    def is_public(self):
        return (
            self.status
            == self.STATUS_APPROVED
        )


# =========================================================
# INVOICE
# =========================================================


class Invoice(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_PART_PAID = "part_paid"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (
            STATUS_DRAFT,
            "Draft",
        ),
        (
            STATUS_SENT,
            "Sent",
        ),
        (
            STATUS_PART_PAID,
            "Part Paid",
        ),
        (
            STATUS_PAID,
            "Paid",
        ),
        (
            STATUS_OVERDUE,
            "Overdue",
        ),
        (
            STATUS_CANCELLED,
            "Cancelled",
        ),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    job = models.OneToOneField(
        Job,
        on_delete=models.SET_NULL,
        related_name="invoice",
        blank=True,
        null=True,
    )

    quote = models.ForeignKey(
        Quote,
        on_delete=models.SET_NULL,
        related_name="invoices",
        blank=True,
        null=True,
    )

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    issue_date = models.DateField(
        default=timezone.localdate,
    )

    due_date = models.DateField(
        blank=True,
        null=True,
    )

    apply_vat = models.BooleanField(
        default=False
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            self.invoice_number
            or f"Invoice {self.pk}"
        )

    def save(
        self,
        *args,
        **kwargs,
    ):
        super().save(
            *args,
            **kwargs,
        )

        if not self.invoice_number:
            self.invoice_number = (
                f"INV-{self.pk:05d}"
            )

            Invoice.objects.filter(
                pk=self.pk
            ).update(
                invoice_number=self.invoice_number
            )

    @property
    def subtotal(self):
        return sum(
            (
                item.line_total
                for item in self.items.all()
            ),
            Decimal("0.00"),
        )

    @property
    def vat_amount(self):
        if not self.apply_vat:
            return Decimal("0.00")

        return (
            self.subtotal
            * Decimal("0.15")
        ).quantize(
            Decimal("0.01")
        )

    @property
    def total(self):
        return (
            self.subtotal
            + self.vat_amount
        )

    @property
    def amount_paid(self):
        return sum(
            (
                payment.amount
                for payment in self.payments.all()
            ),
            Decimal("0.00"),
        )

    @property
    def balance_due(self):
        balance = (
            self.total
            - self.amount_paid
        )

        if balance < Decimal("0.00"):
            return Decimal("0.00")

        return balance


# =========================================================
# INVOICE ITEMS
# =========================================================


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )

    description = models.CharField(
        max_length=255
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description

    @property
    def line_total(self):
        return (
            self.quantity
            * self.unit_price
        ).quantize(
            Decimal("0.01")
        )


# =========================================================
# PAYMENTS
# =========================================================


class Payment(models.Model):
    METHOD_CASH = "cash"
    METHOD_EFT = "eft"
    METHOD_CARD = "card"
    METHOD_OTHER = "other"

    METHOD_CHOICES = [
        (
            METHOD_CASH,
            "Cash",
        ),
        (
            METHOD_EFT,
            "EFT",
        ),
        (
            METHOD_CARD,
            "Card",
        ),
        (
            METHOD_OTHER,
            "Other",
        ),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    payment_date = models.DateField(
        default=timezone.localdate,
    )

    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default=METHOD_EFT,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-payment_date",
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.invoice.invoice_number} "
            f"- R{self.amount}"
        )


# =========================================================
# PUBLIC BUSINESS PROFILE
# =========================================================


class BusinessPublicProfile(models.Model):
    """
    Public-facing profile for a TradeFlow business.

    This is deliberately kept separate from the main
    Business model so operational and financial data stay
    isolated from the public-facing marketplace layer.

    Private information such as:
    - banking details
    - VAT information
    - customer records
    - quotations
    - jobs
    - invoices
    - payments

    is not stored or exposed through this model.
    """

    # =====================================================
    # BUSINESS RELATIONSHIP
    # =====================================================

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="public_profile",
    )


    # =====================================================
    # PUBLIC URL
    # =====================================================

    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True,
    )


    # =====================================================
    # PUBLICATION STATUS
    # =====================================================

    public_profile_enabled = models.BooleanField(
        default=False,
    )


    # =====================================================
    # MARKETPLACE TRADE CATEGORY
    # =====================================================

    TRADE_ELECTRICAL = "electrical"
    TRADE_PLUMBING = "plumbing"
    TRADE_MECHANICAL = "mechanical"
    TRADE_WELDING = "welding"
    TRADE_HVAC = "hvac"
    TRADE_CARPENTRY = "carpentry"
    TRADE_BUILDING = "building"
    TRADE_AUTOMOTIVE = "automotive"
    TRADE_OTHER = "other"

    TRADE_CHOICES = [
        (
            TRADE_ELECTRICAL,
            "Electrical",
        ),
        (
            TRADE_PLUMBING,
            "Plumbing",
        ),
        (
            TRADE_MECHANICAL,
            "Mechanical / Millwright",
        ),
        (
            TRADE_WELDING,
            "Welding / Fabrication",
        ),
        (
            TRADE_HVAC,
            "Refrigeration / HVAC",
        ),
        (
            TRADE_CARPENTRY,
            "Carpentry",
        ),
        (
            TRADE_BUILDING,
            "Building / Construction",
        ),
        (
            TRADE_AUTOMOTIVE,
            "Automotive",
        ),
        (
            TRADE_OTHER,
            "Other",
        ),
    ]

    trade_category = models.CharField(
        max_length=30,
        choices=TRADE_CHOICES,
        default=TRADE_OTHER,
    )


    # =====================================================
    # PUBLIC BUSINESS CONTENT
    # =====================================================

    headline = models.CharField(
        max_length=180,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    services = models.TextField(
        blank=True,
        help_text=(
            "Enter one service per line."
        ),
    )


    # =====================================================
    # PUBLIC CONTACT OPTIONS
    # =====================================================

    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
    )

    emergency_callouts = models.BooleanField(
        default=False,
    )

    show_phone_publicly = models.BooleanField(
        default=False,
    )

    show_email_publicly = models.BooleanField(
        default=False,
    )


    # =====================================================
    # VERIFICATION
    # =====================================================

    # This field must not be included in the business
    # owner's public profile form.
    #
    # TradeFlow administrators control verification through
    # the verification workflow.

    is_verified = models.BooleanField(
        default=False,
    )


    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    # =====================================================
    # MODEL OPTIONS
    # =====================================================

    class Meta:
        ordering = [
            "business__name",
        ]

        verbose_name = (
            "Business Public Profile"
        )

        verbose_name_plural = (
            "Business Public Profiles"
        )


    # =====================================================
    # DISPLAY
    # =====================================================

    def __str__(self):
        return (
            f"Public profile for "
            f"{self.business.name}"
        )


    # =====================================================
    # SLUG GENERATION
    # =====================================================

    def _generate_unique_slug(self):
        """
        Generate a readable and unique public URL slug.

        Example:

        March24 Electrical Services

        becomes:

        march24-electrical-services

        If another business already uses the slug:

        march24-electrical-services-2
        """

        base_slug = slugify(
            self.business.name
        )[:160]


        if not base_slug:
            base_slug = "business"


        candidate = base_slug

        counter = 2


        queryset = (
            BusinessPublicProfile.objects
            .exclude(
                pk=self.pk
            )
        )


        while queryset.filter(
            slug=candidate
        ).exists():

            suffix = (
                f"-{counter}"
            )

            available_length = (
                180
                - len(suffix)
            )

            candidate = (
                f"{base_slug[:available_length]}"
                f"{suffix}"
            )

            counter += 1


        return candidate


    def save(
        self,
        *args,
        **kwargs,
    ):
        """
        Automatically create the public slug the first time
        the profile is saved.

        The slug is deliberately not regenerated every time
        the business name changes. This keeps an established
        public URL stable.
        """

        if not self.slug:

            self.slug = (
                self._generate_unique_slug()
            )


        super().save(
            *args,
            **kwargs,
        )


    # =====================================================
    # WHATSAPP HELPER
    # =====================================================

    @property
    def whatsapp_digits(self):
        """
        Return a WhatsApp-compatible phone number containing
        digits only.

        Example:

        0780608202

        becomes:

        27780608202

        If no dedicated WhatsApp number has been provided,
        the business phone number is used as a fallback.
        """

        value = (
            self.whatsapp_number
            or self.business.phone
            or ""
        )


        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )


        # Convert a South African local number such as
        # 0780608202 into international form:
        #
        # 27780608202

        if digits.startswith("0"):

            digits = (
                "27"
                + digits[1:]
            )


        return digits


    # =====================================================
    # SERVICES HELPER
    # =====================================================

    @property
    def service_list(self):
        """
        Convert the services TextField into a clean list.

        The business owner enters one service per line.
        """

        return [
            service.strip()

            for service
            in self.services.splitlines()

            if service.strip()
        ]


# =========================================================
# BUSINESS VERIFICATION
# =========================================================


class BusinessVerification(models.Model):
    """
    Verification application submitted by a TradeFlow
    business owner and reviewed by TradeFlow platform staff.

    Business owners can provide verification information,
    but they cannot approve or verify themselves.

    The authoritative public verified badge remains
    BusinessPublicProfile.is_verified and is synchronized
    from this model whenever verification status changes.
    """

    # =====================================================
    # STATUS
    # =====================================================

    STATUS_NOT_SUBMITTED = "not_submitted"
    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (
            STATUS_NOT_SUBMITTED,
            "Not submitted",
        ),
        (
            STATUS_PENDING,
            "Pending review",
        ),
        (
            STATUS_VERIFIED,
            "Verified",
        ),
        (
            STATUS_REJECTED,
            "Rejected / needs information",
        ),
    ]


    # =====================================================
    # REGISTRATION TYPE
    # =====================================================

    TYPE_SOLE_PROPRIETOR = "sole_proprietor"
    TYPE_PRIVATE_COMPANY = "private_company"
    TYPE_CLOSE_CORPORATION = "close_corporation"
    TYPE_PARTNERSHIP = "partnership"
    TYPE_NON_PROFIT = "non_profit"
    TYPE_OTHER = "other"

    REGISTRATION_TYPE_CHOICES = [
        (
            TYPE_SOLE_PROPRIETOR,
            "Sole proprietor",
        ),
        (
            TYPE_PRIVATE_COMPANY,
            "Private company (Pty) Ltd",
        ),
        (
            TYPE_CLOSE_CORPORATION,
            "Close corporation (CC)",
        ),
        (
            TYPE_PARTNERSHIP,
            "Partnership",
        ),
        (
            TYPE_NON_PROFIT,
            "Non-profit organisation",
        ),
        (
            TYPE_OTHER,
            "Other",
        ),
    ]


    # =====================================================
    # BUSINESS
    # =====================================================

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name="verification",
    )


    # =====================================================
    # APPLICATION INFORMATION
    # =====================================================

    legal_business_name = models.CharField(
        max_length=200,
        blank=True,
    )

    registration_type = models.CharField(
        max_length=30,
        choices=REGISTRATION_TYPE_CHOICES,
        default=TYPE_PRIVATE_COMPANY,
    )

    registration_number = models.CharField(
        max_length=100,
        blank=True,
    )

    contact_name = models.CharField(
        max_length=150,
        blank=True,
    )

    contact_email = models.EmailField(
        blank=True,
    )

    contact_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    supporting_information = models.TextField(
        blank=True,
        help_text=(
            "Provide any information that can help TradeFlow "
            "confirm the business identity and registration."
        ),
    )


    # =====================================================
    # REVIEW
    # =====================================================

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_SUBMITTED,
    )

    admin_notes = models.TextField(
        blank=True,
    )

    submitted_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    reviewed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="reviewed_business_verifications",
        blank=True,
        null=True,
    )


    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    # =====================================================
    # MODEL OPTIONS
    # =====================================================

    class Meta:
        ordering = [
            "-submitted_at",
            "-updated_at",
        ]

        verbose_name = (
            "Business Verification"
        )

        verbose_name_plural = (
            "Business Verifications"
        )


    # =====================================================
    # DISPLAY
    # =====================================================

    def __str__(self):
        return (
            f"{self.business.name} "
            f"verification "
            f"({self.get_status_display()})"
        )


    # =====================================================
    # PUBLIC BADGE SYNCHRONIZATION
    # =====================================================

    def sync_public_profile_verification(self):
        """
        Keep the public marketplace badge synchronized with
        the authoritative verification application status.
        """

        BusinessPublicProfile.objects.filter(
            business=self.business
        ).update(
            is_verified=(
                self.status
                == self.STATUS_VERIFIED
            )
        )


    def save(
        self,
        *args,
        **kwargs,
    ):
        super().save(
            *args,
            **kwargs,
        )

        self.sync_public_profile_verification()


# =========================================================
# PUBLIC QUOTE REQUESTS
# =========================================================


class QuoteRequest(models.Model):
    """
    A customer enquiry submitted through a business's
    public TradeFlow mini-page.

    Quote requests are private operational records.

    They are visible only to the business that received
    them and are never exposed through the public profile.
    """

    # =====================================================
    # STATUS
    # =====================================================

    STATUS_NEW = "new"
    STATUS_CONTACTED = "contacted"
    STATUS_CONVERTED = "converted"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (
            STATUS_NEW,
            "New",
        ),
        (
            STATUS_CONTACTED,
            "Contacted",
        ),
        (
            STATUS_CONVERTED,
            "Converted",
        ),
        (
            STATUS_CLOSED,
            "Closed",
        ),
    ]


    # =====================================================
    # PREFERRED CONTACT METHOD
    # =====================================================

    CONTACT_WHATSAPP = "whatsapp"
    CONTACT_PHONE = "phone"
    CONTACT_EMAIL = "email"

    CONTACT_CHOICES = [
        (
            CONTACT_WHATSAPP,
            "WhatsApp",
        ),
        (
            CONTACT_PHONE,
            "Phone call",
        ),
        (
            CONTACT_EMAIL,
            "Email",
        ),
    ]


    # =====================================================
    # URGENCY
    # =====================================================

    URGENCY_NORMAL = "normal"
    URGENCY_SOON = "soon"
    URGENCY_URGENT = "urgent"

    URGENCY_CHOICES = [
        (
            URGENCY_NORMAL,
            "Normal",
        ),
        (
            URGENCY_SOON,
            "As soon as possible",
        ),
        (
            URGENCY_URGENT,
            "Emergency / urgent",
        ),
    ]


    # =====================================================
    # TARGET BUSINESS
    # =====================================================

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="quote_requests",
    )


    # =====================================================
    # CUSTOMER DETAILS
    # =====================================================

    customer_name = models.CharField(
        max_length=150,
    )

    phone = models.CharField(
        max_length=30,
    )

    email = models.EmailField(
        blank=True,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )


    # =====================================================
    # WORK REQUEST
    # =====================================================

    description = models.TextField()

    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default=URGENCY_NORMAL,
    )

    preferred_contact = models.CharField(
        max_length=20,
        choices=CONTACT_CHOICES,
        default=CONTACT_WHATSAPP,
    )


    # =====================================================
    # BUSINESS WORKFLOW
    # =====================================================

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )


    # Once the request is converted, keep permanent links
    # to the real TradeFlow customer and quotation.

    converted_customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        related_name="source_quote_requests",
        blank=True,
        null=True,
    )

    converted_quote = models.ForeignKey(
        Quote,
        on_delete=models.SET_NULL,
        related_name="source_quote_requests",
        blank=True,
        null=True,
    )


    # =====================================================
    # TIMESTAMPS
    # =====================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    # =====================================================
    # MODEL OPTIONS
    # =====================================================

    class Meta:
        ordering = [
            "-created_at",
        ]

        verbose_name = (
            "Quote Request"
        )

        verbose_name_plural = (
            "Quote Requests"
        )


    # =====================================================
    # DISPLAY
    # =====================================================

    def __str__(self):
        return (
            f"{self.customer_name} → "
            f"{self.business.name}"
        )