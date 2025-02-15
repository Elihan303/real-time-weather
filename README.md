## Comando para iniciar el servidor

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

Confirma status del servidor arriba: http://localhost:8000/status

## Ejecutar servidor con html

python -m http.server 8080

sitio: http://localhost:8080/index.html

En caso de que el sitio se quede con cache: http://localhost:8080/index.html?nocache=123
