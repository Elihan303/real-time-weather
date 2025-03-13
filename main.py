from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx
import json
import logging

API_KEY = ""  # OpenWeatherMap API Key
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
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            return {"error": f"HTTP error: {e.response.status_code}"}
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            return {"error": "Request error"}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": "Unexpected error"}

# Función recursiva para manejar conexiones WebSocket
async def handle_websocket_connection(websocket: WebSocket, connection_count: int = 0):
    """
    Maneja una conexión WebSocket de manera recursiva.
    """
    try:
        # Esperar datos del cliente (latitud y longitud)
        data = await websocket.receive_text()
        location = json.loads(data)  # Convertir datos de string a diccionario

        # Obtener datos del clima
        weather_data = await fetch_weather(location["lat"], location["lon"])
        if "error" in weather_data:
            await websocket.send_json({"error": f"Failed to fetch weather data {weather_data['error']}"})
        else:
            await websocket.send_json(weather_data)
        logger.info("Datos del clima enviados al cliente.")

        # Llamada recursiva para manejar la siguiente solicitud
        await handle_websocket_connection(websocket, connection_count + 1)

    except WebSocketDisconnect:
        logger.info("Conexión WebSocket cerrada.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        await websocket.send_json({"error": "Invalid JSON format"})
    except Exception as e:
        logger.error(f"Error en la conexión WebSocket: {e}")
        await websocket.send_json({"error": "Internal server error"})
    finally:
        # Liberar el semáforo cuando la conexión se cierra
        semaphore.release()
        logger.info(f"Conexión WebSocket liberada. Conexiones activas: {MAX_CONNECTIONS - semaphore._value}")

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

    # Manejar la conexión WebSocket de manera recursiva
    await handle_websocket_connection(websocket)

@app.get("/status")
def status():
    """
    Endpoint para verificar el estado de la API.
    """
    return {"status": "API en ejecución"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)