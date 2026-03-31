@echo off
setlocal

rem Portalis Alpha portable launcher
rem Resolves everything from this batch file location so it works from any USB drive letter.

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

set "PYTHON_EXE=%ROOT_DIR%\tools\python\python.exe"
set "APP_MAIN=%ROOT_DIR%\NAVSYS\app\main.py"
set "TOOLS_DIR=%ROOT_DIR%\tools"
set "TESSERACT_DIR=%TOOLS_DIR%\tesseract"
set "POPPLER_DIR=%TOOLS_DIR%\poppler"
set "TEMP_DIR=%ROOT_DIR%\temp"
set "CACHE_DIR=%ROOT_DIR%\cache"
set "HF_CACHE_DIR=%CACHE_DIR%\hf"
set "LOG_DIR=%ROOT_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\portalis_alpha_latest.log"

if not exist "%ROOT_DIR%" (
  echo [ERROR] Root folder not found:
  echo %ROOT_DIR%
  pause
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Portable Python not found:
  echo %PYTHON_EXE%
  echo.
  echo Expected NAVSYS_USB structure:
  echo tools\python\python.exe
  pause
  exit /b 1
)

if not exist "%APP_MAIN%" (
  echo [ERROR] Portalis app entrypoint not found:
  echo %APP_MAIN%
  echo.
  echo Expected NAVSYS_USB structure:
  echo NAVSYS\app\main.py
  pause
  exit /b 1
)

if not exist "%TOOLS_DIR%" (
  echo [ERROR] Tools folder missing:
  echo %TOOLS_DIR%
  pause
  exit /b 1
)

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"
if not exist "%HF_CACHE_DIR%" mkdir "%HF_CACHE_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set "TEMP=%TEMP_DIR%"
set "TMP=%TEMP_DIR%"
set "PYTHONPATH=%ROOT_DIR%;%ROOT_DIR%\NAVSYS;%ROOT_DIR%\modules"
set "HF_HOME=%HF_CACHE_DIR%"
set "HUGGINGFACE_HUB_CACHE=%HF_CACHE_DIR%"
set "TRANSFORMERS_CACHE=%HF_CACHE_DIR%"
set "PATH=%ROOT_DIR%\tools\python;%ROOT_DIR%\tools\python\Scripts;%TESSERACT_DIR%;%POPPLER_DIR%;%POPPLER_DIR%\Library\bin;%PATH%"

if exist "%TESSERACT_DIR%\tessdata" (
  set "TESSDATA_PREFIX=%TESSERACT_DIR%\tessdata"
)

cd /d "%ROOT_DIR%"

echo ============================================
echo PORTALIS ALPHA PORTABLE LAUNCHER
echo Root:   %ROOT_DIR%
echo Python: %PYTHON_EXE%
echo App:    %APP_MAIN%
echo Log:    %LOG_FILE%
echo ============================================
echo.

rem Open local browser after a short delay so the Flask server can come up first.
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:5000/portalis'"

echo [%DATE% %TIME%] Starting Portalis Alpha...>"%LOG_FILE%"
echo Root=%ROOT_DIR%>>"%LOG_FILE%"
echo Python=%PYTHON_EXE%>>"%LOG_FILE%"
echo App=%APP_MAIN%>>"%LOG_FILE%"
echo.>>"%LOG_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "& { & '%PYTHON_EXE%' '%APP_MAIN%' 2>&1 | Tee-Object -FilePath '%LOG_FILE%' -Append }"

set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Portalis Alpha exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
