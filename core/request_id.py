import uuid


class RequestIDMiddleware:
    """
    Attach a unique reference ID to every TradeFlow request.

    The request ID is available internally as:

        request.request_id

    It is also returned to the browser as:

        X-Request-ID

    No passwords, API keys, form contents or private data
    are stored in the request ID.
    """

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):

        request_id = uuid.uuid4().hex

        request.request_id = request_id

        response = self.get_response(
            request
        )

        response[
            "X-Request-ID"
        ] = request_id

        return response