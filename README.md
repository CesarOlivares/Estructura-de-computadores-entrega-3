# Estructura de Computadores — Evaluación 3

**Caso 2: Línea de Producción con Balanceo Dinámico** · ECSD 2026-1 · USACH

Simulación distribuida de una planta conservera ficticia de jurel en lata (425 g),
con cuatro etapas en serie y balanceo dinámico de carga en la etapa replicada:

```
cola → FILETEADO → cola → ENVASADO → cola → SELLADO → cola → ESTERILIZACIÓN → listos
         ×1                ×2–3              ×1                 ×1
        4 s               12 s               3 s                7 s
```

Cada lote de latas recorre las cuatro etapas. La etapa de envasado se replica: sus
réplicas **piden** trabajo cuando quedan libres, en vez de recibirlo asignado, así
que el reparto se adapta solo a la velocidad de cada una.

## Integrantes

- César Olivares
- Simón García-Huidobro

---

## Entregables

| | Archivo |
|---|---|
| **Informe** | [`informe/informe_caso2.pdf`](informe/informe_caso2.pdf) |
| **Presentación** | [`presentacion/presentacion_caso2.pdf`](presentacion/presentacion_caso2.pdf) |
| **Código y demo** | este repositorio — ver [Ejecución](#ejecución) |

Las fuentes LaTeX de ambos documentos están junto a sus PDF. El material que
entregó el curso (enunciado, resumen del caso y rúbrica) está en
[`enunciado/`](enunciado/).

El `.zip` del código fuente que pide el enunciado se genera desde el propio
repositorio, así que nunca queda desincronizado del código:

```bash
git archive --format=zip --prefix=caso2-linea-produccion/ -o caso2-codigo-fuente.zip HEAD
```

Incluye solo lo versionado: ni artefactos de compilación, ni `.git`, ni la base
de datos generada en ejecución.

---

## Cómo obtenerlo

Repositorio: **https://github.com/CesarOlivares/Estructura-de-computadores-entrega-3**

```bash
git clone https://github.com/CesarOlivares/Estructura-de-computadores-entrega-3.git
```

O, sin git: botón verde **Code → Download ZIP**, y descomprimir. Después,
doble clic en `INICIAR.bat` dentro de la carpeta.

---

## Requisitos previos

Lo único que hay que tener instalado:

| | Versión mínima | Cómo verificar |
|---|---|---|
| **Docker Desktop** | 4.x, con el motor corriendo | `docker run hello-world` |
| **Docker Compose** | v2 | `docker compose version` |

No hace falta instalar Python, Redis ni ninguna dependencia: todo va dentro de los
contenedores.

> **En Windows** Docker Desktop necesita WSL2 y que la virtualización esté
> habilitada en la BIOS (en procesadores AMD la opción se llama `SVM Mode`).
> Ver `docs/fases/fase-0-entorno.md` si el motor no arranca.

---

## Ejecución

### En Windows: doble clic en **`INICIAR.bat`**

Eso es todo. El script comprueba Docker, abre Docker Desktop si el motor está
apagado, construye las imágenes, espera a que el tablero responda y abre el
navegador solo. Si algo falla, la ventana queda abierta explicando qué pasó.

Para detener, doble clic en **`DETENER.bat`** (pregunta si conservar o borrar
los datos).

En macOS o Linux el equivalente es `./iniciar.sh`.

### A mano

Desde la raíz del repositorio, **un solo comando**:

```bash
docker compose up -d --build
```

La primera vez tarda unos minutos construyendo las imágenes. Después de eso,
espera unos 20 segundos a que los servicios terminen de arrancar y abre:

### **http://localhost:8501**

Ese es el tablero de operaciones. Es lo único que se necesita mirar.

### Verificar que quedó todo arriba

```bash
docker compose ps
```

Deben aparecer 8 contenedores en estado `Up`, con `redis` además en `healthy`.

### Detener

```bash
docker compose down      # detiene todo; la base de datos se conserva
docker compose down -v   # además borra el volumen: empieza de cero
```

---

## Qué queda corriendo

| Puerto | Servicio | Para qué |
|---|---|---|
| **8501** | **Tablero (Streamlit)** | **La interfaz. Es la que se usa.** |
| 8000 | orders-api | Crear y consultar órdenes · docs en `/docs` |
| 8001 | metrics-api | Métricas y cuello de botella · docs en `/docs` |
| 6379 | Redis | Colas y estado de las réplicas (no tiene interfaz web) |

Los puertos 8000 y 8001 exponen la documentación automática de FastAPI en
`http://localhost:8000/docs` y `http://localhost:8001/docs`, donde se pueden probar
los endpoints a mano.

---

## Cómo usarlo

En el panel izquierdo del tablero hay un botón **«Ingresar lote a la línea»**. Cada
clic crea una orden real: se guarda en SQLite y entra a la cola de Redis.

La pantalla se actualiza sola cada 2 segundos y muestra:

- **El cartel superior**: si alguna etapa está acumulando trabajo, y por qué.
- **Tres indicadores**: lotes en la línea, lotes terminados y cuánto demora un lote
  de principio a fin.
- **El recorrido**: dónde está cada lote, con las colas entre etapas y una línea por
  réplica indicando si está trabajando y cuántos lotes lleva hechos.
- **El gráfico**: cuánto esperan los lotes antes de cada etapa, en el tiempo.

> **Importante para la demostración:** no ingreses muchos lotes de golpe. Si se
> inyectan todos a la vez se apilan en la primera cola y el tablero marcará
> *fileteado* como el atasco — correctamente, porque es ahí donde más esperan.
> Para ver el cuello de botella donde corresponde, ingresa un lote cada 5 segundos
> aproximadamente.

---

## La demostración de la condición de carrera

Al final del tablero, después del separador, hay una sección aparte:
**«Por qué la línea no produce el mismo lote dos veces»**. Es la respuesta
ejecutable al problema central del Caso 2.

Explica el problema en dos tarjetas enfrentadas —el reclamo en dos pasos
(`LRANGE` + `LREM`) contra el atómico (`BRPOP`)— y trae un botón,
**«Ejecutar la comparación»**, que corre el experimento en vivo: encola la
misma cantidad de lotes dos veces, una con cada modo, y grafica los dos
resultados lado a lado en la misma escala.

Con 100 lotes y 3 máquinas, el resultado típico es:

| | Reclamo en dos pasos | Reclamo atómico |
|---|---|---|
| Lotes envasados | **300** | **100** |
| Lotes duplicados | **100** (todos, hasta 3 veces) | **0** |
| Lotes perdidos | 0 | 0 |

Tres detalles que hacen que la demostración pruebe algo:

- **Es el mismo código.** Las dos funciones comparadas se importan de
  `servicios/comun/reclamo.py`, el módulo que también importa
  `servicios/estacion/worker.py` para trabajar de verdad. No hay una copia
  para la demo que pueda quedar desincronizada.
- **Es el Redis real**, con hilos concurrentes compitiendo por una cola real.
  Si el reclamo atómico fallara, ahí se vería: el color de las tarjetas sale
  del resultado medido, no del modo.
- **No toca la línea.** Usa claves `demo:carrera:<id>` propias de cada corrida,
  que se borran al terminar. Se puede ejecutar con lotes circulando.

La versión con contenedores reales en vez de hilos es
`experimentos/fase6_carrera.sh`, y da el mismo resultado.

---

## Configuración

Todos los parámetros tienen valores por defecto que funcionan, así que **no hay que
crear ningún archivo para levantar el sistema**. Se cambian solo para experimentar,
anteponiéndolos al comando o poniéndolos en un archivo `.env` en la raíz
(hay un `.env.example` con todos los valores documentados: `cp .env.example .env`).

| Variable | Defecto | Qué controla |
|---|---|---|
| `CICLO_FILETEADO` | `4` | Segundos por lote en fileteado |
| `CICLO_ENVASADO` | `12` | Segundos por lote en envasado |
| `CICLO_SELLADO` | `3` | Segundos por lote en sellado |
| `CICLO_ESTERILIZACION` | `7` | Segundos por lote en esterilización |
| `CICLO_ENVASADO_LENTO` | `24` | Ciclo de la réplica lenta (perfil `experimento`) |
| `VENTANA_S` | `60` | Ventana móvil sobre la que se promedian las esperas |
| `MODO_RECLAMO` | `atomico` | `atomico` (correcto) o `ingenuo` (reproduce la condición de carrera) |
| `PLAZO_REDIS_S` | `2` | Segundos que un servicio espera a Redis antes de darlo por caído (503 en órdenes) |

Ejemplo, acelerando la línea diez veces para una prueba rápida:

```bash
CICLO_FILETEADO=0.4 CICLO_ENVASADO=1.2 CICLO_SELLADO=0.3 CICLO_ESTERILIZACION=0.7 \
  docker compose up -d
```

Dos parámetros más viven como valores por defecto en el código de `metricas`
(`FACTOR_ADVERTENCIA=1.5` y `FACTOR_CRITICO=3`): son los múltiplos del tiempo de
ciclo de cada etapa a partir de los cuales se considera advertencia o atasco. La
justificación está en `docs/diseno.md` §4.

---

## Escalar la etapa replicada

Envasado es la etapa que se replica. Este es el experimento central del proyecto:

```bash
docker compose up -d --scale envasado=1    # el cuello está en envasado (12 s)
docker compose up -d --scale envasado=2    # el cuello se desplaza a esterilización (7 s)
docker compose up -d --scale envasado=3    # el lead time ya casi no mejora
```

Con dos réplicas, envasado produce efectivamente un lote cada 6 s y deja de ser la
etapa más lenta: el límite pasa a ser esterilización, con 7 s. Agregar una tercera
réplica no mejora el resultado, porque el freno ya se mudó de lugar.

---

## Experimentos

Los scripts de `experimentos/` automatizan las dos demostraciones técnicas. Son
scripts de bash: en Windows se ejecutan desde **WSL** o **Git Bash**.

### Condición de carrera (Fase 6)

Demuestra que reclamar una orden en dos operaciones separadas permite que dos
réplicas tomen el mismo lote, y que hacerlo en una sola operación atómica lo impide.

Esta es la versión con **contenedores reales**: levanta tres réplicas de
envasado en cada modo y las hace competir. Es más lenta y exige reiniciar la
línea entre corridas; la versión de un clic, sin reiniciar nada, es el botón
del tablero (ver arriba).

```bash
# Versión rota, a propósito: se esperan duplicados
MODO_RECLAMO=ingenuo CICLO_ENVASADO=0.05 docker compose up -d --scale envasado=3
./experimentos/fase6_carrera.sh 200

# Versión correcta: cero duplicados
MODO_RECLAMO=atomico CICLO_ENVASADO=0.05 docker compose up -d --scale envasado=3
./experimentos/fase6_carrera.sh 200
```

### Balanceo dinámico (Fase 7)

Demuestra que el reparto se adapta a la velocidad de cada réplica. Levanta dos
réplicas normales más una configurada al doble de lento, sobre la misma cola:

```bash
CICLO_ENVASADO=1.2 CICLO_ENVASADO_LENTO=2.4 \
  docker compose --profile experimento up -d --scale envasado=2
./experimentos/fase7_balanceo.sh 60
```

La réplica lenta debe procesar visiblemente menos lotes que las otras dos. Un
round-robin les habría repartido la misma cantidad a las tres.

---

## Estructura del repositorio

```
INICIAR.bat    arranque de un clic en Windows (DETENER.bat lo detiene)
iniciar.sh     lo mismo para macOS y Linux
servicios/
  comun/       las dos formas de reclamar trabajo, compartidas por
               las estaciones y por la demostración del tablero
  ordenes/     orders-api — crea y consulta órdenes (puerto 8000)
  estacion/    una imagen desplegada 4 veces, una por etapa
  metricas/    metrics-api — espera, servicio, lead time y cuello (puerto 8001)
  ui/          tablero Streamlit (puerto 8501)
docs/
  diseno.md    contratos de las APIs, esquema de datos, criterio de cuello
  defensa.md   guion de la defensa
  fases/       bitácora por fase: qué se logró, dificultades, pendientes
informe/       informe del caso 2 en PDF, su fuente LaTeX y las figuras
               (generar_figuras.py las reconstruye desde los resultados medidos)
presentacion/  slides de la defensa en PDF, con su fuente LaTeX
demo/          prototipo desechable de cola + workers (Fase 1)
experimentos/  scripts de los experimentos de las fases 6 y 7,
               y sus resultados medidos en resultados/
enunciado/     material entregado por el curso: enunciado, resumen y rúbrica
```

`servicios/comun/` es el único código compartido entre servicios, y lo es por
un motivo concreto: si el tablero tuviera su propia copia de las funciones de
reclamo, su demostración probaría esa copia y no lo que corre en la planta.
Por eso las imágenes de `estacion` y `ui` se construyen con `servicios/` como
contexto y no con su propia carpeta.

### Arquitectura

Tres nodos lógicos, agrupados por lo que hace que cada uno cambie de escala:

| Nodo | Contiene | Por qué van juntos |
|---|---|---|
| A | tablero, orders-api | Exponen el sistema al operador |
| B | las 4 estaciones | Es lo único que se replica bajo carga |
| C | Redis, metrics-api, SQLite | Concentran el estado compartido |

El estado compartido no puede duplicarse sin coordinación, y por eso vive en un solo
nodo. Las estaciones no tienen estado propio, y por eso se pueden multiplicar.

### Persistencia

SQLite en `/datos/planta.db`, montado en un **volumen de Docker**. Sobrevive a
`docker compose down`: al volver a levantar, las órdenes anteriores siguen ahí.

Se guardan dos tablas: `ordenes` y `eventos`. Los tiempos de espera, de servicio y
el lead time **no se guardan**: se calculan desde `eventos` cada vez que se piden.
Guardar el mismo dato dos veces es la forma más fácil de que se contradigan.

---

## Si algo falla

| Síntoma | Qué revisar |
|---|---|
| `docker: error during connect` | Docker Desktop no está corriendo. Ábrelo y espera a que diga `Engine running` — o usa `INICIAR.bat`, que lo abre y lo espera solo. |
| El tablero dice que no puede mostrar los datos | Revisa `docker compose ps`. El propio mensaje indica qué servicio falta. |
| Puerto ya en uso (`port is already allocated`) | Algo más ocupa el 8000, 8001, 6379 u 8501. Ciérralo o cambia el puerto en `docker-compose.yml`. |
| El tablero está vacío y todo en cero | No hay lotes. Ingresa algunos desde el panel izquierdo. |
| Las réplicas aparecen como «sin réplicas activas» | Las estaciones todavía están arrancando. Espera unos segundos. |

Registros de un servicio en particular:

```bash
docker compose logs -f ui
docker compose logs -f envasado
```
