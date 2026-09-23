"""Read-only reference data: airports, routes, tiers, users, cabin classes."""
from app.db.database import repositories as db
from app.utils.errors import BadRequestError, NotFoundError


# Airports

def list_airports() -> list[dict]:
    return sorted(db.airports.all(), key=lambda a: a["iata_code"])


def get_airport(code: str) -> dict:
    airport = db.airports.get(code.upper())
    if not airport:
        raise NotFoundError(f"Airport {code} not found.")
    return airport


def airport_map() -> dict[str, dict]:
    return {a["airport_id"]: a for a in db.airports.all()}


def airport_brief(airport: dict) -> dict:
    return {"code": airport["iata_code"], "name": airport["name"], "city": airport["city"]}


def is_domestic(origin: str, destination: str, airports: dict[str, dict] | None = None) -> bool:
    airports = airports or airport_map()
    return airports[origin]["country"] == airports[destination]["country"]


# Routes

def list_routes(active: bool | None = None) -> list[dict]:
    routes = db.routes.all()
    if active is not None:
        routes = [r for r in routes if r["active"] == active]
    return sorted(routes, key=lambda r: r["route_id"])


def get_route(route_id: str) -> dict:
    route = db.routes.get(route_id)
    if not route:
        raise NotFoundError(f"Route {route_id} not found.")
    return route


def find_route(origin: str, destination: str) -> dict | None:
    return db.routes.find_one(origin=origin.upper(), destination=destination.upper(), active=True)


def valid_routes(origin: str | None = None, destination: str | None = None) -> list[dict]:
    """Active routes whose airports both exist, enriched with airport details."""
    airports = airport_map()
    result = []
    for route in list_routes(active=True):
        if origin and route["origin"] != origin.upper():
            continue
        if destination and route["destination"] != destination.upper():
            continue
        if route["origin"] in airports and route["destination"] in airports:
            result.append(
                {
                    **route,
                    "origin_airport": airports[route["origin"]],
                    "destination_airport": airports[route["destination"]],
                }
            )
    return result


def source_airports() -> list[dict]:
    codes = {r["origin"] for r in valid_routes()}
    return [a for a in list_airports() if a["iata_code"] in codes]


def destination_airports(origin: str | None = None) -> list[dict]:
    if origin:
        get_airport(origin)
    codes = {r["destination"] for r in valid_routes(origin=origin)}
    return [a for a in list_airports() if a["iata_code"] in codes]


# Tiers and users

def list_tiers() -> list[dict]:
    return sorted(db.tiers.all(), key=lambda t: t["priority"])


def get_tier(tier_id: str) -> dict:
    tier = db.tiers.get(tier_id.upper())
    if not tier:
        raise NotFoundError(f"Tier {tier_id} not found.")
    return tier


def _with_tier(user: dict, tiers: dict[str, dict]) -> dict:
    return {**user, "tier": tiers.get(user.get("tier_id"))}


def list_users(tier_id: str | None = None) -> list[dict]:
    tiers = {t["tier_id"]: t for t in db.tiers.all()}
    users = db.users.find(tier_id=tier_id.upper()) if tier_id else db.users.all()
    return [_with_tier(u, tiers) for u in sorted(users, key=lambda u: u["user_id"])]


def get_user(user_id: str) -> dict:
    user = db.users.get(user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found.")
    return _with_tier(user, {t["tier_id"]: t for t in db.tiers.all()})


# Cabin classes

def list_classes() -> list[dict]:
    return sorted(db.classes.all(), key=lambda c: c["rank"])


def get_class(class_id: str) -> dict:
    cabin = db.classes.get(class_id)
    if not cabin:
        raise BadRequestError(f"Cabin class {class_id} does not exist.")
    return cabin


def class_names() -> dict[str, str]:
    return {c["class_id"]: c["name"] for c in db.classes.all()}
