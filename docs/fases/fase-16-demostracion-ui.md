# Fase 16 — La demostración de la carrera dentro del tablero

**Estado: CERRADA (23/08/2026)**

## Objetivo

Que la condición de carrera de la Fase 6 —el resultado central del proyecto— se
pueda ver en la interfaz, comparada lado a lado, sin salir a la terminal ni
reiniciar la línea. Y que evaluar el proyecto no exija saber Docker.

## Por qué hacía falta

Hasta la Fase 15 la evidencia de la Fase 6 existía solo como
`experimentos/fase6_carrera.sh`: un script de bash que en Windows hay que correr
desde WSL o Git Bash, que exige levantar la línea con `MODO_RECLAMO=ingenuo`,
correrlo, volver a levantarla con `MODO_RECLAMO=atomico` y correrlo de nuevo,
comparando dos salidas de texto separadas por varios minutos.

Es reproducible, pero no es demostrable: en una defensa de 15 minutos nadie va a
ver esos dos números juntos. Y el tablero —que es lo que el evaluador mira— no
decía nada del problema que el sistema resuelve. Mostraba que la línea funciona,
no **por qué** se puede confiar en que funciona.

## Qué se logró

- [x] Sección nueva al final del tablero: **«Por qué la línea no produce el
      mismo lote dos veces»**. Contexto en castellano, los dos reclamos
      enfrentados paso por paso, y un botón que corre la comparación.
- [x] Gráfico de dos paneles con **eje Y compartido**: cuántos lotes se
      procesaron una vez, dos, tres, en cada modo.
- [x] Dos tarjetas de veredicto con el número que tiene consecuencia física:
      lotes envasados contra lotes pedidos.
- [x] Las funciones de reclamo movidas a `servicios/comun/reclamo.py`,
      importadas tanto por `estacion/worker.py` como por `ui/carrera.py`.
- [x] `INICIAR.bat` / `DETENER.bat` / `iniciar.sh`: arranque de un clic.
- [x] Resultado medido en el tablero (100 lotes, 3 máquinas): **300
      procesamientos con el reclamo ingenuo contra 100 con el atómico**, con
      los 100 lotes duplicados 3 veces en el primer caso y 0 en el segundo.
      Reproduce exactamente la proporción medida en la Fase 6 con contenedores
      (598/200), que es la comprobación de que la demostración no miente.

## Decisiones tomadas en esta fase

### El código de reclamo se comparte, no se copia

La demostración podía haberse escrito con su propia versión de las dos
funciones: son diez líneas cada una. No se hizo, y es la decisión importante de
la fase. Una copia probaría la copia. Bastaría con editar una de las dos para
que el tablero siguiera mostrando "cero duplicados" mientras la planta los
produce — el peor fallo posible en una herramienta cuyo propósito es dar
confianza.

Costo: las imágenes de `estacion` y `ui` ya no se construyen desde su propia
carpeta sino desde `servicios/`, con `dockerfile:` explícito y un
`.dockerignore` para no arrastrar los `.pyc`. Es más ceremonia en el compose a
cambio de que la demostración signifique algo.

### Hilos en vez de contenedores, y decirlo

Los competidores de la demostración son hilos del proceso del tablero, no
contenedores. Levantar tres contenedores por modo tomaría minutos y exigiría
darle al tablero acceso al socket de Docker, que es una puerta que no se abre
por una demo.

El argumento de por qué sigue siendo válido: lo que la carrera necesita no es
que los competidores sean procesos distintos, sino que sean **concurrentes
sobre la misma cola**. Durante el `LRANGE`, la pausa y el `LREM`, cada hilo está
esperando a la red y no ocupando el intérprete, así que compiten igual. La
prueba de que el argumento se sostiene es empírica: la proporción de duplicados
es la misma que midió la Fase 6 con contenedores reales. La versión con
contenedores se conserva y el tablero la menciona.

### El color sale del resultado, no del modo

La tarjeta del reclamo atómico se pinta verde porque midió cero duplicados, no
porque sea el modo bueno. Si alguna vez produjera uno, se pondría roja sola. Un
tablero que solo sabe confirmar lo que espera no sirve para comprobar nada.

### La sección va al final y separada

El tablero se lee de arriba a abajo por urgencia (cartel → números → línea →
gráfico). La demostración no se monitorea, se ejecuta a pedido: es de otra
naturaleza y va después de un separador. Quien solo quiere ver la producción no
baja hasta ahí; quien pregunta "¿cómo sé que dos máquinas no toman el mismo
lote?" encuentra la respuesta ejecutable.

## Principales dificultades

1. **El experimento tenía que terminar solo.** Las réplicas de verdad corren
   para siempre; las de la demostración tienen que darse por terminadas cuando
   la cola se vacía. Con una sola lectura vacía era frágil: una réplica puede
   mirar justo en el hueco entre que otra saca un lote y termina de procesarlo,
   y darse por terminada con trabajo todavía en curso. Se resolvió exigiendo
   tres lecturas vacías consecutivas (`VACIAS_PARA_TERMINAR`), y bajando el
   timeout del `BRPOP` a 0,5 s solo para la demo: en producción son 2 s, y
   esperar dos segundos por réplica al final de cada corrida se notaba.

2. **Compartir código entre dos imágenes Docker no es gratis.** El primer
   intento fue copiar `comun/` con una ruta relativa hacia arriba
   (`COPY ../comun`), que Docker rechaza: nada fuera del contexto de build es
   accesible. Había que subir el contexto a `servicios/` y nombrar el
   Dockerfile explícitamente, lo que a su vez metía los `__pycache__` de
   ejecuciones locales en el contexto e invalidaba la caché de capas sin
   motivo. De ahí el `.dockerignore`.

3. **Dos gráficos con escala propia no son una comparación.** La primera
   versión dibujaba cada modo con su eje Y independiente: los dos paneles se
   veían igual de llenos y la diferencia —que es de cantidad, no de forma—
   desaparecía por completo. Compartir el eje Y es lo que convierte dos
   gráficos en una comparación. Lección que aplica más allá de este gráfico.

4. **Verificar la refactorización destapó un defecto en la evidencia de la
   Fase 6.** Después de mover las funciones de reclamo al módulo compartido se
   volvió a correr `fase6_carrera.sh` para comprobar que nada se hubiera roto,
   y el modo atómico reportó 3 duplicados. No los había: `conteo:procesadas`
   era un hash único que incrementaban las cuatro estaciones con el mismo
   `orden_id`, así que el avance normal de un lote por la línea se leía como
   duplicación. El contador pasó a ser por etapa
   (`conteo:procesadas:<etapa>`) y el script ahora vacía las cinco colas antes
   de medir. Está documentado al final de `fase-6-carrera.md`, con la medición
   repetida.

   Lo incómodo del hallazgo: el resultado original de la Fase 6 era correcto
   **por suerte** —con 200 órdenes casi ninguna alcanzaba a salir de sellado
   antes de la lectura— y nadie lo habría notado sin repetir el experimento en
   condiciones distintas. La demostración del tablero no tiene este problema
   porque cuenta en memoria y su cola no desemboca en ninguna otra etapa, pero
   el script sí lo tenía y es el que va como evidencia reproducible.

5. **El `.bat` tenía que fallar bien.** Un arranque de un clic que se cierra
   solo cuando algo sale mal es peor que no tenerlo, porque no deja rastro de
   qué pasó. Cada punto de fallo del script deja la ventana abierta con el
   motivo y el siguiente paso: Docker no instalado, Docker Desktop que no
   arranca (con el puntero a la fase 0 por lo de WSL2 y la BIOS), puerto
   ocupado, tablero que tarda de más.

## Qué queda para la siguiente fase

Vuelve a **Fase 15**: la sección nueva entra en el informe como parte de la
evidencia de la Fase 6, y en la defensa reemplaza al plan B de la lámina 8 —
ahora la demostración de la carrera es un clic y no depende de que la terminal
coopere. Falta la captura de la sección para los anexos.
