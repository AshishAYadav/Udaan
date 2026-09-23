"""Centralised TinyDB access.

A single TinyDB instance is shared by the whole application. Reads are served
from an in-memory cache. Writes go through a re-entrant lock; multi-step business
operations (e.g. check seat availability -> reserve seats) are grouped with
``with transaction():`` and flushed to disk once, when the outermost transaction
ends. A standalone write is its own transaction.
"""
import copy
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from threading import RLock
from typing import Any

from tinydb import TinyDB, where
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage

from app.config import settings

_lock = RLock()
_db: TinyDB | None = None
_depth = 0  # transaction nesting level; protected by _lock

COUNTERS_TABLE = "counters"


def get_db() -> TinyDB:
    global _db
    if _db is None:
        settings.database_path.parent.mkdir(parents=True, exist_ok=True)
        _db = TinyDB(settings.database_path, storage=CachingMiddleware(JSONStorage))
        _db.storage.WRITE_CACHE_SIZE = 10**9  # flushed explicitly at the end of each transaction
    return _db


def close_db() -> None:
    global _db
    if _db is not None:
        _db.close()
        _db = None


@contextmanager
def transaction():
    """Serialise a multi-step read/modify/write sequence and persist it once at the end."""
    global _depth
    with _lock:
        _depth += 1
        try:
            yield
        finally:
            _depth -= 1
            if _depth == 0:
                get_db().storage.flush()


class Repository:
    """Minimal repository over one TinyDB table keyed by a business identifier."""

    def __init__(self, table_name: str, key: str):
        self.table_name = table_name
        self.key = key

    @property
    def table(self):
        return get_db().table(self.table_name)

    def all(self) -> list[dict]:
        return [copy.deepcopy(dict(doc)) for doc in self.table.all()]

    def scan(self, predicate: Callable[[dict], bool]) -> list[dict]:
        """Read-only fast path: matching records without copying. Callers must not mutate them."""
        return [doc for doc in self.table.all() if predicate(doc)]

    def get(self, record_id: str) -> dict | None:
        doc = self.table.get(where(self.key) == record_id)
        return copy.deepcopy(dict(doc)) if doc else None

    def find(self, **filters: Any) -> list[dict]:
        return self.filter(lambda doc: all(doc.get(k) == v for k, v in filters.items()))

    def find_one(self, **filters: Any) -> dict | None:
        matches = self.find(**filters)
        return matches[0] if matches else None

    def filter(self, predicate: Callable[[dict], bool]) -> list[dict]:
        return [copy.deepcopy(dict(doc)) for doc in self.table.all() if predicate(doc)]

    def insert(self, record: dict) -> dict:
        with transaction():
            self.table.insert(record)
        return record

    def insert_many(self, records: Iterable[dict]) -> None:
        with transaction():
            self.table.insert_multiple(list(records))

    def update(self, record_id: str, changes: dict) -> dict | None:
        with transaction():
            self.table.update(changes, where(self.key) == record_id)
        return self.get(record_id)

    def remove(self, record_id: str) -> None:
        with transaction():
            self.table.remove(where(self.key) == record_id)

    def remove_where(self, **filters: Any) -> None:
        with transaction():
            self.table.remove(lambda doc: all(doc.get(k) == v for k, v in filters.items()))

    def count(self) -> int:
        return len(self.table)

    def is_empty(self) -> bool:
        return len(self.table) == 0

    def truncate(self) -> None:
        with transaction():
            self.table.truncate()


class Repositories:
    """All collections used by the application."""

    def __init__(self):
        self.users = Repository("users", "user_id")
        self.tiers = Repository("tiers", "tier_id")
        self.airports = Repository("airports", "airport_id")
        self.routes = Repository("routes", "route_id")
        self.aircrafts = Repository("aircrafts", "aircraft_id")
        self.classes = Repository("classes", "class_id")
        self.flights = Repository("flights", "flight_id")
        self.fares = Repository("fares", "fare_id")
        self.passengers = Repository("passengers", "passenger_id")
        self.payments = Repository("payments", "payment_id")
        self.bookings = Repository("bookings", "booking_id")
        self.booking_history = Repository("booking_history", "history_id")
        self.ssr_catalog = Repository("ssr_catalog", "ssr_type")
        self.ssrs = Repository("specialservicerequests", "ssr_id")
        self.checkins = Repository("checkins", "checkin_id")
        self.tickets = Repository("tickets", "ticket_id")
        self.payment_attempts = Repository("payment_attempts", "attempt_id")
        self.webhooks = Repository("webhooks", "webhook_id")
        self.webhook_deliveries = Repository("webhook_deliveries", "delivery_id")

    def every(self) -> list[Repository]:
        return list(vars(self).values())


repositories = Repositories()


def next_id(prefix: str) -> str:
    """Return the next sequential identifier for a prefix, e.g. BK001, BK002."""
    with transaction():
        counters = get_db().table(COUNTERS_TABLE)
        row = counters.get(where("prefix") == prefix)
        value = (row["value"] if row else 0) + 1
        counters.upsert({"prefix": prefix, "value": value}, where("prefix") == prefix)
    return f"{prefix}{value:03d}"


def set_counter(prefix: str, value: int) -> None:
    with transaction():
        get_db().table(COUNTERS_TABLE).upsert(
            {"prefix": prefix, "value": value}, where("prefix") == prefix
        )


def reset_database() -> None:
    with transaction():
        for repo in repositories.every():
            repo.truncate()
        get_db().table(COUNTERS_TABLE).truncate()
        get_db().table("meta").truncate()
