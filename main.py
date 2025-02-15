from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx
import json
import logging

API_KEY = "b71357df24d6ddeaaecb68dd63cfd995"  # OpenWeatherMap API Key
app = FastAPI()

# Límite de conexiones simultáneas
MAX_CONNECTIONS = 3
active_connections = []  # Lista para rastrear conexiones activas

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para obtener el clima
async def fetch_weather(lat: float, lon: float):
    await asyncio.sleep(1)  # Simular latencia
    URL = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={API_KEY}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(URL)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return {"error": str(e)}

@app.websocket("/ws/weather")
async def weather_endpoint(websocket: WebSocket):
    # Verificar si se ha alcanzado el máximo de conexiones
    if len(active_connections) >= MAX_CONNECTIONS:
        await websocket.accept()
        await websocket.send_json({"error": "max_connections_reached"})
        await websocket.close()
        logger.warning("Máximo de conexiones alcanzado. Rechazando solicitud.")
        return

    # Aceptar la conexión y agregarla a la lista de conexiones activas
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"Nueva conexión WebSocket aceptada. Conexiones activas: {len(active_connections)}")

    try:
        while True:
            # Esperar datos del cliente (latitud y longitud)
            data = await websocket.receive_text()
            location = json.loads(data)  # Convertir datos de string a diccionario

            # Obtener datos del clima
            weather_data = await fetch_weather(location["lat"], location["lon"])
            if "error" in weather_data:
                await websocket.send_json({"error": "Failed to fetch weather data"})
            else:
                await websocket.send_json(weather_data)
            logger.info("Datos del clima enviados al cliente.")

    except WebSocketDisconnect:
        logger.info("Conexión WebSocket cerrada.")
    except Exception as e:
        logger.error(f"Error en la conexión WebSocket: {e}")
        await websocket.send_json({"error": "Internal server error"})
    finally:
        # Remover la conexión de la lista de conexiones activas
        active_connections.remove(websocket)
        logger.info(f"Conexión WebSocket removida. Conexiones activas: {len(active_connections)}")

@app.get("/status")
def status():
    return {"status": "API en ejecución"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)