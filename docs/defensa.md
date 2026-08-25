# Defensa — plan de contenido y preguntas probables

> **El guion hablado ya no está acá.** Vive en
> [`guion-defensa.md`](guion-defensa.md), escrito palabra por palabra sobre las
> 21 láminas del deck, con lo que hay que decir en cada una.
>
> Este documento se conserva porque tiene el plan por lámina del que salió
> aquel, el guion detallado de la demo en vivo y las preguntas probables.
> Ensayar cronometrado: si pasa de 15 min se corta contenido, no se habla más
> rápido.

## Guion (15 láminas ≈ 1 min c/u)

1. **El caso** — Línea de producción con balanceo dinámico. Dominio: planta
   conservera *ficticia* de jurel 425 g. 4 etapas en serie, envasado replicada.
2. **La pregunta del caso** — ¿Qué pasa con el cuello de botella cuando
   escalas la etapa lenta? (Adelanto: no desaparece, **se muda**.)
3. **Arquitectura** — 5 servicios, 3 nodos lógicos (operación / procesamiento /
   estado). Por qué esa agrupación: cada nodo escala por un motivo distinto.
4. **Una imagen, cuatro estaciones** — mismo código, 4 configuraciones por
   variables de entorno. Escalar = `--scale envasado=3`.
5. **Balanceo por demanda** — las réplicas *piden* trabajo al quedar libres
   (cola compartida), no lo reciben asignado. Un round-robin alimenta a la
   réplica lenta igual que a las rápidas; la cola no.
6. **Condición de carrera** — la provocamos antes de resolverla (commit de la
   versión rota): mirar+sacar en 2 pasos → duplicados con 3 réplicas y 200
   órdenes. `BRPOP` (1 operación atómica) → 0 duplicados. Está en el historial.
7. **Criterio de cuello de botella** — espera, no servicio. Un ciclo largo es
   una tarea lenta; un atasco es espera creciente. Umbrales relativos al ciclo
   (1.5× advertencia, 3× crítico), ventana móvil 60 s.
8. **DEMO EN VIVO (≈4 min)** — ver guion de demo abajo.
9. **Resultado central (tabla)** — 1 réplica: cuello envasado (espera 67,8 s,
   lead 82,9 s). 2 réplicas: cuello **se desplaza a esterilización** (lead
   65,6 s, −21 %). 3 réplicas: lead 62,0 s (−5 %): el límite ya se mudó.
10. **Réplica lenta** — 11/12/7 contra el 10/10/10 de un round-robin. Nadie
    programó ese reparto: emerge del mecanismo.
11. **Saturación** — ráfaga de 25: crítico solo a los 32 s, la ola recorre la
    línea, todo normal solo a los 278 s. Sin tocar nada.
12. **Errores** — matar Redis: 503 en 2,1 s con mensaje claro (el hallazgo:
    el cuelgue estaba en el DNS, no en el socket — 46 s medidos). La UI nombra
    al servicio que realmente falta.
13. **Persistencia y reproducibilidad** — 2 tablas, nada guardado 2 veces,
    sobrevive a `down`. Clon limpio + `docker compose up` verificado.
14. **Resiliencia (no exigida, sí explicada)** — qué haríamos: BLMOVE + cola
    en-proceso para lotes a mitad de ciclo, Sentinel para Redis, MySQL si hay
    failover, 2ª instancia de API tras un balanceador HTTP.
15. **Conclusión** — el cuello no se elimina: se muda. Medir espera es lo que
    permite verlo en vivo. Supuestos declarados. Preguntas.

## Guion de la demo en vivo (lámina 8)

1. `docker compose up -d --scale envasado=2` ya corriendo ANTES de empezar
   (o `INICIAR.bat`, que hace lo mismo y abre el navegador solo).
2. Tablero en 8501: línea al día, 5 réplicas visibles con su ciclo.
3. Ingresar lotes **espaciados ~5 s** desde la UI (⚠️ no de golpe: si se
   inyecta todo junto, el cuello sale en fileteado — correcto, pero es la
   respuesta a otra pregunta; explicarlo si alguien pregunta).
4. Ver crecer la espera de esterilización en el gráfico → cartel ámbar → rojo.
5. **La condición de carrera, al final del tablero**: bajar a «Por qué la línea
   no produce el mismo lote dos veces», leer las dos tarjetas de pasos (dos
   operaciones contra una) y apretar **«Ejecutar la comparación»**. En ~7 s
   quedan los dos paneles lado a lado: 300 lotes envasados contra 100 pedidos
   por un lado, 100 contra 100 por el otro.
   - Decir en voz alta que es **el mismo código** que corre en las estaciones
     (`servicios/comun/reclamo.py`, importado por las dos partes) y que la
     prueba usa una cola aparte, así que la línea de arriba sigue produciendo.
   - Si preguntan por qué hilos y no contenedores: porque lo que la carrera
     necesita es concurrencia sobre la misma cola, no procesos separados —
     y la proporción de duplicados es la misma que midió la Fase 6 con
     contenedores reales.
6. `docker compose stop redis` → la UI explica y nombra a Redis; volver a
   levantar → todo sigue. (Plan B si algo falla: capturas en anexos.)

> El botón del punto 5 reemplaza al plan B que teníamos para la carrera: ya no
> hace falta reiniciar la línea en modo `ingenuo` ni correr el script de bash
> delante de la comisión.

## Preguntas que podrían hacernos

**¿Dónde está el "balanceador" que pide el enunciado?**
Es la cola compartida: el punto único por el que pasa el trabajo y que decide
quién procesa qué. Elegimos reparto por demanda porque un balanceador clásico
(round-robin) no es dinámico: le sigue mandando trabajo a la réplica lenta.
Nuestro experimento 4 muestra el reparto adaptándose solo (11/12/7). Si se
quisiera un balanceador HTTP, iría delante de las réplicas para consultas de
estado — para el trabajo, la cola es superior en este caso.

**¿Y el "lock/contador distribuido" que menciona el enunciado?**
Cubierto por el mismo mecanismo: BRPOP es una operación atómica servida por el
único hilo de comandos de Redis — es un mutex implícito por elemento. Un lock
explícito con TTL habría *administrado* la ventana de carrera; la extracción
atómica la *elimina*. Y lo demostramos: versión de 2 pasos → duplicados;
atómica → 0 en 200.

**¿Por qué el cuello es esterilización si envasado es más lento (12 s > 7 s)?**
Porque con 2 réplicas el tiempo *efectivo* de envasado es ~6 s por lote. Y en
general el cuello no es la etapa de mayor ciclo sino la de mayor *espera*: la
que recibe trabajo más rápido de lo que drena. Por eso medimos espera y no
servicio — con servicio, el detector habría señalado envasado para siempre.

**¿Qué pasa si una réplica muere a mitad de un lote?**
Ese lote ya salió de la cola y se pierde de la línea (queda en_proceso en la
base). Es una limitación conocida y aceptada: el enunciado excluye tolerancia
a fallos. Sabemos el camino: BLMOVE a una cola "en proceso" por réplica y un
barrendero que la devuelva al detectar latido vencido — está en el informe.

**¿Por qué SQLite y no MySQL?**
Un solo nodo de estado, escrituras cortas, y cero infraestructura extra que
administrar en la demo. WAL + busy_timeout + una conexión por operación
resuelven la concurrencia real del sistema (lo estresamos en el experimento 4
y encontramos su límite — está en dificultades). El cambio a MySQL toca un
solo módulo (bd.py) si hiciera falta failover.

**¿Cómo saben que las métricas son correctas?**
Los servicios medidos coinciden con los ciclos configurados (4,8/12,4/3,4/7,3
contra 4/12/3/7): la instrumentación se valida sola. Y todo se calcula desde
la tabla de eventos — no hay un segundo lugar que pueda contradecirla.

**¿Por qué la espera se mide contra el entra_cola de cada etapa y no contra
la creación de la orden?**
Con 4 etapas en serie, medir contra la creación le cargaría a sellado todo lo
que pasó antes en fileteado y envasado, y señalaría al culpable equivocado.
Cada etapa responde solo por su propia cola.

## Pendientes antes de la defensa

- [x] Pasar el guion a slides — hay **dos formatos** en `presentacion/`, ver el
      README de esa carpeta: el A (17 láminas, continuo) y el B (21, partido en
      actos, con menos texto por lámina).
- [ ] **Elegir uno de los dos formatos** y borrar el otro. Los dos PDF están
      compilados y al día.
- [ ] Repartir los turnos de exposición (rúbrica: *Participación del equipo*).
- [ ] Ensayar cronometrado. Con 4 min de demo quedan ~11 min para el resto.
- [x] Compilar `informe/informe_caso2.tex` a PDF con gráficos de resultados
      y bibliografía — falta completar capturas de anexos.
- [ ] Prueba de equipo de la Fase 2 (cuestionario de docs/diseno.md §6, ambos
      sin mirar el documento) — obligatoria según el plan.
- [ ] Repetir la prueba de clon limpio en la máquina 2 (integrante que no
      escribió el README).
- [ ] Armar el .zip del código fuente.
