from django.shortcuts import render


# =========================================================
# CUSTOM ERROR HANDLERS
# =========================================================


def custom_404(request, exception):
    """
    Display TradeFlow's custom 404 page when a requested
    resource cannot be found.

    Django passes the exception automatically to this
    handler.
    """
    return render(
        request,
        "core/404.html",
        status=404,
    )


def custom_500(request):
    """
    Display TradeFlow's custom 500 page when an unexpected
    server error occurs.
    """
    return render(
        request,
        "core/500.html",
        status=500,
    )