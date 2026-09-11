@echo off
setlocal DisableDelayedExpansion

set "QD_RUNTIME_ID="
for /f "usebackq delims=" %%R in (`%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-connector.ps1" -PrintRuntimeId`) do set "QD_RUNTIME_ID=%%R"
if not defined QD_RUNTIME_ID exit /b 2
set "QD_RUNTIME=%LOCALAPPDATA%\QuantDinger\Connector\runtimes\%QD_RUNTIME_ID%"

"%QD_RUNTIME%\python\python.exe" -I "%QD_RUNTIME%\app\connector.py" %*
