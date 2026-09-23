"""Populate an empty database with deterministic reference data and schedules.

Run manually to rebuild the sandbox:  python -m app.seed.seeder --reset
The database is also rebuilt automatically when SCHEMA_VERSION changes.
"""
import argparse
from collections import Counter
from datetime import date, timedelta

from app.auth.security import hash_password
from app.config import settings
from app.db.database import get_db, reset_database, set_counter, transaction
from app.db.database import repositories as db
from app.models.enums import Role
from app.seed import data
from app.services import schedule_generator

SCHEMA_VERSION = 4
SEED_TIMESTAMP = "2026-01-01T00:00:00+00:00"


class IdFactory:
    """Generates sequential IDs in memory; counters are persisted once at the end."""

    def __init__(self):
        self.counts: Counter[str] = Counter()

    def __call__(self, prefix: str) -> str:
        self.counts[prefix] += 1
        return f"{prefix}{self.counts[prefix]:03d}"

    def persist(self) -> None:
        for prefix, value in self.counts.items():
            set_counter(prefix, value)


def _user(new_id: IdFactory, username: str, password: str, role: Role, first: str, last: str,
          email: str, phone: str = "", tier: str | None = None) -> dict:
    return {
        "user_id": new_id("USR"),
        "username": username,
        "password_hash": hash_password(password),
        "role": role.value,
        "first_name": first,
        "last_name": last,
        "email": email,
        "phone": phone,
        "tier_id": tier,
        "created_at": SEED_TIMESTAMP,
    }


def _seed_reference(new_id: IdFactory) -> None:
    airports = {
        code: {"airport_id": code, "iata_code": code, "name": name, "city": city, "country": country, "timezone": tz}
        for code, name, city, country, tz in data.AIRPORTS
    }
    db.airports.insert_many(airports.values())

    routes = [
        {
            "route_id": new_id("RT"),
            "origin": origin,
            "destination": destination,
            "duration_minutes": duration,
            "distance_km": distance,
            "active": True,
        }
        for origin, destination, duration, distance in data.ROUTES
    ]
    db.routes.insert_many(routes)

    aircraft = []
    models = [model for model, count in data.FLEET.items() for _ in range(count)]
    for i, model in enumerate(models):
        config, bassinets = data.AIRCRAFT_TYPES[model]
        aircraft.append(
            {
                "aircraft_id": new_id("AC"),
                "registration": f"VT-U{chr(65 + i // 26)}{chr(65 + i % 26)}",
                "model": model,
                "total_seats": sum(config.values()),
                "cabin_configuration": config,
                "bassinet_positions": bassinets,
            }
        )
    db.aircrafts.insert_many(aircraft)

    db.classes.insert_many(
        {"class_id": cid, "name": name, "description": desc, "rank": rank, "baggage_allowance_kg": bag}
        for cid, name, desc, rank, bag in data.CABIN_CLASSES
    )
    db.tiers.insert_many(data.TIERS)

    admin = data.ADMIN
    users = [_user(new_id, admin["username"], admin["password"], Role.ADMIN, admin["first_name"], admin["last_name"], admin["email"])]
    users += [
        _user(new_id, username, data.CUSTOMER_PASSWORD, Role.CUSTOMER, first, last, email, phone, tier)
        for username, first, last, email, phone, tier in data.USERS
    ]
    db.users.insert_many(users)
    db.ssr_catalog.insert_many({**item, "currency": settings.currency} for item in data.SSR_CATALOG)


def seed_database() -> dict:
    """Reference data, then generated schedules from tomorrow for `seed_days` days."""
    new_id = IdFactory()
    with transaction():
        _seed_reference(new_id)
        summary = schedule_generator.generate(
            date.today() + timedelta(days=1), settings.seed_days, seed=settings.seed_random_seed, new_id=new_id
        )
        new_id.persist()
        get_db().table("meta").insert({"schema_version": SCHEMA_VERSION})
    return summary


def _schema_version() -> int | None:
    rows = get_db().table("meta").all()
    return rows[0]["schema_version"] if rows else None


def init_database() -> bool:
    """Seed an empty database, or rebuild one created by an older schema. Returns True if seeded."""
    if not db.airports.is_empty() and _schema_version() == SCHEMA_VERSION:
        return False
    reset_database()
    seed_database()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Udaan sandbox database.")
    parser.add_argument("--reset", action="store_true", help="Delete all data and reseed")
    args = parser.parse_args()
    if args.reset:
        reset_database()
    print("Database seeded." if init_database() else "Database already up to date; use --reset to rebuild.")
    print(f"Flights: {db.flights.count()}, fares: {db.fares.count()}, aircraft: {db.aircrafts.count()}")


if __name__ == "__main__":
    main()
