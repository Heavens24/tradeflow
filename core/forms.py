from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory

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


# =========================================================
# AUTHENTICATION
# =========================================================


class TradeFlowRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "you@example.com",
                "autocomplete": "email",
            }
        ),
    )

    first_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "First name",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Last name",
                "autocomplete": "family-name",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        ]

        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        )

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        )

    def clean_email(self):
        email = self.cleaned_data.get(
            "email",
            "",
        ).strip().lower()

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email


class TradeFlowLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Username",
                "autocomplete": "username",
                "autofocus": True,
            }
        )
    )

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )


# =========================================================
# BUSINESS
# =========================================================


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business

        fields = [
            "name",
            "phone",
            "email",
            "address",
            "city",
            "registration_number",
            "vat_number",
            "bank_name",
            "bank_account_name",
            "bank_account_number",
            "bank_branch_code",
            "bank_account_type",
            "default_quote_terms",
            "default_invoice_terms",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Business name",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Phone number",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "business@example.com",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Business address",
                }
            ),

            "city": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Bloemfontein",
                }
            ),

            "registration_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Optional CIPC registration number"
                    ),
                }
            ),

            "vat_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Optional VAT registration number"
                    ),
                }
            ),

            "bank_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. FNB, Standard Bank, Absa, Capitec"
                    ),
                }
            ),

            "bank_account_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Name appearing on the bank account"
                    ),
                }
            ),

            "bank_account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Bank account number",
                }
            ),

            "bank_branch_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Branch code or universal branch code"
                    ),
                }
            ),

            "bank_account_type": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Cheque, Business, Current, Savings"
                    ),
                }
            ),

            "default_quote_terms": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "e.g. Quotation valid for 7 days.\n"
                        "Materials subject to availability.\n"
                        "Work starts after acceptance."
                    ),
                }
            ),

            "default_invoice_terms": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "e.g. Payment due within 7 days.\n"
                        "Please use the invoice number "
                        "as your payment reference."
                    ),
                }
            ),
        }


# =========================================================
# CUSTOMER
# =========================================================


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer

        fields = [
            "name",
            "phone",
            "email",
            "address",
            "notes",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer full name",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 0821234567",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "customer@example.com",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer address",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Optional notes",
                    "rows": 5,
                }
            ),
        }


# =========================================================
# QUOTE
# =========================================================


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote

        fields = [
            "customer",
            "status",
            "issue_date",
            "expiry_date",
            "apply_vat",
            "notes",
        ]

        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "issue_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "apply_vat": forms.CheckboxInput(
                attrs={
                    "class": "checkbox",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Terms, payment instructions "
                        "or additional information"
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        business=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if business:
            self.fields["customer"].queryset = (
                Customer.objects.filter(
                    business=business
                ).order_by("name")
            )

    def clean(self):
        cleaned_data = super().clean()

        issue_date = cleaned_data.get(
            "issue_date"
        )

        expiry_date = cleaned_data.get(
            "expiry_date"
        )

        if (
            issue_date
            and expiry_date
            and expiry_date < issue_date
        ):
            self.add_error(
                "expiry_date",
                (
                    "Expiry date cannot be earlier "
                    "than the issue date."
                ),
            )

        return cleaned_data


# =========================================================
# QUOTE ITEMS
# =========================================================


class QuoteItemForm(forms.ModelForm):
    class Meta:
        model = QuoteItem

        fields = [
            "description",
            "quantity",
            "unit_price",
        ]

        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Replace 20A circuit breaker"
                    ),
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get(
            "quantity"
        )

        if quantity is not None and quantity <= 0:
            raise forms.ValidationError(
                "Quantity must be greater than zero."
            )

        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get(
            "unit_price"
        )

        if (
            unit_price is not None
            and unit_price < 0
        ):
            raise forms.ValidationError(
                "Unit price cannot be negative."
            )

        return unit_price


QuoteItemFormSet = inlineformset_factory(
    Quote,
    QuoteItem,
    form=QuoteItemForm,
    extra=4,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# =========================================================
# JOB
# =========================================================


class JobForm(forms.ModelForm):
    class Meta:
        model = Job

        fields = [
            "customer",
            "title",
            "description",
            "status",
            "start_date",
            "due_date",
            "notes",
        ]

        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Replace DB circuit breaker"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Describe the work that must "
                        "be completed"
                    ),
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "start_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Internal notes, instructions "
                        "or customer requirements"
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        business=None,
        from_quote=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if business:
            self.fields["customer"].queryset = (
                Customer.objects.filter(
                    business=business
                ).order_by("name")
            )

        if from_quote:
            self.fields["customer"].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get(
            "start_date"
        )

        due_date = cleaned_data.get(
            "due_date"
        )

        if (
            start_date
            and due_date
            and due_date < start_date
        ):
            self.add_error(
                "due_date",
                (
                    "Due date cannot be earlier "
                    "than the start date."
                ),
            )

        return cleaned_data


# =========================================================
# INVOICE
# =========================================================


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice

        fields = [
            "customer",
            "status",
            "issue_date",
            "due_date",
            "apply_vat",
            "notes",
        ]

        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "issue_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "due_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "apply_vat": forms.CheckboxInput(
                attrs={
                    "class": "checkbox",
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Payment terms or invoice notes"
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        business=None,
        from_job=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if business:
            self.fields["customer"].queryset = (
                Customer.objects.filter(
                    business=business
                ).order_by("name")
            )

        if from_job:
            self.fields["customer"].disabled = True

    def clean(self):
        cleaned_data = super().clean()

        issue_date = cleaned_data.get(
            "issue_date"
        )

        due_date = cleaned_data.get(
            "due_date"
        )

        if (
            issue_date
            and due_date
            and due_date < issue_date
        ):
            self.add_error(
                "due_date",
                (
                    "Due date cannot be earlier "
                    "than the issue date."
                ),
            )

        return cleaned_data


# =========================================================
# INVOICE ITEMS
# =========================================================


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem

        fields = [
            "description",
            "quantity",
            "unit_price",
        ]

        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Description",
                }
            ),

            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get(
            "quantity"
        )

        if quantity is not None and quantity <= 0:
            raise forms.ValidationError(
                "Quantity must be greater than zero."
            )

        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get(
            "unit_price"
        )

        if (
            unit_price is not None
            and unit_price < 0
        ):
            raise forms.ValidationError(
                "Unit price cannot be negative."
            )

        return unit_price


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=4,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# =========================================================
# PAYMENT
# =========================================================


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment

        fields = [
            "amount",
            "payment_date",
            "method",
            "reference",
            "notes",
        ]

        widgets = {
            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "payment_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "method": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "reference": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "EFT reference, receipt number, etc."
                    ),
                }
            ),

            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Optional payment notes",
                }
            ),
        }

    def __init__(
        self,
        *args,
        invoice=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.invoice = invoice

    def clean_amount(self):
        amount = self.cleaned_data.get(
            "amount"
        )

        if amount is None:
            return amount

        if amount <= 0:
            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )

        if (
            self.invoice
            and amount > self.invoice.balance_due
        ):
            raise forms.ValidationError(
                (
                    "Payment cannot be greater than "
                    "the outstanding balance."
                )
            )

        return amount