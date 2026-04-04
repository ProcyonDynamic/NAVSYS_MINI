@echo off
setlocal

set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

set "PYTHONPATH=%REPO_ROOT%"

echo [UCHM] Repo root: %REPO_ROOT%
echo [UCHM] Generating validation cases...
python ".\tests\generate_uchm_validation_cases.py" generate

if errorlevel 1 (
    echo [UCHM] Validation case generation FAILED.
    pause
    exit /b 1
)

echo [UCHM] Validation case generation completed successfully.
set "OUTPUT_DIR=.\tests\fixtures\jrc_usercharts_generated\validation_cases"

if exist "%OUTPUT_DIR%" (
    echo [UCHM] Opening generated validation folder...
    start "" "%OUTPUT_DIR%"
)

pause
exit /b 0
