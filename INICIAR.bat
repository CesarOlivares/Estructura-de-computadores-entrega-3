@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Linea de produccion - ECSD Caso 2

rem ===========================================================================
rem  Arranque de un clic para la linea de produccion completa.
rem
rem  Existe para que evaluar el proyecto no exija saber Docker: doble clic aqui
rem  y el navegador termina abierto en el tablero. Hace, en orden, lo mismo que
rem  haria alguien a mano:
rem
rem     1. comprobar que Docker esta instalado
rem     2. arrancar Docker Desktop si el motor no esta corriendo, y esperarlo
rem     3. docker compose up -d --build
rem     4. esperar a que el tablero pase a "healthy"
rem     5. abrir http://localhost:8501
rem
rem  Cualquier fallo deja la ventana abierta con el motivo y que hacer. Los
rem  comandos equivalentes estan en el README: esto no reemplaza saberlos, solo
rem  evita tener que teclearlos.
rem ===========================================================================

rem Ejecutar siempre desde la carpeta del repositorio, sin importar desde donde
rem se haya invocado el .bat (al hacer doble clic, %~dp0 es esa carpeta).
cd /d "%~dp0"

echo.
echo   LINEA DE PRODUCCION - Conservera de jurel
echo   Estructura de Computadores, Evaluacion 3 - Caso 2
echo   ---------------------------------------------------------------
echo.

rem --- 1. ¿Esta Docker instalado? --------------------------------------------
where docker >nul 2>&1
if errorlevel 1 (
    echo   [X] No se encontro Docker.
    echo.
    echo   Instala Docker Desktop desde https://www.docker.com/products/docker-desktop
    echo   y vuelve a ejecutar este archivo.
    goto fallo
)

rem --- 2. ¿Esta corriendo el motor? -------------------------------------------
echo   [1/4] Comprobando Docker...
docker info >nul 2>&1
if not errorlevel 1 goto motor_listo

echo         El motor no esta corriendo. Abriendo Docker Desktop...

rem La ruta de instalacion cambia segun si se instalo para todos los usuarios o
rem solo para el actual; se prueban las tres habituales.
set "ESCRITORIO="
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" set "ESCRITORIO=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" set "ESCRITORIO=%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
if exist "%LOCALAPPDATA%\Docker\Docker Desktop.exe" set "ESCRITORIO=%LOCALAPPDATA%\Docker\Docker Desktop.exe"

if not defined ESCRITORIO (
    echo   [X] Docker esta instalado pero no se encontro Docker Desktop.
    echo       Abrelo a mano, espera a que diga "Engine running" y reintenta.
    goto fallo
)
start "" "%ESCRITORIO%"

rem Arrancar el motor toma entre 20 s y 2 min segun la maquina.
set /a intentos=0
:esperar_motor
ping -n 4 127.0.0.1 >nul
docker info >nul 2>&1
if not errorlevel 1 goto motor_listo
set /a intentos+=1
set /a segundos=intentos*3
if !intentos! geq 60 (
    echo.
    echo   [X] Docker Desktop no termino de arrancar en 3 minutos.
    echo       Revisalo en la bandeja del sistema: si pide habilitar WSL2 o la
    echo       virtualizacion en la BIOS, hay que hacerlo una vez ^(ver
    echo       docs/fases/fase-0-entorno.md^).
    goto fallo
)
echo         Esperando al motor de Docker... !segundos! s
goto esperar_motor

:motor_listo
echo         Docker responde.

rem --- 3. Levantar la linea ---------------------------------------------------
echo.
echo   [2/4] Construyendo y levantando los servicios.
echo         La primera vez tarda unos minutos: descarga e instala todo dentro
echo         de los contenedores. Las siguientes son casi instantaneas.
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo   [X] Fallo "docker compose up". El error esta unas lineas mas arriba.
    echo       Lo mas comun es un puerto ocupado ^(8000, 8001, 6379 u 8501^):
    echo       cierra lo que lo use o cambia el puerto en docker-compose.yml.
    goto fallo
)

rem --- 4. Esperar a que el tablero este listo ---------------------------------
echo.
echo   [3/4] Esperando a que el tablero responda...

set /a intentos=0
:esperar_tablero
set "SALUD="
for /f "delims=" %%s in ('docker inspect -f "{{.State.Health.Status}}" ui 2^>nul') do set "SALUD=%%s"
if "!SALUD!"=="healthy" goto tablero_listo
set /a intentos+=1
if !intentos! geq 40 (
    echo.
    echo   [!] El tablero tarda mas de lo normal en responder.
    echo       Se abrira igual; si la pagina no carga, revisa:
    echo           docker compose ps
    echo           docker compose logs ui
    goto abrir
)
ping -n 3 127.0.0.1 >nul
goto esperar_tablero

:tablero_listo
echo         Listo.

:abrir
rem --- 5. Abrir el navegador --------------------------------------------------
echo.
echo   [4/4] Abriendo http://localhost:8501
start "" http://localhost:8501

echo.
echo   ---------------------------------------------------------------
echo   El sistema quedo corriendo en segundo plano.
echo.
echo   Tablero .............. http://localhost:8501
echo   API de ordenes ....... http://localhost:8000/docs
echo   API de metricas ...... http://localhost:8001/docs
echo.
echo   Para usarlo: boton "Ingresar lote a la linea" en el panel
echo   izquierdo, un lote cada ~5 segundos.
echo.
echo   Para detenerlo: doble clic en DETENER.bat
echo   ---------------------------------------------------------------
echo.
echo   Puedes cerrar esta ventana.
pause
exit /b 0

:fallo
echo.
pause
exit /b 1
