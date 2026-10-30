@echo off
REM Genera dist\SistemaAcademico.exe (ejecutar desde esta carpeta, en Windows).
REM Requiere Python 3.9+ instalado desde python.org (incluye Tkinter).
chcp 65001 >nul
REM Solo instala PyInstaller si no esta (asi funciona aunque la red bloquee pip).
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo Instalando PyInstaller...
  python -m pip install pyinstaller || goto :error
)
REM Opcional (verificar firmas criptograficamente): python -m pip install pyhanko

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name SistemaAcademico ^
  --hidden-import ui.gui.ventana ^
  main_gui.py || goto :error

echo.
echo Listo: dist\SistemaAcademico.exe
echo La carpeta "data" (base de datos y PDF) se creara junto al .exe al abrirlo.
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Revise los mensajes de arriba.
pause
exit /b 1
