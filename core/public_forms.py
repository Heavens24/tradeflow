from django import forms

from .models import (
    BusinessPublicProfile,
    BusinessReview,
    QuoteRequest,
)


# =========================================================
# PUBLIC BUSINESS PROFILE FORM
# =========================================================


class PublicBusinessProfileForm(
    forms.ModelForm
):
    """
    Allow a business owner to control only the fields that
    belong to their public TradeFlow mini-page.

    Private Business fields such as banking information,
    VAT details, registration information and customer data
    are not part of this form.

    Verification is deliberately excluded. Only TradeFlow
    administrators may control verification status.
    """

    class Meta:
        model = BusinessPublicProfile

        fields = [
            "public_profile_enabled",
            "trade_category",
            "headline",
            "description",
            "services",
            "whatsapp_number",
            "emergency_callouts",
            "show_phone_publicly",
            "show_email_publicly",
        ]

        widgets = {

            "public_profile_enabled": (
                forms.CheckboxInput(
                    attrs={
                        "class": "checkbox",
                    }
                )
            ),

            "trade_category": (
                forms.Select(
                    attrs={
                        "class": "form-control",
                    }
                )
            ),

            "headline": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. Reliable electrical "
                        "services in Bloemfontein"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Tell potential customers "
                        "about your business, "
                        "experience and the type of "
                        "work you provide."
                    ),
                }
            ),

            "services": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 7,
                    "placeholder": (
                        "Enter one service per line.\n"
                        "Electrical fault finding\n"
                        "Circuit breaker replacement\n"
                        "DB board repairs\n"
                        "Emergency call-outs"
                    ),
                }
            ),

            "whatsapp_number": (
                forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "placeholder": (
                            "e.g. 0780608202"
                        ),
                    }
                )
            ),

            "emergency_callouts": (
                forms.CheckboxInput(
                    attrs={
                        "class": "checkbox",
                    }
                )
            ),

            "show_phone_publicly": (
                forms.CheckboxInput(
                    attrs={
                        "class": "checkbox",
                    }
                )
            ),

            "show_email_publicly": (
                forms.CheckboxInput(
                    attrs={
                        "class": "checkbox",
                    }
                )
            ),

        }


# =========================================================
# PUBLIC QUOTE REQUEST FORM
# =========================================================


class PublicQuoteRequestForm(
    forms.ModelForm
):
    """
    Customer-facing request form.

    The business is never selectable by the customer.
    The view attaches the request to the business associated
    with the public profile URL.
    """

    class Meta:
        model = QuoteRequest

        fields = [
            "customer_name",
            "phone",
            "email",
            "location",
            "description",
            "urgency",
            "preferred_contact",
        ]

        widgets = {

            "customer_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your full name",
                    "autocomplete": "name",
                }
            ),

            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 0821234567",
                    "autocomplete": "tel",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                }
            ),

            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Suburb, area or job location"
                    ),
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 7,
                    "placeholder": (
                        "Describe the work you need done, "
                        "the problem you're experiencing, "
                        "and any useful details."
                    ),
                }
            ),

            "urgency": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "preferred_contact": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

        }


    def clean_customer_name(self):
        value = (
            self.cleaned_data.get(
                "customer_name",
                "",
            )
            .strip()
        )

        if len(value) < 2:
            raise forms.ValidationError(
                "Please enter your name."
            )

        return value


    def clean_phone(self):
        value = (
            self.cleaned_data.get(
                "phone",
                "",
            )
            .strip()
        )

        digits = "".join(
            character
            for character in value
            if character.isdigit()
        )

        if len(digits) < 9:
            raise forms.ValidationError(
                "Please enter a valid phone number."
            )

        return value


    def clean_description(self):
        value = (
            self.cleaned_data.get(
                "description",
                "",
            )
            .strip()
        )

        if len(value) < 10:
            raise forms.ValidationError(
                (
                    "Please provide a little more "
                    "information about the work."
                )
            )

        return value


# =========================================================
# PUBLIC BUSINESS REVIEW FORM
# =========================================================


class PublicBusinessReviewForm(
    forms.ModelForm
):
    """
    Customer-facing review form.

    Only customer-written review content is exposed.

    The customer, business, job and moderation status are
    never selectable through this form. Those trusted values
    are attached by the server from the signed review link.
    """

    class Meta:
        model = BusinessReview

        fields = [
            "rating",
            "comment",
        ]

        widgets = {

            "rating": forms.RadioSelect(
                attrs={
                    "class": "rating-radio",
                }
            ),

            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "maxlength": 2000,
                    "placeholder": (
                        "Tell others about the service you "
                        "received. What went well?"
                    ),
                }
            ),

        }


    def clean_comment(self):
        value = (
            self.cleaned_data.get(
                "comment",
                "",
            )
            .strip()
        )

        return value