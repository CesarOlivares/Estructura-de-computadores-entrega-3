# Fase 14 — Experimentos

**Estado: CERRADA (22/08/2026)**

## Objetivo

Cinco experimentos con **hipótesis escrita antes de correr**, datos medidos
(no estimados) y conclusión. Los JSON y bitácoras crudas quedan en
`experimentos/resultados/`.

## Protocolo común (experimentos 1–3)

Estado limpio (`docker compose down -v`), escala de envasado según el
experimento, e inyección de **1 orden cada 5 s durante 180 s** vía
`POST /ordenes` (`experimentos/fase14_carga.sh`). El ritmo constante importa:
una ráfaga apilaría todo en la primera cola y mediría la pregunta equivocada
(lección de la Fase 10). Medición al final de la inyección, ventana de 60 s.

Con 1 orden cada 5 s la línea recibe 0,20 lotes/s. Capacidades por etapa:
fileteado 0,25 · envasado 0,083×réplicas · sellado 0,33 · esterilización 0,143.

---

## Experimento 1 — Envasado con 1 réplica

**Hipótesis:** envasado (12 s de ciclo, capacidad 0,083 < 0,20 de llegada) se
atasca; el resto sigue el ritmo.

**Datos medidos:**

| Etapa | Espera (s) | Servicio (s) | En cola | Estado |
|---|---|---|---|---|
| Fileteado | 0,66 | 4,78 | 0 | normal |
| **Envasado** | **67,78** | 12,99 | **14** | **crítico** |
| Sellado | 0,68 | 3,46 | 0 | normal |
| Esterilización | 0,88 | 7,28 | 0 | normal |

Cuello detectado: **envasado** · Lead time promedio: **82,9 s** (el mínimo
físico sin colas es 26 s: casi todo el exceso es espera frente a envasado).

**Conclusión:** confirmada. Nótese que el tiempo de *servicio* de envasado
sigue siendo ~12 s — lo que crece es la *espera*. Es exactamente la
distinción del criterio de la Fase 2.

## Experimento 2 — Envasado con 2 réplicas ⭐

**Hipótesis:** el tiempo efectivo de envasado baja a ~6 s por lote
(capacidad 0,167), deja de ser el límite, y el cuello **se desplaza** a
esterilización (7 s, capacidad 0,143 < 0,20).

**Datos medidos:**

| Etapa | Espera (s) | Servicio (s) | En cola | Estado |
|---|---|---|---|---|
| Fileteado | 0,18 | 4,96 | 0 | normal |
| Envasado | 17,52 | 12,58 | 4 | normal |
| Sellado | 0,74 | 3,38 | 0 | normal |
| **Esterilización** | **25,21** | 7,25 | **4** | **crítico** |

Cuello detectado: **esterilización** · Lead time: **65,6 s** (−21 % vs E1)
· Reparto entre réplicas de envasado: **13 / 12**.

**Conclusión:** confirmada — es la frase del enunciado demostrada con datos:
al escalar la etapa replicada, el cuello de botella se mueve a otra etapa.
Nótese que esterilización tiene el ciclo más CORTO de las etapas señaladas
(7 s vs 12 s de envasado): un criterio basado en tiempo de servicio jamás la
habría señalado.

## Experimento 3 — Envasado con 3 réplicas

**Hipótesis:** el lead time casi no mejora, porque el límite ya se mudó a
esterilización.

**Datos medidos:**

| Etapa | Espera (s) | Servicio (s) | En cola | Estado |
|---|---|---|---|---|
| Fileteado | 0,22 | 4,59 | 0 | normal |
| Envasado | 0,73 | 12,24 | 0 | normal |
| Sellado | 0,89 | 3,33 | 0 | normal |
| **Esterilización** | **34,50** | 7,30 | **8** | **crítico** |

Cuello: **esterilización** · Lead time: **62,0 s** · Reparto: 10 / 10 / 9.

**Conclusión:** confirmada. La tercera réplica dejó la espera de envasado en
0,7 s (capacidad sobrada), pero el lead time solo bajó de 65,6 a 62,0 s
(−5 %, contra −21 % del paso de 1→2). Invertir en la etapa equivocada casi
no compra nada: el dinero de la tercera envasadora estaría mejor puesto en
una segunda autoclave.

**Resumen 1→2→3 réplicas:**

| Réplicas de envasado | Cuello detectado | Espera del cuello | Lead time |
|---|---|---|---|
| 1 | envasado | 67,8 s | 82,9 s |
| 2 | esterilización | 25,2 s | 65,6 s |
| 3 | esterilización | 34,5 s | 62,0 s |

## Experimento 4 — Una réplica lenta

**Hipótesis:** con 2 réplicas normales + 1 al doble de ciclo sobre la misma
cola, el reparto por demanda le da a la lenta ~la mitad de lotes. Un
round-robin repartiría 10/10/10 sin importar la velocidad.

**Protocolo:** ciclos 6 s / 6 s / 12 s, 30 órdenes directas a `cola:envasado`
(`experimentos/fase7_balanceo.sh 30`). Esperado por demanda: ~12/12/6.

**Datos medidos:** envasado-1: **11** · envasado-2: **12** · lenta: **7**.

**Conclusión:** confirmada. Nadie asignó ese reparto: emergió de que cada
réplica pide trabajo solo cuando termina el anterior. Es la evidencia de que
el balanceo es dinámico y no un round-robin.

## Experimento 5 — Saturación y recuperación automática

**Hipótesis:** ante una ráfaga (25 órdenes de golpe, envasado ×2), la etapa
saturada pasa a crítico **sola** y, al cesar la carga, vuelve a normal
**sola** — sin reiniciar nada ni tocar nada.

**Datos medidos** (`experimentos/resultados/exp5-saturacion.txt`, muestras
cada 15 s):

| t | Cuello | Observación |
|---|---|---|
| 1 s | — | todo normal |
| 17 s | fileteado (advertencia) | la ráfaga se apila en la PRIMERA cola |
| 32 s | fileteado (crítico) | |
| 94–170 s | fileteado crítico | la ola avanza: esterilización advertencia→crítico |
| 186 s | envasado | fileteado ya drenó y volvió a normal solo |
| 232 s | esterilización | la cola remanente se concentra al final de la línea |
| **278 s** | **—** | **las 4 etapas de vuelta en normal, sin intervención** |

**Conclusión:** confirmada, y con un bonus: se ve la **ola de congestión
recorrer la línea** (fileteado → envasado → esterilización) hasta disiparse.
La recuperación automática es efecto directo de la ventana móvil de 60 s:
cuando las esperas viejas salen de la ventana, el estado se limpia solo.

---

## Principales dificultades

1. **Con ciclos de ~1 s, el experimento 4 midió otra cosa.** El primer
   intento usó ciclos acelerados (1,2 s / 2,4 s) y dio 21/20/19: la réplica
   lenta procesó casi lo mismo que las rápidas.

   - *Causa:* a ese ritmo (~4 lotes/s cruzando 4 etapas), el costo real por
     lote lo dominaba la **escritura de eventos en SQLite** sobre el volumen
     de Docker (dos transacciones por lote por etapa, seis procesos
     compitiendo por el lock de escritura), no el `sleep` del ciclo. El
     tiempo efectivo por lote era ~11 s para todas y la diferencia 1,2 vs
     2,4 desaparecía dentro del ruido.
   - *Solución:* repetir con ciclos 6 s / 12 s, donde el overhead (<1 s) es
     despreciable. Resultado limpio: 11/12/7.
   - *Lección:* al acelerar una simulación hay que verificar que lo que se
     mide siga siendo lo que se quería medir. El overhead constante no
     escala con la simulación.

2. **`down -v` con el perfil experimento activo no borra el volumen** ("
   volume is still in use"): los contenedores del perfil no se detienen con
   el `down` sin perfil. Se resolvió bajando con
   `docker compose --profile experimento down -v`.

## Decisiones tomadas en esta fase

- **Ritmo de inyección de 5 s** para E1–E3: mayor que fileteado (4 s) para no
  saturar la entrada, menor que la capacidad de envasado ×1 (12 s) y que
  esterilización (7 s), de modo que el cuello quede donde lo pone la
  aritmética de capacidades y no el patrón de llegada.
- E4 se corre con órdenes directas a `cola:envasado` (script de la Fase 7)
  porque lo que se mide es el reparto entre réplicas, no la línea completa.

## Qué queda para la siguiente fase

**Fase 15 — Informe y defensa.** Los números de esta bitácora van directo a
la sección de resultados; la tabla resumen 1→2→3 réplicas es el gráfico
central de la presentación.
