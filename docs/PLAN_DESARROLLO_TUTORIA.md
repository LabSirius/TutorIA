# Plan de Desarrollo TutorIA — Flujo Robusto

> Guía paso a paso para construir TutorIA aplicando las mejores prácticas de Anthropic.
> Cada fase incluye el **prompt exacto** que debes darle a Claude Code en VS Code.

---

## Visión general del flujo

```
FASE 0 → FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6
Contexto   Backend   Prompts   Evals    Frontend  Open edX  Deploy
(1 día)    (1 sem)   (1 sem)   (1 sem)  (2 sem)   (2 sem)   (1 sem)
```

**Regla de oro:** cada fase produce algo funcional y testeado antes de pasar a la siguiente.

---

## FASE 0 — Dar contexto a Claude Code (día 1)

### Qué hacer
Antes de pedirle cualquier código, Claude Code necesita entender el proyecto completo. Abre Claude Code en VS Code dentro de la carpeta del repo y dale este prompt:

### Prompt para Claude Code

```
Lee todos los archivos del repo: README.md, CONTRIBUTING.md, docs/, y 
cualquier archivo en la raíz. Este es el proyecto TutorIA del Grupo Sirius 
de la UTP.

Contexto clave:
- Es un agente tutor virtual con IA para Open edX
- Open edX ya está corriendo en un servidor con recursos limitados
- NO tenemos API key de pago. Usaremos Ollama con un modelo open-source 
  (Llama 3.2 o Mistral) como LLM, expuesto como API compatible con OpenAI
- El backend es Python/FastAPI
- El frontend se integra dentro de Open edX via el plugin 
  openedx-ai-extensions o un XBlock custom
- La infraestructura final será Azure, pero por ahora todo es local/servidor
- Sigue la convención de commits del CONTRIBUTING.md
- Toda rama se crea desde dev

Confirma que entendiste el proyecto y lista la estructura actual del repo.
```

### Entregable
Claude Code confirma que leyó el repo y entiende el stack.

---

## FASE 1 — Backend: API + Base de datos + Servicio LLM (semana 1-2)

### Qué construir
El backend que recibe mensajes del estudiante, los procesa con el LLM, y devuelve respuestas pedagógicas.

### Prompt para Claude Code — Paso 1.1: Scaffolding

```
Crea el scaffolding del backend en backend/. Usa FastAPI con esta estructura:

backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # App FastAPI con CORS, lifespan events
│   ├── config.py            # Settings con pydantic-settings (.env)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py           # POST /api/chat — conversación con TutorIA
│   │   ├── sessions.py       # CRUD de sesiones de tutoría
│   │   ├── students.py       # Perfil del estudiante, nivel, gustos
│   │   ├── evaluations.py    # Generar y calificar quizzes
│   │   └── analytics.py      # Estadísticas para el panel docente
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py    # Wrapper para LLM (OpenAI-compatible API)
│   │   ├── rag_service.py    # Pipeline RAG con ChromaDB
│   │   ├── prompt_manager.py # Carga y selecciona prompts pedagógicos
│   │   └── tts_service.py    # Placeholder para Text-to-Speech
│   ├── models/
│   │   ├── __init__.py
│   │   ├── student.py        # SQLAlchemy + Pydantic: perfil estudiante
│   │   ├── session.py        # Sesión conversacional con historial
│   │   ├── evaluation.py     # Quiz, preguntas, resultados
│   │   ├── module.py         # Asignatura → módulos → temas
│   │   └── analytics.py      # Métricas de uso y progreso
│   ├── prompts/
│   │   ├── system_base.txt        # Prompt base de TutorIA
│   │   ├── diagnostico.txt        # Diagnóstico inicial
│   │   ├── explicacion_basica.txt # Explicación para nivel básico
│   │   ├── explicacion_avanzada.txt
│   │   ├── verificacion.txt       # Verificación de comprensión
│   │   ├── socratico.txt          # Método socrático
│   │   ├── modelado_cognitivo.txt # Pensamiento en voz alta
│   │   ├── retroalimentacion.txt  # Feedback de error
│   │   ├── alerta_riesgo.txt      # Derivar a docente
│   │   └── cierre.txt             # Cierre metacognitivo
│   └── db/
│       ├── __init__.py
│       ├── database.py       # Engine SQLAlchemy async + session
│       └── migrations/       # Alembic
├── requirements.txt
├── Dockerfile
├── .env.example
└── tests/
    ├── test_chat.py
    ├── test_llm_service.py
    └── test_rag_service.py

Requisitos técnicos:
- llm_service.py debe usar la librería 'openai' apuntando a una BASE_URL 
  configurable (por defecto http://localhost:11434/v1 para Ollama)
- La API key debe ser configurable pero con default "ollama" para dev local
- El modelo debe ser configurable (default: "llama3.2")
- Usa SQLite para dev, PostgreSQL para producción (configurable por .env)
- ChromaDB para el vector store del RAG
- Los archivos en prompts/ déjalos vacíos con un comentario TODO
- requirements.txt: fastapi, uvicorn, openai, chromadb, sqlalchemy, 
  alembic, pydantic-settings, python-multipart, httpx, pytest

Crea rama feature/backend-scaffolding desde dev.
Haz commits atómicos siguiendo la convención del CONTRIBUTING.md.
```

### Prompt para Claude Code — Paso 1.2: Modelos de base de datos

```
Ahora implementa los modelos SQLAlchemy en backend/app/models/. 
Basate en el documento de requerimientos (docs/TutorIA_Requerimientos).

Tablas necesarias:

students:
  - id, nombre, email, fecha_registro
  - nivel_global (principiante/intermedio/avanzado)
  - gustos_intereses (JSON)
  - configuracion (preferencia audio, idioma, etc.)

sessions:
  - id, student_id (FK), modulo_id (FK)
  - fecha_inicio, fecha_fin, estado
  - historial_mensajes (JSON array de {role, content, timestamp})
  - resumen_sesion (texto generado al cierre)

modules:
  - id, asignatura_id, nombre, orden, descripcion
  - objetivos_aprendizaje (JSON)
  - contenido_texto (TEXT — fuente para RAG)
  - nivel_dificultad, estado (activo/inactivo)

subjects (asignaturas):
  - id, nombre, descripcion, version_curriculo

evaluations:
  - id, student_id (FK), module_id (FK), session_id (FK)
  - tipo (quiz/ejercicio_codigo/problema)
  - preguntas (JSON), respuestas (JSON), calificacion
  - retroalimentacion, fecha

student_progress:
  - id, student_id (FK), module_id (FK)
  - nivel_modulo, conceptos_dominados (JSON)
  - conceptos_pendientes (JSON), intentos, ultima_sesion

analytics_events:
  - id, student_id (FK), tipo_evento, datos (JSON), timestamp

Crea también las migraciones de Alembic.
Commit: "feat: implementa modelos de base de datos"
```

### Prompt para Claude Code — Paso 1.3: Servicio LLM

```
Implementa backend/app/services/llm_service.py completo.

Debe:
1. Usar la librería 'openai' con base_url configurable (para Ollama)
2. Tener un método send_message(messages, system_prompt, temperature=0.7)
   que retorne la respuesta del LLM
3. Tener un método stream_message() para streaming de respuestas
4. Manejar errores de conexión con retry (3 intentos, backoff exponencial)
5. Loggear cada request: tokens usados, latencia, modelo

Implementa también backend/app/services/prompt_manager.py:
1. Carga los prompts desde backend/app/prompts/*.txt
2. Método get_prompt(tipo, contexto_estudiante) que:
   - Selecciona el prompt correcto según el tipo de interacción
   - Inyecta variables del contexto del estudiante (nombre, nivel, 
     módulo actual, conceptos dominados)
   - Retorna el system prompt completo listo para enviar al LLM

Implementa backend/app/routers/chat.py:
1. POST /api/chat recibe: { student_id, message, session_id? }
2. Recupera el perfil del estudiante y su sesión activa
3. Construye el system prompt con prompt_manager
4. Envía al LLM con el historial de la sesión como contexto
5. Guarda la respuesta en el historial de la sesión
6. Retorna: { response, session_id, prompt_type_used }

Escribe tests en tests/test_chat.py que mockeen el LLM.
Commit: "feat: implementa servicio LLM y endpoint de chat"
```

### Entregable de FASE 1
Un backend funcional que puedes probar con:
```bash
cd backend && uvicorn app.main:app --reload
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"student_id": 1, "message": "Hola, quiero aprender Python"}'
```

---

## FASE 2 — Prompts pedagógicos (semana 3)

### Qué hacer
Escribir los system prompts usando el Marco Pedagógico V2 de la Dra. Grajales. 
**Esto se hace en este chat (Claude Chat), no en Claude Code**, porque requiere 
diseño pedagógico, no código.

### Lo que se produce aquí
1. Prompt base del sistema (personalidad de TutorIA)
2. 9 prompts especializados según el Marco V2:
   - Diagnóstico inicial
   - Explicación básica (analogías rurales de Risaralda)
   - Explicación avanzada
   - Verificación de comprensión
   - Socrático
   - Modelado cognitivo
   - Retroalimentación de error
   - Alerta de riesgo
   - Cierre metacognitivo
3. Reglas de adaptabilidad (lógica de decisión)

### Luego con Claude Code

```
Lee los archivos de prompts en backend/app/prompts/ y reemplaza los TODOs
con el contenido que te voy a pegar. También actualiza prompt_manager.py
para implementar las reglas de adaptabilidad del Marco Pedagógico V2:

Reglas:
- Si el estudiante acierta al primer intento → reducir andamiaje, 
  subir dificultad
- Si comete el mismo error 2 veces → cambiar estrategia explicativa
- Si responde "no sé" → retroceder al último concepto dominado
- Si lleva 3+ sesiones sin avanzar → generar alerta para docente
- Si expresa frustración → pausar contenido, empatía, ofrecer pausa
- Si no usa TutorIA en 5+ días → notificación proactiva amable

Commit: "feat: implementa prompts pedagógicos y reglas de adaptabilidad"
```

### Entregable de FASE 2
Los 10 archivos de prompts completos + lógica de adaptabilidad en el código.

---

## FASE 3 — Evaluaciones (evals) del agente (semana 4)

### Qué hacer
Crear un set de pruebas que verifican que TutorIA se comporta correctamente. 
Aplicando la metodología de Anthropic: definir inputs, outputs esperados, 
y métricas.

### Prompt para Claude Code

```
Crea un framework de evaluaciones en backend/evals/:

backend/evals/
├── eval_runner.py          # Script que corre todas las evals
├── eval_cases/
│   ├── diagnostico.json    # Casos de prueba para diagnóstico
│   ├── adaptabilidad.json  # Casos para reglas de adaptabilidad
│   ├── nivel_basico.json   # Respuestas para estudiante principiante
│   ├── nivel_avanzado.json # Respuestas para estudiante avanzado
│   ├── frustracion.json    # Manejo emocional
│   ├── fuera_tema.json     # Preguntas fuera del módulo
│   └── seguridad.json      # No dar respuestas dañinas
└── eval_metrics.py         # Funciones de scoring

Cada archivo JSON tiene este formato:
{
  "test_name": "diagnostico_estudiante_nuevo",
  "student_profile": { nivel, modulo, historial },
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
2. Enviar al LLM con el prompt correspondiente
3. Evaluar la respuesta contra expected/forbidden behavior
4. Generar un reporte con score por categoría

Usa un LLM como juez (el mismo Ollama) para evaluar si la respuesta
cumple los criterios. Esto es la técnica "LLM-as-judge" de Anthropic.

Commit: "feat: framework de evaluaciones pedagógicas"
```

### Entregable de FASE 3
```bash
cd backend && python -m evals.eval_runner
# Output: Reporte con scores por categoría
```

---

## FASE 4 — RAG: contenido pedagógico (semana 5)

### Qué hacer
Crear el contenido textual de las asignaturas e indexarlo en ChromaDB para 
que TutorIA pueda buscar y citar material relevante.

### Lo que se produce aquí (Claude Chat)
El contenido de los módulos de Programación I y Matemática, contextualizado 
para Risaralda, en archivos de texto plano.

### Prompt para Claude Code

```
Implementa el pipeline RAG completo en backend/app/services/rag_service.py:

1. Función ingest_content(module_id):
   - Lee el contenido del módulo desde la base de datos
   - Divide en chunks de ~500 tokens con overlap de 50
   - Genera embeddings (usa el endpoint de embeddings de Ollama)
   - Almacena en ChromaDB con metadata: module_id, subject, tema

2. Función search_context(query, module_id, top_k=3):
   - Busca en ChromaDB los chunks más relevantes
   - Filtra por module_id para no mezclar asignaturas
   - Retorna los chunks como contexto para el LLM

3. Actualiza el endpoint POST /api/chat para:
   - Antes de enviar al LLM, buscar contexto relevante con RAG
   - Incluir el contexto en el system prompt como sección "Material de referencia"
   - El LLM debe citar el material cuando lo use

4. Crea un comando CLI para ingestar contenido:
   python -m app.cli ingest --module-id 1

También crea backend/data/ con archivos placeholder:
  data/programacion1/
    modulo01_pensamiento_computacional.txt
    modulo02_variables_tipos.txt
    modulo03_estructuras_control.txt
  data/matematica/
    modulo01_logica_proposicional.txt
    modulo02_teoria_conjuntos.txt

Commit: "feat: implementa pipeline RAG con ChromaDB"
```

### Entregable de FASE 4
RAG funcional: el chat ahora cita material de los módulos en sus respuestas.

---

## FASE 5 — Integración con Open edX (semana 6-7)

### Qué hacer
Conectar el backend con la instancia de Open edX que ya está corriendo.

### Prompt para Claude Code

```
Crea la integración con Open edX en openedx/:

Opción A (preferida): Configurar openedx-ai-extensions
- Crea openedx/README.md con instrucciones para:
  1. Instalar el plugin en la instancia de Open edX
  2. Configurar para que apunte a nuestro backend FastAPI
  3. Crear perfiles de AI para cada tipo de interacción
  4. Configurar scopes por curso

Opción B (fallback): XBlock custom
- Crea openedx/tutoria_xblock/ con un XBlock que:
  1. Muestre un widget de chat dentro del curso
  2. Envíe mensajes al backend via API
  3. Renderice respuestas con markdown
  4. Tenga botón de audio (TTS placeholder)
  5. Muestre el avatar de TutorIA

En ambos casos, crea openedx/docker-compose.override.yml para
development local que conecte Open edX con el backend.

Commit: "feat: integración con Open edX"
```

---

## FASE 6 — Panel docente + Analytics (semana 8)

### Prompt para Claude Code

```
Implementa el panel del docente:

1. Backend endpoints en backend/app/routers/analytics.py:
   - GET /api/analytics/course/{id}/summary
     (estudiantes activos, progreso promedio, tasa aprobación)
   - GET /api/analytics/student/{id}/detail
     (módulos completados, evaluaciones, tiempo de uso)
   - GET /api/analytics/course/{id}/alerts
     (estudiantes en riesgo: inactivos 5+ días o 3+ sesiones estancados)

2. Frontend del panel:
   Si Open edX no permite UI custom fácilmente, crea una SPA mínima en 
   frontend/ con React que consuma estos endpoints.
   
   Vistas:
   - Dashboard general del curso (cards con métricas)
   - Lista de estudiantes con indicadores de riesgo
   - Detalle de estudiante (timeline de sesiones, evaluaciones)
   - Vista de contenido por módulo (qué temas generan más dudas)

Commit: "feat: panel docente con analytics"
```

---

## FASE 7 — Deploy y pruebas piloto (semana 9-10)

### Prompt para Claude Code

```
Prepara el proyecto para deploy:

1. Crea infra/docker-compose.yml completo:
   - backend (FastAPI)
   - ollama (con modelo pre-descargado)
   - chromadb
   - postgres
   - nginx (reverse proxy)

2. Crea infra/docker-compose.prod.yml con overrides para producción:
   - Variables de entorno para Azure
   - Volúmenes persistentes
   - Health checks
   - Restart policies

3. Crea .github/workflows/ci.yml:
   - Lint (ruff)
   - Tests (pytest)
   - Build Docker images
   - Deploy a Azure (manual trigger)

4. Crea scripts/setup.sh que automatice:
   - Instalar Ollama
   - Descargar modelo
   - Ingestar contenido de módulos
   - Crear usuario admin
   - Correr migraciones

Commit: "chore: configuración de deploy y CI/CD"
```

---

## Resumen: qué se hace dónde

| Tarea | Herramienta | Fase |
|-------|-------------|------|
| Scaffolding del backend | Claude Code (VS Code) | 1 |
| Modelos de BD y migraciones | Claude Code | 1 |
| Servicio LLM + chat endpoint | Claude Code | 1 |
| Diseño de prompts pedagógicos | Claude Chat (aquí) | 2 |
| Reglas de adaptabilidad | Claude Chat → Claude Code | 2 |
| Framework de evaluaciones | Claude Code | 3 |
| Contenido de asignaturas | Claude Chat → archivos | 4 |
| Pipeline RAG | Claude Code | 4 |
| Integración Open edX | Claude Code | 5 |
| Panel docente | Claude Code | 6 |
| Docker + CI/CD + Deploy | Claude Code | 7 |
| Documentación y papers | Claude Chat | Continuo |

---

## Checklist por fase

- [ ] **FASE 0** — Claude Code entiende el proyecto
- [ ] **FASE 1** — Backend funcional, puedo hacer POST /api/chat y recibir respuesta
- [ ] **FASE 2** — Los 10 prompts están escritos y el agente se comporta como tutor
- [ ] **FASE 3** — Las evals pasan con score > 80% en cada categoría
- [ ] **FASE 4** — RAG funciona, el agente cita material de los módulos
- [ ] **FASE 5** — TutorIA funciona dentro de Open edX
- [ ] **FASE 6** — El docente puede ver estadísticas de sus estudiantes
- [ ] **FASE 7** — Todo corre en Docker, CI/CD funciona, listo para piloto

---

*TutorIA · Universidad Tecnológica de Pereira · Grupo Sirius · 2026*
