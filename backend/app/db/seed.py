"""CLI to seed reference data into the database.

Usage:
    python -m app.db.seed prompts    # seed the 10 pedagogical prompt templates
    python -m app.db.seed badges     # seed the gamification badges
    python -m app.db.seed all        # seed everything
"""
import argparse
import asyncio

from app.db import database
from app.db.seeds.badges import seed_badges
from app.db.seeds.prompt_templates import seed_prompt_templates


async def _seed_prompts() -> None:
    async with database.async_session() as session:
        async with session.begin():
            inserted = await seed_prompt_templates(session)
    print(f"Prompt template seed complete: {inserted} inserted (idempotent).")


async def _seed_badges() -> None:
    async with database.async_session() as session:
        async with session.begin():
            inserted = await seed_badges(session)
    print(f"Badge seed complete: {inserted} inserted (idempotent).")


async def _seed_all() -> None:
    await _seed_prompts()
    await _seed_badges()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.db.seed", description="Seed reference data."
    )
    parser.add_argument(
        "target", choices=["prompts", "badges", "all"], help="dataset to seed"
    )
    args = parser.parse_args()

    runners = {
        "prompts": _seed_prompts,
        "badges": _seed_badges,
        "all": _seed_all,
    }
    asyncio.run(runners[args.target]())


if __name__ == "__main__":
    main()
