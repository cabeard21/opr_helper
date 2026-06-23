@echo off
setlocal

set "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1"
set "DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173"

echo Starting OPR Helper backend for frontend proxy at http://127.0.0.1:8000
echo Allowed origins: %DJANGO_CORS_ALLOWED_ORIGINS%

".venv\Scripts\python.exe" backend\manage.py runserver 127.0.0.1:8000
