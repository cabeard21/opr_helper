@echo off
setlocal

set "APP_HOST_IP=%~1"
if "%APP_HOST_IP%"=="" set "APP_HOST_IP=100.80.244.14"

echo Starting OPR Helper on http://%APP_HOST_IP%:5173
echo Backend will listen on http://%APP_HOST_IP%:8000

start "OPR Helper Backend" cmd /k "%~dp0launch_backend_network.bat" %APP_HOST_IP%
start "OPR Helper Frontend" cmd /k "%~dp0launch_frontend_network.bat" %APP_HOST_IP%
