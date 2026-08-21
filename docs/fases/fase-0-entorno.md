# Fase 0 — Entorno y repositorio (máquina 2)

> Bitácora de fase. Convención del equipo: cada fase deja un `.md` con lo logrado,
> las principales dificultades y lo pendiente para la siguiente fase.
> La Fase 0 se hace una vez por máquina; esta bitácora corresponde a la segunda
> máquina del equipo (laptop Lenovo, Windows 11, disco C: de 119 GB + D: de 930 GB).

**Estado: CERRADA (21/08/2026)** — con un pendiente diferido no bloqueante
(usuario de Ubuntu; ver dificultad #6).

---

## Objetivo

Dejar la máquina capaz de correr el proyecto: Docker + Docker Compose funcionando
sobre WSL2, git configurado con la identidad del integrante, y el repositorio del
proyecto clonado desde GitHub.

## Qué se logró

- [x] Verificada la virtualización en firmware: **ya venía habilitada** (a diferencia
      de la máquina 1, donde hubo que activar `SVM Mode` en la BIOS).
- [x] Motor WSL2 presente (versión 2.4.13, kernel 5.15), versión predeterminada 2.
- [x] Diagnóstico y liberación de espacio en C:: de **0 GB libres a 18 GB** sin
      tocar ninguna herramienta en uso (ver dificultad #1).
- [x] Ubuntu instalado en `D:\WSL\Ubuntu` con `wsl --install -d Ubuntu --location`,
      para no cargar el disco C:. Arranca y ejecuta comandos (verificado).
- [ ] ~~Usuario Linux creado~~ **Diferido** (no bloqueante; ver dificultad #6).
- [x] Docker Desktop 4.87 instalado con programa en `D:\Docker\App` y datos de WSL
      en `D:\Docker\wsl` (`--installation-dir` y `--wsl-default-data-root`);
      disco del motor verificado en D: (1,7 GB).
- [x] `docker run hello-world` responde ("Hello from Docker!") y
      `docker compose version` → v5.4.0.
- [x] Identidad de git configurada; commits verificados como atribuidos a la
      cuenta de GitHub del integrante.
- [x] Repositorio clonado con historial. Se agregaron los commits
      `chore: initialize repository` (README, .gitignore, bitácoras) y
      `demo: throwaway queue prototype` (la demo de la Fase 1, que faltaba
      en el repositorio).

## Principales dificultades

1. **Disco C: completamente lleno (0 bytes libres).** `wsl --install` falló con
   `0x80070070` ("Espacio en disco insuficiente"). El diagnóstico por carpetas
   reveló que el mayor consumo no era basura del sistema sino **instaladores de
   Autodesk Inventor descargados cuatro veces** (`Downloads\Autodesk`, 8,5 GB) más
   la carpeta de extracción del instalador (`C:\Autodesk`, 6,2 GB) y restos
   huérfanos de aplicaciones ya desinstaladas (Roblox, 2,9 GB). Borrar solo eso
   liberó ~18 GB sin desinstalar nada en uso.
   *Lección: antes de borrar por volumen, medir por carpeta y distinguir
   instalador ≠ programa instalado ≠ datos de usuario.*

2. **Registro de WSL corrupto por la instalación fallida.** El intento posterior a
   liberar espacio falló con `0x8000000d`: "hay una instalación en curso para esta
   distribución". La instalación que murió por disco lleno dejó a Ubuntu atascado
   en estado `Installing`. Se resolvió con `wsl --shutdown` (que limpió el registro
   pendiente) y reintentando. *Lección: una instalación interrumpida puede dejar
   estado colgado que bloquea los reintentos; el error ya no describe la causa
   original sino el síntoma heredado.*

3. **`wsl --install` no trae ninguna distribución por defecto** — la misma trampa
   documentada en la máquina 1. Verlo repetirse en un segundo equipo confirma que
   es comportamiento de la herramienta, no un accidente: el motor WSL2 se instala
   solo, y Ubuntu hay que pedirlo explícitamente.

4. **La instalación estándar asume que todo cabe en C:.** Con un C: de 119 GB y un
   D: de 930 GB casi vacío, la solución no fue vaciar C: sino **redirigir lo pesado
   a D:**: la distro con `--location` (soportado desde WSL 2.4.4) y los datos de
   Docker (imágenes y contenedores, lo que realmente crece) con
   `--wsl-default-data-root` del instalador de Docker Desktop.

5. **Ubuntu instalado pero incapaz de arrancar (`E_UNEXPECTED`).** Tras la
   instalación, todo intento de arranque fallaba con "Error catastrófico",
   incluso no interactivo y tras reiniciar el servicio. Se descartó la consola
   (falló igual en PowerShell directo) y el disco (D: es NTFS). La causa era la
   versión de WSL (2.4.13, antigua): al actualizar a 2.7.12 con `wsl --update`,
   el arranque quedó corregido de inmediato. *Lección: ante un error opaco del
   runtime, actualizar la plataforma antes de reinstalar el contenido.*

6. **El asistente de primer arranque de Ubuntu no es apto para sesiones no
   interactivas.** El aprovisionamiento inicial quedó esperando indefinidamente
   la creación del usuario, entrada que una sesión en segundo plano no puede
   entregar. Como Docker Desktop trae su propia distro (`docker-desktop`) y el
   proyecto entero corre sobre Docker, **el usuario de Ubuntu se difirió**: es
   una comodidad (terminal Linux de trabajo), no un requisito. Se creará cuando
   haga falta con una sesión interactiva real (abrir "Ubuntu" desde el menú
   Inicio).

## Decisiones tomadas en esta fase

- **Ubuntu y datos de Docker en D:, no en C:** — por espacio (ver dificultad #4).
- **Convención de bitácoras por fase** (este archivo es la primera): cada fase deja
  `docs/fases/fase-N-nombre.md` con lo logrado, dificultades y pendientes, más
  evidencias (capturas, salidas de comandos) en `docs/fases/evidencias/fase-N/`.
  El código NO se duplica por fase: su historia la lleva git, un commit por fase
  verificada.

## Qué queda para la siguiente fase

Al cerrar esta fase (checklist de arriba completo), esta máquina queda al día con
la máquina 1, donde las Fases 0 y 1 ya están verificadas. **La siguiente fase del
proyecto es la Fase 2 — Diseño en papel**: contratos de las tres APIs, esquema de
las tablas `ordenes` y `eventos`, y criterio de cuello de botella, todo en
`docs/diseno.md`. No se escribe código de servicios hasta cerrar ese documento.

(El pendiente administrativo del correo al profesor quedó descartado el
21/08/2026 por decisión del equipo.)
