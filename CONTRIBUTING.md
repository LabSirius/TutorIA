# Guía de contribución / Contributing Guide

## Español

### ¿Quién puede contribuir?

Este repositorio es mantenido por el equipo del proyecto TutorIA del Grupo de Investigación Sirius — Universidad Tecnológica de Pereira. Las contribuciones externas son bienvenidas siempre que estén alineadas con los objetivos del proyecto.

### Ramas (Branches)

Trabajamos con la siguiente estructura de ramas:

| Rama | Propósito |
|------|-----------|
| `main` | Versión estable. Nadie sube directo aquí |
| `dev` | Rama de desarrollo principal |
| `feature/nombre-tarea` | Para desarrollar una funcionalidad nueva |
| `fix/nombre-bug` | Para corregir un error |
| `docs/nombre-doc` | Para agregar o actualizar documentación |

**Ejemplo:**
```bash
# 1. Primero párate en dev
git checkout dev

# 2. Desde dev, crea tu rama de trabajo
git checkout -b feature/rag-pipeline
```

### Cómo subir cambios

1. Crea una rama desde `dev` (nunca desde `main`)
2. Realiza tus cambios
3. Haz commit con un mensaje claro (ver convención abajo)
4. Sube tu rama y abre un Pull Request hacia `dev`
5. Espera revisión antes de hacer merge

### Convención de commits

Usamos el formato: `tipo: descripción corta en minúsculas`

| Tipo | Cuándo usarlo |
|------|--------------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de error |
| `docs` | Documentación |
| `chore` | Tareas de configuración o mantenimiento |
| `test` | Pruebas |
| `refactor` | Mejora de código sin cambiar funcionalidad |

**Ejemplos:**
```
feat: add chat endpoint with ollama integration
fix: correct pgvector similarity search query
docs: update README with azure deployment notes
chore: configure github actions for ci
test: add unit tests for prompt manager rules
refactor: extract llm client into service layer
```

### Convenciones de código

- Todo el código (nombres de variables, funciones, clases, comentarios, docstrings, endpoints, columnas de base de datos) se escribe en **inglés**
- Los textos que ve el estudiante (prompts pedagógicos, mensajes de UI, contenido de cursos) se escriben en **español**
- Se sigue una arquitectura por capas: `routers` (HTTP) → `services` (lógica de negocio) → `models` (datos)

### Subir archivos de documentación

Si solo vas a subir archivos (PDFs, imágenes, documentos) sin tocar código:

1. Coloca el archivo en la carpeta correcta (`docs/`, `data/`, etc.)
2. En la terminal:
```bash
git add .
git commit -m "docs: add nombre-del-archivo"
git push
```

### Lo que NO debe subirse al repo

- Archivos `.env` con credenciales o API keys
- Datos personales de estudiantes
- Archivos temporales o de sistema (`.DS_Store`, `Thumbs.db`)
- Carpetas `node_modules/` o `venv/`
- Modelos de Ollama descargados (son binarios pesados)
- Volúmenes de PostgreSQL o dumps de la base de datos

---

## English

### Who can contribute?

This repository is maintained by the TutorIA project team from the Sirius Research Group — Universidad Tecnológica de Pereira. External contributions are welcome as long as they align with the project's objectives.

### Branches

We work with the following branch structure:

| Branch | Purpose |
|--------|---------|
| `main` | Stable version. No direct pushes |
| `dev` | Main development branch |
| `feature/task-name` | For developing a new feature |
| `fix/bug-name` | For fixing a bug |
| `docs/doc-name` | For adding or updating documentation |

**Example:**
```bash
# 1. First move to dev
git checkout dev

# 2. From dev, create your working branch
git checkout -b feature/rag-pipeline
```

### How to submit changes

1. Create a branch from `dev` (never from `main`)
2. Make your changes
3. Commit with a clear message (see convention below)
4. Push your branch and open a Pull Request against `dev`
5. Wait for review before merging

### Commit convention

We use the format: `type: short description in lowercase`

| Type | When to use it |
|------|---------------|
| `feat` | New functionality |
| `fix` | Bug fix |
| `docs` | Documentation |
| `chore` | Configuration or maintenance tasks |
| `test` | Tests |
| `refactor` | Code improvement without changing functionality |

**Examples:**
```
feat: add chat endpoint with ollama integration
fix: correct pgvector similarity search query
docs: update README with azure deployment notes
chore: configure github actions for ci
test: add unit tests for prompt manager rules
refactor: extract llm client into service layer
```

### Code conventions

- All code (variable names, functions, classes, comments, docstrings, endpoints, database columns) is written in **English**
- Student-facing text (pedagogical prompts, UI messages, course content) is written in **Spanish**
- We follow a layered architecture: `routers` (HTTP) → `services` (business logic) → `models` (data)

### Uploading documentation files

If you're only uploading files (PDFs, images, documents) without touching code:

1. Place the file in the correct folder (`docs/`, `data/`, etc.)
2. In the terminal:
```bash
git add .
git commit -m "docs: add file-name"
git push
```

### What should NOT be committed

- `.env` files with credentials or API keys
- Students' personal data
- Temporary or system files (`.DS_Store`, `Thumbs.db`)
- `node_modules/` or `venv/` folders
- Downloaded Ollama models (heavy binaries)
- PostgreSQL volumes or database dumps