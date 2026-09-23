"""Generate flight schedules from the command line.

    python -m app.seed.generate_schedules --days 60 [--start 2026-10-01] [--seed 7] [--min 3 --max 4]

Uses the same validated generator as POST /api/admin/schedules/generate.
"""
import argparse
from datetime import date, timedelta

from app.services import schedule_generator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=date.fromisoformat, default=date.today() + timedelta(days=1))
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--min", dest="min_per_route", type=int, default=3)
    parser.add_argument("--max", dest="max_per_route", type=int, default=4)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    summary = schedule_generator.generate(args.start, args.days, args.min_per_route, args.max_per_route, args.seed)
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
