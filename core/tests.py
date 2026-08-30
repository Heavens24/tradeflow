from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Business,
    BusinessPublicProfile,
    BusinessSubscription,
    Customer,
    Invoice,
    Quote,
)


class DashboardOnboardingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="onboarding-owner",
            password="test-pass-12345",
        )
        self.business = Business.objects.create(
            owner=self.user,
            name="Onboarding Electrical",
            phone="0712345678",
            city="Bloemfontein",
        )
        BusinessSubscription.objects.create(
            business=self.business,
        )
        self.client.login(
            username="onboarding-owner",
            password="test-pass-12345",
        )

    def test_dashboard_starts_with_business_only_complete(self):
        response = self.client.get(
            reverse("core:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["onboarding_completed"],
            1,
        )
        self.assertEqual(
            response.context["onboarding_percentage"],
            17,
        )
        self.assertEqual(
            response.context["onboarding_next_url"],
            reverse("core:business_setup"),
        )

    def test_dashboard_progress_uses_real_business_data(self):
        self.business.email = "owner@example.com"
        self.business.address = "1 Main Street"
        self.business.save()

        profile = BusinessPublicProfile.objects.create(
            business=self.business,
            public_profile_enabled=True,
        )

        customer = Customer.objects.create(
            business=self.business,
            name="Thabo Mokoena",
            phone="0780608202",
        )

        quote = Quote.objects.create(
            business=self.business,
            customer=customer,
        )

        Invoice.objects.create(
            business=self.business,
            customer=customer,
            quote=quote,
        )

        response = self.client.get(
            reverse("core:dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(profile.public_profile_enabled)
        self.assertEqual(
            response.context["onboarding_completed"],
            6,
        )
        self.assertEqual(
            response.context["onboarding_percentage"],
            100,
        )
        self.assertTrue(
            response.context["onboarding_complete"]
        )

    def test_continue_setup_points_to_first_incomplete_step(self):
        self.business.email = "owner@example.com"
        self.business.address = "1 Main Street"
        self.business.save()

        response = self.client.get(
            reverse("core:dashboard")
        )

        self.assertEqual(
            response.context["onboarding_completed"],
            2,
        )
        self.assertEqual(
            response.context["onboarding_next_url"],
            reverse("core:public_profile_settings"),
        )
        self.assertFalse(
            response.context["marketplace_requires_pro"]
        )

    def test_free_business_can_manage_public_profile(self):
        response = self.client.get(
            reverse("core:public_profile_settings")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "core/public_business_settings.html",
        )
