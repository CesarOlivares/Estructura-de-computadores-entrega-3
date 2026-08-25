# Presentación de la defensa

Dos formatos de la misma charla, con el mismo contenido y las mismas figuras.
Hay que **elegir uno** antes de la defensa; el otro se borra.

| Archivo | Formato | Láminas |
|---|---|---|
| [`presentacion_caso2.tex`](presentacion_caso2.tex) | **A** — minimalista continuo | 17 |
| [`presentacion_caso2_alt.tex`](presentacion_caso2_alt.tex) | **B** — editorial por actos | 21 (5 son divisorias) |

## En qué se diferencian

**Formato A.** Láminas seguidas, sin cortes. Título en versalitas con filete de
acento, tres o cuatro viñetas por lámina. Es más denso: cabe más argumento por
lámina, pero exige que el que expone lleve el ritmo.

**Formato B.** La charla está partida en cuatro actos más un interludio de demo,
cada uno anunciado por una lámina a fondo tinta. Titulares en caja mixta con
tipografía Light, antetítulo espaciado, y una franja «clave» al pie de cada
lámina con la frase que hay que decir en voz alta. Menos texto por lámina.

Las divisorias del formato B llevan una línea **«Expone: …»**. La rúbrica evalúa
*Participación del equipo* («todos los integrantes exponen equilibradamente»), y
tenerlo escrito evita que en la defensa uno se coma el turno del otro. El reparto
que está escrito es una propuesta — cámbienlo si prefieren otro.

Ninguno de los dos numera los temas. El formato A lo hacía y la numeración no
coincidía con la del pie de página, porque contaba temas y no láminas.

## Compilar

Ambos necesitan **XeLaTeX** (usan `fontspec`). La primera línea de cada archivo
ya lo declara con `%!TEX program = xelatex`.

### Local

```bash
cd presentacion
xelatex presentacion_caso2_alt.tex
xelatex presentacion_caso2_alt.tex   # segunda pasada, para el total de láminas
```

Requiere MiKTeX o TeX Live con `beamer`, `fontspec`, `babel-spanish`, `tikz` y
`booktabs`.

### Overleaf

**New Project → Upload Project**, y subir `presentaciones-overleaf.zip`
(o el repositorio completo). Después, **Menú → Compiler → XeLaTeX**.

## Sobre las tipografías

El diseño se hizo con las fuentes de Windows: **Segoe UI Light** para los
titulares, **Segoe UI Semibold** para los antetítulos y **Bahnschrift** para las
cifras grandes. Overleaf no las tiene, y sin previsión caería todo a Latin
Modern, que arruina el diseño.

Por eso el bloque de tipografía de ambos archivos es una cascada de tres
niveles, que se resuelve sola según dónde se compile:

1. Segoe UI + Bahnschrift — las de Windows, el diseño original.
2. **Lato** (tiene Light y Semibold) + **Roboto Condensed** — libres, incluidas
   en TeX Live completo, que es lo que corre Overleaf.
3. Las genéricas de LaTeX, para que la compilación nunca falle por una fuente
   que falta.

No hay que instalar ni subir ningún archivo de fuente: los paquetes `lato` y
`roboto` ya están en Overleaf. Tampoco se pueden versionar las de Microsoft en
un repositorio público, que es la otra razón para la cascada.

## Figuras

Las seis figuras salen de `informe/figuras/`, generadas por
`informe/figuras/generar_figuras.py` a partir de los datos crudos de
`experimentos/resultados/`. No se editan a mano: si cambia un experimento, se
vuelve a correr el script.

El `\graphicspath` de ambos archivos busca en `../informe/figuras/`,
`informe/figuras/` y `figuras/`, así que compilan igual desde esta carpeta,
desde la raíz del repositorio o desde un proyecto de Overleaf aplanado.
