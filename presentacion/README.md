# Presentación de la defensa

Dos formatos de la misma charla, con el mismo contenido y las mismas figuras.
Hay que **elegir uno** antes de la defensa; el otro se borra.

| Formato | Fuente | PDF | Láminas |
|---|---|---|---|
| **A** — minimalista continuo | [`presentacion_caso2.tex`](presentacion_caso2.tex) | [`presentacion_caso2.pdf`](presentacion_caso2.pdf) | 17 |
| **B** — editorial por actos | [`presentacion_caso2_alt.tex`](presentacion_caso2_alt.tex) | [`presentacion_caso2_alt.pdf`](presentacion_caso2_alt.pdf) | 21 (5 son divisorias) |

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

Requiere MiKTeX o TeX Live con `beamer`, `fontspec`, `babel-spanish`, `tikz`,
`booktabs`, `lato` y `roboto`. En MiKTeX conviene dejar la instalación
automática de paquetes activada, o la primera compilación se queda esperando
una respuesta:

```bash
initexmf --set-config-value "[MPM]AutoInstall=1"
```

### Overleaf

**New Project → Upload Project**, y subir `presentaciones-overleaf.zip`
(o el repositorio completo). Después, **Menú → Compiler → XeLaTeX**.

## Sobre las tipografías

El texto usa **Segoe UI**, con **Light** en los titulares y **Semibold**
espaciado en los antetítulos. Overleaf no tiene las fuentes de Microsoft, y sin
previsión caería todo a Latin Modern, que arruina el diseño. Por eso el bloque
de tipografía de ambos archivos es una cascada que se resuelve sola según dónde
se compile:

1. **Segoe UI** Light / Semibold — Windows, el diseño original.
2. **Lato** — libre, tiene Light y Semibold, y viene en TeX Live completo, que
   es lo que corre Overleaf.
3. Las genéricas de LaTeX, para que la compilación nunca falle por una fuente
   que falta.

No hay que instalar ni subir ningún archivo: el paquete `lato` ya está en
Overleaf. Tampoco se podrían versionar las de Microsoft en un repositorio
público, que es la otra razón para la cascada.

### Por qué las cifras grandes no usan Bahnschrift

La condensada es **Roboto Condensed**, del árbol de TeX Live, y **sin
alternativa de Windows a propósito**.

Bahnschrift es la condensada natural en Windows y es la que usaba el formato A,
pero es una **fuente variable**: un solo archivo con todos los pesos dentro.
`dvipdfmx` no sabe incrustarla — la lee como si fuera una colección TTC y aborta
con `Invalid TTC index` / `Invalid font: -1 (17)`. Compilaba en la máquina donde
se generó el primer PDF y fallaba en la otra, que es la peor clase de
dependencia oculta.

Roboto Condensed es estática, da el mismo aire DIN, y al venir del árbol de TeX
Live sale idéntica en las dos máquinas y en Overleaf.

## Figuras

Las seis figuras salen de `informe/figuras/`, generadas por
`informe/figuras/generar_figuras.py` a partir de los datos crudos de
`experimentos/resultados/`. No se editan a mano: si cambia un experimento, se
vuelve a correr el script.

El `\graphicspath` de ambos archivos busca en `../informe/figuras/`,
`informe/figuras/` y `figuras/`, así que compilan igual desde esta carpeta,
desde la raíz del repositorio o desde un proyecto de Overleaf aplanado.
