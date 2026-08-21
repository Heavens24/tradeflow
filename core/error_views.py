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

    The request ID allows a user-reported problem to be
    matched with the corresponding Render log entry.

    Do not log request bodies, passwords, tokens,
    API keys or other sensitive information.
    """

    username = "anonymous"

    if (
        hasattr(request, "user")
        and request.user.is_authenticated
    ):
        username = request.user.username


    request_id = getattr(
        request,
        "request_id",
        "unknown",
    )


    logger.warning(
        (
            "404 not found: "
            "request_id=%s "
            "path=%s "
            "user=%s"
        ),
        request_id,
        request.path,
        username,
    )


    return render(
        request,
        "core/404.html",
        {
            "request_id": request_id,
        },
        status=404,
    )


def custom_500(request):
    """
    Display TradeFlow's branded 500 page when an unexpected
    server error occurs.

    Django's django.request logger records the underlying
    exception and traceback. This handler adds the same
    request reference so the incident can be located
    quickly in Render logs.
    """

    username = "anonymous"

    if (
        hasattr(request, "user")
        and request.user.is_authenticated
    ):
        username = request.user.username


    request_id = getattr(
        request,
        "request_id",
        "unknown",
    )


    logger.error(
        (
            "500 server error: "
            "request_id=%s "
            "path=%s "
            "user=%s"
        ),
        request_id,
        request.path,
        username,
    )


    return render(
        request,
        "core/500.html",
        {
            "request_id": request_id,
        },
        status=500,
    )