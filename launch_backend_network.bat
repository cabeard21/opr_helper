@echo off
setlocal

set "APP_HOST_IP=%~1"
if "%APP_HOST_IP%"=="" set "APP_HOST_IP=100.80.244.14"

set "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.102,%APP_HOST_IP%"
set "DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.102:5173,http://%APP_HOST_IP%:5173"

echo Starting OPR Helper backend for http://%APP_HOST_IP%:8000
echo Allowed origins: %DJANGO_CORS_ALLOWED_ORIGINS%

".venv\Scripts\python.exe" backend\manage.py runserver 0.0.0.0:8000
