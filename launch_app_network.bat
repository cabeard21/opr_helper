@echo off
setlocal

set "APP_HOST=%~1"
if "%APP_HOST%"=="" set "APP_HOST=localhost"

echo Starting OPR Helper on http://%APP_HOST%:5173
echo API requests will be proxied through the frontend dev server.
echo For another device, open http://YOUR_LAPTOP_IP:5173

start "OPR Helper Backend" cmd /k "%~dp0launch_backend_network.bat"
start "OPR Helper Frontend" cmd /k "%~dp0launch_frontend_network.bat" %APP_HOST%
