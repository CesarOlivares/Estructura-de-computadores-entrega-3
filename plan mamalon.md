# Plan de trabajo — Contexto permanente del proyecto

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

Cada fase tiene una **prueba concreta**. Mientras la prueba no pase, esa fase no está
terminada y no se avanza a la siguiente. No sirve "creo que ya funciona": tiene que
haber un comando que ejecutar y un resultado que mirar.

### Resumen

| Fase | Qué se logra | Prueba para avanzar | Est. |
|---|---|---|---|
| **0** ✅ | Entorno y repo | `docker run hello-world` corre; repo en GitHub | — |
| **1** ✅ | Mini-demo desechable: cola + workers | Órdenes repartidas entre 3 workers, cero duplicados | — |
| **2** | Diseño en papel: contratos API + esquema de datos | Los dos integrantes responden el cuestionario sin mirar código | 2 h |
| **3** | `orders-api` mínima en Docker | `POST /ordenes` → 201 con id; datos inválidos → 422 | 3 h |
| **4** | Redis y la cola | La orden creada aparece en `cola:fileteado` | 1.5 h |
| **5** | Una estación consume | 5 órdenes se procesan en orden y pasan a la cola siguiente | 2 h |
| **6** | **Condición de carrera: provocarla y resolverla** | Ingenua: ≥1 duplicado. Atómica: 0 en 200 órdenes | 3 h |
| **7** | Balanceo dinámico con N réplicas | La réplica lenta procesa menos; números en tabla | 2 h |
| **8** | Persistencia | Se baja todo, se levanta, las órdenes siguen ahí | 3 h |
| **9** | Métricas | `GET /metricas` devuelve espera, servicio y lead time | 3 h |
| **10** | Cuello de botella + estados | Se satura la línea y el estado pasa a crítico solo | 3 h |
| **11** | UI Streamlit con la lata avanzando | Se crea una orden y se ve el timeline moverse | 5 h |
| **12** | Errores, logging, healthchecks | Se mata Redis: la UI explica, no revienta | 2 h |
| **13** | Reproducibilidad | Clonar en carpeta vacía + `docker compose up` funciona | 2 h |
| **14** | Experimentos | 5 experimentos con hipótesis, datos y conclusión | 3 h |
| **15** | Informe y defensa | Informe completo y ensayo cronometrado bajo 15 min | 6 h |
| **16** | *Opcional:* broker Kafka | Solo si la 13 está cerrada | — |

**Dependencias duras:** 0→1→2→3→4→5→6→7 en ese orden, sin saltarse ninguna.
Después **8, 9, 10 y 11 se pueden repartir entre los dos integrantes** en paralelo.
Luego 12→13→14→15 en orden.

**Si el tiempo aprieta, cortar en este orden:** 16 → reducir la 14 a 3 experimentos →
pulido de la 11. **Nunca cortar la 6 ni la 13.** La 6 es el corazón técnico del caso
y la 13 es lo que hace que el proyecto se pueda evaluar.

---

### Fase 0 — Entorno y repo ✅ COMPLETA

**Qué hay que hacer**
- Habilitar la virtualización en la BIOS (en AMD se llama `SVM Mode`).
- Instalar WSL2 con una distribución: `wsl --install` y luego `wsl --install -d Ubuntu`.
- Instalar Docker Desktop y dejarlo en `Engine running`.
- Instalar y configurar Git.
- Crear el repositorio en GitHub, privado, e invitar al otro integrante.

**Prueba para avanzar**

```
docker run hello-world
```

Debe imprimir `Hello from Docker!`. Además `docker compose version` debe responder
v2 o superior, y el repositorio debe estar clonado con `README.md` y `.gitignore`
commiteados.

**Commit:** `chore: initialize repository`

---

### Fase 1 — Mini-demo desechable ✅ COMPLETA

**Qué hay que hacer**

Código de usar y botar, para entender el mecanismo antes de construir sobre él.

- `demo/productor.py`: encola 15 órdenes en Redis con `LPUSH`.
- `demo/trabajador.py`: saca órdenes con `BRPOP` y simula procesarlas.
- Levantar Redis en un contenedor, lanzar 3 trabajadores en 3 terminales y correr
  el productor en una cuarta.

**Prueba para avanzar**

Sumar las órdenes que reportó cada trabajador al terminar:

- El total debe ser exactamente **15**.
- **Ninguna orden puede aparecer en dos trabajadores.**

El reparto no tiene por qué ser parejo. Lo que importa es que sume y que no se repita.

**Commit:** `demo: throwaway queue prototype`

> **Observación importante para el informe:** con tres trabajadores de igual
> velocidad, el reparto sale idéntico a un round-robin. Eso es coincidencia, no
> mecanismo. La diferencia se demuestra en la Fase 7, cuando una réplica lenta
> pasa a procesar menos.

---

### Fase 2 — Diseño en papel

No se escribe código. Se decide y se escribe, para que los dos integrantes
programen contra lo mismo y no haya que rehacer.

**Qué hay que hacer**

1. **Contratos de las APIs.** Para cada endpoint: método, ruta, cuerpo de entrada,
   cuerpo de respuesta y códigos de estado.

   - `orders-api`
     - `POST /ordenes` — crea una orden. Entrada `{producto, cantidad}`.
       Responde `201` con `{id, estado, creada_en}`. Datos inválidos → `422`.
     - `GET /ordenes/{id}` — `200` con la orden, `404` si no existe.
     - `GET /ordenes` — lista, con filtro opcional por estado.
     - `GET /salud` — `200` para el healthcheck.
   - `estacion` (el mismo servicio desplegado 4 veces)
     - `GET /estado` — `{etapa, replica_id, procesadas, ocupada, en_cola}`.
     - `GET /salud`.
   - `metrics-api`
     - `GET /metricas` — por etapa: espera promedio, servicio promedio, lead time
       promedio, órdenes en cola.
     - `GET /metricas/cuello` — qué etapa es el cuello de botella y por qué.
     - `GET /metricas/historico` — serie temporal para el gráfico de la UI.

2. **Esquema de datos.** Dos tablas mínimas:

   - `ordenes(id, producto, cantidad, estado, creada_en, terminada_en)`
   - `eventos(id, orden_id, etapa, replica_id, tipo, timestamp)`
     donde `tipo` es `entra_cola`, `inicia` o `termina`.

   Todo lo demás — espera, servicio, lead time — **se calcula desde `eventos`**, no
   se guarda duplicado. Guardar el mismo dato dos veces es la forma más fácil de
   que se contradigan.

3. **Cerrar la decisión abierta #1:** criterio de cuello de botella.
   Recomendación: **tiempo de espera promedio en una ventana móvil**, no largo de
   cola ni tiempo de servicio. Ver §4.

4. Escribir todo en `docs/diseno.md`.

**Prueba para avanzar**

Los dos integrantes, **sin mirar el documento**, deben poder responder:

- ¿Qué devuelve exactamente `POST /ordenes` cuando sale bien y cuando sale mal?
- ¿Qué campos tiene un evento y en qué momentos se escribe uno?
- ¿Cómo se decide que una estación es cuello de botella?

Si alguno de los dos duda, el documento no está listo.

**Commit:** `docs: define api contracts and data model`

---

### Fase 3 — `orders-api` mínima en Docker

**Qué hay que hacer**

- `servicios/ordenes/app.py` — FastAPI con `POST /ordenes`, `GET /ordenes/{id}`,
  `GET /salud`. Todavía sin Redis y sin base de datos: la orden se guarda en memoria.
- Validación con Pydantic: `cantidad` entero mayor que 0, `producto` no vacío.
- `servicios/ordenes/Dockerfile`
- `servicios/ordenes/requirements.txt`
- `docker-compose.yml` en la raíz, con este único servicio por ahora.

**Prueba para avanzar**

Levantar y probar los dos casos, el válido y el inválido:

```
docker compose up -d
curl -X POST http://localhost:8000/ordenes -H "Content-Type: application/json" -d "{\"producto\":\"jurel-425g\",\"cantidad\":10}"
curl -X POST http://localhost:8000/ordenes -H "Content-Type: application/json" -d "{\"producto\":\"jurel-425g\",\"cantidad\":-5}"
```

- La primera debe responder **201** con un `id`.
- La segunda debe responder **422**, no 500 y no 201.

Ese 422 es la mitad del requisito de "manejo básico de errores" del enunciado.

**Commit:** `feat: minimal orders api with validation`

---

### Fase 4 — Redis y la cola

**Qué hay que hacer**

- Agregar el servicio `redis` al `docker-compose.yml`.
- Al crear una orden, `orders-api` hace `LPUSH` del id a `cola:fileteado`.
- Configurar el host de Redis por variable de entorno, nunca escrito a mano en el código.

**Prueba para avanzar**

```
curl -X POST http://localhost:8000/ordenes -H "Content-Type: application/json" -d "{\"producto\":\"jurel-425g\",\"cantidad\":10}"
docker compose exec redis redis-cli LRANGE cola:fileteado 0 -1
```

El id que devolvió la API tiene que aparecer en la lista.

**Commit:** `feat: add redis queue and healthcheck`

---

### Fase 5 — Una estación consume

**Qué hay que hacer**

- `servicios/estacion/worker.py` — un solo archivo que sirve para las cuatro etapas.
  Ciclo: `BRPOP` de `COLA_ENTRADA` → esperar `TIEMPO_CICLO` → `LPUSH` a `COLA_SALIDA`.
- Toda la configuración por variables de entorno:

  ```
  NOMBRE_ETAPA=envasado
  COLA_ENTRADA=cola:envasado
  COLA_SALIDA=cola:sellado
  TIEMPO_CICLO=12
  ```

- Agregar **solo la etapa de fileteado** al compose. Las otras tres vienen después.

**Prueba para avanzar**

Crear 5 órdenes seguidas y observar los logs:

```
docker compose logs -f fileteado
```

Las 5 se procesan **en el orden en que se crearon** y terminan apareciendo en
`cola:envasado`.

**No avanzar si** el worker consume CPU estando ocioso: eso significa que está
consultando en un ciclo en vez de bloquear con `BRPOP`.

**Commit:** `feat: station worker consuming orders`

---

### Fase 6 — Condición de carrera: provocarla y resolverla ⚠️ NO CORTAR

La fase más importante del proyecto. Se hace **en dos pasos, y se commitea la
versión rota antes de arreglarla.** Ese par de commits demuestra por sí solo que se
entendió el problema antes de resolverlo.

**Paso 1 — la versión ingenua**

- Reemplazar `BRPOP` por dos operaciones separadas: mirar la cola con `LRANGE` y
  después sacar el elemento con `LREM`.
- Entre esas dos operaciones hay una ventana en la que otra réplica puede mirar y
  ver la misma orden.
- Levantar 3 réplicas de envasado y meter 200 órdenes.
- **Commitear esta versión rota.**

**Paso 2 — la versión atómica**

- Volver a `BRPOP`, que saca el elemento en una sola operación indivisible.
- Repetir el experimento con las mismas 200 órdenes.

**Prueba para avanzar**

Un script que cuente cuántas veces se procesó cada orden:

- Versión ingenua: **al menos 1 duplicado.** Si no aparece ninguno, hay que subir la
  carga o meter una espera artificial entre `LRANGE` y `LREM` hasta que aparezca.
  Sin duplicado no hay demostración.
- Versión atómica: **exactamente 0 duplicados en 200 órdenes.**

**Commits:**

```
feat: reproduce race condition with naive claiming
feat: implement atomic order claiming
test: verify no duplicate processing under load
```

---

### Fase 7 — Balanceo dinámico con N réplicas

**Qué hay que hacer**

- Escalar envasado: `docker compose up --scale envasado=3`.
- Cada réplica debe exponer su identidad (`replica_id`) en los logs y en `GET /estado`.
- Configurar **una de las réplicas con un `TIEMPO_CICLO` mayor** que las otras.

**Prueba para avanzar**

Correr 60 órdenes y armar una tabla:

| Réplica | Tiempo de ciclo | Órdenes procesadas |
|---|---|---|
| envasado-1 | 12 s | ~24 |
| envasado-2 | 12 s | ~24 |
| envasado-3 | **24 s** | **~12** |

**La réplica lenta tiene que procesar visiblemente menos.** Esa tabla es la prueba
de que el reparto es por demanda y no un round-robin, y es el argumento central que
hay que defender en el informe.

**Commits:**

```
feat: scale stations and expose replica identity
feat: dynamic load balancing with configurable times
```

---

### Fase 8 — Persistencia

**Qué hay que hacer**

- SQLite con las tablas `ordenes` y `eventos` definidas en la Fase 2.
- `orders-api` escribe la orden al crearla.
- Cada estación escribe un evento al tomar una orden y otro al terminarla.
- Montar la base en un **volumen de Docker**, si no se pierde al bajar los contenedores.

**Prueba para avanzar**

```
docker compose down
docker compose up -d
curl http://localhost:8000/ordenes
```

Las órdenes creadas antes del `down` tienen que seguir ahí. Si desaparecen, el
volumen está mal configurado.

**Commit:** `feat: persist orders and events in sqlite`

---

### Fase 9 — Métricas

**Qué hay que hacer**

- `servicios/metricas/app.py` — lee la tabla `eventos` y calcula, por etapa:

  ```
  Tiempo de espera   = t_inicio - t_creada
  Tiempo de servicio = t_fin    - t_inicio
  Lead time          = t_fin    - t_creada
  ```

- `GET /metricas` devuelve los tres promedios por etapa más las órdenes en cola.

**Prueba para avanzar**

```
curl http://localhost:8000/metricas
```

Los números tienen que ser **coherentes con los tiempos de ciclo configurados**: el
tiempo de servicio de envasado debe rondar los 12 s, el de sellado los 3 s. Si el
servicio de sellado sale en 40 s, el cálculo está mal, no la línea.

**Commit:** `feat: metrics service with lead time breakdown`

---

### Fase 10 — Cuello de botella y estados

**Qué hay que hacer**

- Implementar el criterio decidido en la Fase 2: **tiempo de espera promedio en
  ventana móvil**, no tiempo de servicio.
- Cerrar la decisión abierta #2: los umbrales de `normal` / `advertencia` / `crítico`
  y el tamaño de la ventana.
- `GET /metricas/cuello` devuelve qué etapa está atascada y por qué.

**Prueba para avanzar**

Crear órdenes mucho más rápido de lo que la línea puede procesar:

- La etapa saturada tiene que pasar a **crítico sola**, sin tocar nada.
- Al dejar de crear órdenes, tiene que **volver a normal sola**.

**No avanzar si** la etapa marcada como cuello de botella es simplemente la de mayor
tiempo de ciclo. Eso significa que se está midiendo servicio en vez de espera, que es
justamente el error que este proyecto argumenta que no hay que cometer.

**Commit:** `feat: bottleneck detection with sliding window`

---

### Fase 11 — UI Streamlit

**Qué hay que hacer**

- Timeline de producción: cada orden avanzando por las 4 etapas.
- Indicador de carga por réplica.
- Alerta visual cuando hay cuello de botella.
- **Histórico de estadísticas**, no solo tiempo real — la rúbrica lo exige aparte.
- Un formulario para **crear órdenes desde la UI**: el enunciado pide interacción
  real, no solo visualización.

**Prueba para avanzar**

Crear una orden desde la interfaz y verla recorrer las cuatro etapas hasta terminar,
sin recargar la página a mano.

**Commit:** `feat: streamlit operations dashboard`

---

### Fase 12 — Errores, logging y healthchecks

**Qué hay que hacer**

- Códigos HTTP correctos en todos los servicios: `404` si no existe, `422` si la
  entrada es inválida, `503` si una dependencia no responde.
- Logging con `replica_id` en cada línea, para poder seguir qué réplica hizo qué.
- `healthcheck` de cada servicio en el `docker-compose.yml`.

**Prueba para avanzar**

```
docker compose stop redis
```

La UI tiene que mostrar un **mensaje claro** del tipo "no hay conexión con el
servicio de coordinación". No un traceback, no una pantalla en blanco, no colgarse.

**Commits:**

```
feat: error handling and http status codes
feat: structured logging with replica id
```

---

### Fase 13 — Reproducibilidad ⚠️ NO CORTAR

Es lo que hace que el proyecto se pueda evaluar. Si el profesor no lo puede
levantar, nada de lo anterior cuenta.

**Qué hay que hacer**

- `README.md` completo: instalación, configuración y ejecución.
- `.env.example` con todas las variables y valores por defecto que funcionen.
- Que **un solo comando** levante todo el sistema.

**Prueba para avanzar**

La prueba tiene que hacerla **el integrante que no escribió el README**, en una
carpeta vacía y distinta:

```
git clone <url> prueba-limpia
cd prueba-limpia
docker compose up
```

Tiene que funcionar **sin ningún paso manual y sin instalar nada más**. Si hay que
crear un archivo a mano, copiar algo o instalar una dependencia suelta, la fase no
está terminada.

**Commit:** `docs: readme with setup and run instructions`

---

### Fase 14 — Experimentos

**Qué hay que hacer**

Cinco experimentos. Cada uno con **hipótesis escrita antes de correrlo**, datos
medidos y conclusión.

| # | Experimento | Qué se espera |
|---|---|---|
| 1 | Envasado con 1 réplica | Envasado es el cuello de botella (12 s) |
| 2 | Envasado con 2 réplicas | Tiempo efectivo baja a ~6 s; **el cuello se desplaza a esterilización** (7 s) |
| 3 | Envasado con 3 réplicas | El lead time casi no mejora: el límite ya se mudó |
| 4 | Una réplica lenta | Procesa menos que las otras; el reparto se adapta solo |
| 5 | Saturación | La etapa saturada pasa a crítico y se recupera al bajar la carga |

El experimento 2 es el que **demuestra literalmente la frase del enunciado**. Es el
resultado más importante del informe.

**Prueba para avanzar**

Una tabla con datos reales medidos, no estimados. Cada experimento con su hipótesis,
sus números y su conclusión escrita.

**Commit:** `docs: experiment results for 1, 2 and 3 replicas`

---

### Fase 15 — Informe y defensa

**Qué hay que hacer**

- Informe en PDF, máximo 15 páginas más 15 de anexos.
- Slides para 15 minutos.
- `.zip` con el código fuente.

**No olvidar** (son puntos de rúbrica que el enunciado no menciona):

- Justificar **por qué mantener 2+ nodos** y explicar **cómo se abordaría la
  resiliencia**, aunque no se haya implementado.
- **Análisis crítico de las dificultades** de programación encontradas.
- Declarar **todos los supuestos** de §5 como supuestos, nunca como parte del enunciado.
- Defender la decisión de la **cola pull en vez de balanceador clásico** (§4).

**Prueba para avanzar**

Ensayo completo cronometrado. Si pasa de 15 minutos, hay que cortar contenido, no
hablar más rápido.

**Commit:** `docs: architecture decisions and assumptions`

---

### Fase 16 — Broker Kafka *(opcional)*

**Solo si la Fase 13 está cerrada.** El total de Desarrollo está topado en 100 y los
criterios base ya suman 100, así que el bonus es un colchón, no un extra. Con dos
personas y poco tiempo, la recomendación es **no ir por él**.

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

**Actualizado 21/08/2026.** Fases 0 y 1 completas y verificadas — la Fase 0
además rehecha y verificada en la **máquina 2** (ver `docs/fases/fase-0-entorno.md`;
Ubuntu y datos de Docker viven en D: por falta de espacio en C:). **Fase 2:**
diseño escrito y commiteado en `docs/diseno.md`; su prueba oficial (cuestionario
§6 respondido por ambos sin mirar) **sigue pendiente y es bloqueante antes de
repartir las fases 8–11**. **Fase 3 completa y verificada** (batería de 8 casos
contra el contrato, todos pasando). **La siguiente es la Fase 4.**

### Lo que ya está hecho

**Fase 0 — Entorno y repositorio** ✅

- Virtualización `SVM` habilitada en la BIOS (venía apagada de fábrica).
- WSL2 instalado con Ubuntu 26.04, kernel 6.18, versión 2.
- Docker Desktop 4.86.0 funcionando · `docker run hello-world` responde ·
  `docker compose version` → v5.3.1.
- Git 2.54 configurado.
- Repositorio creado en GitHub y pusheado.

**Fase 1 — Mini-demo desechable** ✅

- `demo/productor.py` y `demo/trabajador.py` funcionando contra Redis en contenedor.
- Verificado con 3 trabajadores y 15 órdenes: reparto 5/5/5, **cero duplicados,
  cero pérdidas**.

### Lo que falta

Las fases 4 a 15, más la **prueba de equipo de la Fase 2** (cuestionario de
`docs/diseno.md` §6, ambos integrantes sin mirar el documento). El detalle del
avance por fase vive en las bitácoras de `docs/fases/`.

### Reparto sugerido entre los dos

Las fases 0 a 7 son una cadena y conviene hacerlas juntos o al menos coordinados,
porque cada una depende de la anterior. Desde la 8 se puede repartir:

| Integrante | Fases |
|---|---|
| A | 8 (persistencia) y 9 (métricas) |
| B | 10 (cuello de botella) y 11 (UI Streamlit) |

La 11 es la más larga de todas: conviene que quien la tome parta apenas exista la
API de métricas, aunque sea con datos incompletos.

Después la 12, 13, 14 y 15 se hacen en orden y entre los dos.

### Entorno de trabajo

- Windows 11. Lo que requiere interfaz gráfica (instaladores, BIOS, GitHub web) lo
  hace el usuario a mano; el resto se ejecuta en la terminal.
- Python 3.12 instalado nativo, más un entorno virtual en `.venv` para la demo.
- Redis corre en un contenedor: `docker start demo-redis` para levantarlo.

### Advertencias de entorno encontradas en la Fase 0

Sirven de insumo para el **análisis crítico de dificultades** del informe (15 pts
de rúbrica):

1. La virtualización venía deshabilitada en el firmware. Ningún software puede
   activarla desde el sistema operativo: hay que entrar a la BIOS.
2. `wsl --install` instaló el motor de WSL2 pero **no descargó ninguna
   distribución**. Hubo que instalar Ubuntu aparte con `wsl --install -d Ubuntu`.
3. Docker Desktop se caía al arrancar por *sockets de Unix huérfanos* que quedaron
   de un arranque fallido y que Windows no puede borrar (`ERROR_CANT_ACCESS_FILE`).
   Cada caída sembraba el bloqueo de la siguiente. Se resolvió renombrando los
   directorios afectados y desactivando la función de IA de Docker (`EnableDockerAI`),
   cuyo *Inference manager* era el primer servicio en caer y que este proyecto no usa.

### Siguiente acción concreta

Fase 4: agregar el servicio `redis` al `docker-compose.yml` y hacer que
`orders-api` encole el id de cada orden nueva en `cola:fileteado`, con el host
de Redis por variable de entorno. Además, en cuanto estén juntos: pasar la
prueba de equipo de la Fase 2 (es requisito antes de repartir las fases 8–11).

---

## 11. Pendientes administrativos

**Resuelto (21/08/2026):** el correo al profesor con las tres preguntas
(caso asignado, grupo de 2, respaldo por escrito) quedó descartado por decisión
del equipo. No volver a recordarlo.
