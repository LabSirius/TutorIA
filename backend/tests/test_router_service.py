import pytest

from app.services.router_service import RequestRouter, request_router


@pytest.mark.parametrize(
    "message",
    [
        "Hola",
        "¿Qué es una variable en Python?",
        "Explícame en detalle el teorema de Bayes con demostración formal",
        "",
    ],
)
async def test_choose_provider_returns_ollama_for_any_input(message):
    result = await RequestRouter().choose_provider(
        message, {"student_level": "beginner"}
    )
    assert result == "ollama"


async def test_choose_provider_never_returns_claude():
    # Explicit equality guard: even a "complex" query must stay local for now.
    result = await request_router.choose_provider(
        "consulta muy compleja que requeriría razonamiento avanzado", {}
    )
    assert result == "ollama"
    assert result != "claude"
