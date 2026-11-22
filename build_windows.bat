@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m pip install --upgrade pip
if errorlevel 1 exit /b 1
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed --name MinecraftPythonLauncher --collect-all glfw --collect-all OpenGL launcher.py
if errorlevel 1 exit /b 1
echo.
echo Build complete: dist\MinecraftPythonLauncher.exe
endlocal
