"""Domain enumerations. Use these instead of free-form status strings."""
from enum import StrEnum


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CHANGED = "CHANGED"
    CANCELLED = "CANCELLED"


ACTIVE_BOOKING_STATUSES = {BookingStatus.CONFIRMED, BookingStatus.CHANGED}


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


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
