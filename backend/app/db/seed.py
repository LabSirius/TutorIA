"""CLI to seed reference data into the database.

Usage:
    python -m app.db.seed prompts    # seed the 10 pedagogical prompt templates
"""
import argparse
import asyncio

from app.db import database
from app.db.seeds.prompt_templates import seed_prompt_templates


async def _seed_prompts() -> None:
    async with database.async_session() as session:
        async with session.begin():
            inserted = await seed_prompt_templates(session)
    print(f"Prompt template seed complete: {inserted} inserted (idempotent).")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.db.seed", description="Seed reference data."
    )
    parser.add_argument("target", choices=["prompts"], help="dataset to seed")
    args = parser.parse_args()

    if args.target == "prompts":
        asyncio.run(_seed_prompts())


if __name__ == "__main__":
    main()
