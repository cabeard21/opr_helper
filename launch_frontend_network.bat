@echo off
setlocal

set "APP_HOST_IP=%~1"
if "%APP_HOST_IP%"=="" set "APP_HOST_IP=100.80.244.14"

set "VITE_API_BASE_URL=http://%APP_HOST_IP%:8000/api"
set "VITE_DISABLE_HMR=1"

echo Starting OPR Helper frontend for http://%APP_HOST_IP%:5173
echo API base URL: %VITE_API_BASE_URL%
echo Vite HMR disabled for mobile browser stability

cmd /c npm run dev --prefix frontend -- --host 0.0.0.0
