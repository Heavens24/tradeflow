import resend

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    """
    Django email backend for sending email through
    the Resend HTTPS API.

    This avoids SMTP and therefore avoids SMTP port
    restrictions/timeouts on Render.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        resend.api_key = settings.RESEND_API_KEY


    def send_messages(self, email_messages):

        if not email_messages:
            return 0

        sent_count = 0

        for message in email_messages:

            try:

                recipients = list(message.to or [])

                if message.cc:
                    recipients.extend(message.cc)

                if message.bcc:
                    recipients.extend(message.bcc)

                if not recipients:
                    continue

                params = {
                    "from": (
                        message.from_email
                        or settings.DEFAULT_FROM_EMAIL
                    ),
                    "to": recipients,
                    "subject": message.subject,
                    "text": message.body,
                }

                # If Django supplied HTML content,
                # send that through Resend as well.
                for alternative in getattr(
                    message,
                    "alternatives",
                    [],
                ):
                    if (
                        len(alternative) >= 2
                        and alternative[1] == "text/html"
                    ):
                        params["html"] = alternative[0]
                        break

                resend.Emails.send(params)

                sent_count += 1

            except Exception:

                if not self.fail_silently:
                    raise

        return sent_count