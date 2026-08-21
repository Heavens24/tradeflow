from django.urls import path

from . import public_views
from . import views


app_name = "core"


urlpatterns = [
    # =====================================================
    # HOME / AUTHENTICATION
    # =====================================================
    path(
        "",
        views.home,
        name="home",
    ),

    path(
        "register/",
        views.register_view,
        name="register",
    ),

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),

    # Django login_required uses /accounts/login/ by default
    # unless LOGIN_URL is configured.
    #
    # Keep this alias so all existing @login_required views
    # continue working without requiring a settings.py change.
    path(
        "accounts/login/",
        views.login_view,
        name="login_legacy",
    ),


    # =====================================================
    # DASHBOARD
    # =====================================================
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),


    # =====================================================
    # BUSINESS
    # =====================================================

    # Existing private business setup.
    path(
        "business/setup/",
        views.business_setup,
        name="business_setup",
    ),


    # Private public-profile settings.
    path(
        "business/public-profile/",
        public_views.public_profile_settings,
        name="public_profile_settings",
    ),


    # Public business mini-page.
    #
    # Example:
    #
    # /business/march24-electrical-services/
    path(
        "business/<slug:slug>/",
        public_views.public_business_profile,
        name="public_business_profile",
    ),


    # =====================================================
    # SIMPLE AI ASSISTANT
    # =====================================================
    path(
        "ai/document-assistant/",
        views.ai_document_assistant,
        name="ai_document_assistant",
    ),


    # =====================================================
    # CUSTOMERS
    # =====================================================
    path(
        "customers/",
        views.customer_list,
        name="customer_list",
    ),

    path(
        "customers/new/",
        views.customer_create,
        name="customer_create",
    ),

    path(
        "customers/<int:customer_id>/statement/",
        views.customer_statement,
        name="customer_statement",
    ),

    path(
        "customers/<int:customer_id>/statement/print/",
        views.customer_statement_print,
        name="customer_statement_print",
    ),

    path(
        "customers/<int:customer_id>/edit/",
        views.customer_edit,
        name="customer_edit",
    ),

    path(
        "customers/<int:customer_id>/delete/",
        views.customer_delete,
        name="customer_delete",
    ),


    # =====================================================
    # QUOTES
    # =====================================================
    path(
        "quotes/",
        views.quote_list,
        name="quote_list",
    ),

    path(
        "quotes/new/",
        views.quote_create,
        name="quote_create",
    ),

    path(
        "quotes/<int:quote_id>/",
        views.quote_detail,
        name="quote_detail",
    ),

    path(
        "quotes/<int:quote_id>/print/",
        views.quote_print,
        name="quote_print",
    ),

    path(
        "quotes/<int:quote_id>/edit/",
        views.quote_edit,
        name="quote_edit",
    ),

    path(
        "quotes/<int:quote_id>/delete/",
        views.quote_delete,
        name="quote_delete",
    ),

    path(
        "quotes/<int:quote_id>/convert-to-job/",
        views.quote_to_job,
        name="quote_to_job",
    ),


    # =====================================================
    # JOBS
    # =====================================================
    path(
        "jobs/",
        views.job_list,
        name="job_list",
    ),

    path(
        "jobs/new/",
        views.job_create,
        name="job_create",
    ),

    path(
        "jobs/<int:job_id>/",
        views.job_detail,
        name="job_detail",
    ),

    path(
        "jobs/<int:job_id>/edit/",
        views.job_edit,
        name="job_edit",
    ),

    path(
        "jobs/<int:job_id>/delete/",
        views.job_delete,
        name="job_delete",
    ),

    path(
        "jobs/<int:job_id>/create-invoice/",
        views.job_to_invoice,
        name="job_to_invoice",
    ),


    # =====================================================
    # INVOICES
    # =====================================================
    path(
        "invoices/",
        views.invoice_list,
        name="invoice_list",
    ),

    path(
        "invoices/new/",
        views.invoice_create,
        name="invoice_create",
    ),

    path(
        "invoices/<int:invoice_id>/",
        views.invoice_detail,
        name="invoice_detail",
    ),

    path(
        "invoices/<int:invoice_id>/print/",
        views.invoice_print,
        name="invoice_print",
    ),

    path(
        "invoices/<int:invoice_id>/edit/",
        views.invoice_edit,
        name="invoice_edit",
    ),

    path(
        "invoices/<int:invoice_id>/delete/",
        views.invoice_delete,
        name="invoice_delete",
    ),


    # =====================================================
    # PAYMENTS
    # =====================================================
    path(
        "payments/",
        views.payment_list,
        name="payment_list",
    ),

    path(
        "invoices/<int:invoice_id>/payment/",
        views.payment_create,
        name="payment_create",
    ),

    path(
        "payments/<int:payment_id>/delete/",
        views.payment_delete,
        name="payment_delete",
    ),
]