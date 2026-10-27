# Plan de Desarrollo TutorIA — Flujo Robusto

> Guía paso a paso para construir TutorIA.
> Cada fase pendiente incluye el **prompt exacto** que debes darle a Claude Code en VS Code.
>
> **Actualizado el 27 de octubre de 2026**, tras completar la integración de punta a punta
> con Open edX Verawood (Fases 3.III y 3.IV, Opción B: TutorIA como *provider*).
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
| **FASE 3** — Integración con Open edX (Verawood, TutorIA como *provider*) | 🟡 3.I–3.IV ✅ — **integración demostrada de punta a punta** (27-10-2026). Falta la **3b** (identidad real del estudiante, sesiones, streaming real, ventana de contexto) |
| **FASE 4** — Prompts pedagógicos | 🟡 Infraestructura lista; **falta la redacción pedagógica** |
| **FASE 5** — RAG: contenido pedagógico | 🟡 Pipeline listo; **falta el contenido + CLI de ingesta** |
| **FASE 6** — Panel docente + Analytics | 🟡 Endpoints listos; **falta la UI** |
| **FASE 7** — Evals del agente | ⬜ Pendiente |
| **FASE 8** — Deploy y piloto (Azure) | ⬜ Pendiente |

**Regla de oro:** cada fase produce algo funcional y testeado antes de pasar a la siguiente.

**Camino crítico hoy:** la **tubería** ya funciona: un estudiante escribe en el chat de un
curso de Open edX y TutorIA responde con el modelo local, sin que ningún dato salga de la
infraestructura del proyecto. Lo que falta es **lo que viaja por ella**. La primera prueba
de punta a punta devolvió una respuesta larga, enciclopédica y con errores de contenido:
no hace diagnóstico ni es socrática (los prompts siguen siendo *placeholders*, FASE 4) y no
usa material del curso (el RAG no tiene contenido, FASE 5). Prioridades:

1. **Fase 3b** (técnica, corta): streaming real token por token, ventana de contexto de
   Ollama, identidad real del estudiante y definición de sesión.
2. **FASES 4 y 5** (pedagógicas, en paralelo con la Dra. Grajales): prompts reales y
   contenido curricular. Sin ellas, TutorIA es un tutor *arquitectónicamente*, pero no
   *pedagógicamente*.

---

## Visión general del flujo

```
FASE 0 → FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6 → FASE 7 → FASE 8
Contexto Backend  RefactorV2 OpenedX  Prompts  RAG     Panel    Evals    Deploy
  ✅       ✅        ✅      🟡(3b)    🟡      🟡       🟡       ⬜       ⬜
```

---

## FASE 0 — Dar contexto a Claude Code ✅

Antes de pedir código, Claude Code debe leer: `README.md`, `CONTRIBUTING.md`,
`docs/TutorIA_Requerimientos_V2.md`, `docs/MArco_V2_texto.md`,
`docs/PLAN_DESARROLLO_TUTORIA.md` y `docs/tutoria_architecture_V2.svg`.

> **Sesiones nuevas de Claude Code:** una sesión nueva no conoce el historial del proyecto.
> Cada prompt debe incluir una sección **CONTEXT** (qué es TutorIA, qué archivos leer, por qué
> se hace el cambio), decisiones fijas, orden de ejecución y criterios de verificación.

Contexto clave que debe confirmar:

- Agente tutor virtual con IA para Open edX Verawood.
- Motor LLM: **Ollama local** (contenedorizado) con API compatible con OpenAI.
  Sin API key de pago hoy; Claude API se incorporará por clasificador (RF-23).
- Backend Python/FastAPI. **TutorIA es un servicio autónomo**: Open edX lo consume como
  **provider compatible con OpenAI** a través del framework `openedx-ai-extensions`
  (ver FASE 3). Además expone un **servidor MCP** como interfaz estándar secundaria.
- **PostgreSQL + pgvector es la única base de datos** (datos + vectores + prompts).
- Infraestructura final: servidor propio en Azure (IaaS).
- Todo el **código en inglés**; solo contenido pedagógico y textos de estudiante en español.
- Convención de commits del `CONTRIBUTING.md`; toda rama se crea desde `dev`.
- **Los commits no llevan atribución a Claude ni a IA** (ni `Co-Authored-By`, ni
  "Generated with"). Configurado en `~/.claude/settings.json` con
  `"attribution": {"commit": "", "pr": ""}`, y reforzado al final de cada prompt.

---

## FASE 1 — Backend: API + BD + Servicio LLM ✅

Backend construido y refactorizado a V2. **Estructura real hoy:**

```
backend/
├── app/
│   ├── main.py                 # FastAPI: CORS, lifespan (checks + scheduler + MCP)
│   ├── config.py               # pydantic-settings (.env)
│   ├── routers/
│   │   ├── chat.py             # POST /api/chat
│   │   ├── openai_compat.py    # POST /v1/chat/completions (provider para Open edX, SSE)
│   │   ├── sessions.py         # CRUD de sesiones
│   │   ├── students.py         # Perfil del estudiante
│   │   ├── feedback.py         # Retroalimentación continua + gamificación
│   │   ├── analytics.py        # Panel docente + trazabilidad
│   │   └── admin.py            # Disparador manual de sync Open edX
│   ├── services/
│   │   ├── chat_service.py     # process_chat_turn() — un turno (REST + MCP + provider)
│   │   ├── llm_service.py      # OllamaProvider.generate()/stream() + get_provider()
│   │   ├── router_service.py   # RequestRouter (placeholder RF-23)
│   │   ├── rag_service.py      # Pipeline RAG con pgvector
│   │   ├── embedding_client.py # Ollama /api/embeddings + retry
│   │   ├── chunking.py         # Chunking que preserva conceptos
│   │   ├── prompt_manager.py   # Prompts desde BD + caché + reglas Marco V2
│   │   ├── gamification_service.py
│   │   └── tts_service.py      # Placeholder TTS
│   ├── mcp_server/             # servidor MCP: server.py (FastMCP + tool chat_with_tutor)
│   ├── models/                 # SQLAlchemy + Pydantic (14 tablas)
│   ├── schemas/rag.py
│   ├── gateways/openedx_gateway/   # mongo_client · mysql_client · course_keys · schemas · sync_service
│   └── db/                     # database.py · seed.py · seeds/ · migrations/ (Alembic)
├── scripts/mcp_smoke_test.py   # cliente MCP de prueba (va dentro de la imagen)
├── requirements.txt  Dockerfile  pytest.ini  .env.example
└── tests/                      # 72 en verde; tests/test_openedx_gateway.py (11) falla al importar → se corre con --ignore
```

**Decisiones técnicas vigentes:**

- `llm_service.py` usa la librería `openai` contra `LLM_BASE_URL`, API key `ollama`,
  modelo `llama3.2`. Ollama se mantiene cargado entre turnos (`OLLAMA_KEEP_ALIVE=30m`).
- `ollama-init` descarga **los dos modelos**: `nomic-embed-text` y `llama3.2`.
- **PostgreSQL en todos los entornos** vía `asyncpg`. **pgvector** es el vector store.
- Los prompts viven en la **base de datos**, no en archivos `.txt`.
- `requirements.txt`: fastapi **>=0.118** (necesario para mantener la sesión de BD abierta
  durante el streaming), uvicorn, openai, sqlalchemy, asyncpg, aiomysql, pgvector, alembic,
  motor, apscheduler, pydantic-settings, python-multipart, httpx, pytest, pytest-asyncio,
  **mcp** (pin `>=1.20,<2`: la 2.x eliminó `mcp.server.fastmcp`).

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

### Cómo levantarlo (entorno local)

```powershell
# TutorIA (PowerShell, en la raíz del repo)
docker compose up -d          # postgres, ollama, ollama-init (descarga modelos) y backend
docker compose ps             # backend/postgres/ollama "running"; ollama_init "Exited (0)" es normal
```

```bash
# Open edX (Ubuntu/WSL2; Tutor instalado con pipx)
tutor local start -d
tutor local status
```

### Pruebas (tests)

- Durante el desarrollo, correr solo los tests relacionados (`pytest tests/test_x.py`,
  `pytest -k nombre`). **Suite completa antes de cada commit importante y antes de push.**
- Hoy: `docker exec -it tutoria_backend pytest --ignore=tests/test_openedx_gateway.py`.
- Los tests **simulan** el LLM (son rápidos). Lo lento son las verificaciones manuales con
  el modelo real (`curl`, smoke test).
- Los tests no deben depender del `.env` local (fijan sus propios valores).

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

---

## FASE 3 — Integración con Open edX (Verawood, TutorIA como *provider*) 🟡

Prioridad por directriz del Dr. José Jaramillo: descubrir bloqueos técnicos temprano y
habilitar un demo tangible del sistema funcionando de punta a punta. **Logrado el 27-10-2026.**

### Decisión de arquitectura: Escenario B — TutorIA autónomo

Tras evaluar dos escenarios con el **AI Extension Framework** (`openedx-ai-extensions`), el
equipo (Dr. José, Ana, Sofía) eligió el **Escenario B**: TutorIA **permanece como servicio
autónomo**; Open edX solo es el punto de acceso. Preserva los tres valores centrales —
personalización por estudiante (Nivel 2), estadísticas para el docente y gamificación —
porque viven en el backend. (Escenario A, reconstruir TutorIA dentro del framework, se
descartó.) Documentos: `Reporte_Verawood_TutorIA.docx`, `Escenarios_Integracion_TutorIA.docx`,
`Plan_Escenario_B_TutorIA.docx`.

### Decisión de integración (aprobada por el Dr. José): Opción B — TutorIA como *provider*

La revisión del código del framework demostró que su función de **MCP externo solo ejecuta
MCP remoto del lado del proveedor** (en la práctica, OpenAI): el framework no tiene cliente
MCP propio. Con Ollama local, el tool MCP no se ejecuta, y usar un orquestador en la nube
violaría el principio de datos locales (Ley 1581) y tendría costo.

**Decisión** (`Informe_Integracion_MCP_TutorIA.docx`): TutorIA expone un endpoint
**compatible con OpenAI** y se registra como el **provider** del framework. Open edX habla
con TutorIA como si fuera el modelo. Todo local, sin costo. **El servidor MCP de 3.II se
conserva** como interfaz estándar secundaria (otros clientes MCP, artículo).

### Sub-fase 3.I — Migración del entorno a Verawood ✅

- Teak eliminado; **Tutor 22 (Verawood)** instalado limpio en WSL2 (Ubuntu, Docker Desktop),
  con **pipx** (Tutor tiene su propio entorno aislado).
- Curso de prueba con opaque key `course-v1:UTP+V001+2026_07_V1`; superusuario `admin`.
- **Esquemas re-validados** (idénticos a Teak): MongoDB `modulestore.active_versions`,
  `structures`, `definitions`; matrículas en MySQL `student_courseenrollment`.
- Backend de TutorIA conectado a la red `tutor_local_default` (resuelve `mongodb`, `mysql`,
  y el LMS alcanza `tutoria_backend:8000`).
- Pasarela actualizada: `mongo_client.py`, `mysql_client.py`, `course_keys.py`,
  `sync_service.py` (matrículas desde MySQL, `is_active=1`, sin usuarios de sistema).

### Sub-fase 3.II — Servidor MCP de TutorIA ✅

- SDK oficial (`from mcp.server.fastmcp import FastMCP`), pin `mcp>=1.20,<2`.
- La orquestación de un turno vive en **`app/services/chat_service.py`**:
  `process_chat_turn(db, student_id, message, session_id=None) -> ChatTurnResult`.
  **REST, MCP y el endpoint provider llaman a la misma función**: no hay pedagogía duplicada.
- Errores como excepciones de dominio (`StudentNotFound`, `SessionNotFound`).
- Tool `chat_with_tutor` montado en `/mcp` (streamable-http), con el *session manager*
  combinado con el `lifespan` de `main.py`. Convención: apuntar a **`/mcp/`** (con barra final).
- Corregido el bug de persistencia de turnos en sesiones existentes (`flag_modified`).
- Verificado con `backend/scripts/mcp_smoke_test.py`.

### Sub-fase 3.III — Endpoint provider + configuración del framework ✅

**En TutorIA (`app/routers/openai_compat.py`, `POST /v1/chat/completions`):**

- Forma OpenAI Chat Completions. Toma **el último mensaje del usuario**; TutorIA gestiona su
  propia sesión (no usa el historial que manda el framework), lo que preserva la
  adaptabilidad Nivel 2.
- **Sin mensaje de usuario** (el framework a veces abre el chat solo con mensajes de
  sistema): responde `200` con un saludo en español, sin llamar al LLM ni tocar la BD.
- **Streaming SSE** (`stream: true`): fragmento de rol inmediato, latido `: keepalive` cada
  15 s mientras se genera, contenido en fragmentos, cierre `stop` y `[DONE]`. Errores dentro
  del stream se envían como mensaje en español. Hoy es **pseudo-streaming**: la respuesta se
  genera completa y luego se trocea (el streaming real es la Fase 3b).
- **Identidad (MVP):** estudiante fijo `OPENEDX_DEFAULT_STUDENT_ID` (hoy **2**, "Estudiante
  Prueba Open edX", en `backend/.env`) y reutilización de su sesión más reciente.

**En Open edX (Tutor):**

1. Plugin instalado **en el entorno pipx de Tutor**:
   ```bash
   pipx inject tutor git+https://github.com/openedx/openedx-ai-extensions.git
   tutor plugins enable openedx-ai-extensions
   tutor config save
   tutor images build openedx
   tutor images build mfe
   tutor local launch -I
   tutor local exec lms python manage.py lms migrate openedx_ai_extensions
   ```
   > **Incidente:** el build de `mfe` fallaba con `apt 404` porque Debian 11 "bullseye" llegó
   > a fin de vida. Se resolvió con **tutor-mfe 22.1.0** (base Debian 12 "bookworm"):
   > `pipx runpip tutor install --upgrade "tutor-mfe>=22.1.0,<23"`. Un build que parezca
   > colgado (CPU ~0 %) se cancela y se relanza con
   > `tutor images build mfe --no-registry-cache --docker-arg="--progress=plain"`.
2. **Provider** en `$(tutor config printroot)/config.yml` (`AI_EXTENSIONS:` en la columna 1,
   sin espacios delante; si el YAML queda mal, Tutor falla en todos los comandos y el archivo
   se edita directo en `~/.local/share/tutor/config.yml`):
   ```yaml
   AI_EXTENSIONS:
     tutoria:
       API_BASE: "http://tutoria_backend:8000/v1"
       MODEL: "hosted_vllm/tutoria"
   ```
   El prefijo `hosted_vllm` hace que LiteLLM llame a un endpoint compatible con OpenAI y deja
   el provider ≠ `openai` (vía Completion, sin hilo *server-side*).
3. **Profile** (Django admin → *Open edX AI Extensions* → AI workflow profiles):
   slug `tutoria-chat`, base `examples/openai/chat.json`, content patch:
   ```json
   {
     "processor_config": { "LLMProcessor": { "provider": "tutoria", "stream": true } },
     "actuator_config": { "UIComponents": {
       "request":  { "config": { "buttonText": "Abrir TutorIA", "customMessage": "Habla con tu tutor" } },
       "response": { "config": { "customMessage": "TutorIA" } } } }
   }
   ```
   > **`"stream": true` es obligatorio.** Con `false`, el framework usa la *Responses API* de
   > LiteLLM, que falla dentro de Open edX (`No module named 'mcp'`) antes de llegar a TutorIA.
   > Con `true` y un provider no-OpenAI, el framework usa la vía Completion.
4. **Scope:** profile `tutoria-chat`, service variant `lms`, course
   `course-v1:UTP+V001+2026_07_V1`, UI slot **`ai-assist-button`** (junto al título de cada
   unidad), sin location regex, habilitado.
5. **Solo entorno local — mini-plugin `uwsgi_timeout`:** uWSGI corta a los **60 s** sin datos
   hacia el navegador (Caddy registra `502 EOF` a los 60.06 s). Con la respuesta generada en
   CPU (~3 min) era necesario subirlo:
   ```bash
   cat > "$(tutor plugins printroot)/uwsgi_timeout.yml" <<'EOF'
   name: uwsgi_timeout
   version: 0.1.0
   patches:
     uwsgi-config: |
       http-timeout = 600
   EOF
   tutor plugins enable uwsgi_timeout && tutor config save && tutor local restart lms
   ```
   Con streaming real y GPU en Azure no debería hacer falta.

### Sub-fase 3.IV — Prueba de punta a punta ✅ (27-10-2026)

**Flujo demostrado:** estudiante en el curso → botón "Abrir TutorIA" → framework → TutorIA
(`/v1/chat/completions`, SSE) → Ollama local → respuesta completa en el chat del curso.
Ningún dato sale de la infraestructura del proyecto.

**Observaciones de la prueba:**

- **Latencia:** ~3-5 min por turno en el portátil con Open edX encendido (generación a
  ~3.7 tokens/s; respuestas de cientos de tokens).
- **Calidad:** la respuesta fue enciclopédica, larga y con errores de contenido (p. ej. "IA
  débil/fuerte" presentadas como etapas históricas). Esperable: prompts *placeholder*,
  RAG sin contenido y un modelo de 3B. Es tarea de las FASES 4 y 5.
- **Cola en Ollama:** en CPU atiende una petición a la vez; los intentos cortados siguen
  generando y retrasan a los siguientes. En pruebas: **un mensaje y esperar la respuesta**.
- **Residuos:** los intentos cortados por el límite de 60 s quedaron guardados **truncados**
  en el historial del chat de Open edX (TutorIA sí guardó la respuesta completa).
- **Pendiente de verificar** de punta a punta: gamificación y trazabilidad registradas en la
  BD de TutorIA para el estudiante 2, y documentar el flujo en `openedx/README.md`.

### Sub-fase 3b — Pendientes de integración ⬜

Orden sugerido:

1. **Subir el trabajo** de `feature/openedx-integration` (commits del endpoint, bienvenida,
   streaming, keepalive, keep-alive de Ollama, FastAPI, tests).
2. **Streaming real token por token** usando `OllamaProvider.stream()` (ya existe): las
   primeras palabras llegan en segundos, el estudiante ve avanzar la respuesta y la conexión
   nunca queda en silencio. Debe conservar la persistencia del turno completo y la
   trazabilidad (`prompt_key`).
3. **Ventana de contexto de Ollama:** hoy **4096 tokens** (Ollama la elige sola en CPU); al
   superarla **descarta en silencio** lo más antiguo, lo que incumple el requisito de
   mantener el contexto de toda la sesión. Configurar `OLLAMA_CONTEXT_LENGTH` (local: 8192,
   ~0.9 GB extra; Azure: mayor, según memoria/GPU). **No se recorta el historial** que se
   envía al modelo: el requisito pedagógico es contexto de sesión completo.
4. **Identidad real del estudiante:** mapear el `user_id` de Open edX al `Student` de
   TutorIA (migración Alembic `external_user_id` + backfill). Requiere saber qué identidad
   envía el framework al provider (investigar antes de programar).
5. **Definición de sesión:** cuándo empieza una sesión nueva (p. ej. tras N minutos de
   inactividad). Evita las "sesiones infinitas" del MVP.
6. **Autenticación** Open edX ↔ TutorIA (JWT o equivalente) antes de datos reales.

### Mejoras derivadas del framework

- **Streaming chat:** pseudo-streaming ✅; streaming real → Fase 3b, punto 2.
- **Educator assistant** (deseable, a validar con la Dra. Grajales): asistente para el
  docente que interprete las analíticas. Alcance nuevo, no confirmado.

### Preguntas críticas con el Dr. José — RESUELTAS

- ✅ **Versión de Open edX:** Verawood (Tutor 22).
- ✅ **Plugin vs XBlock:** ninguno contiene la lógica. TutorIA autónomo, consumido por
  `openedx-ai-extensions` como **provider compatible con OpenAI** (Opción B).
- 🔴 **Autenticación Open edX ↔ TutorIA:** pendiente (Fase 3b, punto 6).

---

## FASE 4 — Prompts pedagógicos 🟡

**Puede ejecutarse en paralelo** con la Fase 3b. La Dra. Grajales redacta los 10 prompts;
luego se cargan a la base de datos.

### Qué falta

La infraestructura está lista: los 10 prompts existen en `prompt_templates` con contenido
`[PLACEHOLDER — pendiente de redacción por la Dra. Grajales durante la Fase 4]`. Falta **la
redacción pedagógica real**, validada por la investigadora postdoctoral (Marco V2, §6.2).

> **Lección de la prueba 3.IV:** los prompts deben pedir **turnos cortos** (diagnóstico,
> preguntas socráticas, un paso a la vez). Además de ser lo pedagógicamente correcto, reduce
> mucho la latencia en CPU, que depende del número de tokens generados.

### Las 10 claves (`prompt_templates.key`)

`system_base` · `diagnostic` · `basic_explanation` · `advanced_explanation` ·
`comprehension_check` · `socratic` · `cognitive_modeling` · `error_feedback` ·
`risk_alert` · `metacognitive_closure`

### Cómo cargar el contenido redactado

1. **Hoy:** editar `backend/app/db/seeds/prompt_templates.py` y ejecutar
   `python -m app.db.seed prompts` (idempotente).
2. **Objetivo (RF-19/21):** endpoint de administración para editar prompts desde el panel,
   versionando en `prompt_template_history` (FASE 6).

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
| Acierta al primer intento → reducir andamiaje | ⬜ Fuera del MVP |
| 5+ días sin usar → notificación proactiva | ⬜ Fuera del MVP |

### Entregable

Los 10 prompts redactados y validados en la BD, y el agente comportándose como tutor.

---

## FASE 5 — RAG: contenido pedagógico 🟡

### Lo que ya existe ✅

`rag_service.py` sobre pgvector: `ingest_content(module_id, text)` (chunking ~500 tokens,
embeddings `nomic-embed-text` 768 dim, inserción transaccional), `search_context(query,
module_id, top_k=3)` con índice HNSW, `delete_module_content(module_id)`. El chat inyecta el
contexto recuperado como "Material de referencia" **cuando la sesión tiene módulo asignado**.

> **Importante:** esto es recuperación, **no** entrenamiento. El LLM nunca se modifica.

> **Nota:** `modulestore.definitions` de Open edX es la fuente natural del contenido
> curricular (identificada en `sync_service.py` como `DEFINITIONS_COLLECTION`, sin consumir).
> El framework también envía el contenido de la unidad actual como mensaje de sistema;
> hoy TutorIA lo ignora (usa solo el último mensaje del estudiante). Evaluar si aprovecharlo.

### Lo que falta ⬜

1. **El contenido** de Programación I e Introducción a la Matemática (y el curso de prueba
   de IA agéntica), contextualizado para Risaralda.
2. **El CLI de ingesta**, que nunca se construyó.
3. **Asignar módulo a la sesión** del estudiante que llega desde Open edX (hoy no se asigna,
   así que el RAG no se activa en el flujo de Open edX).

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

Commit: "feat: add curricular content ingestion cli"
Do not add any Co-Authored-By trailer or any Claude/AI attribution to commit messages.
```

### Riesgo a validar pronto

`nomic-embed-text` no está verificado sobre **texto en español**. Al ingestar el primer
módulo, medir la calidad de recuperación; si es pobre, cambiar a un modelo multilingüe.

---

## FASE 6 — Panel docente + Analytics 🟡

### Endpoints ya disponibles ✅

| Endpoint | Qué da |
|---|---|
| `GET /api/analytics/course/{id}/summary` | estudiantes activos, progreso, aprobación |
| `GET /api/analytics/student/{id}/detail` | módulos completados, evaluaciones, tiempo |
| `GET /api/analytics/course/{id}/alerts` | **stub — devuelve `[]`** |
| `GET /api/analytics/student/{id}/conversations` | sesiones paginadas (RF-18) |
| `GET /api/analytics/session/{id}/transcript` | historial completo + `prompt_key` por turno |
| `GET /api/feedback/gamification/{student_id}` | XP, racha, insignias |

Autorización: cabecera `X-Teacher-Id` (placeholder hasta tener autenticación real).

> La **lógica** del panel vive en TutorIA y no cambia con la integración. Falta definir la
> **presentación** dentro de Open edX (¿MFE en el Instructor Dashboard? ¿vista propia?).
> El framework incluye además paneles de analítica de uso de IA (tokens, interacciones).

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

3. UI del panel:
   - Resumen del curso (métricas)
   - Lista de estudiantes con indicadores de riesgo
   - Detalle de estudiante (timeline, evaluaciones, gamificación)
   - Transcripción de conversaciones con la estrategia usada en cada turno
   - Editor de prompts pedagógicos

Commit: "feat: teacher dashboard with analytics"
Do not add any Co-Authored-By trailer or any Claude/AI attribution to commit messages.
```

---

## FASE 7 — Evals del agente ⬜

Depende de las FASES 4 y 5: evaluar prompts placeholder no mide nada.

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
│   ├── factuality.json     # Exactitud del contenido (ver prueba 3.IV)
│   └── safety.json         # No dar respuestas dañinas
└── eval_metrics.py         # Funciones de scoring

Cada archivo JSON tiene este formato:
{
  "test_name": "diagnostic_new_student",
  "student_profile": { "level": ..., "module": ..., "history": [] },
  "input_message": "Hola, soy nuevo aquí",
  "expected_behavior": ["Debe aplicar diagnóstico inicial", "..."],
  "forbidden_behavior": ["No debe dar la respuesta directamente", "..."]
}

eval_runner.py debe cargar cada caso, obtener el prompt con prompt_manager.get_prompt(),
enviarlo al LLM con llm_service.get_provider("ollama").generate(...), evaluar contra
expected/forbidden behavior con un LLM como juez, y generar un reporte por categoría.

Nombres de archivos y claves en inglés; contenido de los casos en español.

Commit: "feat: pedagogical evaluation framework"
Do not add any Co-Authored-By trailer or any Claude/AI attribution to commit messages.
```

---

## FASE 8 — Deploy y pruebas piloto (Azure) ⬜

> **Bloqueado por la compra del servidor Azure.** Sus especificaciones (RAM, GPU)
> determinan el tamaño del modelo, la ventana de contexto y, por tanto, la calidad
> pedagógica y la latencia.

El despliegue incluye el backend de TutorIA (API REST, endpoint provider `/v1` y servidor
MCP en `/mcp/`) y la instancia de Open edX Verawood con `openedx-ai-extensions` configurado
(provider `tutoria`, profile y scope), según la Fase 3.III.

### Prompt para Claude Code

```
Prepara el proyecto para deploy:

1. docker-compose.prod.yml con overrides para producción:
   - Variables de entorno para el servidor Azure
   - Volúmenes persistentes
   - Health checks y restart policies
   - GPU passthrough para ollama (deploy.resources.reservations.devices)
   - OLLAMA_CONTEXT_LENGTH acorde a la memoria disponible

2. .github/workflows/ci.yml:
   - Lint (ruff)
   - Tests (pytest) con un servicio postgres+pgvector
   - Build de imágenes Docker
   - Deploy a Azure (trigger manual)

3. scripts/setup.sh:
   - docker compose up -d postgres ollama ollama-init
   - alembic upgrade head
   - python -m app.db.seed all
   - Ingestar el contenido de los módulos

Commit: "chore: deploy and ci/cd configuration"
Do not add any Co-Authored-By trailer or any Claude/AI attribution to commit messages.
```

### Antes del piloto

- **Autenticación real** Open edX ↔ TutorIA (datos personales — Ley 1581 de 2012).
- Autenticación en las bases de datos; aislamiento de los datos del estudiante (Habeas Data).
- Identidad real del estudiante y definición de sesión (Fase 3b).
- Medir **RNF-01** (< 5 s) sobre el hardware de Azure, con streaming real.
- Validación pedagógica de los prompts por 2 docentes por asignatura (RNF-09).
- Quitar el ajuste local `uwsgi_timeout` si deja de ser necesario.

---

## Resumen: qué se hace dónde

| Tarea | Herramienta | Fase |
|-------|-------------|------|
| Backend, BD, servicio LLM, refactor V2 | Claude Code | 1-2 ✅ |
| Migración a Verawood + validación de esquemas | Sofía + Claude Chat | 3 ✅ |
| Servidor MCP (`chat_service` + `mcp_server`) | Claude Code | 3 ✅ |
| Endpoint provider `/v1/chat/completions` (SSE) | Claude Code | 3 ✅ |
| Instalación/config de `openedx-ai-extensions` (provider, profile, scope) | Sofía (Tutor + Django admin) | 3 ✅ |
| Streaming real, ventana de contexto, identidad, sesiones | Claude Code + Sofía | 3b ⬜ |
| **Diseño de prompts pedagógicos** | **Claude Chat + Dra. Grajales** | **4 🟡** |
| **Contenido de asignaturas** + CLI de ingesta | **Claude Chat → archivos** + Claude Code | **5 🟡** |
| Panel docente (UI + CRUD + alertas) | Claude Code | 6 🟡 |
| Framework de evaluaciones | Claude Code | 7 ⬜ |
| Docker + CI/CD + Deploy | Claude Code | 8 ⬜ |
| Documentación y artículos | Claude Chat | Continuo |

---

## Checklist por fase

- [x] **FASE 0** — Claude Code entiende el proyecto
- [x] **FASE 1** — Backend funcional: `POST /api/chat` responde
- [x] **FASE 2** — Refactor V2: PostgreSQL+pgvector, prompts en BD, gamificación,
      trazabilidad, pasarela Open edX
- [ ] **FASE 3** — TutorIA integrado en Open edX Verawood
  - [x] 3.I — Migración a Verawood + validación de esquemas
  - [x] 3.II — Servidor MCP de TutorIA, probado con cliente MCP
  - [x] 3.III — Endpoint `/v1/chat/completions` (SSE) + framework configurado (provider `tutoria`, profile `tutoria-chat`, scope `ai-assist-button`)
  - [x] 3.IV — Prueba de punta a punta dentro del curso (27-10-2026)
  - [ ] 3b — Streaming real, ventana de contexto, identidad real, sesiones, autenticación
- [ ] **FASE 4** — Los 10 prompts redactados y validados; el agente se comporta como tutor
- [ ] **FASE 5** — Contenido ingestado; el agente cita material de los módulos
- [ ] **FASE 6** — La docente ve estadísticas, transcripciones y edita prompts
- [ ] **FASE 7** — Las evals pasan con score > 80% en cada categoría
- [ ] **FASE 8** — Todo en Docker sobre Azure, CI/CD, autenticación real, RNF-01 medido

---

## Deuda técnica pendiente

| Tema | Detalle | Estado |
|---|---|---|
| **Autenticación** | `X-Teacher-Id` / `X-Admin-Token` son placeholders; el endpoint provider no autentica. **Máxima prioridad** antes de datos reales. | 🔴 Pendiente |
| **Identidad del estudiante** | El endpoint provider usa un estudiante fijo (`OPENEDX_DEFAULT_STUDENT_ID=2`). Mapear `user_id` de Open edX → `Student` (`external_user_id` + backfill). | 🔴 Fase 3b |
| **Sesión infinita (MVP)** | Se reutiliza siempre la sesión más reciente del estudiante. Definir cuándo empieza una sesión nueva. | 🔴 Fase 3b |
| **Ventana de contexto** | Ollama usa 4096 tokens en CPU y descarta en silencio lo más antiguo. Configurar `OLLAMA_CONTEXT_LENGTH` (local 8192; Azure mayor). No recortar el historial. | 🔴 Fase 3b |
| **Latencia en CPU** | Aislado y en caliente: ~38-66 s (respuestas cortas). Con Open edX encendido: 1.5-2.5 min de generación directa; ~3-5 min en el chat. ~3.7 tokens/s. → **GPU en Azure obligatoria**; streaming real para la experiencia; prompts de turnos cortos. | 🔴 Bloquea el piloto |
| Streaming real | Hoy pseudo-streaming (genera todo y luego trocea). Usar `OllamaProvider.stream()`. | 🔴 Fase 3b |
| `uwsgi_timeout` (local) | Mini-plugin de Tutor que sube `http-timeout` de uWSGI a 600 s. Solo para el portátil. | Ajuste local |
| Responses API de LiteLLM | Con `"stream": false`, el framework falla en Open edX (`No module named 'mcp'`). Mantener `"stream": true` en el profile. | Restricción documentada |
| Respuestas truncadas en Open edX | Intentos cortados quedaron guardados incompletos en el historial del chat del framework. Residuo de pruebas. | Menor |
| Calidad del contenido | La prueba 3.IV mostró errores de contenido (modelo 3B sin RAG ni prompts). Prompts, RAG, evals de exactitud y elección de modelo en Azure. | 🔴 Fases 4/5/7 |
| Log SQL activado | El backend imprime cada consulta SQL (`echo` de SQLAlchemy); llena el log de ruido. Apagarlo o hacerlo configurable. | Menor |
| Tests de la pasarela | `tests/test_openedx_gateway.py` falla al importar (`ENROLLMENTS_COLLECTION`) y obliga a usar `--ignore`. Reescribir sus 11 tests contra el esquema MySQL/opaque keys. | Pendiente |
| `sync_modules` devuelve 0 | Reimplementar recorriendo `blocks[]` de `structures`. | 🔴 TODO fase-3b |
| `create_all` en `main.py` | Alembic es la fuente de verdad. Puede eliminarse. | Pendiente |
| Gamificación | Números PROVISIONALES en `config.py` + `badges.criteria_json` (RF-24). Verificar que se registra en el flujo de Open edX. | Pendiente |
| `night_owl` | Usa hora UTC; Colombia es UTC-5. | Pendiente |
| `{prerequisites}` sin sustituir | El prompt de diagnóstico usa `{prerequisites}`, que `student_context` no aporta. | Pendiente (FASE 4) |
| `message_history` mutable | Persistencia corregida con `flag_modified`. Solución durable: columna JSON mutable rastreable. | Resuelto (mejora pendiente) |
| Embeddings con `num_ctx=8192` | Algo pide a `nomic-embed-text` (máx. 2048) una ventana de 8192; no es código de TutorIA. Investigar. | Menor |
| Hosts permitidos MCP | FastMCP solo acepta `localhost`. Solo relevante si un cliente externo usa el MCP (no lo usa Open edX con la Opción B). | Si aplica |
| Ruta `/mcp` vs `/mcp/` | Apuntar siempre a `/mcp/`. | Convención adoptada |
| `.env` vs pytest en host | `.env` con hostnames Docker rompe pytest en el host; falta `.env.test`. | Pendiente |
| `DEFINITIONS_COLLECTION` | Fuente de contenido para RAG, sin consumir. | TODO fase-5 |
| Alertas de riesgo | `GET /api/analytics/course/{id}/alerts` devuelve `[]`. | Pendiente (FASE 6) |

---

*TutorIA · Universidad Tecnológica de Pereira · Grupo de Investigación Sirius · 2026*