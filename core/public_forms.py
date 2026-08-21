from django import forms

from .models import BusinessPublicProfile


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
    """

    class Meta:
        model = BusinessPublicProfile

        fields = [
            "public_profile_enabled",
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