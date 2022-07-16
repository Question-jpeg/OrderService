from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
    PushTicketError,
)
from requests.exceptions import ConnectionError, HTTPError


# Basic arguments. You should extend this function with the push features you
# want to use, or simply pass in a `PushMessage` object.
def send_push_message(token, title, body, extra={"_displayInForeground": True}):
    response = PushClient().publish(
        PushMessage(to=token,
                    title=title,
                    body=body,
                    sound='default',
                    data=extra))

    response.validate_response()
