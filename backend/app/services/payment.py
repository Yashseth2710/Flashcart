"""A stand-in for a payment provider.

Real card handling belongs with a provider who is certified to do it; nothing
here touches a real card and no card number is stored. What this exists for is
to keep the shape of the real thing: a call that takes an amount, can decline,
and returns a reference the order can be reconciled against.

Test numbers follow the convention providers use, so the failure paths can be
driven from the interface rather than only from a test.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal

# The number a provider's sandbox reserves for a decline.
ALWAYS_DECLINES = "4000000000000002"


@dataclass(frozen=True)
class Charge:
    reference: str
    amount: Decimal


class PaymentGateway:
    def charge(self, *, amount: Decimal, card_number: str) -> Charge | None:
        """Returns the charge, or None if it was declined.

        Declining is a normal outcome rather than an error, so the caller has to
        decide what to do about it instead of an exception unwinding the work.
        """
        if card_number.replace(" ", "") == ALWAYS_DECLINES:
            return None
        return Charge(reference=f"ch_{uuid.uuid4().hex[:24]}", amount=amount)
