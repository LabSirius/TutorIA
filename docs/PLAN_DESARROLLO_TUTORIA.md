# Plan de Desarrollo TutorIA — Flujo Robusto

> Guía paso a paso para construir TutorIA.
> Cada fase pendiente incluye el **prompt exacto** que debes darle a Claude Code en VS Code.
>
> **Actualizado tras el Refactor V2** (julio 2026). Las fases completadas describen
> el sistema **tal como existe hoy**; las pendientes conservan el formato de prompt.
> Referencias: [Requerimientos V2](TutorIA_Requerimientos_V2.md) · [Marco Pedagógico V2](MArco_V2_texto.md)

---

## Estado actual

| Fase | Estado |
|------|--------|
| **FASE 0** — Contexto | ✅ Completada |
| **FASE 1** — Backend (API + BD + LLM) | ✅ Completada |
| **FASE 2** — Refactor a Requerimientos V2 | ✅ Completada (8 commits) |
| **FASE 3** — Integración con Open edX | 🔴 Prioridad inmediata (incluye la pasarela MongoDB) |
| **FASE 4** — Prompts pedagógicos | 🟡 Infraestructura lista; **falta la redacción pedagógica** |
| **FASE 5** — RAG: contenido pedagógico | 🟡 Pipeline listo; **falta el contenido + CLI de ingesta** |
| **FASE 6** — Panel docente + Analytics | 🟡 Endpoints listos; **falta la UI** |
| **FASE 7** — Evals del agente | ⬜ Pendiente |
| **FASE 8** — Deploy y piloto (Azure) | ⬜ Pendiente |

**Regla de oro:** cada fase produce algo funcional y testeado antes de pasar a la siguiente.

**Camino crítico hoy:** FASE 3 (integración con Open edX) es la nueva prioridad
por directriz del Dr. José Jaramillo → luego FASE 4 (prompts) y FASE 5 (contenido),
que pueden ejecutarse en paralelo si la Dra. Grajales tiene disponibilidad para
redactar los prompts mientras el equipo técnico avanza en Open edX. Sin los prompts
reales, TutorIA es un tutor *arquitectónicamente*, pero no *pedagógicamente*.

---

## Visión general del flujo

```
FASE 0 → FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6 → FASE 7 → FASE 8
Contexto Backend  RefactorV2 OpenedX  Prompts  RAG     Panel    Evals    Deploy
  ✅       ✅        ✅        🔴       🟡      🟡       🟡       ⬜       ⬜
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
- Backend Python/FastAPI. Frontend **dentro de Open edX** (plugin/XBlock), no una SPA aparte.
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
│   ├── gateways/openedx_gateway/   # mongo_client · schemas · sync_service
│   └── db/
│       ├── database.py         # Engine async (asyncpg)
│       ├── seed.py             # CLI: prompts | badges | all
│       ├── seeds/              # prompt_templates.py · badges.py
│       └── migrations/         # Alembic (3 migraciones)
├── requirements.txt  Dockerfile  pytest.ini  .env.example
└── tests/                      # 69 tests
```

**Decisiones técnicas vigentes:**

- `llm_service.py` usa la librería `openai` contra `LLM_BASE_URL`
  (por defecto `http://localhost:11434/v1`), API key `ollama`, modelo `llama3.2`.
- **PostgreSQL en todos los entornos** vía `asyncpg`. No hay SQLite.
- **pgvector** es el vector store (no ChromaDB).
- Los prompts viven en la **base de datos**, no en archivos `.txt`.
- `requirements.txt`: fastapi, uvicorn, openai, sqlalchemy, **asyncpg**, **pgvector**,
  alembic, **motor**, **apscheduler**, pydantic-settings, python-multipart, httpx,
  pytest, pytest-asyncio.

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
nombres de colecciones de Mongo por confirmar; números de gamificación PROVISIONALES.

---

## FASE 3 — Integración con Open edX 🔴

Prioridad inmediata por directriz del Dr. José Jaramillo. Descubrir bloqueos
técnicos temprano (schemas MongoDB reales, autenticación JWT, compatibilidad de
plugin/XBlock) antes de invertir semanas en contenido pedagógico. Además habilita
un demo tangible del sistema funcionando end-to-end, aunque sea con prompts
placeholder.

### Parte A — Frontend dentro de Open edX

```
Crea la integración con Open edX en openedx/:

Opción A (preferida): configurar openedx-ai-extensions
- Crea openedx/README.md con instrucciones para:
  1. Instalar el plugin en la instancia de Open edX
  2. Configurarlo para que apunte a nuestro backend FastAPI
  3. Crear perfiles de AI para cada tipo de interacción
  4. Configurar scopes por curso

Opción B (fallback): XBlock custom
- Crea openedx/tutoria_xblock/ con un XBlock que:
  1. Muestre un widget de chat dentro del curso
  2. Envíe mensajes a POST /api/chat
  3. Renderice respuestas con markdown
  4. Tenga botón de audio (TTS placeholder)
  5. Muestre el avatar de TutorIA

Crea openedx/docker-compose.override.yml para conectar Open edX con el backend
en desarrollo local.

Commit: "feat: integración con Open edX"
```

### Parte B — Pasarela MongoDB → PostgreSQL (RF-22)

La pasarela **ya está construida** (`app/gateways/openedx_gateway/`), pero **nunca
se ha ejecutado contra una instancia real**. Pendiente:

1. **Confirmar los nombres de colección** en `sync_service.py`
   (`modulestore.active_versions`, `modulestore.structures`,
   `student_courseenrollment`) contra la instancia real. Son suposiciones.
   Ojo: en muchos despliegues las **matrículas viven en MySQL, no en Mongo** — si es
   el caso, `sync_enrollments()` necesita otra fuente.
2. Configurar `OPENEDX_MONGO_URL` / `OPENEDX_MONGO_DB` y `OPENEDX_SYNC_ENABLED=true`.
3. Probar primero en seco:
   `POST /api/admin/sync-openedx?dry_run=true` con la cabecera `X-Admin-Token`.
4. Sustituir la autenticación por cabecera con **JWT real de Open edX**.

Para desarrollar sin Open edX hay un servicio `openedx-mongo` comentado en
`docker-compose.yml` que se puede descomentar.

### Preguntas críticas para el Dr. José antes de arrancar

- ¿Cuál es la URL de la instancia de Open edX del proyecto y las credenciales admin?
- ¿Qué versión de Open edX corre (nombre en clave: Nutmeg, Olive, Palm, Quince)?
- ¿Podemos instalar plugins o hay restricciones institucionales?
- ¿Prefiere el plugin `openedx-ai-extensions` o un XBlock custom?

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

3. UI del panel DENTRO de Open edX (no una SPA aparte):
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

### Prompt para Claude Code

```
Prepara el proyecto para deploy:

1. Añade el servicio `backend` a docker-compose.yml:
   - depends_on: postgres (service_healthy) y ollama (service_healthy)
   - OLLAMA_BASE_URL=http://ollama:11434 (DNS interno de docker)
   - Ejecuta alembic upgrade head al arrancar
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
| Integración Open edX + validación de pasarela | Claude Code | 3 🔴 |
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
      trazabilidad, pasarela Open edX (69 tests en verde)
- [ ] **FASE 3** — TutorIA funciona dentro de Open edX; la pasarela sincroniza datos reales
- [ ] **FASE 4** — Los 10 prompts redactados y validados; el agente se comporta como tutor
- [ ] **FASE 5** — Contenido ingestado; el agente cita material de los módulos
- [ ] **FASE 6** — La docente ve estadísticas, transcripciones y edita prompts
- [ ] **FASE 7** — Las evals pasan con score > 80% en cada categoría
- [ ] **FASE 8** — Todo en Docker sobre Azure, CI/CD, JWT real, RNF-01 medido

---

## Deuda técnica pendiente

| Tema | Detalle |
|---|---|
| **Autenticación** | `X-Teacher-Id` / `X-Admin-Token` son placeholders. **Máxima prioridad** antes de datos reales. |
| `create_all` en `main.py` | Marcado con TODO; Alembic es la fuente de verdad. Puede eliminarse. |
| Colecciones de Open edX | Nombres supuestos; confirmar contra la instancia real (FASE 3). |
| Gamificación | Números PROVISIONALES en `config.py` + `badges.criteria_json`, pendientes de RF-24. |
| `night_owl` | Usa hora UTC; Colombia es UTC-5. Falta decidir la política de zona horaria. |
| Matrícula estudiante↔asignatura | Se deduce de sesiones/progreso; debería venir de la pasarela. |
| Alertas de riesgo | `GET /api/analytics/course/{id}/alerts` devuelve `[]`. |
| `update_streak` / notificaciones | La racha se actualiza en cada chat; faltan las notificaciones proactivas. |

---

*TutorIA · Universidad Tecnológica de Pereira · Grupo de Investigación Sirius · 2026*