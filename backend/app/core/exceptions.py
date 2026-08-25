from fastapi import HTTPException, status


class EmailAlreadyRegistered(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="That email is already registered.",
        )


class InvalidCredentials(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password do not match.",
        )


class NotAuthenticated(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
        )


class NotPermitted(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account cannot do that.",
        )


class ProductNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That product does not exist.",
        )


class VariantNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That variant does not exist.",
        )


class StockBelowCommitted(HTTPException):
    def __init__(self, committed: int) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{committed} units are already reserved or sold. "
                "Set the total to at least that."
            ),
        )


class SaleNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That sale does not exist.",
        )


class SaleItemNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That product is not in the sale.",
        )


class NotEnoughStockToAllocate(HTTPException):
    def __init__(self, available: int) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Only {available} in the warehouse. " "Add stock or allocate fewer to the sale."
            ),
        )


class AlreadyInTheSale(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="That product is already in this sale.",
        )


class SaleAlreadyStarted(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="A sale that has started cannot be changed.",
        )


class StockIsSpokenFor(HTTPException):
    def __init__(self, committed: int) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{committed} units are already held or sold in this sale. "
                "They cannot be taken back."
            ),
        )


class OrdersMustBeKept(HTTPException):
    def __init__(self, count: int) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This account has {count} order{'s' if count != 1 else ''} on it and cannot "
                "be deleted. Contact support if you need it removed."
            ),
        )


class ConfirmationDoesNotMatch(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That is not the email address on this account.",
        )


class SaleNotRunning(HTTPException):
    def __init__(self, status_name: str) -> None:
        detail = (
            "This sale has not started yet."
            if status_name == "UPCOMING"
            else "This sale has ended."
        )
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class NotEnoughLeft(HTTPException):
    """Someone else got there first, between the page loading and the button."""

    def __init__(self, available: int) -> None:
        detail = (
            "That has just sold out."
            if available == 0
            else f"Only {available} left. Lower the quantity and try again."
        )
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class PurchaseLimitReached(HTTPException):
    def __init__(self, limit: int, already: int) -> None:
        held = f"You already have {already} of them." if already else ""
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"There is a limit of {limit} per person on this one. {held}".strip(),
        )


class ReservationNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That hold does not exist.",
        )


class ReservationNotActive(HTTPException):
    def __init__(self, status_name: str) -> None:
        wording = {
            "COMPLETED": "That hold has already been checked out.",
            "EXPIRED": "That hold has run out of time.",
            "CANCELLED": "That hold has already been let go.",
        }
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=wording.get(status_name, "That hold is no longer active."),
        )


class OrderNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That order does not exist.",
        )


class HoldAlreadyBought(HTTPException):
    """The unique index on orders.reservation_id refused a second order."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="That hold has already been checked out.",
        )


class PaymentDeclined(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="The payment was declined. Nothing has been charged.",
        )


class KeyReusedOnDifferentRequest(HTTPException):
    """Same idempotency key, different body: returning the old result would be a lie."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="That request key has already been used for a different order.",
        )


class SavedItemNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That product is not in your saved list.",
        )


class ReminderNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not being reminded about that sale.",
        )


class SaleAlreadyFinished(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="That sale has already ended.",
        )


class TooManyAttempts(HTTPException):
    """The caller is going faster than a person plausibly can.

    Answered with how long until the window turns over, so a well-behaved
    client can wait exactly that long instead of guessing or hammering.
    """

    def __init__(self, retry_after_seconds: int) -> None:
        moment = "a second" if retry_after_seconds <= 1 else f"{retry_after_seconds} seconds"
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"That is a lot of tries at once. Wait {moment} and go again.",
            headers={"Retry-After": str(retry_after_seconds)},
        )
