# Fase 0 — Entorno y repositorio (máquina 2)

> Bitácora de fase. Convención del equipo: cada fase deja un `.md` con lo logrado,
> las principales dificultades y lo pendiente para la siguiente fase.
> La Fase 0 se hace una vez por máquina; esta bitácora corresponde a la segunda
> máquina del equipo (laptop Lenovo, Windows 11, disco C: de 119 GB + D: de 930 GB).

**Estado: EN CURSO** (actualizar al cerrar la fase)

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
      para no cargar el disco C:. *(pendiente de verificar al cierre)*
- [ ] Usuario Linux creado en el primer arranque de Ubuntu.
- [ ] Docker Desktop instalado con programa en `D:\Docker\App` y datos de WSL en
      `D:\Docker\wsl` (`--installation-dir` y `--wsl-default-data-root`).
- [ ] `docker run hello-world` responde y `docker compose version` ≥ v2.
- [ ] Identidad de git configurada (`user.name`, `user.email`).
- [ ] Repositorio clonado con historial (no el ZIP descargado de GitHub).

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

Pendiente administrativo que sigue abierto: correo al profesor (confirmar Caso 2
para el Grupo 2, autorización del grupo de 2 personas, respaldo por escrito).
