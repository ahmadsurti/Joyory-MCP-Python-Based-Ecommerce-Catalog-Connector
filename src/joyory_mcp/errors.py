"""Friendly error types for Joyory MCP tools."""


class JoyoryError(Exception):
    """Base class for all Joyory errors."""


class JoyoryUnavailableError(JoyoryError):
    """Joyory is temporarily unreachable or returned a server error."""
    user_message = "Joyory search is temporarily unavailable. Please try again shortly."


class JoyoryNoResultsError(JoyoryError):
    """Search returned zero results."""
    def __init__(self, query: str):
        self.query = query
        super().__init__(f"No results for: {query}")

    @property
    def user_message(self) -> str:
        return f"Joyory returned no products for '{self.query}'."


class JoyoryProductNotFoundError(JoyoryError):
    """Product ID not found."""
    def __init__(self, product_id: str):
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")

    @property
    def user_message(self) -> str:
        return f"Unable to find product '{self.product_id}' on Joyory."


class JoyoryAPIChangedError(JoyoryError):
    """The discovered API endpoint no longer works."""
    user_message = "Joyory search is temporarily unavailable. Please try again shortly."


class JoyoryTimeoutError(JoyoryError):
    """Request to Joyory timed out."""
    user_message = "Joyory request timed out. Please try again."


def friendly_message(exc: Exception) -> str:
    """Return a user-facing error message from any exception."""
    if hasattr(exc, "user_message"):
        return exc.user_message
    return "Unable to retrieve product information from Joyory right now."
