# Fase 13 — Reproducibilidad

**Estado: CERRADA (22/08/2026)** — con una repetición pendiente en la máquina 2 (ver al final).

## Objetivo

Que el proyecto se pueda evaluar: clonar en una carpeta vacía y que
`docker compose up` levante todo, **sin pasos manuales y sin instalar nada más**.

## Qué se logró

- [x] **README completo** (lo dejó adelantado la Fase 11): requisitos,
  ejecución con un solo comando, uso del tablero, configuración, experimentos,
  estructura del repositorio y tabla de diagnóstico de fallas.
- [x] **`.env.example`** con todas las variables, sus valores por defecto y
  para qué sirve cada una — incluida `PLAZO_REDIS_S`, nueva de la Fase 12.
  El archivo deja explícito que **no es obligatorio crearlo**: los defaults
  del compose funcionan solos.
- [x] **Un solo comando levanta todo**: `docker compose up -d --build`.
  Sin scripts previos, sin archivos que crear, sin dependencias del host
  (ni Python: los curl de verificación son opcionales).
- [x] **Prueba de clon limpio, ejecutada de verdad** (no asumida):

  ```
  git clone <repo> prueba-limpia && cd prueba-limpia && docker compose up -d --build
  ```

  Resultado medido en carpeta vacía: **8/8 contenedores `healthy`**, se creó
  la orden 1 vía `POST /ordenes`, recorrió las cuatro etapas hasta
  `terminada`, y el tablero respondió en el puerto 8501. Cero pasos manuales.

## Principales dificultades

1. **El proyecto del clon no choca con el original… salvo por los puertos.**
   Docker Compose nombra contenedores, imágenes y volúmenes según la carpeta
   (`prueba-limpia-*`), así que el clon convive con el original sin pisarlo —
   pero los **puertos publicados** (8000, 8001, 6379, 8501) son del host y sí
   chocan. Para la prueba hubo que bajar la pila original primero. Es el
   comportamiento esperado; quedó anotado en la tabla "Si algo falla" del
   README (`port is already allocated`).

## Decisiones tomadas en esta fase

### `.env.example` documenta, no configura

Alternativa descartada: exigir `cp .env.example .env` como paso de
instalación. Se descartó porque agregaría el único paso manual del proyecto
para un archivo cuyos valores son idénticos a los defaults. La regla de la
fase es "cero pasos manuales", y un README que diga "primero copie tal
archivo" ya la rompe.

## Verificación

| Criterio del plan | Resultado |
|---|---|
| Clonar en carpeta vacía + `docker compose up` funciona | ✅ ejecutado, 8/8 healthy |
| Sin pasos manuales ni instalaciones adicionales | ✅ solo Docker Desktop |
| README con instalación, configuración y ejecución | ✅ |
| `.env.example` con todas las variables y defaults que funcionan | ✅ |

## Qué queda para la siguiente fase

**Fase 14 — Experimentos.** Los cinco del plan, con hipótesis escrita antes
de correr, datos medidos y conclusión.

**Pendiente de equipo (antes de la defensa):** repetir la prueba de clon
limpio en la **máquina 2**, hecha por el integrante que no escribió el README
— el plan la define así a propósito: la máquina del autor siempre tiene algo
instalado que la del evaluador no.
