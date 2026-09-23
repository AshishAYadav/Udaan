"""Static, deterministic seed data."""

AIRPORTS = [
    ("DXB", "Dubai International Airport", "Dubai", "United Arab Emirates", "Asia/Dubai"),
    ("LHR", "London Heathrow Airport", "London", "United Kingdom", "Europe/London"),
    ("JFK", "John F. Kennedy International Airport", "New York", "United States", "America/New_York"),
    ("DEL", "Indira Gandhi International Airport", "Delhi", "India", "Asia/Kolkata"),
    ("BOM", "Chhatrapati Shivaji Maharaj International Airport", "Mumbai", "India", "Asia/Kolkata"),
    ("BLR", "Kempegowda International Airport", "Bengaluru", "India", "Asia/Kolkata"),
    ("SIN", "Singapore Changi Airport", "Singapore", "Singapore", "Asia/Singapore"),
    ("CDG", "Paris Charles de Gaulle Airport", "Paris", "France", "Europe/Paris"),
    ("FRA", "Frankfurt Airport", "Frankfurt", "Germany", "Europe/Berlin"),
    ("DOH", "Hamad International Airport", "Doha", "Qatar", "Asia/Qatar"),
    ("SYD", "Sydney Kingsford Smith Airport", "Sydney", "Australia", "Australia/Sydney"),
    ("HND", "Tokyo Haneda Airport", "Tokyo", "Japan", "Asia/Tokyo"),
]

# (origin, destination, duration_minutes, distance_km, flight_number)
ROUTES = [
    ("DXB", "LHR", 450, 5470, "UD101"),
    ("DEL", "DXB", 215, 2190, "UD103"),
    ("BOM", "SIN", 330, 3900, "UD105"),
    ("LHR", "JFK", 480, 5540, "UD107"),
    ("BLR", "DEL", 165, 1740, "UD109"),
    ("LHR", "DXB", 420, 5470, "UD102"),
    ("DXB", "DEL", 190, 2190, "UD104"),
    ("SIN", "BOM", 350, 3900, "UD106"),
    ("JFK", "LHR", 415, 5540, "UD108"),
    ("DEL", "BLR", 170, 1740, "UD110"),
    ("DOH", "CDG", 400, 4970, "UD111"),
    ("FRA", "SIN", 740, 10260, "UD113"),
    ("SYD", "SIN", 480, 6290, "UD115"),
    ("HND", "SIN", 430, 5320, "UD117"),
]

# Seeded timetable: flight number -> (day parity, local departure "HH:MM").
# Five flights a day. Even days fly the "eastbound bank", odd days the returns. Times are
# chosen so banks connect within the connection rules, e.g.
#   BLR 06:00 -> DEL 08:45 | DEL 11:00 -> DXB | DXB 16:00 -> LHR | LHR 22:30 -> JFK
#   LHR 08:00 -> DXB 18:00 | DXB 21:00 -> DEL
TIMETABLE = {
    "UD109": (0, "06:00"),
    "UD105": (0, "09:00"),
    "UD103": (0, "11:00"),
    "UD101": (0, "16:00"),
    "UD107": (0, "22:30"),
    "UD102": (1, "08:00"),
    "UD106": (1, "09:00"),
    "UD110": (1, "17:00"),
    "UD108": (1, "18:00"),
    "UD104": (1, "21:00"),
}

# model -> (cabin configuration, bassinet positions)
AIRCRAFT_TYPES = {
    "A350-900": ({"FIRST": 8, "BUSINESS": 36, "PREMIUM_ECONOMY": 24, "ECONOMY": 232}, 6),
    "B787-9": ({"BUSINESS": 30, "PREMIUM_ECONOMY": 28, "ECONOMY": 232}, 4),
    "A321neo": ({"BUSINESS": 12, "ECONOMY": 180}, 2),
    "B777-300ER": ({"FIRST": 8, "BUSINESS": 42, "PREMIUM_ECONOMY": 24, "ECONOMY": 280}, 8),
    "A320neo": ({"ECONOMY": 180}, 0),
}
AIRCRAFT_COUNT = 15  # 5 flights/day; each aircraft flies every 3rd day, well clear of block + turnaround time

CABIN_CLASSES = [
    ("ECONOMY", "Economy", "Standard economy cabin", 1, 25),
    ("PREMIUM_ECONOMY", "Premium Economy", "Extra legroom and enhanced service", 2, 30),
    ("BUSINESS", "Business", "Lie-flat seats, lounge access and priority services", 3, 40),
    ("FIRST", "First", "Private suites with dedicated service", 4, 50),
]

TIERS = [
    {
        "tier_id": "BRONZE",
        "name": "Bronze",
        "priority": 1,
        "eligible_ssrs": ["MEAL", "WHEELCHAIR"],
        "free_ssrs": ["WHEELCHAIR"],
        "ssr_discount_percent": 0.0,
        "extra_baggage_kg": 0,
        "benefits": ["Earn miles on every flight"],
    },
    {
        "tier_id": "SILVER",
        "name": "Silver",
        "priority": 2,
        "eligible_ssrs": ["MEAL", "WHEELCHAIR", "EXCESS_BAGGAGE"],
        "free_ssrs": ["WHEELCHAIR"],
        "ssr_discount_percent": 10.0,
        "extra_baggage_kg": 5,
        "benefits": ["Priority check-in", "10% off paid services", "+5 kg baggage"],
    },
    {
        "tier_id": "GOLD",
        "name": "Gold",
        "priority": 3,
        "eligible_ssrs": ["MEAL", "LOUNGE", "WHEELCHAIR", "BASSINET", "EXCESS_BAGGAGE"],
        "free_ssrs": ["WHEELCHAIR", "LOUNGE"],
        "ssr_discount_percent": 20.0,
        "extra_baggage_kg": 15,
        "benefits": ["Priority check-in and boarding", "Complimentary lounge", "20% off paid services", "+15 kg baggage"],
    },
]

# (username, first, last, email, phone, tier). Sandbox password for all customers: CUSTOMER_PASSWORD.
USERS = [
    ("john", "John", "Smith", "john.smith@example.com", "+971500000001", "GOLD"),
    ("priya", "Priya", "Sharma", "priya.sharma@example.com", "+919800000002", "SILVER"),
    ("ahmed", "Ahmed", "Khan", "ahmed.khan@example.com", "+971500000003", "BRONZE"),
    ("emma", "Emma", "Wilson", "emma.wilson@example.com", "+447700000004", "GOLD"),
    ("rahul", "Rahul", "Verma", "rahul.verma@example.com", "+919800000005", "BRONZE"),
    ("sofia", "Sofia", "Garcia", "sofia.garcia@example.com", "+33600000006", "SILVER"),
]
CUSTOMER_PASSWORD = "password123"

ADMIN = {
    "username": "admin",
    "password": "admin",  # sandbox default; change in any shared environment
    "first_name": "System",
    "last_name": "Administrator",
    "email": "admin@udaan.example",
}

SSR_CATALOG = [
    {
        "ssr_type": "MEAL",
        "name": "Special meal",
        "description": "Pre-ordered special meal",
        "price": 15.0,
        "options": ["VGML", "AVML", "HNML", "KSML", "MOML", "CHML", "DBML"],
        "max_quantity": 1,
        "required_passenger_type": None,
        "min_flight_minutes": 90,
    },
    {
        "ssr_type": "LOUNGE",
        "name": "Lounge access",
        "description": "Departure lounge access",
        "price": 45.0,
        "options": [],
        "max_quantity": 1,
        "required_passenger_type": None,
        "min_flight_minutes": None,
    },
    {
        "ssr_type": "WHEELCHAIR",
        "name": "Wheelchair assistance",
        "description": "WCHR (ramp), WCHS (steps) or WCHC (cabin seat)",
        "price": 0.0,
        "options": ["WCHR", "WCHS", "WCHC"],
        "max_quantity": 1,
        "required_passenger_type": None,
        "min_flight_minutes": None,
    },
    {
        "ssr_type": "BASSINET",
        "name": "Bassinet",
        "description": "Bulkhead bassinet for an infant, subject to aircraft positions",
        "price": 20.0,
        "options": [],
        "max_quantity": 1,
        "required_passenger_type": "INFANT",
        "min_flight_minutes": None,
    },
    {
        "ssr_type": "EXCESS_BAGGAGE",
        "name": "Excess baggage",
        "description": "Additional checked baggage in 5 kg blocks",
        "price": 30.0,
        "options": [],
        "max_quantity": 6,
        "required_passenger_type": None,
        "min_flight_minutes": None,
    },
]
