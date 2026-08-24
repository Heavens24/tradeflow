from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.urls import reverse_lazy


# =========================================================
# CUSTOM ERROR HANDLERS
# =========================================================
#
# These handlers are used when DEBUG=False.
#
# TradeFlow's branded production error handlers live in
# core/error_views.py.
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

    # -----------------------------------------------------
    # STEP 1
    # -----------------------------------------------------
    #
    # User enters their TradeFlow account email address.
    # -----------------------------------------------------

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name=(
                "core/password_reset.html"
            ),
            email_template_name=(
                "core/password_reset_email.txt"
            ),
            subject_template_name=(
                "core/password_reset_subject.txt"
            ),
            success_url=reverse_lazy(
                "password_reset_done"
            ),
        ),
        name="password_reset",
    ),


    # -----------------------------------------------------
    # STEP 2
    # -----------------------------------------------------

    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name=(
                "core/password_reset_done.html"
            ),
        ),
        name="password_reset_done",
    ),


    # -----------------------------------------------------
    # STEP 3
    # -----------------------------------------------------

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name=(
                "core/password_reset_confirm.html"
            ),
            success_url=reverse_lazy(
                "password_reset_complete"
            ),
        ),
        name="password_reset_confirm",
    ),


    # -----------------------------------------------------
    # STEP 4
    # -----------------------------------------------------

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name=(
                "core/password_reset_complete.html"
            ),
        ),
        name="password_reset_complete",
    ),


    # =====================================================
    # TRADEFLOW APPLICATION
    # =====================================================

    path(
        "",
        include(
            "core.urls"
        ),
    ),

]