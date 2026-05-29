**PROYECTO TUTORIA**

Documento de Requerimientos de Software

*Agente Autónomo basado en Grandes Modelos de Lenguaje*

*para Democratizar el Acceso a la Educación Superior en Zonas Rurales de
Colombia*

Universidad Tecnológica de Pereira --- Grupo de Investigación Sirius

Versión 1.0 \| Abril 2026

> **1. INTRODUCCIÓN**

El presente documento describe los requerimientos funcionales y no
funcionales del sistema TutorIA, un agente autónomo de inteligencia
artificial basado en Grandes Modelos de Lenguaje (LLMs) diseñado para
democratizar el acceso a la educación superior en zonas rurales de
Colombia. La plataforma se integrará al entorno Open edX y empleará
Claude (Anthropic) como motor de generación de código y base del agente
conversacional.

TutorIA actuará como tutor virtual inteligente con personalidad
pedagógica proactiva, adaptado a estudiantes con conocimiento cero en
las materias impartidas, cubriendo inicialmente Programación I (Python)
e Introducción a la Matemática, en alineación con los currículos de
pregrado y posgrado de la institución.

**1.1 Propósito**

Este documento tiene como propósito definir el alcance, los actores, los
requerimientos funcionales (RF) y no funcionales (RNF), y los casos de
uso principales del sistema TutorIA, sirviendo como referencia técnica
para los equipos de desarrollo, diseño pedagógico e investigación.

**1.2 Alcance**

TutorIA es una plataforma educativa basada en IA que provee tutoría
personalizada, evaluaciones adaptativas, retroalimentación proactiva, y
un panel docente con analíticas de aprendizaje. Su despliegue inicial
cubre dos materias universitarias, con capacidad de expansión modular a
otras asignaturas.

**1.3 Definiciones y Acrónimos**

  -----------------------------------------------------------------------
  **Término /        **Definición**
  Sigla**            
  ------------------ ----------------------------------------------------
  **TutorIA**        Agente autónomo de IA para tutoría educativa
                     personalizada

  **LLM**            Large Language Model -- Modelo de Lenguaje de Gran
                     Escala

  **Open edX**       Plataforma LMS (Learning Management System) de
                     código abierto donde se desplegará el agente

  **Claude**         Modelo de lenguaje de Anthropic utilizado como motor
                     del agente

  **RF**             Requerimiento Funcional

  **RNF**            Requerimiento No Funcional

  **TTS**            Text-to-Speech -- Síntesis de voz a partir de texto

  **RAG**            Retrieval-Augmented Generation -- Generación
                     aumentada por recuperación de contexto

  **Avatar**         Representación visual animada del tutor virtual

  **Módulo**         Unidad curricular dentro de una asignatura
  -----------------------------------------------------------------------

> **2. DESCRIPCIÓN GENERAL DEL SISTEMA**

**2.1 Contexto del Sistema**

TutorIA se desplegará dentro de Open edX, integrándose como un agente
conversacional accesible desde el LMS. El backend del agente se
construirá utilizando Claude de Anthropic para la generación de
respuestas y código, y toda la base del proyecto se publicará en un
repositorio abierto (open-source) en GitHub para garantizar
transparencia y reproducibilidad académica.

**2.2 Actores del Sistema**

  ---------------------------------------------------------------------------
  **Actor**           **Descripción**
  ------------------- -------------------------------------------------------
  **Estudiante**      Usuario principal. Interactúa con TutorIA mediante
                      texto y voz, recibe retroalimentación personalizada,
                      realiza evaluaciones y visualiza videos explicativos
                      del avatar.

  **Docente**         Accede al panel de estadísticas para monitorear el
                      progreso de los estudiantes. Puede gestionar y revisar
                      el contenido de las asignaturas.

  **Administrador**   Configura el sistema, gestiona usuarios, materias y
                      módulos curriculares dentro de Open edX.

  **TutorIA           Agente autónomo que actúa como tutor virtual: responde
  (Sistema)**         preguntas, genera retroalimentación, aplica
                      evaluaciones y adapta la experiencia al perfil del
                      estudiante.
  ---------------------------------------------------------------------------

**2.3 Asignaturas Iniciales**

En la primera fase del proyecto se implementarán dos asignaturas, cada
una organizada en módulos curriculares alineados con los planes de
estudio de pregrado y maestría:

-   Programación I (Python): Introducción al pensamiento computacional,
    variables y tipos de datos, estructuras de control, funciones,
    manejo de listas y diccionarios, programación orientada a objetos
    básica, manejo de archivos, y buenas prácticas de codificación.

-   Introducción a la Matemática: Lógica proposicional, teoría de
    conjuntos, relaciones y funciones, aritmética y álgebra básica,
    geometría analítica introductoria, y fundamentos de estadística
    descriptiva.

> **3. REQUERIMIENTOS FUNCIONALES**

La siguiente tabla describe todos los requerimientos funcionales del
sistema. Prioridad: Alta (crítico para MVP), Media (segunda iteración),
Baja (versiones futuras).

  ---------------------------------------------------------------------------------------------
  **ID**      **Nombre**        **Descripción**                 **Prioridad**   **Categoría**
  ----------- ----------------- ------------------------------- --------------- ---------------
  **RF-01**   **Despliegue en   El sistema TutorIA debe         **Alta**        Plataforma
              Open edX**        integrarse y desplegarse como                   
                                agente dentro de la plataforma                  
                                Open edX, siendo accesible                      
                                desde la interfaz del LMS para                  
                                estudiantes y docentes.                         

  **RF-02**   **Repositorio     Todo el código fuente,          **Alta**        Plataforma
              Abierto**         configuraciones y documentación                 
                                base del proyecto deben                         
                                publicarse en un repositorio de                 
                                acceso público (GitHub u otro),                 
                                permitiendo su reproducción y                   
                                colaboración académica.                         

  **RF-03**   **Integración con El agente debe utilizar la API  **Alta**        Plataforma
              Claude            de Claude de Anthropic como                     
              (Anthropic)**     motor LLM principal para la                     
                                generación de respuestas                        
                                pedagógicas, código de ejemplo                  
                                y retroalimentación adaptativa.                 

  **RF-04**   **Gestión de      El sistema debe crear y         **Alta**        Perfil
              Perfil de         mantener un perfil individual                   
              Estudiante**      por estudiante que almacene:                    
                                nivel de conocimiento actual                    
                                por asignatura, historial de                    
                                interacciones, gustos e                         
                                intereses declarados, ritmo de                  
                                aprendizaje y resultados de                     
                                evaluaciones previas.                           

  **RF-05**   **Adaptación del  TutorIA debe ajustar            **Alta**        Perfil
              Nivel de          automáticamente el nivel de                     
              Aprendizaje**     dificultad y la forma de                        
                                explicar los conceptos según el                 
                                perfil de aprendizaje del                       
                                estudiante, identificando                       
                                brechas de conocimiento y                       
                                adaptando el ritmo de avance.                   

  **RF-06**   **Persistencia    El agente debe mantener y       **Alta**        Perfil
              del Contexto**    recuperar el contexto de cada                   
                                sesión y de sesiones anteriores                 
                                para garantizar continuidad en                  
                                el proceso de aprendizaje,                      
                                evitando repetición innecesaria                 
                                y personalizando el saludo y                    
                                referencias al estudiante.                      

  **RF-07**   **Chat            Los estudiantes deben poder     **Alta**        Interacción
              Conversacional    interactuar con TutorIA                         
              con el            mediante texto libre en                         
              Estudiante**      lenguaje natural. El agente                     
                                debe responder en lenguaje                      
                                claro, didáctico y adaptado al                  
                                nivel del estudiante.                           

  **RF-08**   **Respuesta por   TutorIA debe poder responder al **Alta**        Interacción
              Audio (TTS)**     estudiante en audio mediante                    
                                síntesis de voz                                 
                                (Text-to-Speech), permitiendo                   
                                al estudiante escuchar las                      
                                explicaciones sin necesidad de                  
                                leer, útil en contextos de baja                 
                                conectividad o necesidades                      
                                especiales.                                     

  **RF-09**   **Avatar de       El sistema debe presentar un    **Alta**        Interacción
              TutorIA**         avatar visual animado que                       
                                represente a TutorIA durante                    
                                las interacciones y en los                      
                                videos explicativos,                            
                                humanizando la experiencia de                   
                                tutoría.                                        

  **RF-10**   **Videos          TutorIA debe contar con videos  **Alta**        Interacción
              Explicativos con  pregrabados o generados                         
              Avatar**          dinámicamente en los que el                     
                                avatar explique los temas de                    
                                las asignaturas, alineados con                  
                                los módulos curriculares de                     
                                cada materia.                                   

  **RF-11**   **Entrenamiento   El sistema debe ser entrenado y **Alta**        Contenido
              con Contenido     configurado exclusivamente con                  
              Solo-Texto**      materiales en formato texto                     
                                (sin imágenes, audio ni video                   
                                como fuente de entrenamiento),                  
                                garantizando la calidad y                       
                                claridad del corpus pedagógico.                 

  **RF-12**   **Organización    Cada asignatura debe estar      **Alta**        Contenido
              por Módulos       organizada en módulos que sigan                 
              Curriculares**    el plan educativo oficial de la                 
                                materia, tanto para programas                   
                                de pregrado como de maestría,                   
                                definidos por los docentes.                     

  **RF-13**   **Alineación      Los materiales de las           **Alta**        Contenido
              Curricular**      asignaturas y las respuestas de                 
                                TutorIA deben estar alineados                   
                                con el currículo oficial de la                  
                                universidad y de la maestría                    
                                para las materias impartidas.                   

  **RF-14**   **Diseño para     TutorIA debe estar diseñado     **Alta**        Contenido
              Conocimiento      para estudiantes sin                            
              Cero**            conocimiento previo de las                      
                                materias impartidas, empleando                  
                                analogías, ejemplos cotidianos                  
                                y un lenguaje accesible y                       
                                progresivo.                                     

  **RF-15**   **Evaluaciones    El sistema debe generar y       **Alta**        Evaluación
              Formativas        aplicar evaluaciones cortas                     
              Pequeñas**        (quizzes, ejercicios de código,                 
                                problemas matemáticos) al                       
                                término de cada módulo o tema,                  
                                adaptadas al nivel del                          
                                estudiante, con                                 
                                retroalimentación inmediata.                    

  **RF-16**   **Tutor Proactivo TutorIA debe tener              **Alta**        Evaluación
              e Incentivador**  comportamiento proactivo:                       
                                motivar al estudiante a                         
                                continuar estudiando, sugerir                   
                                temas a repasar, felicitar                      
                                logros, identificar momentos de                 
                                desánimo y ofrecer estrategias                  
                                de estudio personalizadas.                      

  **RF-17**   **Registro de     Los resultados de cada          **Alta**        Evaluación
              Resultados de     evaluación deben quedar                         
              Evaluación**      registrados en el perfil del                    
                                estudiante y ser accesibles                     
                                tanto para el estudiante como                   
                                para el docente en el panel de                  
                                estadísticas.                                   

  **RF-18**   **Panel Docente   Los docentes deben tener acceso **Alta**        Docente
              -- Estadísticas** a un panel donde puedan                         
                                visualizar: progreso individual                 
                                y grupal de los estudiantes,                    
                                resultados de evaluaciones,                     
                                tiempo de uso por módulo, temas                 
                                con mayor dificultad y alertas                  
                                de estudiantes en riesgo de                     
                                deserción.                                      

  **RF-19**   **Panel Docente   Los docentes deben poder        **Media**       Docente
              -- Gestión de     revisar, actualizar y aprobar                   
              Contenido**       el contenido de las asignaturas                 
                                dentro de la plataforma,                        
                                garantizando que el material                    
                                esté alineado con el currículo                  
                                vigente.                                        

  **RF-20**   **Gestión de      El sistema debe permitir crear, **Alta**        Admin
              Asignaturas y     editar, activar y desactivar                    
              Módulos**         asignaturas y módulos                           
                                curriculares desde una interfaz                 
                                administrativa, comenzando con                  
                                Programación I (Python) e                       
                                Introducción a la Matemática.                   
  ---------------------------------------------------------------------------------------------

> **4. REQUERIMIENTOS NO FUNCIONALES**

  -------------------------------------------------------------------------------------------
  **ID**       **Categoría**        **Descripción**                      **Criterio de
                                                                         Aceptación**
  ------------ -------------------- ------------------------------------ --------------------
  **RNF-01**   **Rendimiento**      El agente debe responder a consultas *Tiempo de respuesta
                                    del estudiante en un tiempo          \< 5 segundos para
                                    razonable para no interrumpir el     texto; \< 10
                                    flujo de aprendizaje.                segundos para
                                                                         audio.*

  **RNF-02**   **Disponibilidad**   La plataforma debe estar disponible  *Disponibilidad
                                    de forma continua para soportar a    mínima del 99%
                                    estudiantes en zonas rurales con     mensual.*
                                    diferentes husos horarios y horarios 
                                    de estudio.                          

  **RNF-03**   **Escalabilidad**    El sistema debe soportar el          *Soporte para al
                                    crecimiento de usuarios, asignaturas menos 500 usuarios
                                    y módulos sin degradación del        concurrentes en fase
                                    servicio.                            inicial, con
                                                                         arquitectura
                                                                         escalable
                                                                         horizontal.*

  **RNF-04**   **Accesibilidad**    La plataforma debe ser accesible     *Compatible con
                                    desde dispositivos de bajo costo y   dispositivos con
                                    conexiones de baja velocidad,        mínimo 2GB de RAM;
                                    priorizando los entornos rurales     funcional con
                                    colombianos.                         conectividad de 3G.*

  **RNF-05**   **Seguridad y        Los datos personales, perfiles de    *Cifrado TLS para
               Privacidad**         aprendizaje e historial de           transmisión; cifrado
                                    interacciones de los estudiantes     AES-256 para
                                    deben protegerse conforme a la Ley   almacenamiento de
                                    1581 de 2012 (Habeas Data) y         datos sensibles.*
                                    estándares de cifrado.               

  **RNF-06**   **Usabilidad**       La interfaz debe ser intuitiva para  *Puntuación SUS
                                    estudiantes con escasa experiencia   (System Usability
                                    tecnológica, con navegación simple y Scale) ≥ 75 en
                                    onboarding guiado.                   pruebas con usuarios
                                                                         objetivo.*

  **RNF-07**   **Mantenibilidad**   El código fuente debe seguir         *Cobertura de
                                    principios de diseño limpio y estar  documentación ≥ 80%;
                                    documentado para facilitar           código bajo estándar
                                    contribuciones externas al           de linting
                                    repositorio abierto.                 definido.*

  **RNF-08**   **Portabilidad**     El sistema debe poder desplegarse en *Contenedorización
                                    distintos entornos (cloud,           con Docker; soporte
                                    on-premise) y ser compatible con la  para despliegue en
                                    infraestructura de universidades     AWS, GCP o
                                    colombianas.                         servidores locales.*

  **RNF-09**   **Calidad            Las respuestas del agente deben      *Evaluación
               Pedagógica**         superar revisión de calidad          pedagógica formal
                                    pedagógica por parte de docentes     con al menos 2
                                    expertos en cada materia antes de    docentes por
                                    producción.                          asignatura antes de
                                                                         lanzamiento.*

  **RNF-10**   **Idioma**           El sistema debe operar completamente *100% de la interfaz
                                    en español colombiano, con           y respuestas en
                                    posibilidad futura de soportar       español en la
                                    lenguas nativas.                     versión 1.0.*
  -------------------------------------------------------------------------------------------

> **5. CASOS DE USO**

A continuación se describen los tres casos de uso principales del
sistema TutorIA, representando los flujos de mayor valor para los
actores del sistema.

**Caso de Uso CU-01: Sesión de Tutoría Personalizada con el Estudiante**

+---------------+------------------------------------------------------+
| **CU-01 ---   |                                                      |
| Sesión de     |                                                      |
| Tutoría       |                                                      |
| Personalizada |                                                      |
| con el        |                                                      |
| Estudiante**  |                                                      |
+---------------+------------------------------------------------------+
| **            | El estudiante inicia una sesión con TutorIA para     |
| Descripción** | aprender o resolver dudas sobre un tema de su        |
|               | asignatura. El agente adapta la sesión al perfil del |
|               | estudiante, responde en texto y/o audio, usa el      |
|               | avatar y propone micro-evaluaciones al finalizar el  |
|               | tema.                                                |
+---------------+------------------------------------------------------+
| **Actores**   | Estudiante (actor principal), TutorIA (sistema)      |
+---------------+------------------------------------------------------+
| **Pre         | • El estudiante está registrado y autenticado en     |
| condiciones** | Open edX.                                            |
|               |                                                      |
|               | • El estudiante tiene al menos una asignatura activa |
|               | asignada.                                            |
|               |                                                      |
|               | • El perfil del estudiante existe en el sistema      |
|               | (nuevo o existente con historial).                   |
+---------------+------------------------------------------------------+
| **Flujo       | 1\. El estudiante accede al módulo de TutorIA desde  |
| Principal**   | Open edX.                                            |
|               |                                                      |
|               | 2\. TutorIA recupera el perfil y el historial del    |
|               | estudiante (RF-06).                                  |
|               |                                                      |
|               | 3\. TutorIA saluda al estudiante personalizadamente  |
|               | y sugiere continuar donde quedó o explorar un nuevo  |
|               | tema del módulo actual.                              |
|               |                                                      |
|               | 4\. El estudiante escribe una pregunta o selecciona  |
|               | un tema.                                             |
|               |                                                      |
|               | 5\. TutorIA analiza la pregunta con Claude           |
|               | (Anthropic), recupera contenido del módulo y genera  |
|               | una explicación adaptada al nivel del estudiante     |
|               | (RF-05).                                             |
|               |                                                      |
|               | 6\. El avatar de TutorIA presenta la respuesta en    |
|               | pantalla (texto + audio TTS si el estudiante lo      |
|               | tiene activado) (RF-08, RF-09).                      |
|               |                                                      |
|               | 7\. El estudiante hace preguntas de seguimiento; el  |
|               | agente mantiene el hilo conversacional (RF-07).      |
|               |                                                      |
|               | 8\. Al completar el tema, TutorIA propone una        |
|               | micro-evaluación (quiz o ejercicio práctico)         |
|               | (RF-15).                                             |
|               |                                                      |
|               | 9\. El estudiante realiza la evaluación y recibe     |
|               | retroalimentación inmediata.                         |
|               |                                                      |
|               | 10\. TutorIA actualiza el perfil con el avance y     |
|               | registra el resultado (RF-04, RF-17).                |
|               |                                                      |
|               | 11\. TutorIA motiva al estudiante y sugiere el       |
|               | próximo paso (RF-16).                                |
+---------------+------------------------------------------------------+
| **Flujos      | FA-01: El estudiante es nuevo (sin historial).       |
| A             | TutorIA aplica un diagnóstico inicial de nivel de    |
| lternativos** | conocimiento antes de empezar el primer módulo.      |
|               |                                                      |
|               | FA-02: El estudiante tiene una pregunta fuera del    |
|               | alcance del módulo activo. TutorIA indica            |
|               | amablemente que el tema está fuera del programa      |
|               | actual y sugiere el módulo correspondiente.          |
|               |                                                      |
|               | FA-03: El estudiante solicita escuchar la respuesta  |
|               | en audio. TutorIA activa la respuesta TTS con el     |
|               | avatar animado.                                      |
|               |                                                      |
|               | FA-04: El estudiante falla la micro-evaluación.      |
|               | TutorIA refuerza el tema con una explicación         |
|               | alternativa y ofrece un nuevo intento con preguntas  |
|               | diferentes.                                          |
+---------------+------------------------------------------------------+
| **Post        | • El perfil del estudiante queda actualizado con el  |
| condiciones** | progreso, nivel y resultados de evaluación de la     |
|               | sesión.                                              |
|               |                                                      |
|               | • El historial de la sesión queda disponible para el |
|               | docente en el panel de estadísticas.                 |
|               |                                                      |
|               | • TutorIA tiene el contexto completo para continuar  |
|               | en la próxima sesión.                                |
+---------------+------------------------------------------------------+

**Caso de Uso CU-02: Consulta del Panel de Estadísticas por el Docente**

+---------------+------------------------------------------------------+
| **CU-02 ---   |                                                      |
| Consulta del  |                                                      |
| Panel de      |                                                      |
| Estadísticas  |                                                      |
| por el        |                                                      |
| Docente**     |                                                      |
+---------------+------------------------------------------------------+
| **            | El docente accede al panel de estadísticas de        |
| Descripción** | TutorIA para monitorear el rendimiento académico de  |
|               | sus estudiantes, identificar quiénes requieren       |
|               | intervención y revisar el contenido de la            |
|               | asignatura.                                          |
+---------------+------------------------------------------------------+
| **Actores**   | Docente (actor principal), TutorIA (sistema)         |
+---------------+------------------------------------------------------+
| **Pre         | • El docente está autenticado en Open edX con rol de |
| condiciones** | docente.                                             |
|               |                                                      |
|               | • El docente tiene al menos una asignatura asignada  |
|               | con estudiantes activos.                             |
|               |                                                      |
|               | • Existen datos de sesiones de TutorIA registrados   |
|               | en el sistema.                                       |
+---------------+------------------------------------------------------+
| **Flujo       | 1\. El docente accede al módulo de Panel Docente     |
| Principal**   | desde Open edX.                                      |
|               |                                                      |
|               | 2\. El sistema muestra el resumen general de la      |
|               | asignatura: número de estudiantes activos, progreso  |
|               | promedio por módulo, tasa de aprobación de           |
|               | evaluaciones.                                        |
|               |                                                      |
|               | 3\. El docente selecciona un estudiante específico   |
|               | para ver su perfil detallado.                        |
|               |                                                      |
|               | 4\. El sistema presenta: módulos completados, tiempo |
|               | de sesión, resultados de evaluaciones, temas con     |
|               | mayor dificultad y frecuencia de interacción con     |
|               | TutorIA.                                             |
|               |                                                      |
|               | 5\. El docente visualiza las alertas automáticas del |
|               | sistema para estudiantes con bajo rendimiento o      |
|               | inactividad prolongada (RF-18).                      |
|               |                                                      |
|               | 6\. El docente accede a la sección de contenido de   |
|               | la asignatura para revisar los materiales activos de |
|               | cada módulo (RF-19).                                 |
|               |                                                      |
|               | 7\. El docente puede proponer ajustes al contenido   |
|               | de un módulo mediante el formulario de sugerencias.  |
|               |                                                      |
|               | 8\. El sistema registra la revisión y actualiza el   |
|               | estado del contenido.                                |
+---------------+------------------------------------------------------+
| **Flujos      | FA-01: No hay datos suficientes para estadísticas.   |
| A             | El sistema muestra un mensaje indicando que se       |
| lternativos** | necesitan más sesiones registradas y sugiere un      |
|               | período de espera.                                   |
|               |                                                      |
|               | FA-02: El docente quiere exportar el reporte. El     |
|               | sistema genera un archivo descargable (PDF/Excel)    |
|               | con las estadísticas del grupo o del estudiante      |
|               | seleccionado.                                        |
|               |                                                      |
|               | FA-03: El docente detecta un error en el contenido   |
|               | de un módulo. Puede marcarlo para revisión y el      |
|               | sistema notifica al administrador.                   |
+---------------+------------------------------------------------------+
| **Post        | • El docente tiene visibilidad completa del estado   |
| condiciones** | académico de sus estudiantes.                        |
|               |                                                      |
|               | • Las sugerencias de contenido quedan registradas    |
|               | para revisión por el equipo académico.               |
|               |                                                      |
|               | • El acceso al panel queda auditado para garantizar  |
|               | privacidad de datos estudiantiles.                   |
+---------------+------------------------------------------------------+

**Caso de Uso CU-03: Creación y Configuración de un Módulo Curricular**

+---------------+------------------------------------------------------+
| **CU-03 ---   |                                                      |
| Creación y    |                                                      |
| Configuración |                                                      |
| de un Módulo  |                                                      |
| Curricular**  |                                                      |
+---------------+------------------------------------------------------+
| **            | El administrador, en colaboración con el docente,    |
| Descripción** | crea un nuevo módulo dentro de una asignatura        |
|               | existente, cargando el contenido textual, definiendo |
|               | los objetivos de aprendizaje, configurando la        |
|               | evaluación formativa y activando el módulo para los  |
|               | estudiantes.                                         |
+---------------+------------------------------------------------------+
| **Actores**   | Administrador (actor principal), Docente (actor      |
|               | secundario), TutorIA (sistema)                       |
+---------------+------------------------------------------------------+
| **Pre         | • El administrador está autenticado en el sistema    |
| condiciones** | con permisos de administración.                      |
|               |                                                      |
|               | • La asignatura en la cual se creará el módulo ya    |
|               | existe (Programación I o Introducción a la           |
|               | Matemática).                                         |
|               |                                                      |
|               | • El contenido textual del módulo ha sido            |
|               | previamente revisado y aprobado por el docente       |
|               | responsable.                                         |
+---------------+------------------------------------------------------+
| **Flujo       | 1\. El administrador accede al panel de              |
| Principal**   | administración de contenidos dentro de Open edX.     |
|               |                                                      |
|               | 2\. Selecciona la asignatura destino y hace clic en  |
|               | \'Crear nuevo módulo\'.                              |
|               |                                                      |
|               | 3\. Ingresa el nombre del módulo, número de orden    |
|               | dentro de la asignatura y descripción general.       |
|               |                                                      |
|               | 4\. Carga el contenido textual del módulo (solo      |
|               | texto, sin imágenes ni archivos multimedia) en el    |
|               | editor de contenido (RF-11).                         |
|               |                                                      |
|               | 5\. Define los objetivos de aprendizaje del módulo,  |
|               | alineados con el currículo oficial (RF-12, RF-13).   |
|               |                                                      |
|               | 6\. Configura el banco de preguntas de la evaluación |
|               | formativa: tipo, número de preguntas, criterios de   |
|               | aprobación y retroalimentación automática (RF-15).   |
|               |                                                      |
|               | 7\. Asigna el módulo al nivel de conocimiento        |
|               | correspondiente (básico, intermedio) para que        |
|               | TutorIA pueda adaptar su uso al perfil del           |
|               | estudiante (RF-05).                                  |
|               |                                                      |
|               | 8\. El docente responsable revisa el módulo en modo  |
|               | previsualización y lo aprueba (RF-19).               |
|               |                                                      |
|               | 9\. El administrador activa el módulo para que esté  |
|               | disponible a los estudiantes inscritos.              |
|               |                                                      |
|               | 10\. TutorIA indexa el contenido del módulo e        |
|               | integra el material en su base de conocimiento para  |
|               | su uso en sesiones (RF-03).                          |
+---------------+------------------------------------------------------+
| **Flujos      | FA-01: El docente rechaza el módulo en la revisión.  |
| A             | El sistema regresa el módulo a estado \'borrador\'   |
| lternativos** | con los comentarios del docente para corrección por  |
|               | parte del administrador.                             |
|               |                                                      |
|               | FA-02: El contenido cargado excede el límite de      |
|               | texto permitido. El sistema notifica el error e      |
|               | indica al administrador que debe dividir el          |
|               | contenido en submódulos.                             |
|               |                                                      |
|               | FA-03: El administrador desea desactivar             |
|               | temporalmente un módulo ya activo. El sistema lo     |
|               | marca como inactivo sin eliminar el historial de     |
|               | estudiantes que ya lo completaron.                   |
+---------------+------------------------------------------------------+
| **Post        | • El módulo queda activo dentro de la asignatura y   |
| condiciones** | disponible para los estudiantes inscritos.           |
|               |                                                      |
|               | • TutorIA puede usar el contenido del módulo en      |
|               | sesiones de tutoría y evaluaciones.                  |
|               |                                                      |
|               | • El docente puede visualizar el módulo activo en su |
|               | panel de gestión de contenido.                       |
|               |                                                      |
|               | • Queda un registro de quién creó, revisó y aprobó   |
|               | el módulo, con fecha y versión.                      |
+---------------+------------------------------------------------------+

> **6. RESTRICCIONES Y SUPUESTOS**

**6.1 Restricciones**

-   El entrenamiento del agente se realiza exclusivamente con contenido
    en formato texto; no se utilizan imágenes, audio ni video como
    fuente de datos de entrenamiento.

-   La plataforma se integrará en Open edX como LMS base; no se
    contempla un LMS diferente en la fase inicial.

-   Se emplea Claude (Anthropic) como motor LLM principal; no se
    consideran otros proveedores de LLM en la versión 1.0.

-   Las asignaturas disponibles en la versión 1.0 son únicamente
    Programación I (Python) e Introducción a la Matemática.

-   El contenido de las asignaturas debe estar alineado con el currículo
    oficial de la Universidad Tecnológica de Pereira y de su programa de
    maestría.

-   Toda la base de código se publicará bajo licencia de código abierto
    en un repositorio público.

**6.2 Supuestos**

-   Los estudiantes tienen acceso a un dispositivo con conexión a
    internet mínima de 3G para usar la plataforma.

-   Los docentes participan activamente en la validación pedagógica del
    contenido de cada módulo antes de su activación.

-   La API de Claude (Anthropic) estará disponible con los niveles de
    servicio requeridos para el volumen de usuarios esperado.

-   La infraestructura de Open edX puede ser extendida mediante plugins
    o APIs para integrar el agente TutorIA.

> **7. TRAZABILIDAD DE REQUERIMIENTOS**

La siguiente matriz relaciona cada requerimiento funcional con los casos
de uso que lo implementan, garantizando cobertura completa.

  --------------------------------------------------------------------------
  **ID RF**   **Nombre**               **CU-01**    **CU-02**    **CU-03**
  ----------- ------------------------ ------------ ------------ -----------
  **RF-01**   Despliegue en Open edX   **✓**        **✓**        **✓**

  **RF-02**   Repositorio Abierto                                **✓**

  **RF-03**   Integración con Claude   **✓**                     **✓**

  **RF-04**   Gestión de Perfil de     **✓**                     
              Estudiante                                         

  **RF-05**   Adaptación del Nivel     **✓**                     **✓**

  **RF-06**   Persistencia del         **✓**                     
              Contexto                                           

  **RF-07**   Chat Conversacional      **✓**                     

  **RF-08**   Respuesta por Audio      **✓**                     
              (TTS)                                              

  **RF-09**   Avatar de TutorIA        **✓**                     

  **RF-10**   Videos Explicativos      **✓**                     

  **RF-11**   Entrenamiento Solo-Texto                           **✓**

  **RF-12**   Organización por Módulos **✓**                     **✓**

  **RF-13**   Alineación Curricular    **✓**                     **✓**

  **RF-14**   Diseño para Conocimiento **✓**                     
              Cero                                               

  **RF-15**   Evaluaciones Formativas  **✓**                     **✓**

  **RF-16**   Tutor Proactivo          **✓**                     

  **RF-17**   Registro de Resultados   **✓**        **✓**        

  **RF-18**   Panel Docente --                      **✓**        
              Estadísticas                                       

  **RF-19**   Panel Docente --                      **✓**        **✓**
              Contenido                                          

  **RF-20**   Gestión de                                         **✓**
              Asignaturas/Módulos                                
  --------------------------------------------------------------------------

*Universidad Tecnológica de Pereira \| Grupo de Investigación Sirius \|
Proyecto TutorIA \| v1.0 --- Abril 2026*
