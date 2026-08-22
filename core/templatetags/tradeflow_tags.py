from django import template

from core.models import (
    Business,
    QuoteRequest,
)


register = template.Library()


@register.simple_tag
def new_quote_request_count(user):
    """
    Return the number of NEW public quote requests belonging
    to the signed-in TradeFlow user's business.

    This template tag allows the main sidebar badge to work
    across Dashboard, Customers, Quotes, Jobs, Invoices,
    Payments, Settings and other authenticated pages without
    requiring every individual view to manually provide the
    quote-request count.
    """

    if not getattr(
        user,
        "is_authenticated",
        False,
    ):
        return 0


    business = Business.objects.filter(
        owner=user
    ).first()


    if not business:
        return 0


    return QuoteRequest.objects.filter(
        business=business,
        status="new",
    ).count()