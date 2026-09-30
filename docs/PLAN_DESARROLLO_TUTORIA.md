# Plan de Desarrollo TutorIA — Flujo Robusto

> Guía paso a paso para construir TutorIA.
> Cada fase pendiente incluye el **prompt exacto** que debes darle a Claude Code en VS Code.
>
> **Actualizado tras la migración a Verawood y la decisión del Escenario B** (septiembre 2026).
> Las fases completadas describen el sistema **tal como existe hoy**; las pendientes
> conservan el formato de prompt.
> Referencias: [Requerimientos V2](TutorIA_Requerimientos_V2.md) · [Marco Pedagógico V2](MArco_V2_texto.md)

---

## Estado actual

| Fase | Estado |
|------|--------|
| **FASE 0** — Contexto | ✅ Completada |
| **FASE 1** — Backend (API + BD + LLM) | ✅ Completada |
| **FASE 2** — Refactor a Requerimientos V2 | ✅ Completada (8 commits) |
| **FASE 3** — Integración con Open edX (Escenario B vía MCP, sobre Verawood) | 🟡 EN PROGRESO — 3.I ✅ (Verawood), 3.II ✅ (servidor MCP funcionando); falta 3.III/3.IV (framework + e2e) |
| **FASE 4** — Prompts pedagógicos | 🟡 Infraestructura lista; **falta la redacción pedagógica** |
| **FASE 5** — RAG: contenido pedagógico | 🟡 Pipeline listo; **falta el contenido + CLI de ingesta** |
| **FASE 6** — Panel docente + Analytics | 🟡 Endpoints listos; **falta la UI** |
| **FASE 7** — Evals del agente | ⬜ Pendiente |
| **FASE 8** — Deploy y piloto (Azure) | ⬜ Pendiente |

**Regla de oro:** cada fase produce algo funcional y testeado antes de pasar a la siguiente.

**Camino crítico hoy:** FASE 3 (integración con Open edX) sigue siendo la prioridad.
La decisión de arquitectura ya está tomada (**Escenario B: TutorIA autónomo, expuesto
vía MCP**) y el entorno ya está migrado a **Open edX Verawood**. El servidor MCP ya está
construido y probado con respuesta real del modelo (3.II ✅); el trabajo restante de la
fase es instalar y configurar el framework `openedx-ai-extensions` e integrarlo de
extremo a extremo (3.III/3.IV). Luego FASE 4
(prompts) y FASE 5 (contenido), que pueden ejecutarse en paralelo si la Dra. Grajales
tiene disponibilidad. Sin los prompts reales, TutorIA es un tutor *arquitectónicamente*,
pero no *pedagógicamente*.

---

## Visión general del flujo

```
FASE 0 → FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6 → FASE 7 → FASE 8
Contexto Backend  RefactorV2 OpenedX  Prompts  RAG     Panel    Evals    Deploy
  ✅       ✅        ✅        🟡       🟡      🟡       🟡       ⬜       ⬜
```

---

## FASE 0 — Dar contexto a Claude Code ✅

Antes de pedir código, Claude Code debe leer: `README.md`, `CONTRIBUTING.md`,
`docs/TutorIA_Requerimientos_V2.md`, `docs/MArco_V2_texto.md` y
`docs/tutoria_architecture.svg`.

Contexto clave que debe confirmar:

- Agente tutor virtual con IA para Open edX (Open edX ya corre en un servidor propio).
- Motor LLM: **Ollama local** (contenedorizado) con API compatible con OpenAI.
  Sin API key de pago hoy; Claude API se incorporará por clasificador (RF-23).
- Backend Python/FastAPI. **TutorIA es un servicio autónomo** que se integra con
  Open edX vía MCP (ver FASE 3), no una SPA aparte ni un XBlock con la lógica dentro.
- **PostgreSQL + pgvector es la única base de datos** (datos + vectores + prompts).
- Infraestructura final: servidor propio en Azure (IaaS).
- Todo el **código en inglés**; solo contenido pedagógico y textos de estudiante en español.
- Convención de commits del `CONTRIBUTING.md`; toda rama se crea desde `dev`.

---

## FASE 1 — Backend: API + BD + Servicio LLM ✅

Backend construido y refactorizado a V2. **Estructura real hoy:**

```
backend/
├── app/
│   ├── main.py                 # FastAPI: CORS, lifespan (checks + scheduler)
│   ├── config.py               # pydantic-settings (.env)
│   ├── routers/
│   │   ├── chat.py             # POST /api/chat
│   │   ├── sessions.py         # CRUD de sesiones
│   │   ├── students.py         # Perfil del estudiante
│   │   ├── feedback.py         # Retroalimentación continua + gamificación
│   │   ├── analytics.py        # Panel docente + trazabilidad
│   │   └── admin.py            # Disparador manual de sync Open edX
│   ├── services/
│   │   ├── chat_service.py     # process_chat_turn() — orquestación de un turno (REST + MCP)
│   │   ├── llm_service.py      # OllamaProvider.generate() + get_provider()
│   │   ├── router_service.py   # RequestRouter (placeholder RF-23)
│   │   ├── rag_service.py      # Pipeline RAG con pgvector
│   │   ├── embedding_client.py # Ollama /api/embeddings + retry
│   │   ├── chunking.py         # Chunking que preserva conceptos
│   │   ├── prompt_manager.py   # Prompts desde BD + caché + reglas Marco V2
│   │   ├── gamification_service.py
│   │   └── tts_service.py      # Placeholder TTS
│   ├── models/                 # SQLAlchemy + Pydantic (14 tablas)
│   │   ├── student.py  session.py  evaluation.py  module.py  analytics.py
│   │   └── content_chunk.py  prompt_template.py  gamification.py  teacher.py
│   ├── schemas/rag.py
│   ├── gateways/openedx_gateway/   # mongo_client · mysql_client · course_keys · schemas · sync_service
│   └── db/
│       ├── database.py         # Engine async (asyncpg)
│       ├── seed.py             # CLI: prompts | badges | all
│       ├── seeds/              # prompt_templates.py · badges.py
│       └── migrations/         # Alembic (3 migraciones)
├── mcp_server/                 # servidor MCP: server.py (FastMCP + tool chat_with_tutor)
├── requirements.txt  Dockerfile  pytest.ini  .env.example
└── tests/                      # 59 tests en verde (11 de la pasarela fallan al importar tras el cambio a MySQL/opaque keys, ver deuda técnica)
```

**Decisiones técnicas vigentes:**

- `llm_service.py` usa la librería `openai` contra `LLM_BASE_URL`
  (por defecto `http://localhost:11434/v1`), API key `ollama`, modelo `llama3.2`.
- **PostgreSQL en todos los entornos** vía `asyncpg`. No hay SQLite.
- **pgvector** es el vector store (no ChromaDB).
- Los prompts viven en la **base de datos**, no en archivos `.txt`.
- `requirements.txt`: fastapi, uvicorn, openai, sqlalchemy, **asyncpg**, **aiomysql**,
  **pgvector**, alembic, **motor**, **apscheduler**, pydantic-settings, python-multipart,
  httpx, pytest, pytest-asyncio, **mcp** (pin `>=1.20,<2`: la 2.x eliminó
  `mcp.server.fastmcp`; `FastMCP` pasó a llamarse `MCPServer`).

### Modelo de datos (14 tablas, columnas en inglés)

| Tabla | Contenido |
|---|---|
| `students` | perfil + `xp_points`, `current_streak_days`, `badges_earned` |
| `subjects` / `modules` | asignaturas y módulos (+ `external_id` para Open edX) |
| `sessions` | historial conversacional JSON (`role`, `content`, `timestamp`, `prompt_key`) |
| `evaluations` | eventos de retroalimentación (nombre histórico; ver RF-15) |
| `student_progress` · `analytics_events` | progreso y métricas |
| `content_chunks` | fragmentos + `embedding vector(768)` + índice HNSW |
| `prompt_templates` · `prompt_template_history` | prompts versionados + auditoría |
| `badges` · `student_badges` | gamificación (reglas en `criteria_json`) |
| `teachers` · `teacher_courses` | docentes y su asignación a asignaturas |

### Cómo levantarlo

```bash
docker compose up -d postgres ollama ollama-init   # infra + modelo de embeddings
cd backend
cp .env.example .env          # en host: OLLAMA_BASE_URL=http://localhost:11434
pip install -r requirements.txt
alembic upgrade head
python -m app.db.seed all     # prompts + badges
uvicorn app.main:app --reload
```

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"student_id": 1, "message": "Hola, quiero aprender Python"}'
```

---

## FASE 2 — Refactor a Requerimientos V2 ✅

Rama `feature/refactor-to-v2-requirements`. Ocho commits que alinearon el backend
con los Requerimientos V2. Adelantó además el código del pipeline RAG.

| Commit | Cambio | RF |
|---|---|---|
| `chore: switch database to postgresql with pgvector` | SQLite y ChromaDB fuera; una sola BD | RF-11, RF-25 |
| `feat: add v2 data model (rag, prompts, gamification, tracing)` | 7 tablas nuevas + HNSW | RF-11/16/18/21 |
| `refactor: move rag pipeline from chromadb to pgvector` | RAG transaccional con `<=>` | RF-11 |
| `chore: containerize ollama for local dev environment` | Ollama como servicio + `ollama-init` | RNF-08 |
| `refactor: store pedagogical prompts in database` | Prompts editables/versionados | RF-21 |
| `feat: prepare llm layer for future claude api routing` | Provider + `RequestRouter` | RF-23 |
| `feat: rename evaluations to feedback and add gamification` | `/api/feedback` + XP/rachas/insignias | RF-15/16/24 |
| `feat: add conversation traceability and openedx mongo gateway` | Transcripciones + pasarela | RF-18/22 |

**Deuda técnica que dejó** (ver también el final del documento):
autenticación por cabecera (`X-Teacher-Id`, `X-Admin-Token`) pendiente de JWT real;
números de gamificación PROVISIONALES. (Los nombres de colecciones de Mongo, que
eran "guesses", **ya se confirmaron en la FASE 3**.)

---

## FASE 3 — Integración con Open edX (Escenario B vía MCP) 🟡

Prioridad inmediata por directriz del Dr. José Jaramillo. Descubrir bloqueos
técnicos temprano y habilitar un demo tangible del sistema funcionando end-to-end,
aunque sea con prompts placeholder.

### Decisión de arquitectura: Escenario B — TutorIA autónomo, expuesto vía MCP

Tras evaluar dos escenarios de integración con el **AI Extension Framework**
(`openedx-ai-extensions`) de Open edX, el equipo (Dr. José, Ana, Sofía) decidió el
**Escenario B**:

- **Escenario A (descartado) — Adopción total:** TutorIA se reconstruye como
  configuración interna del framework (workflow profiles en Django admin). Se pierde
  la autonomía del backend, y la personalización profunda, la gamificación y la
  trazabilidad para investigación tendrían que reconstruirse dentro del framework.
- **Escenario B (elegido) — Adopción como puerta (vía MCP):** TutorIA **permanece
  como servicio autónomo** y se expone mediante el **Model Context Protocol (MCP)**,
  estándar abierto que el framework soporta oficialmente como cliente. Open edX solo
  actúa como punto de acceso: recibe la interacción del estudiante y la delega en
  TutorIA, que ejecuta toda la lógica pedagógica y devuelve la respuesta.

**Por qué B:** preserva íntegros los tres valores centrales de TutorIA —
personalización por estudiante (Nivel 2), estadísticas para el docente y gamificación —
porque todos viven en el backend autónomo. Menor acoplamiento al ciclo de releases de
Open edX, portabilidad a otros LMS (MCP es estándar), y un patrón de integración
novedoso y publicable (posicionamiento comunitario). El MCP es solo el canal de
comunicación; no interviene en la lógica pedagógica.

> Documentos de respaldo de esta decisión (en `docs/`):
> `Reporte_Verawood_TutorIA.docx`, `Escenarios_Integracion_TutorIA.docx`,
> `Plan_Escenario_B_TutorIA.docx`.

### Entorno: migrado de Teak a Verawood

El framework `openedx-ai-extensions` solo existe a partir de **Verawood**. El entorno
local se migró de Open edX Teak (Tutor 21) a **Open edX Verawood (Tutor 22)**.

**Hallazgo clave validado:** los esquemas de datos de MongoDB y MySQL son **idénticos**
entre Teak y Verawood. La pasarela validada en Teak funciona sin cambios en Verawood.

### Sub-fase 3.I — Migración del entorno a Verawood ✅ COMPLETADA

- Teak eliminado por completo (contenedores, imágenes, volúmenes, configuración).
- Tutor 22 (Verawood) instalado limpio en WSL2 (Ubuntu, Docker Desktop).
- Los 11 servicios de Verawood corriendo; superusuario `admin` creado.
- Curso de prueba re-importado con opaque key correcto
  (`course-v1:UTP+V001+2026_07_V1`).
- **Esquemas re-validados contra Verawood:**
  - MongoDB: `modulestore.active_versions`, `modulestore.structures`,
    `modulestore.definitions` (nombres idénticos a Teak).
  - MySQL: `student_courseenrollment` con las mismas columnas; matrículas en MySQL,
    no en MongoDB; formato opaque key `course-v1:ORG+COURSE+RUN`; `user_id` del admin
    = 4 (Tutor crea 3 usuarios de sistema antes del primer usuario real).
- Backend de TutorIA reconectado a la red `tutor_local_default`; resuelve `mongodb`
  y `mysql` por nombre de servicio.

**Estado de la pasarela (`app/gateways/openedx_gateway/`) tras la validación:**

- `mongo_client.py` — cliente async Mongo (Motor), degradación elegante.
- `mysql_client.py` — **nuevo**, cliente async MySQL (aiomysql) para matrículas.
- `course_keys.py` — **nuevo**, `parse_course_key()` para el formato opaque key.
- `sync_service.py` — actualizado: `sync_enrollments` lee de MySQL con JOIN a
  `auth_user`, filtra `is_active=1` y excluye usuarios de sistema; constantes de
  colección validadas.

### Sub-fase 3.II — Servidor MCP de TutorIA ✅ COMPLETADA

TutorIA queda expuesto como servidor MCP en el mismo proceso que FastAPI. **Estado real:**

- **SDK oficial de MCP** (`from mcp.server.fastmcp import FastMCP`), pin `mcp>=1.20,<2`.
- La orquestación de un turno se extrajo a **`app/services/chat_service.py`**:
  `process_chat_turn(db, student_id, message, session_id=None) -> ChatTurnResult`
  (campos `response`, `session_id`, `prompt_type_used`). El endpoint REST y el tool MCP
  llaman a la **misma** función; no hay pedagogía duplicada.
- Errores como **excepciones de dominio** (`StudentNotFound`, `SessionNotFound`): el
  router las traduce a `HTTPException(404)`, el tool MCP a un error legible.
- **`app/mcp_server/server.py`**: `FastMCP("tutoria")` con un único tool
  **`chat_with_tutor(student_id, message, session_id=None)`** que abre una sesión con el
  mismo sessionmaker de `get_db`, llama a `process_chat_turn` y devuelve
  `{assistant_message, session_id}`.
- Montado en **`/mcp`** (streamable-http). El *session manager* del MCP se ejecuta
  **combinado** con el `lifespan` existente de `main.py` (checks + scheduler), no lo
  reemplaza.
- El tool recibe el `student_id` **interno** de TutorIA (el mapeo del `user_id` de
  Open edX se difiere — TODO fase-3b).
- Verificado en aislamiento con `scripts/mcp_smoke_test.py` (cliente de la librería `mcp`
  contra `http://localhost:8000/mcp/`): conecta, lista el tool y devuelve respuesta real
  de `llama3.2`.

**Convención:** apuntar siempre a `/mcp/` **con barra final** (sin ella, un 307 podría
degradar a `http://` detrás del proxy de Azure).

> **Dato de rendimiento medido:** un turno real en CPU (modelo en frío + Open edX
> corriendo) tardó **~19.5 min**. Confirma que el RNF-01 (< 5 s) exige **GPU en Azure**.
> Pendiente medir un turno **en caliente y aislado** como línea base.

### Sub-fase 3.III — Instalación y configuración del framework en Verawood ⬜

- Instalar `openedx-ai-extensions` en el entorno Verawood.
- Configurar el **provider** Ollama en `AI_EXTENSIONS` (config de Tutor).
- Registrar el servidor MCP de TutorIA como servidor MCP externo
  (`AI_EXTENSIONS_MCP_CONFIGS`).
- Definir un **profile** que delegue en el MCP de TutorIA y un **scope**
  (UI slot + course_id) donde aparece el chat.

### Sub-fase 3.IV — Integración y prueba end-to-end ⬜

- El estudiante entra al curso, ve el widget de chat, envía un mensaje.
- El framework delega en el MCP de TutorIA; el motor responde con la lógica del Marco V2.
- Verificar que personalización, gamificación y trazabilidad operan de extremo a extremo,
  registrando estado en la BD de TutorIA.
- Documentar el flujo en `openedx/README.md`.

### Mejoras derivadas del framework (nuevas)

- **Streaming chat** (confirmado): adaptar `POST /api/chat` y el MCP a respuesta
  token por token (SSE). Mejora la UX, en especial en conexiones rurales lentas.
- **Educator assistant** (deseable, a validar con la Dra. Grajales): asistente
  conversacional para el docente que interprete las analíticas. Es alcance nuevo,
  no un requisito confirmado.

> El contenido pedagógico (prompts, RAG) y el endurecimiento/deploy que originalmente
> figuraban en el plan del Escenario B **convergen con las FASES 4/5 y 8 globales**;
> no se duplican aquí.

### Preguntas críticas con el Dr. José — RESUELTAS

- ✅ **Versión de Open edX:** Verawood (Tutor 22).
- ✅ **Plugin vs XBlock:** ninguno como contenedor de la lógica — TutorIA autónomo
  integrado vía MCP consumido por `openedx-ai-extensions` (Escenario B).
- 🔴 **Autenticación JWT Open edX ↔ TutorIA:** pendiente; se resolverá al integrar el
  framework y endurecer para el piloto (sigue siendo deuda de máxima prioridad).

---

## FASE 4 — Prompts pedagógicos 🟡

**Puede ejecutarse en paralelo con FASE 3** si la Dra. Grajales tiene disponibilidad.
Su trabajo no depende de Claude Code: redacta los 10 prompts en un documento y
luego se cargan a la base de datos. Mientras tanto, el equipo técnico avanza la
integración con Open edX.

### Qué falta

La **infraestructura está lista**: los 10 prompts existen en la tabla
`prompt_templates` con contenido marcado como
`[PLACEHOLDER — pendiente de redacción por la Dra. Grajales durante la Fase 4]`.

Falta **la redacción pedagógica real**. Esto se hace en Claude Chat (no en Claude Code),
porque requiere diseño pedagógico, y **debe validarlo la investigadora postdoctoral
antes de producción** (Marco V2, §6.2).

### Las 10 claves (`prompt_templates.key`)

`system_base` · `diagnostic` · `basic_explanation` · `advanced_explanation` ·
`comprehension_check` · `socratic` · `cognitive_modeling` · `error_feedback` ·
`risk_alert` · `metacognitive_closure`

### Cómo cargar el contenido redactado

Ya **no** se editan archivos `.txt` (esa carpeta se eliminó). Dos vías:

1. **Hoy:** editar `backend/app/db/seeds/prompt_templates.py` y re-ejecutar
   `python -m app.db.seed prompts` (idempotente: solo inserta lo que falta).
2. **Objetivo (RF-19/21):** endpoint de administración para que las docentes editen
   los prompts desde el panel, versionando en `prompt_template_history`.
   **Aún no existe — es trabajo pendiente de la FASE 6.**

### Reglas de adaptabilidad — estado real

Implementadas en `prompt_manager.select_prompt_type()`:

| Regla (Marco V2) | Estado |
|---|---|
| Estudiante nuevo → `diagnostic` | ✅ |
| Expresa frustración → `risk_alert` | ✅ |
| Responde "no sé" → `basic_explanation` | ✅ |
| Mismo error 2+ veces → `socratic` | ✅ |
| 3+ sesiones estancado → `cognitive_modeling` | ✅ (falta notificar al docente) |
| Nivel avanzado → `advanced_explanation` | ✅ |
| Acierta al primer intento → reducir andamiaje | ⬜ Fuera del MVP — deuda pedagógica |
| 5+ días sin usar → notificación proactiva | ⬜ Fuera del MVP — requiere sistema de notificaciones |

### Entregable

Los 10 prompts redactados y validados en la BD, y el agente comportándose como tutor.

---

## FASE 5 — RAG: contenido pedagógico 🟡

### Lo que ya existe ✅

`rag_service.py` sobre pgvector, entregado en el Refactor V2:

- `ingest_content(module_id, text)` — chunking que respeta párrafos (~500 tokens,
  overlap 50), embeddings con `nomic-embed-text` (768 dim) vía Ollama, e inserción
  **transaccional** (si falla un embedding, no se escribe nada; re-ingestar
  reemplaza los chunks del módulo de forma atómica).
- `search_context(query, module_id, top_k=3)` — vecinos más cercanos con `<=>`
  (distancia coseno), usando el índice HNSW.
- `delete_module_content(module_id)`.
- `POST /api/chat` ya inyecta el contexto recuperado como "Material de referencia".

> **Importante:** esto es recuperación, **no** entrenamiento. El LLM nunca se modifica.

> **Nota FASE 3:** la colección `modulestore.definitions` de Open edX (contenido real
> de cada bloque) es la fuente natural para ingestar contenido curricular directamente
> del LMS. Está identificada en `sync_service.py` como `DEFINITIONS_COLLECTION`
> (TODO fase-5), sin consumir todavía.

### Lo que falta ⬜

1. **El contenido** de Programación I e Introducción a la Matemática, contextualizado
   para Risaralda (se produce en Claude Chat → archivos de texto plano).
2. **El CLI de ingesta**, que nunca se construyó.

### Prompt para Claude Code

```
Crea el CLI de ingesta de contenido curricular:

  python -m app.cli ingest --module-id 1
  python -m app.cli ingest --all

Debe:
1. Leer el contenido del módulo desde modules.content_text (o desde un archivo
   con --file) y llamar a rag_service.ingest_content(module_id, text)
2. Imprimir el IngestionResult (chunks_inserted, total_tokens, avg_chunk_size)
3. Fallar con un mensaje claro si el modelo de embeddings no está disponible

Crea también backend/data/ con los archivos de contenido:
  data/programacion1/
    modulo01_pensamiento_computacional.txt
    modulo02_variables_tipos.txt
    modulo03_estructuras_control.txt
  data/matematica/
    modulo01_logica_proposicional.txt
    modulo02_teoria_conjuntos.txt

Commit: "feat: cli de ingesta de contenido curricular"
```

### Riesgo a validar pronto

`nomic-embed-text` no está verificado sobre **texto en español**. Al ingestar el
primer módulo, medir la calidad de recuperación; si es pobre, cambiar a un modelo
multilingüe es barato (solo reindexar, `Vector(768)` → ajustar dimensión si cambia).

---

## FASE 6 — Panel docente + Analytics 🟡

### Endpoints ya disponibles ✅

| Endpoint | Qué da |
|---|---|
| `GET /api/analytics/course/{id}/summary` | estudiantes activos, progreso, aprobación |
| `GET /api/analytics/student/{id}/detail` | módulos completados, evaluaciones, tiempo |
| `GET /api/analytics/course/{id}/alerts` | **stub — devuelve `[]`, falta implementar** |
| `GET /api/analytics/student/{id}/conversations` | sesiones paginadas (RF-18) |
| `GET /api/analytics/session/{id}/transcript` | historial completo + `prompt_key` por turno |
| `GET /api/feedback/gamification/{student_id}` | XP, racha, insignias |

Autorización: cabecera `X-Teacher-Id` validada contra `teacher_courses` (403 si la
docente no tiene la asignatura). **Es un placeholder hasta tener JWT.**

> **Nota Escenario B:** la **lógica** del panel (estos endpoints, métricas,
> trazabilidad) vive en el backend de TutorIA y **no cambia** con MCP. Lo que queda
> por definir es la **presentación** dentro de Open edX (¿MFE embebida en el Instructor
> Dashboard de Verawood? ¿vista propia?). Esa decisión de UX se toma durante la
> integración; no afecta la lógica de analytics.

### Lo que falta ⬜

```
Completa el panel docente:

1. Implementa GET /api/analytics/course/{id}/alerts (hoy devuelve []):
   - inactividad > 5 días
   - 3+ sesiones estancado en el mismo concepto
   - expresiones de frustración en el historial
   Reglas del Marco Pedagógico V2, §6.3.

2. Añade CRUD que el panel necesita y no existe:
   - teachers y teacher_courses (asignar docentes a asignaturas)
   - edición de prompts pedagógicos (RF-19/21) escribiendo en
     prompt_template_history con autor y fecha

3. UI del panel (la presentación dentro de Open edX se define en la integración):
   - Resumen del curso (métricas)
   - Lista de estudiantes con indicadores de riesgo
   - Detalle de estudiante (timeline, evaluaciones, gamificación)
   - Transcripción de conversaciones con la estrategia usada en cada turno
   - Editor de prompts pedagógicos

Commit: "feat: panel docente con analytics"
```

---

## FASE 7 — Evals del agente ⬜

Depende de las FASES 4 y 5: evaluar prompts placeholder no mide nada, y sin
contenido curricular ingestado no hay contexto real que evaluar.

### Prompt para Claude Code

```
Crea un framework de evaluaciones en backend/evals/:

backend/evals/
├── eval_runner.py          # Script que corre todas las evals
├── eval_cases/
│   ├── diagnostic.json     # Casos para el diagnóstico inicial
│   ├── adaptability.json   # Casos para las reglas de adaptabilidad
│   ├── basic_level.json    # Respuestas para estudiante principiante
│   ├── advanced_level.json # Respuestas para estudiante avanzado
│   ├── frustration.json    # Manejo emocional
│   ├── off_topic.json      # Preguntas fuera del módulo
│   └── safety.json         # No dar respuestas dañinas
└── eval_metrics.py         # Funciones de scoring

Cada archivo JSON tiene este formato:
{
  "test_name": "diagnostic_new_student",
  "student_profile": { "level": ..., "module": ..., "history": [] },
  "input_message": "Hola, soy nuevo aquí",
  "expected_behavior": [
    "Debe saludar por nombre",
    "Debe aplicar diagnóstico inicial",
    "No debe asumir conocimiento previo",
    "Debe hacer pregunta abierta, no de verdadero/falso"
  ],
  "forbidden_behavior": [
    "No debe dar la respuesta directamente",
    "No debe usar jerga técnica sin explicar"
  ]
}

eval_runner.py debe:
1. Cargar cada caso de prueba
2. Cargar el prompt correspondiente desde la BD con prompt_manager.get_prompt()
   (los prompts ya NO están en archivos .txt)
3. Enviar al LLM vía llm_service.get_provider("ollama").generate(...)
4. Evaluar la respuesta contra expected/forbidden behavior
5. Generar un reporte con score por categoría

Usa un LLM como juez (el mismo Ollama) — técnica "LLM-as-judge".

Nota: los nombres de archivos y claves van en inglés (regla del proyecto);
el contenido de los casos (mensajes, criterios) va en español.

Commit: "feat: framework de evaluaciones pedagógicas"
```

### Entregable

```bash
cd backend && python -m evals.eval_runner   # reporte con scores por categoría
```

---

## FASE 8 — Deploy y pruebas piloto (Azure) ⬜

> **Bloqueado por la compra del servidor Azure.** Sus especificaciones (RAM, GPU)
> determinan el tamaño máximo del modelo local y, por tanto, la calidad pedagógica.

En el Escenario B, el despliegue incluye tanto el backend de TutorIA (con su servidor
MCP montado en `/mcp`) como la instancia de Open edX Verawood con el framework
configurado para consumir ese MCP.

### Prompt para Claude Code

```
Prepara el proyecto para deploy:

1. Añade el servicio `backend` a docker-compose.yml:
   - depends_on: postgres (service_healthy) y ollama (service_healthy)
   - OLLAMA_BASE_URL=http://ollama:11434 (DNS interno de docker)
   - Ejecuta alembic upgrade head al arrancar
   - Expone el servidor MCP en /mcp (mismo proceso que la API REST)
   (postgres, ollama y ollama-init ya existen)

2. Crea docker-compose.prod.yml con overrides para producción:
   - Variables de entorno para el servidor Azure
   - Volúmenes persistentes
   - Health checks y restart policies
   - Decidir GPU passthrough para ollama (deploy.resources.reservations.devices)

3. Crea .github/workflows/ci.yml:
   - Lint (ruff)
   - Tests (pytest) con un servicio postgres+pgvector
   - Build de imágenes Docker
   - Deploy a Azure (trigger manual)

4. Crea scripts/setup.sh:
   - docker compose up -d postgres ollama ollama-init
   - alembic upgrade head
   - python -m app.db.seed all
   - Ingestar el contenido de los módulos
   - Crear usuario admin
   (ya NO instala Ollama en el host: está contenedorizado)

Commit: "chore: configuración de deploy y CI/CD"
```

### Antes del piloto

- Sustituir la autenticación por cabecera con **JWT de Open edX** (bloqueante:
  hay datos personales de estudiantes de por medio — Ley 1581 de 2012).
- Habilitar autenticación en las bases de datos y confirmar el aislamiento de los
  datos del estudiante (Habeas Data).
- Medir **RNF-01** (< 5 s por respuesta) sobre el hardware real de Azure.
  Inferencia solo-CPU probablemente no lo cumpla bajo carga.
- Validación pedagógica de los prompts por 2 docentes por asignatura (RNF-09).

---

## Resumen: qué se hace dónde

| Tarea | Herramienta | Fase |
|-------|-------------|------|
| Scaffolding del backend | Claude Code | 1 ✅ |
| Modelos de BD y migraciones | Claude Code | 1 ✅ |
| Servicio LLM + chat endpoint | Claude Code | 1 ✅ |
| Refactor a V2 (pgvector, prompts en BD, gamificación, pasarela) | Claude Code | 2 ✅ |
| Migración a Verawood + validación de esquemas | Sofía + Claude Chat | 3 ✅ |
| Actualización de la pasarela (mysql_client, course_keys) | Claude Code | 3 ✅ |
| Servidor MCP de TutorIA (`chat_service` + `mcp_server`) | Claude Code | 3 ✅ |
| Config del framework `openedx-ai-extensions` + integración e2e | Sofía + Claude Code | 3 ⬜ |
| **Diseño de prompts pedagógicos** | **Claude Chat + Dra. Grajales** | **4 🟡** |
| Carga de prompts a la BD | Claude Code (seed) | 4 |
| **Contenido de asignaturas** | **Claude Chat → archivos** | **5 🟡** |
| CLI de ingesta | Claude Code | 5 ⬜ |
| Panel docente (UI + CRUD + alertas) | Claude Code | 6 🟡 |
| Framework de evaluaciones | Claude Code | 7 ⬜ |
| Docker + CI/CD + Deploy | Claude Code | 8 ⬜ |
| Documentación y papers | Claude Chat | Continuo |

---

## Checklist por fase

- [x] **FASE 0** — Claude Code entiende el proyecto
- [x] **FASE 1** — Backend funcional: `POST /api/chat` responde
- [x] **FASE 2** — Refactor V2: PostgreSQL+pgvector, prompts en BD, gamificación,
      trazabilidad, pasarela Open edX (59 tests en verde)
- [ ] **FASE 3** — TutorIA integrado en Open edX Verawood vía MCP; la pasarela
      sincroniza datos reales
  - [x] 3.I — Migración a Verawood + validación de esquemas (idénticos a Teak)
  - [x] 3.II — Servidor MCP de TutorIA (`chat_with_tutor`), probado con cliente MCP (respuesta real de llama3.2)
  - [ ] 3.III — `openedx-ai-extensions` instalado y configurado (provider, MCP, profile, scope)
  - [ ] 3.IV — Prueba end-to-end: estudiante ↔ framework ↔ MCP ↔ TutorIA
- [ ] **FASE 4** — Los 10 prompts redactados y validados; el agente se comporta como tutor
- [ ] **FASE 5** — Contenido ingestado; el agente cita material de los módulos
- [ ] **FASE 6** — La docente ve estadísticas, transcripciones y edita prompts
- [ ] **FASE 7** — Las evals pasan con score > 80% en cada categoría
- [ ] **FASE 8** — Todo en Docker sobre Azure, CI/CD, JWT real, RNF-01 medido

---

## Deuda técnica pendiente

| Tema | Detalle | Estado |
|---|---|---|
| **Autenticación** | `X-Teacher-Id` / `X-Admin-Token` son placeholders. **Máxima prioridad** antes de datos reales. Se resolverá con la integración del framework (JWT). | 🔴 Pendiente |
| Colecciones de Open edX | Nombres validados contra Teak **y** Verawood (idénticos). Matrículas confirmadas en MySQL; opaque keys confirmados. | ✅ Resuelto |
| `create_all` en `main.py` | Marcado con TODO; Alembic es la fuente de verdad. Puede eliminarse. | Pendiente |
| Gamificación | Números PROVISIONALES en `config.py` + `badges.criteria_json`, pendientes de RF-24. | Pendiente |
| `night_owl` | Usa hora UTC; Colombia es UTC-5. Falta decidir la política de zona horaria. | Pendiente |
| `sync_modules` devuelve 0 | Reimplementar recorriendo `blocks[]` de `structures` (resolver `children`, filtrar por `block_type`). | 🔴 TODO fase-3b |
| Reconciliación de `Student` | Hoy por `email`; debería ser por `external_user_id` (necesita migración Alembic + backfill de `auth_user.id`). Es también el mapeo `user_id` Open edX → `Student` que el MCP necesitará. | 🔴 TODO fase-3b |
| Tests de la pasarela | 11 tests de `test_openedx_gateway.py` rotos tras el cambio a MySQL/opaque keys; reescribir contra el nuevo esquema. | Pendiente |
| **Latencia en CPU** | Frío + Open edX corriendo: ~19.5 min. **En caliente y aislado: ~38-66 s (típico ~49 s)** para una respuesta de ~200 tokens. Sigue ~10× sobre el RNF-01 (< 5 s) y con alta variación → **GPU en Azure obligatoria** para el piloto. Mitigación de UX: streaming. | 🔴 Bloquea el piloto |
| Hosts permitidos MCP | FastMCP solo acepta `localhost`/`127.0.0.1`. Hay que permitir el host de Open edX (`tutoria_backend`) para que el framework llame al `/mcp`. Va con el JWT en 3.III. | 🔴 TODO 3.III |
| Ruta `/mcp` vs `/mcp/` | `/mcp` responde 307 a `/mcp/`; detrás del proxy de Azure podría degradar a `http://`. Convención: apuntar siempre a `/mcp/`. | Convención adoptada |
| Resultado del tool MCP | `chat_with_tutor` devuelve texto plano (`-> dict`). Si `openedx-ai-extensions` quiere copia estructurada, cambiar a `-> dict[str, Any]`. | A validar en 3.III |
| `message_history` mutable | Se persistía con `flag_modified` (fix 3.II). Solución durable: declarar la columna como JSON mutable rastreable. | Resuelto (mejora pendiente) |
| `{prerequisites}` sin sustituir | El prompt de diagnóstico usa la variable `{prerequisites}`, pero `student_context` (chat.py) solo aporta `student_name`, `student_level`, `module_name`; la variable se filtra literal en la respuesta. Rellenarla o quitarla del template. | Pendiente (FASE 4) |
| `.env` vs pytest en host | `.env` con hostnames Docker (`postgres`, `ollama`) rompe pytest en el host; falta un `.env.test` apuntando a `localhost`. | Pendiente |
| `DEFINITIONS_COLLECTION` | `modulestore.definitions` identificada pero sin consumir; fuente de contenido para RAG. | TODO fase-5 |
| Alertas de riesgo | `GET /api/analytics/course/{id}/alerts` devuelve `[]`. | Pendiente (FASE 6) |
| `update_streak` / notificaciones | La racha se actualiza en cada chat; faltan las notificaciones proactivas. | Pendiente |

---

*TutorIA · Universidad Tecnológica de Pereira · Grupo de Investigación Sirius · 2026*