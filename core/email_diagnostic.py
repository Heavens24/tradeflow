from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import HttpResponse
from django.conf import settings
from django.middleware.csrf import get_token


@login_required
def email_diagnostic(request):
    """
    Temporary production email diagnostic.

    Sends one test email only to the currently
    authenticated user's registered Django email address.
    """

    recipient = (
        request.user.email or ""
    ).strip()

    if not recipient:
        return HttpResponse(
            "EMAIL TEST FAILED: "
            "Your TradeFlow account has no registered email address.",
            status=400,
            content_type="text/plain",
        )


    if request.method == "GET":

        csrf_token = get_token(request)

        return HttpResponse(
            f"""
            <!DOCTYPE html>
            <html lang="en">

            <head>
                <meta charset="UTF-8">

                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1.0"
                >

                <title>
                    Email Test | TradeFlow
                </title>
            </head>

            <body style="
                margin: 0;
                background: #f4f6f8;
                color: #1f2937;
                font-family: Arial, Helvetica, sans-serif;
            ">

                <div style="
                    max-width: 520px;
                    margin: 70px auto;
                    padding: 20px;
                ">

                    <div style="
                        background: white;
                        padding: 32px;
                        border-radius: 14px;
                        box-shadow: 0 5px 20px rgba(0,0,0,0.08);
                    ">

                        <h1>
                            TradeFlow Email Test
                        </h1>

                        <p>
                            This diagnostic will send one
                            production test email to your
                            registered TradeFlow email:
                        </p>

                        <p>
                            <strong>
                                {recipient}
                            </strong>
                        </p>

                        <form method="POST">

                            <input
                                type="hidden"
                                name="csrfmiddlewaretoken"
                                value="{csrf_token}"
                            >

                            <button
                                type="submit"
                                style="
                                    border: 0;
                                    padding: 13px 20px;
                                    border-radius: 8px;
                                    background: #111827;
                                    color: white;
                                    font-weight: 600;
                                    cursor: pointer;
                                "
                            >
                                Send Test Email
                            </button>

                        </form>

                    </div>

                </div>

            </body>

            </html>
            """,
            content_type="text/html",
        )


    try:

        result = send_mail(
            subject="TradeFlow production email test",
            message=(
                "This is a production email test from TradeFlow.\n\n"
                "If you received this message, "
                "TradeFlow email delivery through Resend is working."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                recipient,
            ],
            fail_silently=False,
        )


        return HttpResponse(
            (
                "EMAIL TEST SUCCESS\n\n"
                f"Messages sent: {result}\n"
                f"Recipient: {recipient}\n"
                f"Provider: {settings.EMAIL_PROVIDER}\n"
                f"From: {settings.DEFAULT_FROM_EMAIL}"
            ),
            content_type="text/plain",
        )


    except Exception as exc:

        return HttpResponse(
            (
                "EMAIL TEST FAILED\n\n"
                f"Error type: {type(exc).__name__}\n"
                f"Error: {exc}\n\n"
                f"Provider: {settings.EMAIL_PROVIDER}\n"
                f"From: {settings.DEFAULT_FROM_EMAIL}"
            ),
            status=500,
            content_type="text/plain",
        )