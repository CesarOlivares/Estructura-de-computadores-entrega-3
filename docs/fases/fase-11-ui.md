# Fase 11 — UI Streamlit

**Estado: CERRADA (21/08/2026)**

## Objetivo

Un tablero que consuma los servicios reales y permita **interacción**, no solo
visualización: timeline de producción, carga por réplica, alerta de cuello de
botella e histórico de estadísticas.

## Qué se logró

- [x] `servicios/ui/` — servicio Streamlit en el puerto 8501, agregado al
      `docker-compose.yml`. Levanta con el mismo `docker compose up`.
- [x] **Timeline de producción**: diagrama de las 4 etapas con las colas entre
      medio, los lotes esperando en cada una y el estado de cada etapa.
- [x] **Indicador de carga por réplica**: una línea por réplica con si está
      trabajando o libre y cuántos lotes lleva hechos.
- [x] **Alerta visual de cuello de botella**: cartel que nombra la etapa
      atascada y explica por qué, con el criterio de `GET /metricas/cuello`.
- [x] **Histórico** además del tiempo real: gráfico de la espera por etapa en
      el tiempo.
- [x] **Interacción real**: se ingresan lotes desde la UI (`POST /ordenes`).
- [x] Mensajes claros cuando un servicio no responde, con diagnóstico de la
      causa real (ver dificultad 2).

## De dónde sale cada dato

| Dato | Origen |
|---|---|
| Espera, servicio, `en_cola`, procesadas por etapa | `GET /metricas?ventana_s=` |
| Etapa atascada, estado de cada etapa, razón | `GET /metricas/cuello?ventana_s=` |
| Carga y estado de cada réplica | Redis, `HGETALL estado:replicas` |
| Ingresar un lote | `POST /ordenes` |
| Semáforo de servicios | `GET /salud` de cada uno + `PING` a Redis |

La UI **no calcula ninguna métrica**: las pide. Todo el cálculo sigue viviendo
en `metricas/app.py`, que es el único lugar donde está.

## Principales dificultades

1. **El ritmo de entrada decide qué etapa aparece como cuello.** Ingresando
   lotes de golpe desde la UI, el cuello detectado es **fileteado**, no
   envasado — y está bien: con todo inyectado a la vez, es en la primera cola
   donde más se espera. Es la misma lección de la Fase 10 (dificultad 1), vista
   ahora desde la interfaz: quien opere la UI en la demo tiene que ingresar los
   lotes espaciados, o el tablero mostrará el resultado correcto para la
   pregunta equivocada.

2. **Cuando Redis se cae, el síntoma engaña.** Medido: con `redis` detenido,
   `GET /metricas` y `POST /ordenes` **no responden en más de 30 s**, mientras
   que el `GET /salud` de ambos servicios contesta en 0,02 s — porque `/salud`
   no consulta Redis.

   Desde la UI parecía que fallaban órdenes y métricas, cuando lo que faltaba
   era Redis. Un mensaje que diga "no responde el servicio de órdenes" manda a
   buscar el error al lugar equivocado.

   Se resolvió en la UI con `diagnostico()`, que ante cualquier fallo consulta
   el `/salud` de los tres y nombra al que realmente falta. Y con `timeout=3 s`
   en las peticiones, para que el tablero corte y avise en vez de congelarse.

   **Causa de fondo, en los servicios:** el cliente de Redis de `ordenes` y
   `metricas` se crea sin `socket_connect_timeout`, así que una consulta a un
   Redis caído espera el timeout de TCP del sistema operativo, que son minutos.
   La Fase 12 pide "503 si una dependencia no responde"; hoy responden colgados.
   **Pendiente para la Fase 12**, en los servicios, no en la UI.

## Decisiones tomadas en esta fase

### El histórico se arma en el cliente, no en un endpoint

`docs/diseno.md` §1.3 preveía un `GET /metricas/historico`. **No se implementó.**
La UI ya consulta `/metricas` cada 2 s para refrescar la pantalla; guardar esas
mismas muestras en memoria de la sesión da la serie temporal sin costo alguno.

Un endpoint de histórico habría necesitado una tabla nueva y un muestreador de
fondo en `metricas` — más piezas para un dato que ya estaba pasando por el cable.

Lo que se pierde: el histórico se reinicia al recargar la página. Para un
tablero de operación en vivo es aceptable; si se quisiera histórico persistente
entre sesiones, ahí sí corresponde el endpoint. **Queda anotado como desvío
consciente del contrato, no como olvido.**

### La carga por réplica se lee de Redis, no por HTTP

`metrics-api` entrega números por **etapa**, no por **réplica**. Las réplicas sí
publican su estado, en el hash `estado:replicas` (ver `publicar_estado()` en
`estacion/worker.py`), justamente para que alguien las observe.

La alternativa era consultar `GET /estado` de cada estación, pero con
`--scale envasado=3` no se sabe de antemano cuántas hay ni en qué dirección
está cada una. El hash resuelve el descubrimiento y el dato de una vez.

Se descartan las réplicas cuyo latido tenga más de 30 s: el hash conserva la
entrada aunque el contenedor se haya detenido, y mostrar una máquina apagada
como si estuviera trabajando sería un dato falso.

### El color marca importancia, no identidad

Pintar las cuatro etapas de cuatro colores distintos —lo primero que uno hace—
logra que las cuatro griten igual de fuerte y que la que tiene el problema no se
distinga de las que van bien.

Regla adoptada: **lo normal se dibuja en gris; el color fuerte queda reservado
para lo que requiere atención.** Ámbar si una etapa acumula trabajo, rojo si
está atascada. La identidad de cada etapa queda en un punto de 8 px junto al
nombre, del mismo color que su línea en el gráfico.

En el gráfico, la etapa atascada va con trazo grueso en su color de estado y las
demás en gris fino, como contexto. Ninguna información depende solo del color:
cada estado lleva icono y texto.

### Una sola pantalla, un solo gráfico

Sin pestañas y sin tablas. Todo lo que se podría graficar aparte —carga por
réplica, largo de cada cola, estado de cada etapa— ya se ve en el diagrama de la
línea; repetirlo en barras no agrega información, agrega pantalla que leer.

El único gráfico es el histórico, porque es lo único que el diagrama no puede
mostrar: la tendencia. Una foto no distingue una ráfaga pasajera de un atasco.

## Verificación

Contra el sistema real levantado con `docker compose up -d --scale envasado=2`:

- Los tiempos de servicio que muestra el tablero coinciden con los ciclos
  configurados: **4,01 / 12,01 / 3,00 / 7,01 s** contra 4 / 12 / 3 / 7.
- Las 5 réplicas aparecen con su tiempo de ciclo y su contador; envasado
  muestra sus 2.
- Se ingresó un lote desde la UI y el servicio devolvió `201` con su id.
- Cantidad inválida (`-5`) → mensaje claro, sin traza de error.
- Con `metricas` detenido: la UI explica y se pueden seguir ingresando lotes.
- Con `redis` detenido: la UI corta en 3 s, nombra a Redis y `en_cola` queda en
  `?` en vez de `0` (un 0 sería mentira).

## Qué queda para la siguiente fase

**Fase 12 — Errores, logging y healthchecks.** Lo urgente es el punto 2 de las
dificultades: `socket_connect_timeout` en el cliente Redis de `ordenes` y
`metricas`, para que devuelvan `503` en vez de colgarse.
