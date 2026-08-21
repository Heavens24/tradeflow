from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.urls import reverse_lazy


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
    # Confirmation page shown after the reset email
    # request has been submitted.
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="core/password_reset_done.html",
        ),
        name="password_reset_done",
    ),

    # Step 3:
    # Secure password-reset link sent to the user's email.
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
    # Confirmation shown after the password
    # has successfully been changed.
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="core/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),


    # =====================================================
    # TRADEFLOW APPLICATION
    # =====================================================
    # All normal TradeFlow routes remain managed by
    # core.urls, including login, registration, dashboard,
    # customers, quotations, jobs, invoices, payments,
    # settings, and the rest of the application.
    path(
        "",
        include("core.urls"),
    ),
]