@echo off
setlocal

set "APP_HOST=%~1"
if "%APP_HOST%"=="" set "APP_HOST=localhost"

set "VITE_DISABLE_HMR=1"

echo Starting OPR Helper frontend for http://%APP_HOST%:5173
echo API requests will use /api and proxy to http://127.0.0.1:8000
echo Vite HMR disabled for mobile browser stability

cmd /c npm run dev --prefix frontend -- --host 0.0.0.0
