"""Seed data for the pedagogical prompt templates (Marco Pedagógico V2).

The content below preserves the placeholder text that previously lived in
backend/app/prompts/*.txt. These are NOT the final prompts: the pedagogical
team (Dra. Grajales) redacts the real prompts in Phase 2. Each row is marked
so nobody mistakes a placeholder for a validated prompt.

The seed is idempotent: it only inserts keys that do not already have an active
template, so it is safe to run repeatedly.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_template import PromptTemplate

_PLACEHOLDER = (
    "[PLACEHOLDER — pendiente de redacción por la Dra. Grajales durante la Fase 2]"
)


def _content(body: str) -> str:
    return f"{_PLACEHOLDER}\n\n{body}"


# (key, content) for the 10 pedagogical prompt keys. Content is Spanish because
# these are student-facing pedagogical artifacts, not code.
PROMPT_SEED: list[tuple[str, str]] = [
    (
        "system_base",
        _content(
            "Prompt base del sistema — personalidad de TutorIA.\n"
            "Define: identidad como agente docente, tono empático, reglas éticas,\n"
            "límites del agente (no evalúa sumativamente, no certifica, deriva crisis).\n"
            "Referencia: Marco Pedagógico V2, sección 2."
        ),
    ),
    (
        "diagnostic",
        _content(
            "Prompt de diagnóstico inicial de conocimientos previos.\n"
            "Activa conocimiento previo del estudiante con preguntas breves y abiertas.\n"
            "Incluye en contexto el mapa de prerrequisitos del concepto objetivo.\n"
            "Referencia: Marco Pedagógico V2, Estrategia 1.\n"
            "Variables: {{student_name}}, {{module_name}}, {{prerequisites}}."
        ),
    ),
    (
        "basic_explanation",
        _content(
            "Prompt de explicación básica adaptada al nivel del estudiante.\n"
            "Usa lenguaje sencillo, ejemplos concretos y analogías con el contexto\n"
            "rural de Risaralda (café, plátano, cooperativas, veredas).\n"
            "Evita notación técnica en primera instancia.\n"
            "Referencia: Marco Pedagógico V2, Estrategia 2.\n"
            "Variables: {{student_name}}, {{student_level}}, {{concept}}, {{module_name}}."
        ),
    ),
    (
        "advanced_explanation",
        _content(
            "Prompt de explicación avanzada con precisión técnica.\n"
            "Conecta el concepto con otros del dominio y con aplicaciones complejas.\n"
            "Para estudiantes con dominio previo demostrado.\n"
            "Referencia: Marco Pedagógico V2, Estrategia 2.\n"
            "Variables: {{student_name}}, {{concept}}, {{related_concepts}}, {{module_name}}."
        ),
    ),
    (
        "comprehension_check",
        _content(
            "Prompt de verificación activa de comprensión.\n"
            "Genera una pregunta que requiere demostrar comprensión, no solo recordar.\n"
            "Tipos: paráfrasis, ejemplo propio, aplicación directa, identificación\n"
            "de error, transferencia — en orden creciente de exigencia cognitiva.\n"
            "Referencia: Marco Pedagógico V2, Estrategia 3.\n"
            "Variables: {{student_name}}, {{concept}}, {{student_level}}."
        ),
    ),
    (
        "socratic",
        _content(
            "Prompt de andamiaje socrático.\n"
            "Guía una secuencia de preguntas que lleva al estudiante a construir la\n"
            "respuesta por sí mismo. Avanza desde lo que ya sabe hacia lo que no sabe.\n"
            "Secuencia: activar conocimiento previo → señalar brecha → orientar\n"
            "hacia solución → verificar comprensión genuina.\n"
            "Referencia: Marco Pedagógico V2, Estrategia 7.\n"
            "Variables: {{student_name}}, {{concept}}, {{known_concepts}}, {{student_level}}."
        ),
    ),
    (
        "cognitive_modeling",
        _content(
            "Prompt de modelado cognitivo explícito (thinking aloud).\n"
            "El agente verbaliza su proceso de pensamiento mientras resuelve un problema.\n"
            "Usa expresiones como: 'lo primero que me pregunto es...', 'aquí tengo que\n"
            "decidir entre... y prefiero... porque...', 'luego verifico si...'.\n"
            "Referencia: Marco Pedagógico V2, Estrategia 6.\n"
            "Variables: {{student_name}}, {{problem}}, {{module_name}}."
        ),
    ),
    (
        "error_feedback",
        _content(
            "Prompt de retroalimentación formativa de error.\n"
            "Cuando el estudiante comete un error: (1) identifica el tipo de error,\n"
            "(2) lo señala sin corregir de inmediato, (3) orienta hacia la autocorrección\n"
            "mediante una pregunta. Retroalimentación específica, orientada al proceso,\n"
            "accionable y oportuna (Hattie & Timperley, 2007).\n"
            "Referencia: Marco Pedagógico V2, Estrategia 4.\n"
            "Variables: {{student_name}}, {{student_answer}}, {{concept}}."
        ),
    ),
    (
        "risk_alert",
        _content(
            "Prompt de alerta de riesgo — derivar a docente.\n"
            "Cuando se detectan indicadores de riesgo (inactividad 5+ días, 3+ sesiones\n"
            "estancado, expresiones de frustración o desmotivación): expresar\n"
            "preocupación empática, preguntar qué pasa, ofrecer pausa, derivar\n"
            "a docente o bienestar universitario si es necesario.\n"
            "Referencia: Marco Pedagógico V2, sección 9 (ética É·5).\n"
            "Variables: {{student_name}}, {{risk_indicators}}."
        ),
    ),
    (
        "metacognitive_closure",
        _content(
            "Prompt de cierre metacognitivo de sesión.\n"
            "Preguntas de reflexión: ¿qué aprendiste hoy?, ¿qué te quedó claro?,\n"
            "¿qué te genera dudas?, ¿qué harías diferente la próxima vez?\n"
            "Actualiza el modelo del estudiante con esa información.\n"
            "Sugiere qué trabajar en la próxima sesión.\n"
            "Referencia: Marco Pedagógico V2, sección 6.1.3 paso 6-7.\n"
            "Variables: {{student_name}}, {{topics_covered}}, {{next_suggested_topic}}."
        ),
    ),
]


async def seed_prompt_templates(session: AsyncSession) -> int:
    """Insert any missing active prompt templates. Returns the number inserted.

    Idempotent: keys that already have an active template are skipped. The
    caller is responsible for committing the transaction.
    """
    existing_keys = set(
        (
            await session.execute(
                select(PromptTemplate.key).where(PromptTemplate.is_active.is_(True))
            )
        ).scalars().all()
    )

    inserted = 0
    for key, content in PROMPT_SEED:
        if key in existing_keys:
            continue
        session.add(
            PromptTemplate(
                key=key,
                content=content,
                version=1,
                is_active=True,
                created_by="system_seed",
            )
        )
        inserted += 1

    await session.flush()
    return inserted
