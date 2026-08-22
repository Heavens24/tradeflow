from django import forms

from .models import BusinessVerification


# =========================================================
# BUSINESS VERIFICATION APPLICATION FORM
# =========================================================


class BusinessVerificationForm(
    forms.ModelForm
):
    """
    Business-owner verification application.

    Administrative fields such as:
    - status
    - admin notes
    - reviewed by
    - reviewed at

    are deliberately excluded.

    Business owners can submit information for review,
    but they can never approve or verify themselves.
    """

    class Meta:
        model = BusinessVerification

        fields = [
            "legal_business_name",
            "registration_type",
            "registration_number",
            "contact_name",
            "contact_email",
            "contact_phone",
            "supporting_information",
        ]

        widgets = {

            "legal_business_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Registered or legal business name"
                    ),
                }
            ),

            "registration_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "registration_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "e.g. CIPC registration number"
                    ),
                }
            ),

            "contact_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Person responsible for this business"
                    ),
                }
            ),

            "contact_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Business verification email"
                    ),
                    "autocomplete": "email",
                }
            ),

            "contact_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Business verification phone number"
                    ),
                    "autocomplete": "tel",
                }
            ),

            "supporting_information": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "Provide any useful information that "
                        "can help TradeFlow confirm your "
                        "business identity or registration."
                    ),
                }
            ),

        }


    def clean_legal_business_name(self):
        value = (
            self.cleaned_data.get(
                "legal_business_name",
                "",
            )
            .strip()
        )

        if len(value) < 2:
            raise forms.ValidationError(
                "Please enter the legal business name."
            )

        return value


    def clean_registration_number(self):
        value = (
            self.cleaned_data.get(
                "registration_number",
                "",
            )
            .strip()
        )

        registration_type = (
            self.cleaned_data.get(
                "registration_type"
            )
        )

        if (
            registration_type
            != BusinessVerification.TYPE_SOLE_PROPRIETOR
            and not value
        ):
            raise forms.ValidationError(
                (
                    "Please provide the business "
                    "registration number."
                )
            )

        return value


    def clean_contact_name(self):
        value = (
            self.cleaned_data.get(
                "contact_name",
                "",
            )
            .strip()
        )

        if len(value) < 2:
            raise forms.ValidationError(
                "Please enter a contact person's name."
            )

        return value


    def clean_contact_phone(self):
        value = (
            self.cleaned_data.get(
                "contact_phone",
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