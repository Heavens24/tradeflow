import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Safely identify production staff accounts and optionally "
        "reset a matching admin password."
    )

    def handle(self, *args, **options):
        User = get_user_model()

        staff_users = User.objects.filter(
            is_staff=True
        ).order_by("username")

        if not staff_users.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No staff accounts exist in this database."
                )
            )
            return

        self.stdout.write(
            "Production staff accounts:"
        )

        for user in staff_users:
            self.stdout.write(
                (
                    f"- username={user.get_username()!r} "
                    f"superuser={user.is_superuser} "
                    f"active={user.is_active}"
                )
            )

        requested_username = os.getenv(
            "DJANGO_ADMIN_RESET_USERNAME",
            "",
        ).strip()

        new_password = os.getenv(
            "DJANGO_ADMIN_RESET_PASSWORD",
            "",
        ).strip()

        if not requested_username:
            self.stdout.write(
                self.style.WARNING(
                    "DJANGO_ADMIN_RESET_USERNAME is not set. "
                    "No password was changed."
                )
            )
            return

        if not new_password:
            raise CommandError(
                "DJANGO_ADMIN_RESET_PASSWORD is not set."
            )

        user = User.objects.filter(
            username__iexact=requested_username
        ).first()

        if not user:
            self.stdout.write(
                self.style.WARNING(
                    (
                        f"No account matched "
                        f"{requested_username!r}. "
                        "No password was changed."
                    )
                )
            )
            return

        if not user.is_staff:
            raise CommandError(
                (
                    f"{user.get_username()!r} exists "
                    "but is not a staff account."
                )
            )

        user.set_password(
            new_password
        )

        user.save(
            update_fields=[
                "password",
            ]
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    "Password successfully reset for "
                    f"{user.get_username()!r}."
                )
            )
        )