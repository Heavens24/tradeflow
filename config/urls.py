from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.urls import reverse_lazy

from core.error_views import test_500


# =========================================================
# CUSTOM ERROR HANDLERS
# =========================================================

handler404 = "core.error_views.custom_404"

handler500 = "core.error_views.custom_500"


urlpatterns = [
    # =====================================================
    # DJANGO ADMIN
    # =====================================================
    path(
        "admin/",
        admin.site.urls,
    ),


    # =====================================================
    # PASSWORD RESET
    # =====================================================

    # Step 1:
    # User enters their TradeFlow account email address.
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="core/password_reset.html",
            email_template_name="core/password_reset_email.txt",
            subject_template_name="core/password_reset_subject.txt",
            success_url=reverse_lazy(
                "password_reset_done"
            ),
        ),
        name="password_reset",
    ),

    # Step 2:
    # Confirmation shown after reset request submission.
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="core/password_reset_done.html",
        ),
        name="password_reset_done",
    ),

    # Step 3:
    # Secure reset link contained in the user's email.
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="core/password_reset_confirm.html",
            success_url=reverse_lazy(
                "password_reset_complete"
            ),
        ),
        name="password_reset_confirm",
    ),

    # Step 4:
    # Password successfully changed.
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="core/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),


    # =====================================================
    # TEMPORARY 500 TEST
    # =====================================================
    #
    # This route exists only so we can verify the branded
    # production 500 page on Render.
    #
    # Remove this route immediately after the test passes.
    path(
        "500-test/",
        test_500,
        name="test_500",
    ),


    # =====================================================
    # TRADEFLOW APPLICATION
    # =====================================================
    path(
        "",
        include("core.urls"),
    ),
]