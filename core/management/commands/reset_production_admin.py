import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Reset the password for the January22 production admin account."

    def handle(self, *args, **options):
        username = "January22"
        new_password = os.getenv("DJANGO_ADMIN_RESET_PASSWORD", "").strip()

        if not new_password:
            raise CommandError(
                "DJANGO_ADMIN_RESET_PASSWORD environment variable is not set."
            )

        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(
                f"Admin user {username!r} does not exist."
            )

        if not user.is_staff:
            raise CommandError(
                f"{username!r} exists but is not a staff account."
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Password successfully reset for {username!r}."
            )
        )