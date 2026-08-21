import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class ReservationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class OrderStatus(str, enum.Enum):
    PAID = "PAID"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"


class IdempotencyStatus(str, enum.Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
