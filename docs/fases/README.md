# Bitácoras por fase

Convención del equipo: **cada fase deja una bitácora** en esta carpeta, escrita al
cerrar la fase (o durante, si es larga). Sirven de insumo directo para el informe
(análisis crítico de dificultades, 15 pts de rúbrica) y para la defensa.

## Reglas

- Un archivo por fase: `fase-N-nombre.md` (ej: `fase-2-diseno.md`).
- Evidencias (capturas, salidas de comandos, tablas medidas) en
  `evidencias/fase-N/`, referenciadas desde la bitácora.
- El **código no se duplica por fase**: vive en su estructura normal
  (`servicios/`, `demo/`) y su historia la lleva git — un commit por fase
  verificada, según la convención de commits del proyecto.
- Distinguir siempre: requisito del enunciado / decisión nuestra / supuesto.

## Plantilla

```markdown
# Fase N — Nombre

**Estado: EN CURSO | CERRADA (fecha)**

## Objetivo
Qué debía lograr esta fase, en una o dos líneas.

## Qué se logró
Checklist contra el criterio de aprobación de la fase.

## Principales dificultades
Cada una con: síntoma, causa encontrada, cómo se resolvió, lección.
(Esto alimenta el análisis crítico del informe — ser específicos.)

## Decisiones tomadas en esta fase
Solo las decisiones nuevas, con su justificación corta.

## Qué queda para la siguiente fase
Pendientes concretos y cuál es la fase que sigue.
```
