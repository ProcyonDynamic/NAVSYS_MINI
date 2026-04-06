@echo off
setlocal

set "REPO_ROOT=%~dp0"
cd /d "%REPO_ROOT%"

set "PYTHONPATH=%REPO_ROOT%"

echo [UCHM] Repo root: %REPO_ROOT%
set /p GENERATED_FILE=Enter generated UCHM path: 
set /p RESAVED_FILE=Enter JRC-resaved UCHM path: 

if "%GENERATED_FILE%"=="" (
    echo [UCHM] Generated UCHM path is required.
    pause
    exit /b 1
)

if "%RESAVED_FILE%"=="" (
    echo [UCHM] JRC-resaved UCHM path is required.
    pause
    exit /b 1
)

echo [UCHM] Comparing files...
python ".\tests\generate_uchm_validation_cases.py" compare "%GENERATED_FILE%" "%RESAVED_FILE%"

if errorlevel 1 (
    echo [UCHM] UCHM comparison FAILED.
    pause
    exit /b 1
)

echo [UCHM] UCHM comparison completed successfully.
pause
exit /b 0
