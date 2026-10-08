@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 start.py
    goto :end
)

where python >nul 2>&1
if %errorlevel%==0 (
    python start.py
    goto :end
)

echo.
echo ERROR: No se encontro Python 3.10+ en el PATH.
echo Instala Python desde https://www.python.org/downloads/
echo y vuelve a ejecutar este archivo.
echo.
pause
exit /b 1

:end
if %errorlevel% neq 0 (
    echo.
    echo TechLoan no pudo iniciarse.
    pause
)
endlocal
