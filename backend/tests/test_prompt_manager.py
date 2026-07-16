import pytest
from sqlalchemy import func, select

from app.services import prompt_manager
from app.services.prompt_manager import PromptTemplateNotFoundError


# ---------------------------------------------------------------------------
# Adaptability rules (Marco V2) — pure, no DB
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"is_first_interaction": True}, "diagnostic"),
        ({"expressed_frustration": True}, "risk_alert"),
        ({"said_dont_know": True}, "basic_explanation"),
        ({"consecutive_errors": 2}, "socratic"),
        ({"sessions_stuck": 3}, "cognitive_modeling"),
        ({"student_level": "advanced"}, "advanced_explanation"),
        ({}, "basic_explanation"),
    ],
)
def test_select_prompt_type_rules(kwargs, expected):
    assert prompt_manager.select_prompt_type(**kwargs) == expected


def test_select_prompt_type_precedence():
    # New-student diagnostic outranks every other signal.
    assert (
        prompt_manager.select_prompt_type(
            is_first_interaction=True, expressed_frustration=True, consecutive_errors=5
        )
        == "diagnostic"
    )
    # Frustration outranks repeated errors.
    assert (
        prompt_manager.select_prompt_type(expressed_frustration=True, consecutive_errors=5)
        == "risk_alert"
    )


# ---------------------------------------------------------------------------
# get_prompt cache behaviour (DB loader mocked)
# ---------------------------------------------------------------------------

async def test_get_prompt_uses_cache_and_substitutes_variables(monkeypatch):
    async def fake_loader():
        return {"diagnostic": "Hola {{student_name}}, trabajemos {{module_name}}."}

    monkeypatch.setattr(prompt_manager, "_load_active_templates", fake_loader)
    prompt_manager.invalidate_cache()

    result = await prompt_manager.get_prompt(
        "diagnostic", {"student_name": "Ana", "module_name": "Variables"}
    )
    assert result == "Hola Ana, trabajemos Variables."


async def test_get_prompt_unknown_key_fails_loudly(monkeypatch):
    async def fake_loader():
        return {"diagnostic": "algo"}

    monkeypatch.setattr(prompt_manager, "_load_active_templates", fake_loader)
    prompt_manager.invalidate_cache()

    with pytest.raises(PromptTemplateNotFoundError):
        await prompt_manager.get_prompt("does_not_exist")


async def test_cache_invalidation_triggers_reload(monkeypatch):
    calls = {"n": 0}

    async def counting_loader():
        calls["n"] += 1
        return {"socratic": "contenido"}

    monkeypatch.setattr(prompt_manager, "_load_active_templates", counting_loader)
    prompt_manager.invalidate_cache()

    await prompt_manager.get_prompt("socratic")  # warms (load #1)
    await prompt_manager.get_prompt("socratic")  # served from cache (no load)
    assert calls["n"] == 1

    prompt_manager.invalidate_cache()
    await prompt_manager.get_prompt("socratic")  # reloads (load #2)
    assert calls["n"] == 2


# ---------------------------------------------------------------------------
# Seed integration (real test DB, no Ollama needed)
# ---------------------------------------------------------------------------

async def test_seed_prompt_templates_lands_ten_active_and_is_idempotent(db):
    from app.db.seeds.prompt_templates import PROMPT_SEED, seed_prompt_templates
    from app.models.prompt_template import PromptTemplate

    first = await seed_prompt_templates(db)
    await db.commit()
    assert first == len(PROMPT_SEED) == 10

    active = (
        await db.execute(
            select(func.count())
            .select_from(PromptTemplate)
            .where(PromptTemplate.is_active.is_(True))
        )
    ).scalar()
    assert active == 10

    # Re-running inserts nothing and does not duplicate rows.
    second = await seed_prompt_templates(db)
    await db.commit()
    assert second == 0
    total = (
        await db.execute(select(func.count()).select_from(PromptTemplate))
    ).scalar()
    assert total == 10
