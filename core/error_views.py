import logging

from django.shortcuts import render


logger = logging.getLogger(__name__)


# =========================================================
# CUSTOM ERROR HANDLERS
# =========================================================


def custom_404(request, exception):
    """
    Display TradeFlow's branded 404 page when a requested
    resource cannot be found.

    Log only basic diagnostic information.
    Do not log request bodies, passwords, tokens,
    API keys or other sensitive information.
    """

    username = "anonymous"

    if (
        hasattr(request, "user")
        and request.user.is_authenticated
    ):
        username = request.user.username


    logger.warning(
        "404 not found: path=%s user=%s",
        request.path,
        username,
    )


    return render(
        request,
        "core/404.html",
        status=404,
    )


def custom_500(request):
    """
    Display TradeFlow's branded 500 page when an unexpected
    server error occurs.

    Django's django.request logger records the underlying
    server exception and traceback. This handler adds a
    concise TradeFlow-specific event to the production log.
    """

    username = "anonymous"

    if (
        hasattr(request, "user")
        and request.user.is_authenticated
    ):
        username = request.user.username


    logger.error(
        "500 server error: path=%s user=%s",
        request.path,
        username,
    )


    return render(
        request,
        "core/500.html",
        status=500,
    )