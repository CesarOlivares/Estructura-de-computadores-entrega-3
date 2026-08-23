@echo off
chcp 65001 >nul
setlocal
title Detener la linea - ECSD Caso 2
cd /d "%~dp0"

rem ===========================================================================
rem  Contraparte de INICIAR.bat: detiene los contenedores.
rem
rem  Se detiene SIN borrar el volumen a proposito. Las ordenes y los eventos
rem  quedan en la base y vuelven a estar ahi al arrancar de nuevo: perder los
rem  datos de una demo por cerrar la ventana seria un mal comportamiento por
rem  defecto. Para empezar de cero esta la opcion 2.
rem ===========================================================================

echo.
echo   Detener la linea de produccion
echo   ---------------------------------------------------------------
echo.
echo     1. Detener y conservar los datos   ^(lo normal^)
echo     2. Detener y borrar los datos      ^(empezar de cero^)
echo     3. Cancelar
echo.
set "OPCION="
set /p "OPCION=  Elige 1, 2 o 3 [1]: "
if not defined OPCION set "OPCION=1"

if "%OPCION%"=="2" goto borrar
if "%OPCION%"=="3" goto salir

echo.
echo   Deteniendo...
docker compose down
goto fin

:borrar
echo.
echo   Deteniendo y borrando el volumen de datos...
docker compose down -v
goto fin

:salir
echo.
echo   Cancelado: no se toco nada.
goto fin

:fin
echo.
pause
exit /b 0
