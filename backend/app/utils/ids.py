"""Identifier and PNR generation."""
import secrets

from app.db.database import next_id, repositories

# Excludes easily confused characters (0/O, 1/I).
PNR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_pnr() -> str:
    """Return a unique 6-character alphanumeric sandbox booking reference."""
    while True:
        pnr = "".join(secrets.choice(PNR_ALPHABET) for _ in range(6))
        if not repositories.bookings.find_one(pnr=pnr):
            return pnr


def generate_ticket_number() -> str:
    """13-digit ticket number: 3-digit sandbox airline prefix + 10-digit serial."""
    serial = int(next_id("TKTNO")[len("TKTNO"):])
    return f"775{serial:010d}"


__all__ = ["next_id", "generate_pnr", "generate_ticket_number"]
