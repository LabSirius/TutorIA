# Proyecto TutorIA — Documento de Requerimientos de Software

**Agente Autónomo basado en Grandes Modelos de Lenguaje para Democratizar el Acceso a la Educación Superior en Zonas Rurales de Colombia**

Universidad Tecnológica de Pereira — Grupo de Investigación Sirius
Julio 2026

---

## 1. Introducción

El presente documento describe los requerimientos funcionales y no funcionales del sistema TutorIA, un agente autónomo de inteligencia artificial basado en Grandes Modelos de Lenguaje (LLMs) diseñado para democratizar el acceso a la educación superior en zonas rurales de Colombia. La plataforma se integrará al entorno Open edX y empleará un motor LLM con interfaz OpenAI-compatible, desplegado con Ollama (modelos open-source locales) durante la fase de desarrollo y piloto, con capacidad de incorporación futura de Claude API (Anthropic) mediante estrategia híbrida con clasificador.

TutorIA actuará como tutor virtual inteligente con personalidad pedagógica proactiva, adaptado a estudiantes con conocimiento cero en las materias impartidas, cubriendo inicialmente Programación I (Python) e Introducción a la Matemática, en alineación con los currículos de pregrado y posgrado de la institución. El comportamiento pedagógico del agente se rige por el Marco Pedagógico V2 desarrollado por la Dra. Luz Elena Grajales López.

### 1.1 Propósito

Este documento tiene como propósito definir el alcance, los actores, los requerimientos funcionales (RF) y no funcionales (RNF), y los casos de uso principales del sistema TutorIA, sirviendo como referencia técnica para los equipos de desarrollo, diseño pedagógico e investigación.

### 1.2 Alcance

TutorIA es una plataforma educativa basada en IA que provee tutoría personalizada, retroalimentación continua con elementos de gamificación, y un panel docente con analíticas de aprendizaje y trazabilidad completa de las interacciones estudiante-agente. Su despliegue inicial cubre dos materias universitarias, con capacidad de expansión modular a otras asignaturas.

### 1.3 Definiciones y Acrónimos

| Término / Sigla | Definición |
|---|---|
| **TutorIA** | Agente autónomo de IA para tutoría educativa personalizada |
| **LLM** | Large Language Model – Modelo de Lenguaje de Gran Escala |
| **Open edX** | Plataforma LMS (Learning Management System) de código abierto donde se desplegará el agente |
| **Ollama** | Herramienta open-source para ejecutar modelos LLM localmente con API compatible OpenAI |
| **Claude** | Modelo de lenguaje de Anthropic, planificado como motor LLM en fase de producción mediante clasificador |
| **Haiku** | Modelo ligero de Anthropic, planificado como clasificador de peticiones para enrutamiento de consultas |
| **RF** | Requerimiento Funcional |
| **RNF** | Requerimiento No Funcional |
| **TTS** | Text-to-Speech – Síntesis de voz a partir de texto |
| **RAG** | Retrieval-Augmented Generation – Generación aumentada por recuperación de contexto |
| **PostgreSQL** | Sistema de gestión de bases de datos relacional, utilizado como base de datos unificada del sistema |
| **pgvector** | Extensión de PostgreSQL para almacenamiento y búsqueda de vectores (embeddings semánticos) |
| **MongoDB** | Base de datos NoSQL utilizada por Open edX para almacenar contenido de cursos |
| **Azure** | Plataforma de nube de Microsoft que proveerá el servidor donde se desplegará TutorIA. El servidor es infraestructura propia del proyecto (IaaS) |
| **Avatar** | Representación visual animada del tutor virtual |
| **Módulo** | Unidad curricular dentro de una asignatura |
| **Gamificación** | Estrategia de aplicar elementos de juego (puntos, insignias, niveles) al proceso educativo para incrementar la motivación |
| **Marco V2** | Marco Pedagógico y Metodológico Versión 2.0 elaborado por la Dra. Luz Elena Grajales López, que define las estrategias pedagógicas del agente |

---

## 2. Descripción General del Sistema

### 2.1 Contexto del Sistema

TutorIA se desplegará dentro de Open edX, integrándose como un agente conversacional accesible desde el LMS. El backend del agente se construye con Python (FastAPI) y emplea un motor LLM con interfaz OpenAI-compatible, lo que permite intercambiar proveedores sin modificar código. En la fase de desarrollo y piloto se utiliza Ollama con modelos open-source locales (Llama 3.2, Mistral u otro); en fases posteriores se podrá incorporar Claude API (Anthropic) mediante estrategia híbrida con clasificador según disponibilidad presupuestal.

El sistema completo (backend FastAPI, base de datos PostgreSQL, Ollama con el modelo LLM local, pipeline RAG) se desplegará en un servidor propio en la nube de Microsoft Azure. Azure se utiliza como infraestructura (Infrastructure-as-a-Service): un servidor donde vive TutorIA con todos sus componentes. No se utiliza Azure OpenAI Service como proveedor de LLM. El modelo de lenguaje corre localmente dentro del propio servidor de Azure mediante Ollama, garantizando que los datos de los estudiantes no salen del servidor controlado por el proyecto y cumpliendo con la Ley 1581 de 2012 (Habeas Data).

Las especificaciones técnicas del servidor Azure (tipo de instancia, capacidad de RAM, presencia y modelo de GPU, almacenamiento) están en proceso de definición y compra. Estas especificaciones son críticas porque determinan el tamaño máximo del modelo LLM que puede ejecutarse localmente y, por tanto, la calidad de las respuestas pedagógicas del agente.

La base de datos unificada del sistema es PostgreSQL, que almacena tanto los datos relacionales (perfiles, sesiones, retroalimentación) como los vectores semánticos del RAG mediante la extensión pgvector, y los prompts pedagógicos del agente. Se implementará una pasarela de sincronización desde MongoDB (base de datos de Open edX) hacia PostgreSQL para unificar la información de cursos, módulos y estudiantes inscritos.

Todo el código fuente del proyecto se publica en un repositorio de acceso público en GitHub para garantizar transparencia y reproducibilidad académica.

### 2.2 Actores del Sistema

| Actor | Descripción |
|---|---|
| **Estudiante** | Usuario principal. Interactúa con TutorIA mediante texto y voz, recibe retroalimentación continua con elementos de gamificación (puntos, insignias, niveles), y visualiza videos explicativos del avatar. |
| **Docente** | Accede al panel de estadísticas para monitorear el progreso de los estudiantes. Tiene trazabilidad completa de las conversaciones entre estudiantes y TutorIA. Puede gestionar y revisar el contenido de las asignaturas y los prompts pedagógicos. |
| **Administrador** | Configura el sistema, gestiona usuarios, materias, módulos curriculares y la pasarela de sincronización MongoDB→PostgreSQL dentro de Open edX. |
| **TutorIA (Sistema)** | Agente autónomo que actúa como tutor virtual: responde preguntas, genera retroalimentación continua, aplica gamificación, adapta la experiencia al perfil del estudiante, y selecciona la estrategia pedagógica según las reglas del Marco Pedagógico V2. |

### 2.3 Asignaturas Iniciales

En la primera fase del proyecto se implementarán dos asignaturas, cada una organizada en módulos curriculares alineados con los planes de estudio de pregrado y maestría:

- **Programación I (Python):** Introducción al pensamiento computacional, variables y tipos de datos, estructuras de control, funciones, manejo de listas y diccionarios, programación orientada a objetos básica, manejo de archivos, y buenas prácticas de codificación.
- **Introducción a la Matemática:** Lógica proposicional, teoría de conjuntos, relaciones y funciones, aritmética y álgebra básica, geometría analítica introductoria, y fundamentos de estadística descriptiva.

---

## 3. Requerimientos Funcionales

Prioridad: **Alta** (crítico para MVP), **Media** (segunda iteración), **Baja** (versiones futuras).

| ID | Nombre | Descripción | Prioridad | Categoría |
|---|---|---|---|---|
| **RF-01** | Despliegue en Open edX | El sistema TutorIA debe integrarse y desplegarse dentro de la plataforma Open edX, siendo accesible desde la interfaz del LMS para estudiantes y docentes. | Alta | Plataforma |
| **RF-02** | Repositorio Abierto | Todo el código fuente, configuraciones y documentación base del proyecto deben publicarse en un repositorio de acceso público (GitHub), permitiendo su reproducción y colaboración académica. | Alta | Plataforma |
| **RF-03** | Integración con Motor LLM | El agente debe utilizar un motor LLM con interfaz OpenAI-compatible, configurado para Ollama (local) en fase de desarrollo/piloto, con capacidad de migración a Claude API (Anthropic) sin modificar código. La configuración del proveedor, modelo y API key debe ser externa al código. | Alta | Plataforma |
| **RF-04** | Gestión de Perfil de Estudiante | El sistema debe crear y mantener un perfil individual por estudiante que almacene: nivel de conocimiento actual por asignatura, historial de interacciones, gustos e intereses declarados, ritmo de aprendizaje, puntos de gamificación y resultados de retroalimentación previos. | Alta | Perfil |
| **RF-05** | Adaptación del Nivel de Aprendizaje | TutorIA debe ajustar automáticamente el nivel de dificultad y la forma de explicar los conceptos según el perfil de aprendizaje del estudiante, identificando brechas de conocimiento y adaptando el ritmo de avance según las reglas de adaptabilidad del Marco Pedagógico V2. | Alta | Perfil |
| **RF-06** | Persistencia del Contexto | El agente debe mantener y recuperar el contexto de cada sesión y de sesiones anteriores para garantizar continuidad en el proceso de aprendizaje, evitando repetición innecesaria y personalizando el saludo y referencias al estudiante. | Alta | Perfil |
| **RF-07** | Chat Conversacional | Los estudiantes deben poder interactuar con TutorIA mediante texto libre en lenguaje natural. El agente debe responder en lenguaje claro, didáctico y adaptado al nivel del estudiante. | Alta | Interacción |
| **RF-08** | Respuesta por Audio (TTS) | TutorIA debe poder responder al estudiante en audio mediante síntesis de voz (Text-to-Speech), permitiendo al estudiante escuchar las explicaciones. | Alta | Interacción |
| **RF-09** | Avatar de TutorIA | El sistema debe presentar un avatar visual que represente a TutorIA durante las interacciones y en los videos explicativos, humanizando la experiencia de tutoría. | Alta | Interacción |
| **RF-10** | Videos Explicativos con Avatar | TutorIA debe contar con videos pregrabados o generados dinámicamente en los que el avatar explique los temas de las asignaturas, alineados con los módulos curriculares. | Alta | Interacción |
| **RF-11** | Indexación de Contenido Pedagógico (RAG) | El contenido textual de las asignaturas debe procesarse mediante un pipeline RAG: dividido en fragmentos, convertido en embeddings vectoriales y almacenado en PostgreSQL con pgvector para búsqueda semántica. Las respuestas del agente deben basarse en el material curricular indexado. Este proceso no implica reentrenar ni modificar los parámetros internos del modelo LLM; el modelo permanece intacto y consulta el contenido indexado en tiempo real durante la generación de cada respuesta. | Alta | Contenido |
| **RF-12** | Organización por Módulos Curriculares | Cada asignatura debe estar organizada en módulos que sigan el plan educativo oficial, definidos por los docentes. | Alta | Contenido |
| **RF-13** | Alineación Curricular | Los materiales de las asignaturas y las respuestas de TutorIA deben estar alineados con el currículo oficial de la universidad y de la maestría. | Alta | Contenido |
| **RF-14** | Diseño para Conocimiento Cero | TutorIA debe estar diseñado para estudiantes sin conocimiento previo, empleando analogías, ejemplos cotidianos y un lenguaje accesible y progresivo. | Alta | Contenido |
| **RF-15** | Retroalimentación Continua | El sistema debe proveer retroalimentación continua al estudiante mediante actividades cortas (quizzes, ejercicios de código, problemas matemáticos) integradas en la conversación, adaptadas al nivel del estudiante, con retroalimentación inmediata y elementos de gamificación. El enfoque es formativo, no evaluativo. | Alta | Retroalimentación |
| **RF-16** | Tutor Proactivo, Incentivador y Gamificado | TutorIA debe tener comportamiento proactivo: motivar al estudiante a continuar estudiando, sugerir temas a repasar, felicitar logros, identificar momentos de desánimo, otorgar recompensas gamificadas (puntos, insignias, rachas) y ofrecer estrategias de estudio personalizadas. | Alta | Retroalimentación |
| **RF-17** | Registro de Resultados | Los resultados de cada interacción de retroalimentación deben quedar registrados en el perfil del estudiante y ser accesibles tanto para el estudiante como para el docente. | Alta | Retroalimentación |
| **RF-18** | Panel Docente – Estadísticas y Trazabilidad | Los docentes deben tener acceso a un panel donde puedan visualizar: progreso individual y grupal, resultados de retroalimentación, tiempo de uso por módulo, temas con mayor dificultad, alertas de deserción, y el historial completo de las conversaciones entre cada estudiante y TutorIA. | Alta | Docente |
| **RF-19** | Panel Docente – Gestión de Contenido y Prompts | Los docentes deben poder revisar, actualizar y aprobar el contenido de las asignaturas y los prompts pedagógicos (almacenados en PostgreSQL) desde la plataforma. | Media | Docente |
| **RF-20** | Gestión de Asignaturas y Módulos | El sistema debe permitir crear, editar, activar y desactivar asignaturas y módulos curriculares desde una interfaz administrativa. | Alta | Admin |
| **RF-21** | Prompts Pedagógicos en Base de Datos | Las instrucciones pedagógicas (system prompts) del agente deben almacenarse en PostgreSQL, no en archivos de texto, permitiendo su edición, versionado, auditoría de cambios y gestión desde el panel docente sin intervención de desarrolladores. | Alta | Plataforma |
| **RF-22** | Pasarela MongoDB → PostgreSQL | El sistema debe implementar una pasarela de sincronización que traslade la información relevante de MongoDB (base de datos de Open edX: cursos, módulos, estudiantes inscritos) hacia PostgreSQL, unificando la información en un solo motor de base de datos. | Alta | Plataforma |
| **RF-23** | Clasificador Inteligente de Peticiones (futuro) | En fases posteriores, cuando se disponga de Claude API, se debe implementar un clasificador ligero (Haiku de Anthropic) que analice cada petición del estudiante y la enrute al modelo LLM más apropiado: modelo local Ollama (corriendo en el servidor Azure) para consultas simples, y Claude API externa para consultas complejas que requieran mayor capacidad de razonamiento. Esto optimiza costos manteniendo el grueso del procesamiento en infraestructura propia. | Baja | Plataforma |
| **RF-24** | Sistema de Gamificación y Recompensas (propuesta) | TutorIA debe incorporar elementos de gamificación como propuesta pedagógica para incrementar la motivación del estudiante. Se propone explorar mecanismos como: puntos de experiencia por interacción exitosa, insignias por logros (completar módulos, rachas de estudio, primer programa), niveles de progreso visual, y retos opcionales con recompensas extras. El diseño final de la mecánica de gamificación se definirá en conjunto con el equipo pedagógico durante las fases de desarrollo posteriores. | Media | Retroalimentación |
| **RF-25** | Despliegue en Infraestructura Azure | El sistema completo (backend FastAPI, base de datos PostgreSQL con pgvector, Ollama con el modelo LLM local, pipeline RAG, pasarela MongoDB) debe desplegarse en un servidor propio en Microsoft Azure (Infrastructure-as-a-Service). El servidor y el modelo LLM son controlados directamente por el proyecto, sin depender de servicios externos de LLM. La infraestructura debe estar containerizada (Docker) para facilitar el despliegue, la escalabilidad y la portabilidad. Las especificaciones técnicas del servidor (tipo de instancia, RAM, GPU) están por definir en función del modelo LLM seleccionado. | Alta | Plataforma |

---

## 4. Requerimientos No Funcionales

| ID | Categoría | Descripción | Criterio de Aceptación |
|---|---|---|---|
| **RNF-01** | Rendimiento | El agente debe responder a consultas del estudiante en un tiempo razonable para no interrumpir el flujo de aprendizaje. | Tiempo de respuesta < 5 seg para texto; < 10 seg para audio. |
| **RNF-02** | Disponibilidad | La plataforma debe estar disponible de forma continua para soportar a estudiantes en zonas rurales. | Disponibilidad mínima del 99% mensual. |
| **RNF-03** | Escalabilidad | El sistema debe soportar el crecimiento de usuarios, asignaturas y módulos sin degradación. | Soporte para al menos 500 usuarios concurrentes; arquitectura escalable. |
| **RNF-04** | Accesibilidad | La plataforma debe ser accesible desde dispositivos de bajo costo y conexiones lentas. | Compatible con dispositivos con 2GB de RAM; funcional con 3G. |
| **RNF-05** | Seguridad y Privacidad | Los datos personales deben protegerse conforme a la Ley 1581 de 2012 (Habeas Data). Los datos permanecen en el servidor Azure controlado por el proyecto, sin viajar a servicios externos. | Cifrado TLS para transmisión; cifrado AES-256 para almacenamiento. |
| **RNF-06** | Usabilidad | La interfaz debe ser intuitiva para estudiantes con escasa experiencia tecnológica. | Puntuación SUS ≥ 75 en pruebas con usuarios objetivo. |
| **RNF-07** | Mantenibilidad | El código fuente debe seguir principios de diseño limpio y estar documentado. | Cobertura de documentación ≥ 80%; código bajo estándar de linting. |
| **RNF-08** | Portabilidad | El sistema debe poder cambiar de proveedor LLM (Ollama → Claude API) sin modificar código, solo configuración. PostgreSQL es la única base de datos requerida (datos + vectores + prompts). El sistema completo debe correr en contenedores Docker para ser desplegado en servidor Azure y facilitar migraciones futuras. | Cambio de LLM = solo modificar .env. Toda la stack contenerizada. |
| **RNF-09** | Calidad Pedagógica | Las respuestas del agente deben superar revisión pedagógica formal antes de producción. | Evaluación con al menos 2 docentes por asignatura. |
| **RNF-10** | Idioma | El sistema debe operar en español colombiano. | 100% de la interfaz y respuestas en español. |
| **RNF-11** | Infraestructura Azure | El sistema debe desplegarse en un servidor propio de Microsoft Azure (IaaS/PaaS, no como servicio SaaS de terceros para el LLM). Las especificaciones técnicas del servidor (tipo de instancia, RAM, GPU, almacenamiento) están en proceso de compra y definición. El modelo LLM local seleccionado (Ollama) debe ser compatible con las capacidades finales del servidor. | Servidor Azure operativo antes de fase piloto. |

---

## 5. Casos de Uso

### CU-01 — Sesión de Tutoría Personalizada con el Estudiante

**Actores:** Estudiante (actor principal), TutorIA (sistema)

**Precondiciones:**
- El estudiante está registrado y autenticado en Open edX.
- El estudiante tiene al menos una asignatura activa asignada.
- El perfil del estudiante existe en el sistema (nuevo o existente con historial).

**Flujo Principal:**
1. El estudiante accede al módulo de TutorIA desde Open edX.
2. TutorIA recupera el perfil, historial y estado de gamificación del estudiante desde PostgreSQL.
3. TutorIA saluda al estudiante personalizadamente y sugiere continuar donde quedó o explorar un nuevo tema del módulo actual.
4. El estudiante escribe una pregunta o selecciona un tema.
5. TutorIA busca contexto relevante del módulo en el índice vectorial de PostgreSQL (pgvector) mediante RAG.
6. El gestor de prompts selecciona la estrategia pedagógica adecuada según las reglas del Marco V2.
7. TutorIA envía la petición al motor LLM (Ollama local en el servidor Azure) con el contexto recuperado y el prompt seleccionado.
8. El avatar de TutorIA presenta la respuesta en pantalla (texto + audio TTS si el estudiante lo tiene activado).
9. El estudiante hace preguntas de seguimiento; el agente mantiene el hilo conversacional.
10. Al completar el tema, TutorIA propone una actividad de retroalimentación continua con elementos gamificados.
11. El estudiante realiza la actividad y recibe retroalimentación inmediata más recompensas (XP, insignias, actualización de racha).
12. TutorIA actualiza el perfil, el progreso del estudiante y el estado de gamificación en PostgreSQL.
13. TutorIA motiva al estudiante celebrando el logro y sugiere el próximo paso.

**Flujos Alternativos:**
- **FA-01:** El estudiante es nuevo (sin historial). El gestor de prompts activa la estrategia de diagnóstico inicial antes de empezar el primer módulo.
- **FA-02:** El estudiante hace una pregunta fuera del alcance del módulo activo. TutorIA indica amablemente que el tema está fuera del programa actual y sugiere el módulo correspondiente.
- **FA-03:** El estudiante solicita escuchar la respuesta en audio. TutorIA activa la respuesta TTS con el avatar animado.
- **FA-04:** El estudiante comete el mismo error dos veces. El gestor de prompts cambia automáticamente a la estrategia socrática.
- **FA-05:** TutorIA detecta señales de frustración en el lenguaje. Activa la estrategia de alerta de riesgo, cambia a un tono empático y notifica al docente.

**Postcondiciones:**
- El perfil del estudiante queda actualizado con el progreso, nivel, resultados y gamificación.
- El historial completo de la sesión (incluida la estrategia pedagógica usada en cada turno) queda registrado en PostgreSQL, disponible para el docente en el panel.
- TutorIA tiene el contexto completo para continuar en la próxima sesión.

---

### CU-02 — Consulta del Panel Docente con Trazabilidad de Conversaciones

**Actores:** Docente (actor principal), TutorIA (sistema)

**Precondiciones:**
- El docente está autenticado en Open edX con rol de docente.
- El docente tiene al menos una asignatura asignada con estudiantes activos.
- Existen datos de sesiones de TutorIA registrados en el sistema.

**Flujo Principal:**
1. El docente accede al módulo de Panel Docente desde Open edX.
2. El sistema muestra el resumen general de la asignatura: número de estudiantes activos, progreso promedio por módulo, tasa de aprobación de retroalimentación, ranking de gamificación.
3. El docente selecciona un estudiante específico para ver su perfil detallado.
4. El sistema presenta: módulos completados, tiempo de sesión, resultados de retroalimentación, temas con mayor dificultad, estado de gamificación (XP, insignias, rachas) y frecuencia de interacción con TutorIA.
5. El docente accede al historial completo de conversaciones del estudiante con TutorIA.
6. El sistema muestra cada mensaje del estudiante y cada respuesta del agente, incluyendo la estrategia pedagógica aplicada en cada turno (diagnóstico, socrático, alerta de riesgo, etc.).
7. El docente visualiza las alertas automáticas del sistema para estudiantes con bajo rendimiento o inactividad prolongada.
8. El docente accede a la sección de contenido y prompts pedagógicos de la asignatura para revisar o actualizar el material y las instrucciones del agente.
9. El docente puede editar un prompt pedagógico directamente desde la interfaz; el sistema registra la nueva versión con el autor y la fecha.

**Flujos Alternativos:**
- **FA-01:** No hay datos suficientes para estadísticas. El sistema muestra un mensaje indicando que se necesitan más sesiones registradas.
- **FA-02:** El docente quiere exportar el reporte. El sistema genera un archivo descargable (PDF/Excel) con las estadísticas del grupo o del estudiante seleccionado.
- **FA-03:** El docente detecta un patrón problemático en las conversaciones. Puede modificar el prompt correspondiente y validar el efecto en las siguientes sesiones.

**Postcondiciones:**
- El docente tiene visibilidad completa del estado académico y conversacional de sus estudiantes.
- Los cambios en prompts pedagógicos quedan versionados con historial de auditoría.
- El acceso al panel queda auditado para garantizar privacidad de datos estudiantiles.

---

### CU-03 — Creación y Configuración de un Módulo Curricular con Ingesta RAG

**Actores:** Administrador (actor principal), Docente (actor secundario), TutorIA (sistema)

**Precondiciones:**
- El administrador está autenticado en el sistema con permisos de administración.
- La asignatura en la cual se creará el módulo ya existe (sincronizada previamente desde Open edX vía pasarela MongoDB → PostgreSQL).
- El contenido textual del módulo ha sido previamente revisado y aprobado por el docente responsable.

**Flujo Principal:**
1. El administrador accede al panel de administración de contenidos dentro de Open edX.
2. Selecciona la asignatura destino y hace clic en 'Crear nuevo módulo'.
3. Ingresa el nombre del módulo, número de orden dentro de la asignatura y descripción general.
4. Carga el contenido textual del módulo en el editor de contenido.
5. Define los objetivos de aprendizaje del módulo, alineados con el currículo oficial.
6. Configura los parámetros de retroalimentación continua: tipo de actividades, criterios de recompensas gamificadas.
7. Asigna el módulo al nivel de conocimiento correspondiente para que TutorIA pueda adaptar su uso al perfil del estudiante.
8. El docente responsable revisa el módulo en modo previsualización y lo aprueba.
9. El administrador activa el módulo para que esté disponible a los estudiantes inscritos.
10. El pipeline RAG procesa el contenido: lo divide en fragmentos, genera embeddings con Ollama y los almacena en PostgreSQL con pgvector.
11. El módulo queda disponible para consulta semántica durante las sesiones de tutoría.

**Flujos Alternativos:**
- **FA-01:** El docente rechaza el módulo en la revisión. El sistema regresa el módulo a estado 'borrador' con los comentarios del docente para corrección.
- **FA-02:** El contenido cargado excede el límite de texto permitido. El sistema notifica el error e indica al administrador que debe dividir el contenido en submódulos.
- **FA-03:** El administrador desea desactivar temporalmente un módulo ya activo. El sistema lo marca como inactivo sin eliminar el historial de estudiantes ni los vectores indexados.
- **FA-04:** La sincronización desde Open edX (MongoDB) trae automáticamente nuevos módulos. La pasarela los inserta como borradores para revisión por parte del docente antes de activarlos.

**Postcondiciones:**
- El módulo queda activo dentro de la asignatura y disponible para los estudiantes inscritos.
- TutorIA puede usar el contenido del módulo en sesiones de tutoría mediante búsqueda semántica en pgvector.
- El docente puede visualizar el módulo activo en su panel de gestión.
- Queda un registro auditable de quién creó, revisó y aprobó el módulo, con fecha y versión.

---

## 6. Restricciones y Supuestos

### 6.1 Restricciones

- La plataforma se integra en Open edX como LMS base. Se requiere una pasarela de sincronización MongoDB → PostgreSQL para unificar los datos.
- PostgreSQL con pgvector es la única base de datos del sistema (datos relacionales, vectores semánticos y prompts pedagógicos).
- En desarrollo y piloto se emplea Ollama con modelos open-source como motor LLM local; la incorporación futura de Claude API se realizará mediante estrategia híbrida con clasificador.
- El sistema completo se despliega en un servidor propio en Microsoft Azure. Azure se utiliza como infraestructura (IaaS), no como proveedor de LLM.
- Las especificaciones técnicas del servidor Azure están en proceso de definición y compra. Esta decisión condiciona el tamaño máximo del modelo LLM local ejecutable.
- Las asignaturas iniciales son Programación I (Python) e Introducción a la Matemática.
- El contenido curricular debe estar alineado con los planes de estudio de la Universidad Tecnológica de Pereira.
- Todo el código se publica bajo licencia de código abierto en un repositorio público.
- Los prompts pedagógicos se almacenan en la base de datos, editables por docentes autorizados sin intervención de desarrolladores.

### 6.2 Supuestos

- Los estudiantes tienen acceso a un dispositivo con conexión a internet mínima de 3G.
- Los docentes participan activamente en la validación pedagógica del contenido y los prompts.
- Se dispondrá de un servidor Azure con capacidad suficiente para ejecutar Ollama con un modelo local adecuado, según las especificaciones que se definan durante la compra.
- La infraestructura de Open edX puede ser extendida mediante plugins o APIs.
- Cuando el presupuesto lo permita, se desplegará un clasificador Haiku para optimizar costos enrutando peticiones simples al modelo Ollama local (en Azure) y complejas a Claude API externa.

---

## 7. Trazabilidad de Requerimientos

Matriz que relaciona cada requerimiento funcional con los casos de uso que lo implementan.

| ID RF | Nombre | CU-01 | CU-02 | CU-03 |
|---|---|:---:|:---:|:---:|
| RF-01 | Despliegue en Open edX | ✓ | ✓ | ✓ |
| RF-02 | Repositorio Abierto | | | |
| RF-03 | Integración con Motor LLM | ✓ | | ✓ |
| RF-04 | Gestión de Perfil de Estudiante | ✓ | ✓ | |
| RF-05 | Adaptación del Nivel | ✓ | | |
| RF-06 | Persistencia del Contexto | ✓ | | |
| RF-07 | Chat Conversacional | ✓ | | |
| RF-08 | Respuesta por Audio (TTS) | ✓ | | |
| RF-09 | Avatar de TutorIA | ✓ | | |
| RF-10 | Videos Explicativos | ✓ | | |
| RF-11 | Indexación RAG | ✓ | | ✓ |
| RF-12 | Organización por Módulos | ✓ | ✓ | ✓ |
| RF-13 | Alineación Curricular | ✓ | | ✓ |
| RF-14 | Diseño para Conocimiento Cero | ✓ | | |
| RF-15 | Retroalimentación Continua | ✓ | ✓ | ✓ |
| RF-16 | Tutor Proactivo Gamificado | ✓ | ✓ | |
| RF-17 | Registro de Resultados | ✓ | ✓ | |
| RF-18 | Panel Docente y Trazabilidad | | ✓ | |
| RF-19 | Panel Docente Gestión de Prompts | | ✓ | ✓ |
| RF-20 | Gestión de Asignaturas | | | ✓ |
| RF-21 | Prompts en Base de Datos | ✓ | ✓ | |
| RF-22 | Pasarela MongoDB → PostgreSQL | | | ✓ |
| RF-23 | Clasificador Inteligente | ✓ | | |
| RF-24 | Gamificación | ✓ | ✓ | |
| RF-25 | Despliegue en Azure | ✓ | ✓ | ✓ |

---

*Universidad Tecnológica de Pereira · Grupo de Investigación Sirius · Proyecto TutorIA · Julio 2026*
