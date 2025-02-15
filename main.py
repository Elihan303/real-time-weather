from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx
import json
import logging

API_KEY = "b71357df24d6ddeaaecb68dd63cfd995"  # OpenWeatherMap API Key
app = FastAPI()

# Límite de conexiones simultáneas
MAX_CONNECTIONS = 2
semaphore = asyncio.Semaphore(MAX_CONNECTIONS)  # Semáforo para controlar conexiones

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Función para obtener el clima
async def fetch_weather(lat: float, lon: float):
    """
    Obtiene los datos del clima desde la API de OpenWeatherMap.
    """
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
    """
    Endpoint WebSocket para obtener datos meteorológicos.
    """
    # Verificar si se ha alcanzado el máximo de conexiones
    if semaphore.locked():
        await websocket.accept()
        await websocket.send_json({"error": "max_connections_reached"})
        await websocket.close()
        logger.warning("Máximo de conexiones alcanzado. Rechazando solicitud.")
        return

    # Adquirir el semáforo antes de aceptar la conexión
    await semaphore.acquire()
    await websocket.accept()
    logger.info(f"Nueva conexión WebSocket aceptada. Conexiones activas: {MAX_CONNECTIONS - semaphore._value}")

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
        # Liberar el semáforo cuando la conexión se cierra
        semaphore.release()
        logger.info(f"Conexión WebSocket liberada. Conexiones activas: {MAX_CONNECTIONS - semaphore._value}")

@app.get("/status")
def status():
    """
    Endpoint para verificar el estado de la API.
    """
    return {"status": "API en ejecución"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)