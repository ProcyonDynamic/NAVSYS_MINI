@echo off
set USB_ROOT=%~dp0..
cd /d %USB_ROOT%

echo ===============================
echo NAVSYS USB DEV ENVIRONMENT
echo ===============================

set PYTHONHOME=%USB_ROOT%\tools\python
set PYTHONPATH=%USB_ROOT%\NAVSYS
set PATH=%USB_ROOT%\tools\python;%USB_ROOT%\tools\python\Scripts;%USB_ROOT%\tools\poppler\Library\bin;%USB_ROOT%\tools\tesseract;%USB_ROOT%\tools\git\cmd;%PATH%
set TESSDATA_PREFIX=%USB_ROOT%\tools\tesseract\tessdata
set TEMP=%USB_ROOT%\temp
set TMP=%USB_ROOT%\temp

echo Starting NAVSYS...
echo.

%USB_ROOT%\tools\python\python.exe %USB_ROOT%\NAVSYS\app\main.py

pause