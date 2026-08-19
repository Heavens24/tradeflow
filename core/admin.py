from django.contrib import admin

from .models import (
    Business,
    Customer,
    Invoice,
    InvoiceItem,
    Job,
    Payment,
    Quote,
    QuoteItem,
)


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


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "business",
        "phone",
        "email",
        "created_at",
    )


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0


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


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


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