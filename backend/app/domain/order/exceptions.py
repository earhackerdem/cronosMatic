class OrderNotFoundError(ValueError):
    """Raised when an order cannot be found or does not belong to the requester."""


class OrderCancellationError(ValueError):
    """Raised when an order cannot be cancelled (e.g. already shipped/delivered)."""
