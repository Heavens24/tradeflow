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


# =========================================================
# TEMPORARY 500 TEST
# =========================================================


def test_500(request):
    """
    Temporary production test endpoint.

    This deliberately raises an exception so Django can
    render TradeFlow's custom 500 page when DEBUG=False.

    Remove this function after the production 500 test
    passes.
    """
    raise RuntimeError(
        "TradeFlow temporary 500 test"
    )