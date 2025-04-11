from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx
import json
import logging
from database import async_session, WeatherReport 

API_KEY = ""  # Coloca tu API Key de OpenWeatherMap
app = FastAPI()

# Límite de conexiones simultáneas
MAX_CONNECTIONS = 2
semaphore = asyncio.Semaphore(MAX_CONNECTIONS)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

# Función para obtener el clima
async def fetch_weather(lat: float, lon: float):
    await asyncio.sleep(1)  # Simula latencia
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

# Función para guardar el reporte en la base de datos
async def save_weather_data(weather_data: dict, lat: float, lon: float):
    try:
        async with async_session() as session:
            report = WeatherReport(
                lat=lat,
                lon=lon,
                temperature=weather_data["main"]["temp"],
                condition=weather_data["weather"][0]["main"],
                description=weather_data["weather"][0]["description"]
            )
            session.add(report)
            await session.commit()
            logger.info("Reporte de clima guardado en la base de datos.")
    except Exception as e:
        logger.error(f"Error guardando en la BD: {e}")

# Manejo recursivo de conexiones WebSocket
async def handle_websocket_connection(websocket: WebSocket, connection_count: int = 0):
    try:
        data = await websocket.receive_text()
        location = json.loads(data)
        weather_data = await fetch_weather(location["lat"], location["lon"])
        if "error" in weather_data:
            await websocket.send_json({"error": f"Failed to fetch weather data {weather_data['error']}"})
        else:
            await websocket.send_json(weather_data)
            # Guardar el reporte en la base de datos
            await save_weather_data(weather_data, location["lat"], location["lon"])
        logger.info("Datos del clima enviados y guardados.")
        await handle_websocket_connection(websocket, connection_count + 1)

    except WebSocketDisconnect:
        logger.info("Conexión WebSocket cerrada.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decodificando JSON: {e}")
        await websocket.send_json({"error": "Formato JSON inválido"})
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        await websocket.send_json({"error": "Internal server error"})
    finally:
        semaphore.release()
        logger.info(f"Conexión WebSocket liberada. Conexiones activas: {MAX_CONNECTIONS - semaphore._value}")

@app.websocket("/ws/weather")
async def weather_endpoint(websocket: WebSocket):
    if semaphore.locked():
        await websocket.accept()
        await websocket.send_json({"error": "max_connections_reached"})
        await websocket.close()
        logger.warning("Máximo de conexiones alcanzado. Rechazando solicitud.")
        return

    await semaphore.acquire()
    await websocket.accept()
    logger.info(f"Nueva conexión aceptada. Conexiones activas: {MAX_CONNECTIONS - semaphore._value}")
    await handle_websocket_connection(websocket)

@app.get("/status")
def status():
    return {"status": "API en ejecución"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
