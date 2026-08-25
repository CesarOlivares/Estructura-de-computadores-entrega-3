# Fase 15 — Informe y defensa

**Estado: EN CURSO (22/08/2026)** — borradores listos; falta compilar, capturas, slides PDF y ensayo.

## Objetivo

Informe PDF (≤15 páginas + 15 de anexos), slides para 15 minutos y el .zip
del código.

## Qué hay hasta ahora

- [x] **Borrador completo del informe** en
      `informe/informe_caso2.tex`, reutilizando la plantilla
      LaTeX/USACH de la entrega anterior (misma portada, colores y estilos;
      compilable con los mismos `logoBN.png` y `portada.png` de la carpeta).
      Incluye todo lo que la rúbrica pide y el enunciado no menciona:
      - justificación de **por qué 2+ nodos** (§2.2) y **cómo se abordaría la
        resiliencia** (§7) aunque no se implementó;
      - **análisis crítico de dificultades** (§8) con las 5 dificultades
        reales de las bitácoras (BIOS/WSL/Docker, fabricar la condición de
        carrera, el cuelgue del DNS, el overhead de SQLite al acelerar, el
        cuello dependiente del patrón de llegada);
      - **supuestos declarados como supuestos** (§9);
      - defensa explícita de la **cola pull como balanceador** (§3.1);
      - resultados con los **datos medidos** de la Fase 14 (tabla central
        1→2→3 réplicas).
- [x] **Guion de defensa** en `docs/defensa.md`: 15 láminas (1 min c/u),
      guion de demo en vivo con plan B, y preguntas probables con respuestas.
- [x] Compilar el .tex con XeLaTeX y ajustar al límite de páginas: **31 págs**
      = 15 de cuerpo + 15 de anexos (más portada). Justo en el máximo.
- [x] **Anexos escritos como contenido**, no como índice de punteros: contratos
      completos de las APIs (A), esquema SQL y momentos de escritura (B),
      capturas del tablero (C), salidas crudas de los experimentos (D),
      historial de commits (E) y bitácoras por fase (F).
- [x] Capturas del tablero: normal / advertencia / crítico, tomadas del sistema
      corriendo con carga real inyectada por `POST /ordenes`.
      El cuarto caso —Redis caído— quedó como **traza HTTP medida** en vez de
      captura: el tablero tarda más en renderizar que lo que espera un
      navegador headless, y la evidencia real son los códigos y los tiempos
      (503 en 2,005 s, `/salud` en 200, recuperación en 13 ms).
- [x] Pasar el guion a slides PDF — dos formatos en `presentacion/`.
- [ ] **Elegir uno de los dos formatos** y borrar el otro.
- [ ] **Ensayar cronometrado** (si pasa de 15 min, cortar contenido, no hablar
      más rápido).
- [x] `.zip` del código fuente: se genera con `git archive` (ver README).
- [ ] Prueba de equipo de la Fase 2 (cuestionario de `docs/diseno.md` §6).
- [ ] Prueba de clon limpio en la máquina 2.

## Decisiones tomadas en esta fase

### El informe cuenta la historia por el argumento, no por cronología

El orden del informe no sigue las fases sino el argumento técnico: qué se
construyó → por qué esas decisiones (pull, atómico, espera) → la evidencia
experimental → los límites (errores, resiliencia, dificultades). Las bitácoras
de `docs/fases/` quedan como anexo: son la cronología.

### La tabla central es una sola

La tabla 1→2→3 réplicas (espera por etapa, cuello detectado, lead time) es el
único dato imprescindible de la defensa: demuestra la frase del enunciado.
Todo lo demás la apoya.

## Qué queda

Los pendientes marcados arriba son del equipo (requieren GUI: Overleaf,
capturas, ensayo). El contenido está: informe y guion se alimentan de
`docs/fases/fase-14-experimentos.md` y de las bitácoras anteriores.
