"""Domain enumerations. Use these instead of free-form status strings."""
from enum import StrEnum


class BookingStatus(StrEnum):
    PENDING = "PENDING"  # held: PNR and seats reserved, awaiting payment
    CONFIRMED = "CONFIRMED"
    CHANGED = "CHANGED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"  # hold lapsed without payment


ACTIVE_BOOKING_STATUSES = {BookingStatus.CONFIRMED, BookingStatus.CHANGED}
# Statuses that hold seats and passengers (confirmed bookings plus unpaid holds)
HOLDING_BOOKING_STATUSES = ACTIVE_BOOKING_STATUSES | {BookingStatus.PENDING}


class PaymentStatus(StrEnum):
    """Status of a payment session (hosted checkout)."""

    PENDING = "PENDING"  # open, awaiting a successful card payment
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"  # superseded or booking cancelled before payment
    REFUNDED = "REFUNDED"


class PaymentAttemptResult(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    DECLINED = "DECLINED"


class CheckinStatus(StrEnum):
    NOT_CHECKED_IN = "NOT_CHECKED_IN"
    CHECKED_IN = "CHECKED_IN"


class TicketStatus(StrEnum):
    NOT_ISSUED = "NOT_ISSUED"
    ISSUED = "ISSUED"
    CANCELLED = "CANCELLED"


class FlightStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    DELAYED = "DELAYED"
    DEPARTED = "DEPARTED"
    CANCELLED = "CANCELLED"


BOOKABLE_FLIGHT_STATUSES = {FlightStatus.SCHEDULED, FlightStatus.DELAYED}


class FlightPhase(StrEnum):
    """Operational phase derived from the stored status and the departure timeline."""

    SCHEDULED = "SCHEDULED"
    CHECKIN_OPEN = "CHECKIN_OPEN"
    CHECKIN_CLOSED = "CHECKIN_CLOSED"
    BOARDING = "BOARDING"
    GATE_CLOSED = "GATE_CLOSED"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"
    CANCELLED = "CANCELLED"


class PassengerType(StrEnum):
    ADULT = "ADULT"
    CHILD = "CHILD"
    INFANT = "INFANT"


class Gender(StrEnum):
    M = "M"
    F = "F"
    X = "X"


class CabinClass(StrEnum):
    ECONOMY = "ECONOMY"
    PREMIUM_ECONOMY = "PREMIUM_ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"


class SSRType(StrEnum):
    MEAL = "MEAL"
    LOUNGE = "LOUNGE"
    WHEELCHAIR = "WHEELCHAIR"
    BASSINET = "BASSINET"
    EXCESS_BAGGAGE = "EXCESS_BAGGAGE"


class SSRStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Role(StrEnum):
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


class Direction(StrEnum):
    OUTBOUND = "OUTBOUND"
    RETURN = "RETURN"


class TripType(StrEnum):
    ONE_WAY = "ONE_WAY"
    ROUND_TRIP = "ROUND_TRIP"
