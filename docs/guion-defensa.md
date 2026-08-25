# Guion de la defensa — Caso 2: Línea de producción con balanceo dinámico

Guion hablado para el deck de `presentacion/presentacion_caso2_alt.tex` (21 láminas).
Está escrito para decirse en voz alta, no para leerse en pantalla.

> **Para imprimir y llevar a la defensa:** [`presentacion/guion-defensa.pdf`](../presentacion/guion-defensa.pdf).
>
> Esta versión en Markdown existe para leerla en GitHub. El mismo texto vive en
> `presentacion/guion-defensa.tex`, y **ese es el que manda**: es el que produce el PDF.
> Si hay que corregir algo, se corrige allá, se recompila y después se refleja acá.
> Son dos copias y pueden desincronizarse.

**Duración.** El guion tiene **1.762 palabras** habladas. A 145 palabras por minuto, que
es un ritmo de exposición normal, son **12 minutos**. Con 4 de demo da **16**, o sea
**uno de más**. Hay que ganar ese minuto de una de estas dos formas, y decidirlo en el
ensayo, no en la defensa:

- **Bajar la demo a 3 minutos.** Es lo más fácil: el paso 5 (matar Redis) se puede
  contar en vez de hacerse, porque su evidencia está en el informe.
- **Cortar el cuarto acto** (diapositivas 18 y 19, Resiliencia). Es el contenido menos
  exigido por el caso y sale sin romper el hilo: de la lámina 17 se pasa directo a
  conclusiones.

Los párrafos marcados con **⟨opcional⟩** son los primeros que deben caer si el
cronómetro aprieta. La regla es cortar contenido, nunca hablar más rápido.

**Turnos:** los cuatro actos son los cortes naturales. Una repartición pareja es
Acto I + Acto III para uno, Acto II + Acto IV para el otro, y la demo entre los dos.
Definirlo antes y anotarlo acá.

---

### (Diapositiva 1 — Portada)

> "Hola, profesor. Hoy presentamos el Caso 2: una línea de producción con balanceo
> dinámico de carga. Construimos un sistema distribuido que simula una planta
> conservera, detecta en vivo dónde se está atascando la producción, y responde una
> pregunta concreta: qué pasa con ese atasco cuando uno agrega más máquinas a la etapa
> lenta."

---

### (Diapositivas 2 y 3 — Primer acto: El problema)

> "La planta tiene cuatro etapas en serie: fileteado, envasado, sellado y
> esterilización. La unidad de trabajo es el **lote**, una cantidad de latas del mismo
> formato, y cada lote pasa por las cuatro en orden.
>
> Cada etapa demora algo distinto por lote: cuatro segundos, doce, tres y siete. A ese
> número lo llamamos **tiempo de ciclo**, y es una propiedad de la máquina: la
> autoclave demora siete segundos y no hay cómo apurarla.
>
> Entre etapa y etapa hay una **cola**, que es la fila de lotes esperando su turno. Y
> acá está el concepto central: si a una etapa le llega trabajo más rápido de lo que
> alcanza a procesarlo, su fila crece sin parar. Eso es un **cuello de botella**.
>
> Envasado es la etapa más lenta, así que es la que se **replica**: levantar varias
> copias idénticas funcionando en paralelo para que se repartan el trabajo.
>
> La pregunta del caso es entonces: ¿qué le pasa al cuello de botella cuando escalamos
> la etapa lenta? Les adelanto la respuesta, porque todo lo que viene es la evidencia
> de esta frase: **el cuello no desaparece, se muda.**"

---

### (Diapositivas 4 y 5 — Segundo acto: Arquitectura)

> "Usamos cinco **servicios**. Un servicio es un programa que corre por su cuenta y le
> ofrece algo a los demás por la red, en vez de ser una función dentro del mismo
> programa.
>
> Los agrupamos en tres **nodos lógicos**, y la agrupación no es arbitraria: cada nodo
> junta lo que escala o falla por el mismo motivo. El A le da la cara al operador; el B
> tiene las cuatro estaciones, que es lo único que se multiplica bajo carga; y el C
> concentra el estado compartido, que por ser compartido no se puede duplicar sin
> coordinación. Separar nodos separa dominios de falla: si las estaciones saturan el
> procesador, el operador sigue siendo atendido.
>
> Un detalle del que estamos conformes: las cuatro estaciones son **el mismo programa**.
> No hay un código de fileteado y otro de envasado; la etapa que le toca y su tiempo de
> ciclo le llegan por configuración al arrancar. Todo corre sobre **Docker**, que
> empaqueta cada programa con lo que necesita en una unidad llamada contenedor, de modo
> que funciona igual en cualquier máquina. Por eso levantar el sistema completo es un
> comando y no una lista de pasos de instalación."

---

### (Diapositiva 6 — Balanceo por demanda)

> "¿Cómo se reparte el trabajo entre las réplicas?
>
> Lo habitual es poner un **balanceador** delante: una pieza que recibe cada lote y
> decide a cuál réplica mandárselo. La forma más simple es **round-robin**: por turnos
> fijos y en orden, uno para cada una.
>
> Nosotros lo hicimos al revés, y es una decisión que defendemos. En vez de que alguien
> les asigne trabajo, las réplicas **piden**: cada una toma el siguiente lote de la cola
> compartida cuando queda libre. Nuestro balanceador es la cola.
>
> ¿Por qué es mejor? Porque round-robin es estático: le sigue mandando lotes a una
> réplica lenta al mismo ritmo que a las rápidas. Pidiendo, la réplica lenta
> simplemente pide menos veces. El balanceo se adapta solo, y más adelante mostramos el
> experimento que lo mide."

---

### (Diapositiva 7 — Condición de carrera)

> "Pero pedir de una cola compartida abre un riesgo, y es el problema central del caso.
>
> Si dos réplicas piden al mismo tiempo, el lote se lo tiene que llevar exactamente
> una. Cuando el resultado depende de cuál llegó primero, eso es una **condición de
> carrera**.
>
> La provocamos a propósito antes de resolverla, y las dos versiones quedaron en el
> historial de commits. La versión ingenua reclama en dos pasos: primero mira cuál es
> el próximo lote, después lo saca. Entre el paso uno y el paso dos el lote sigue en la
> cola, así que otra réplica que mire en ese instante ve el mismo. Ensanchamos esa
> ventana hasta reproducir duplicados: con tres réplicas y cien pedidos, la planta
> envasaba trescientos lotes. El triple de materia prima.
>
> La solución no fue ponerle un candado con expiración, que es lo clásico. Usamos una
> **operación atómica**: una operación que ocurre entera o no ocurre, sin ningún
> instante intermedio en que otro pueda ver el sistema a medio hacer. **Redis**, la
> base de datos en memoria que usamos como cola, atiende sus comandos de uno en uno, así
> que sacar un lote es indivisible por construcción.
>
> La diferencia conceptual es la que nos importa: un candado **administra** la ventana
> de riesgo; la operación atómica la **elimina**. Con ella medimos cero duplicados en
> doscientas órdenes."

---

### (Diapositiva 8 — El criterio de cuello de botella)

> "Antes de los resultados hay que definir cómo decidimos dónde está el atasco, porque
> no hay una definición única y es la decisión técnica más importante que tomamos.
>
> Hay dos tiempos que distinguir. El **tiempo de servicio** es lo que la etapa demora
> procesando un lote que ya tiene en la mano. El **tiempo de espera** es lo que el lote
> pasa haciendo fila antes de que lo tomen.
>
> La analogía es el supermercado: un cajero lento no es un atasco. El atasco es la fila
> que crece frente a su caja.
>
> Nuestro criterio mide **espera, no servicio**. El cuello es la etapa con mayor espera
> promedio sobre una **ventana móvil** de sesenta segundos —mirando solo el último
> minuto, para que una congestión vieja y ya resuelta no contamine el diagnóstico de
> ahora— comparada contra umbrales relativos al ciclo de cada etapa: vez y media es
> advertencia, tres veces es crítico.
>
> Y no es una sutileza. Con dos réplicas, envasado sigue teniendo el ciclo más largo de
> la línea y **no** es el cuello. Midiendo servicio, el detector habría señalado
> envasado para siempre y nunca habríamos visto el fenómeno que veníamos a estudiar."

---

### (Diapositivas 9 y 10 — Demo en vivo, ~4 minutos)

> "Vamos a mostrarlo funcionando. Esto está corriendo de verdad: dos réplicas de
> envasado y las otras tres etapas."

**Guion de la demo:**

1. **La línea al día.** Mostrar las cuatro etapas, las réplicas con su ciclo y su carga,
   y el cartel verde.
2. **Ingresar lotes** desde el panel izquierdo, **espaciados unos cinco segundos**.
   > ⚠️ No inyectar muchos de golpe: se apilan en la primera cola y el tablero marca
   > fileteado como el atasco — correctamente, pero es la respuesta a otra pregunta.
   > Si alguien lo nota, explicar exactamente eso.
3. **Ver crecer la espera** de esterilización. El cartel pasa de verde a ámbar y luego a
   rojo.
   > "Fíjense que el cartel no dice solo 'hay un problema': nombra la etapa, dice
   > cuántos lotes hacen cola y da el número. Ese diagnóstico viene del servicio de
   > métricas; el tablero solo lo muestra."
4. **La condición de carrera, en vivo.** Bajar y apretar «Ejecutar la comparación».
   > "Esto corre el experimento ahora: encola los mismos lotes dos veces, una con cada
   > versión del reclamo. Con cien pedidos, la ingenua envasa trescientos y la atómica
   > cien. Y es **el mismo código** que corre en las estaciones: las dos funciones se
   > importan del mismo módulo, no hay una copia para la demo que pueda quedar
   > desactualizada. Usa una cola aparte, así que la línea de arriba sigue produciendo."
5. **Matar Redis.** Detener el contenedor, mostrar que la interfaz nombra al servicio
   caído sin un error críptico, y volver a levantarlo.

> *Plan B si algo falla: las capturas están en los anexos del informe.*

---

### (Diapositivas 11 y 12 — Tercer acto: la aritmética del escenario)

> "Los experimentos. Todos reproducibles y con sus datos crudos versionados.
>
> El escenario es siempre el mismo: una orden cada cinco segundos durante tres minutos,
> o sea doce lotes por minuto entrando.
>
> Este gráfico es la aritmética de capacidad, y lo mostramos **antes** de los resultados
> a propósito, porque los predice. Cada barra es cuántos lotes por minuto puede sacar
> cada etapa; la línea punteada son los doce que llegan. Toda etapa bajo esa línea
> acumula fila tarde o temprano.
>
> Envasado con una réplica saca cinco. Con dos sube a diez: mejor, pero todavía
> insuficiente. Y ahí aparece esterilización con ocho coma seis, que queda como el
> siguiente límite. La figura ya anticipa el resultado."

---

### (Diapositiva 13 — El resultado central)

> "Esto es lo que medimos: la espera promedio de las cuatro etapas, con una, dos y tres
> réplicas de envasado.
>
> Con **una** réplica, envasado acumula sesenta y siete coma ocho segundos de espera y
> el resto de la línea está casi ociosa.
>
> Con **dos**, el cuello **se desplaza a esterilización**. Y ojo con esto:
> esterilización no cambió nada, sigue demorando siete segundos por lote. Lo que cambió
> es que ahora le llega trabajo más rápido de lo que puede sacarlo, porque envasado
> dejó de ser el freno.
>
> Con **tres**, envasado queda sobrado, con menos de un segundo de espera… y el cuello
> sigue en esterilización. Ahí está la respuesta: el cuello no se eliminó. Se mudó."

---

### (Diapositiva 14 — Cuánto compra cada réplica)

> "La pregunta del jefe de planta es cuánto le compró esa inversión. Para eso está el
> **lead time**: el tiempo total de punta a punta, desde que se crea la orden hasta que
> el lote sale terminado. Suma todas las esperas y todos los ciclos del recorrido.
>
> La segunda réplica compra un veintiuno por ciento de mejora. La tercera,
> prácticamente nada.
>
> Y esa es la conclusión útil: la siguiente inversión correcta no es una tercera
> envasadora, es **una segunda autoclave**. El tablero responde eso en vivo, que es para
> lo que sirve medir."

---

### (Diapositiva 15 — Balanceo con una réplica lenta)

> "Este experimento prueba que el balanceo es dinámico de verdad.
>
> Tres réplicas de envasado sobre la misma cola, pero una configurada al doble de lenta,
> y treinta lotes.
>
> Un round-robin habría entregado diez, diez y diez sin mirar la velocidad de nadie. Lo
> que medimos fue **once, doce y siete**: la lenta procesó un cuarenta por ciento menos.
>
> Nadie programó esa proporción, profesor. No hay una línea de código que diga 'dale
> menos a la lenta'. Salió sola de que cada réplica pide trabajo únicamente cuando queda
> libre. Eso es lo que hace que el balanceo sea dinámico: proporcional a la capacidad
> real de cada máquina, no a un turno preestablecido."

---

### (Diapositiva 16 — Saturación y recuperación)

> "El último experimento fue meterle una ráfaga de veinticinco órdenes de golpe.
>
> A los treinta y dos segundos el sistema **se declara crítico solo**.
>
> ⟨opcional⟩ Y se ve algo bonito: la congestión recorre la línea como una ola, aparece
> en la etapa de entrada y se propaga aguas abajo.
>
> A los doscientos setenta y ocho vuelve todo a normal **sin intervención**. Es
> consecuencia directa de la ventana móvil: las esperas viejas salieron del último
> minuto. El sistema no se 'arregló'; dejó de estar congestionado y la métrica lo
> reflejó."

---

### (Diapositiva 17 — Robustez)

> "Tres cosas que sostienen todo lo demás.
>
> **Errores.** Al matar Redis, el servicio de órdenes responde en dos segundos
> nombrando al servicio que falta. ⟨opcional⟩ Antes se colgaba cuarenta y seis: le
> habíamos puesto un límite de tiempo, pero el cuelgue estaba en la resolución del
> nombre y no en la conexión, y ese límite no lo cubría.
>
> **Persistencia.** Guardamos en **SQLite**, una base de datos que vive en un solo
> archivo. Dos tablas: órdenes y eventos. Los tiempos **no se guardan**, se calculan
> desde los eventos — el dato guardado dos veces es el que termina contradiciéndose.
>
> **Despliegue.** Un comando levanta todo desde cero, probado clonando en una carpeta
> vacía: ocho de ocho contenedores sanos."

---

### (Diapositivas 18 y 19 — Cuarto acto: Resiliencia)

> "El caso no pedía tolerancia a fallos y deliberadamente no la implementamos: el
> sistema **detecta y explica** las fallas en vez de disimularlas. Pero sabemos dónde
> iría cada pieza.
>
> Las **estaciones** no tienen estado propio: mueren sin corromper nada. Falta
> re-encolar el lote en curso si una muere a la mitad. **Redis** es el punto único de
> falla del reparto: ahí iría una réplica de respaldo. Y **SQLite** aguanta esta carga,
> pero con más escritores habría que migrar, y eso toca un solo módulo.
>
> Lo que queremos destacar: ninguna de esas mejoras obliga a rediseñar las otras. Para
> eso servía haber dividido el sistema en nodos desde el principio."

---

### (Diapositivas 20 y 21 — Conclusiones y cierre)

> "Para cerrar, cinco frases, todas medidas.
>
> **El cuello de botella no se elimina, se muda:** de envasado a esterilización al pasar
> de una a dos réplicas.
>
> **Medir espera en vez de servicio es lo que permite verlo:** el cuello real tenía un
> ciclo más corto que envasado.
>
> **El balanceo dinámico emerge del mecanismo:** once, doce y siete con una réplica
> lenta, sin que nadie asignara ese reparto.
>
> **La condición de carrera se elimina, no se administra:** cero duplicados en
> doscientas órdenes.
>
> **Las fallas se explican, no se enmascaran:** un error claro en dos segundos, en vez
> de cuarenta y seis de silencio.
>
> Si me quedo con una sola idea de todo el proyecto, profesor, es esta: **agregar
> máquinas no elimina el cuello de botella, lo traslada.** Por eso lo que hay que
> construir no es una línea más rápida, sino una línea que sepa decirte dónde se está
> atascando ahora mismo. Sin eso, uno invierte a ciegas.
>
> Muchas gracias."

---

## Preguntas probables

**¿Dónde está el balanceador?**
Es la cola compartida: el punto único por el que pasa todo el trabajo y que decide quién
procesa qué. Elegimos reparto por demanda porque un balanceador clásico no es dinámico —
le sigue mandando trabajo a la réplica lenta. El experimento de la réplica lenta lo
muestra adaptándose solo.

**¿Y el lock o contador distribuido?**
Lo cubre el mismo mecanismo. La extracción atómica de Redis es un candado implícito por
elemento, porque Redis atiende sus comandos de uno en uno. Un candado explícito con
expiración habría *administrado* la ventana de carrera; la extracción atómica la
*elimina*. Y lo demostramos: dos pasos da duplicados, un paso da cero en doscientas.

**¿Por qué el cuello es esterilización si envasado es más lento (12 s contra 7 s)?**
Porque con dos réplicas el tiempo efectivo de envasado es de unos seis segundos por lote.
Y en general el cuello no es la etapa de mayor ciclo sino la de mayor espera: la que
recibe trabajo más rápido de lo que puede drenarlo.

**¿Qué pasa si una réplica muere a mitad de un lote?**
Ese lote ya salió de la cola y se pierde de la línea. Es una limitación conocida y
aceptada, porque el caso excluía tolerancia a fallos. Sabemos el camino: mover el lote a
una cola «en proceso» en vez de sacarlo, y un barrendero que lo devuelva al detectar que
la réplica dejó de dar señales.

**¿Por qué SQLite y no un motor con servidor?**
Un solo nodo de estado, escrituras cortas, y cero infraestructura extra que administrar
en la demo. Lo estresamos en el experimento de la réplica lenta y encontramos su límite,
que está documentado. El cambio a otro motor toca un solo módulo si hiciera falta.

**¿Cómo saben que las métricas son correctas?**
Los tiempos de servicio que medimos coinciden con los ciclos configurados —cuatro coma
ocho, doce coma cuatro, tres coma cuatro y siete coma tres, contra cuatro, doce, tres y
siete—. La instrumentación se valida sola. Y todo se calcula desde la tabla de eventos,
así que no hay un segundo lugar que pueda contradecirla.

**¿Por qué la espera se mide contra la entrada a cada cola y no contra la creación de la
orden?**
Porque con cuatro etapas en serie, medir contra la creación le cargaría a sellado todo lo
que pasó antes en fileteado y envasado, y señalaría al culpable equivocado. Cada etapa
responde solo por su propia cola.
