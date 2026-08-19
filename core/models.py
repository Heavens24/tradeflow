from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


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