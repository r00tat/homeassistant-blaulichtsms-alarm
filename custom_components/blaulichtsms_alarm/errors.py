"""Exceptions raised by the blaulichtSMS Alarm API client."""


class BlaulichtSmsError(Exception):
    """Base class for all blaulichtSMS Alarm API errors."""


class BlaulichtSmsApiError(BlaulichtSmsError):
    """The API answered with a result code other than OK."""

    def __init__(self, result: str, description: str | None = None) -> None:
        """Store the API result code and its description."""
        self.result = result
        self.description = description
        super().__init__(f"{result}: {description}" if description else result)


class BlaulichtSmsAuthError(BlaulichtSmsApiError):
    """The API rejected the credentials or the customer configuration."""
