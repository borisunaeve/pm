@echo off
echo Starting PM App Docker Container...
docker-compose up -d --build
echo App started. Access it at http://localhost:8000
