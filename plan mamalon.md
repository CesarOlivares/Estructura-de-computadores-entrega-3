# CLAUDE.md — Contexto permanente del proyecto

> Este archivo es la memoria del proyecto. Léelo completo al inicio de cada sesión
> antes de responder nada. Si algo de lo que te piden contradice este archivo,
> dilo explícitamente antes de actuar.

---

## 1. Qué es esto

Proyecto de la **Evaluación 3** del curso *Estructura de Computadores y Sistemas
Distribuidos* (ECSD 2026-1), Ingeniería Civil Mecatrónica, USACH.

- **Grupo 2 → Caso 2:** Línea de Producción con Balanceo Dinámico
- **Integrantes:** 2 personas (el enunciado pide 3–4; pendiente de confirmar con el profesor)
- **Entrega:** lunes 24/08/2026, 11:30 hrs
- **Entregables:** informe PDF (≤15 pág + 15 anexos), slides PDF (15 min), .zip con
  el código fuente, y demo funcional en vivo
- **Profesor:** Daniel Calderón R.

### Ponderación de la nota

| Componente | Peso |
|---|---|
| Desarrollo | 35 % |
| Código | 25 % |
| Presentación | 20 % |
| Informe | 20 % |

---

## 2. Requisitos EXPLÍCITOS del enunciado

Estos son textuales. No los negocies.

### Generales (todos los casos)

- Arquitectura distribuida con **al menos 3 servicios/procesos**
- Ejecución en **al menos 2 nodos lógicos**
- **UI obligatoria**: Streamlit (recomendado) u otra web equivalente. Debe consumir al
  menos un servicio remoto y permitir **interacción real**, no solo visualización
- **Persistencia obligatoria**: BD (MySQL/SQLite) o archivos estructurados
  (JSON/CSV) solo si está justificado
- Un comando o procedimiento estándar para levantar todo (idealmente `docker compose up`)
- **README** con instalación, configuración y ejecución
- Manejo básico de errores: validación de entradas, respuestas HTTP adecuadas,
  mensajes claros en la UI
- **NO se requiere tolerancia a fallos** (sin reintentos, sin circuit breaker)
- Todo supuesto debe quedar documentado en el informe y explicado en el demo

### Específicos del Caso 2

- Al menos una estación replicada en **2+ instancias detrás de un balanceador**
- Coordinar el reparto de órdenes **evitando condiciones de carrera**
- Detectar cuellos de botella **en vivo**
- **Servicio de Órdenes**: crea y encola órdenes de producción
- **Servicio de Estación**: procesa con tiempos configurables; clasifica estado
  **normal / advertencia / crítico**
- **Servicio de Configuración de Carga**: usa un lock/contador distribuido
  (*por ejemplo* Redis) para que dos réplicas no tomen la misma orden
- **Servicio de Métricas**: calcula **lead time** y detecta cuello de botella **por estación**
- **UI**: timeline de producción, indicador de carga por réplica, alerta visual de
  cuello de botella
- **Distribución sugerida**: Órdenes + Balanceador / Estación de réplicas /
  Coordinación de carga + Métricas

### Tecnologías permitidas

Python (FastAPI/Flask, Streamlit, requests/httpx) · Java (Spring Boot) ·
REST/HTTP + JSON recomendado · Docker/Compose, VMs o hardware real ·
MySQL / SQLite / archivos. Cualquier otra cosa requiere consultar al profesor.

---

## 3. Exigencias de la RÚBRICA que el enunciado NO menciona

Fáciles de perder. Tenerlas presentes desde el principio.

- **Repositorio Git** — 30 pts del componente Código. Commits repartidos en el tiempo,
  ambos integrantes commiteando.
- **Justificar por qué mantener 2+ nodos** y **explicar cómo se abordaría la
  resiliencia** — 30 pts. El enunciado dice que la tolerancia a fallos no se exige;
  la rúbrica exige *explicarla*.
- **Histórico de estadísticas en la UI**, además del tiempo real.
- **Levantar sin pasos manuales ni instalaciones adicionales.**
- **Comentarios en el código** — 15 pts.
- **Análisis crítico de las dificultades de programación** — 15 pts.
- **Bonus de 40 pts por Kafka**, topado a 100. Ver §6.

---

## 4. Decisiones YA TOMADAS (cerradas — no reabrir sin avisar)

### Dominio

Planta conservera de **jurel en lata (425 g)**. Escenario **ficticio** inspirado en la
industria conservera nacional. No se afirman datos de ninguna empresa real.

### Línea de producción — 4 etapas en serie

```
cola → FILETEADO → cola → ENVASADO → cola → SELLADO → cola → ESTERILIZACIÓN → listos
         ×1                ×2–3              ×1                 ×1
```

| Etapa | Naturaleza | Tiempo de ciclo | Réplicas |
|---|---|---|---|
| Fileteado | Manual, paralelizable | 4 s | 1 |
| **Envasado** | Máquina continua | **12 s** | **2–3 (la replicada)** |
| Sellado | Máquina rápida | 3 s | 1 |
| Esterilización | Por lotes, ciclo fijo | 7 s | 1 |

**El experimento estrella:** al escalar envasado de 1 a 2 réplicas su tiempo efectivo
baja de 12 s a 6 s, y el cuello de botella **se desplaza** a esterilización (7 s).
Eso demuestra literalmente la frase del enunciado. Agregar una tercera réplica
casi no mejora el lead time, porque el límite ya se mudó.

### Stack

- **Servicios**: Python + FastAPI
- **UI**: Streamlit
- **Coordinación**: Redis (operación atómica de cola)
- **Persistencia**: SQLite
- **Despliegue**: Docker Compose

### Arquitectura — 3 nodos lógicos

```
NODO A                  NODO B                  NODO C
Streamlit               fileteado               Redis
orders-api              envasado ×2–3           metrics-api
                        sellado                 SQLite
                        esterilizacion
```

**Justificación (va al informe):** cada nodo agrupa responsabilidades que cambian de
escala por motivos distintos. B es el único que se replica bajo carga; C concentra el
estado compartido, que por ser compartido no puede duplicarse sin coordinación; A
expone el sistema al operador.

### Las 4 estaciones son UN SOLO servicio

Misma imagen, mismo código, desplegado 4 veces con variables de entorno distintas:

```
NOMBRE_ETAPA=envasado
COLA_ENTRADA=cola:envasado
COLA_SALIDA=cola:sellado
TIEMPO_CICLO=12
```

No escribir cuatro workers distintos.

### Balanceo: cola *pull*, no balanceador clásico

Las réplicas **piden** trabajo cuando quedan libres, en vez de recibirlo asignado.

- Es lo único que produce balanceo **dinámico** real: un round-robin le seguiría
  mandando trabajo a la réplica lenta.
- Resuelve la condición de carrera con el mismo mecanismo, sin pieza extra.
- Una extracción atómica de cola es mucho más difícil de romper que un lock con
  expiración.

> ⚠️ **El enunciado nombra un "balanceador"**. Esta decisión se aparta de la letra y
> **debe defenderse explícitamente en el informe**, argumentando que el reparto por
> demanda *es* el mecanismo de balanceo. Alternativa conservadora si el profesor
> objeta: un Nginx delante de las réplicas solo para las consultas de estado.

### Cuello de botella: se mide por TIEMPO DE ESPERA, no por tiempo de servicio

Un tiempo de servicio alto significa que la tarea es larga, no que haya atasco.
El atasco aparece cuando el **tiempo de espera crece de forma sostenida**.
Este es el argumento técnico más fuerte del proyecto.

```
Tiempo de espera   = t_inicio - t_creada
Tiempo de servicio = t_fin    - t_inicio
Lead time          = t_fin    - t_creada
```

---

## 5. SUPUESTOS declarados

Deben aparecer como tales en el informe. Nunca presentarlos como parte del enunciado.

1. Los tiempos de ciclo (4 / 12 / 3 / 7 s) son inventados y elegidos para que el
   experimento sea demostrable. No representan una planta real.
2. "Procesar un lote" se simula esperando el tiempo de ciclo. No hay trabajo real.
3. Un lote representa una cantidad de latas del mismo formato; no se modelan latas
   individuales.
4. El enunciado no dice qué entidades persistir. Se decidió: órdenes, eventos e
   historial de métricas.
5. El enunciado no define el criterio de cuello de botella ni sus umbrales.

---

## 6. Decisiones ABIERTAS — no resolver antes de la Fase 2

**No las cierres por tu cuenta ni las improvises mientras programas.** Se deciden con
el usuario, en la fase que corresponde, cuando ya tenga criterio propio.

| # | Decisión | Se decide en |
|---|---|---|
| 1 | Criterio exacto de cuello de botella (¿largo de cola? ¿espera promedio? ¿utilización?) | Fase 2 |
| 2 | Umbrales normal / advertencia / crítico y ventana de observación | Fase 10 |
| 3 | Contratos concretos de las APIs | Fase 2 |
| 4 | Esquema de datos: entidades, campos, relaciones | Fase 2 |
| 5 | Broker de mensajería (bonus Kafka) | Fase 16, **solo** si la Fase 13 está cerrada |

**Sobre el bonus de Kafka:** el total de Desarrollo está topado en 100 y los criterios
base ya suman 100, así que el bonus es un colchón, no un extra. Con 2 personas y poco
tiempo, la recomendación es **no ir por él** salvo que el núcleo esté completamente
terminado. No lo propongas antes.

---

## 7. CÓMO TRABAJAR CON EL USUARIO

Esta sección es tan importante como la especificación técnica. Respétala.

### Nivel de partida

Conocimiento práctico **muy limitado** en Docker, Docker Compose, Redis, FastAPI,
Streamlit, sistemas distribuidos, APIs REST, concurrencia y Git.
**No asumas que sabe hacer algo solo porque es un requisito del proyecto.**

Aprende **haciendo**, no leyendo teoría. Regla:

> teoría mínima necesaria → implementación → experimento → reflexión

### Estructura obligatoria de cada etapa

```
## ETAPA X — nombre
### Objetivo             (en lenguaje simple)
### Conceptos mínimos    (solo lo necesario para ESTA etapa)
### Qué vamos a construir (archivos y rutas exactas)
### Paso a paso          (dónde ejecutar, qué debería salir, qué significa, qué hacer si falla)
### Prueba               (algo concreto que ejecutar)
### Resultado esperado   (exactamente qué debe observar)
### Criterio de aprobación (checklist objetivo)
### Si falla             (diagnóstico, no reescritura)
### Commit               (nombre, mensaje, archivos, qué demuestra)
### CHECKPOINT           (preguntar si funcionó y ESPERAR)
```

### Reglas duras

- **NO avances a la siguiente etapa sin confirmación explícita del usuario.**
  Si dice "funcionó", sigues. Si dice "no funciona", entras en modo debugging.
- **NO entregues varias etapas de una vez.** Una por mensaje.
- **Sé exigente.** Si una etapa no está verificada, no lo dejes avanzar solo para
  mantener el ritmo. Él lo pidió explícitamente.
- **NO agregues funcionalidades opcionales antes de terminar el núcleo.**
- Cuando haya varias alternativas: **una recomendación**, 2–5 razones, alternativas
  descartadas importantes, y la consecuencia de la decisión. No listas enormes.
- Distingue siempre entre requisito del enunciado, decisión tuya y supuesto.
  **Nunca presentes una decisión propia como si fuera del enunciado.**

### Modo debugging

Cuando algo falle, **no reemplaces el código completo**. Sigue este orden:

1. Síntoma — ¿qué se observó?
2. Esperado — ¿qué debería haber pasado?
3. Hipótesis — ¿causas posibles?
4. Prueba mínima — ¿qué ejecutamos para distinguirlas?
5. Corrección — el cambio mínimo necesario
6. Verificación
7. Commit si quedó resuelto

### Sobre el código

- Nada de abstracciones innecesarias ni patrones de diseño de adorno
- No introducir dependencias sin explicar por qué
- Nombres claros, código fácil de leer y de **defender oralmente**
- Si hay una solución sofisticada y una simple, enseña primero la simple
- **Comentarios en el código** (la rúbrica los evalúa)

### Informe y defensa

- Cuando una decisión sea importante, di: **"Esto debería documentarse en el informe."**
- Al cerrar cada bloque grande, entrega una sección **"Preguntas que podrían hacerme"**
  con 3–5 preguntas y respuestas conectadas con lo que se acaba de implementar.
- Avisa cuando sea **"un buen momento para hacer commit"**.

### Definición de "terminado"

Funciona · fue probado · lo puede explicar · tiene manejo básico de errores ·
está integrado · hay evidencia de verificación · hay un commit apropiado.

---

## 8. Roadmap

| Fase | Qué se logra | Checkpoint verificable |
|---|---|---|
| **0** | Entorno y repo | `docker run hello-world` corre; repo en GitHub |
| **1** | Mini-demo desechable: cola + workers compitiendo | Se ven órdenes repartiéndose entre 3 workers |
| **2** | Diseño en papel: contratos API + esquema de datos | Documento revisado por los dos integrantes |
| **3** | `orders-api` mínima en Docker | `POST /ordenes` → 201 con id; 422 con datos inválidos |
| **4** | Redis y la cola | La orden creada aparece en la cola |
| **5** | Una estación consume | 5 órdenes creadas se procesan en orden |
| **6** | **Condición de carrera: provocarla y resolverla** | Versión ingenua: ≥1 duplicado. Atómica: 0 en 200 órdenes |
| **7** | Balanceo dinámico con N réplicas | Réplica lenta procesa menos; números en tabla |
| **8** | Persistencia | Se baja todo, se levanta, las órdenes siguen ahí |
| **9** | Métricas | `GET /metricas` devuelve espera, servicio y lead time |
| **10** | Cuello de botella + estados | Se satura la línea y el estado pasa a crítico solo |
| **11** | UI Streamlit con la lata avanzando por las 4 etapas | Se crean órdenes y se ve el timeline moverse |
| **12** | Errores, logging, healthchecks | Se mata Redis: la UI explica, no revienta |
| **13** | Reproducibilidad | Clonar en carpeta vacía + `docker compose up` funciona |
| **14** | Experimentos 1/2/3 réplicas + réplica lenta + saturación | 5 experimentos con hipótesis, datos y conclusión |
| **15** | Informe y defensa | Informe completo y ensayo cronometrado |
| **16** | *Opcional:* broker | Solo si 13 está cerrado |

**Dependencias duras:** 0→1→2→3→4→5→6→7. Después 8, 9, 10 y 11 se pueden paralelizar
entre los dos integrantes. Luego 12→13→14→15 en orden.

**Si el tiempo aprieta, cortar en este orden:** 16 → reducir 14 a 3 experimentos →
pulido de 11. **Nunca cortar la 6 ni la 13.**

---

## 9. Convención de commits

Formato: `tipo: descripción en imperativo` (inglés, minúscula, sin punto final).
Tipos: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`.

Reglas: un commit = una fase verificada o una corrección puntual. Nada de commits
"avance" o "final". Ambos integrantes deben commitear. Repartir a lo largo de la
semana, no todo el último día.

Historial objetivo:

```
chore: initialize repository
demo: throwaway queue prototype
docs: define api contracts and data model
feat: minimal orders api with validation
feat: add redis queue and healthcheck
feat: station worker consuming orders
feat: reproduce race condition with naive claiming
feat: implement atomic order claiming
test: verify no duplicate processing under load
feat: scale stations and expose replica identity
feat: dynamic load balancing with configurable times
feat: persist orders and events in sqlite
feat: metrics service with lead time breakdown
feat: bottleneck detection with sliding window
feat: streamlit operations dashboard
feat: error handling and http status codes
feat: structured logging with replica id
docs: readme with setup and run instructions
docs: experiment results for 1, 2 and 3 replicas
docs: architecture decisions and assumptions
```

El par `reproduce race condition` → `implement atomic claiming` demuestra por sí solo
que se entendió el problema antes de resolverlo. **Commitear la versión rota antes de
arreglarla.**

---

## 10. Estado actual

**FASE 0 — EN CURSO. Nada verificado todavía.**

- [ ] Docker Desktop instalado y funcionando en Windows
- [ ] `docker run hello-world` responde
- [ ] `docker compose version` responde v2 o superior
- [ ] Git instalado y configurado
- [ ] Repositorio creado en GitHub, con el compañero como colaborador
- [ ] Clonado local
- [ ] `.gitignore` y `README.md` commiteados y pusheados

**Entorno del usuario:** Windows. El usuario debe hacer manualmente lo que requiere
interfaz gráfica (instaladores, BIOS, GitHub web). Todo lo demás lo puedes ejecutar tú
en la terminal.

**Siguiente acción concreta:** diagnóstico del entorno — versión de Windows, estado de
WSL2, y si Docker y Git ya están instalados. Después, la ruta de instalación que
corresponda.

---

## 11. Pendientes administrativos

Correo al profesor con tres preguntas, aún sin enviar:

1. ¿Al Grupo 2 le corresponde el Caso 2?
2. ¿Está autorizado trabajar como grupo de 2, dado que el enunciado pide 3 a 4?
3. Confirmación por escrito de lo conversado en clase.

Recordárselo al usuario si no lo ha hecho: si el grupo debe fusionarse, conviene
saberlo temprano y no a mitad de semana.
