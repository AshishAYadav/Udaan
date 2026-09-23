"""Application settings and prototype business-rule constants."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


class Settings:
    database_path: Path = _resolve_path(os.getenv("DATABASE_PATH", "data/airline.json"))
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    seed_days: int = int(os.getenv("SEED_DAYS", "60"))
    flights_per_day: int = 5

    airline_code: str = "UD"
    airline_name: str = "Udaan Airlines"
    currency: str = "USD"

    # Authentication (OAuth2 password flow issuing HS256 JWTs)
    jwt_secret: str = os.getenv("JWT_SECRET", "udaan-sandbox-dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "udaan-sandbox"
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))

    # Aircraft rotation: minimum ground time after arrival before the next departure
    turnaround_domestic_hours: int = 4
    turnaround_international_hours: int = 8

    # Connections: minimum connecting time and maximum layover (beyond it is a stopover)
    min_connection_domestic_minutes: int = int(os.getenv("MIN_CONNECTION_DOMESTIC_MINUTES", "60"))
    min_connection_international_minutes: int = int(os.getenv("MIN_CONNECTION_INTERNATIONAL_MINUTES", "90"))
    max_connection_domestic_hours: int = int(os.getenv("MAX_CONNECTION_DOMESTIC_HOURS", "4"))
    max_connection_international_hours: int = int(os.getenv("MAX_CONNECTION_INTERNATIONAL_HOURS", "24"))

    # Check-in window. checkin_opens_hours = 0 means check-in is open from booking.
    checkin_opens_hours: int = int(os.getenv("CHECKIN_OPENS_HOURS", "0"))
    checkin_closes_minutes: int = int(os.getenv("CHECKIN_CLOSES_MINUTES", "60"))

    # Business rules
    change_cutoff_hours: int = 24
    change_window_days: int = 7
    max_seats_per_booking: int = 9
    infant_max_age: int = 2
    child_max_age: int = 12
    child_fare_factor: float = 0.75
    infant_fare_factor: float = 0.10
    boarding_minutes_before_departure: int = 45


settings = Settings()
