from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import httpx
import json
import logging

from database import async_session, WeatherReport  

API_KEY = ""  # Coloca tu API Key de OpenWeatherMap
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
class ConnectionManager:
    def __init__(self, max_connections: int):
        self.active_connections: list[WebSocket] = []
        self.lock = asyncio.Lock()  
        self.semaphore = asyncio.Semaphore(max_connections)  

    async def connect(self, websocket: WebSocket):
        await self.semaphore.acquire()
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
            logger.info(f"Conexión aceptada. Conexiones activas: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"Conexión removida. Conexiones activas: {len(self.active_connections)}")
        self.semaphore.release()

    async def broadcast(self, message: str):
        async with self.lock:
            for connection in self.active_connections:
                await connection.send_text(message)

manager = ConnectionManager(max_connections=2)


async def fetch_weather(lat: float, lon: float):
    await asyncio.sleep(1)  
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


async def handle_websocket(websocket: WebSocket):
    try:
        while True:
            data = await websocket.receive_text()
            location = json.loads(data)
            weather_data = await fetch_weather(location["lat"], location["lon"])
            if "error" in weather_data:
                await websocket.send_json({"error": f"Failed to fetch weather data: {weather_data['error']}"})
            else:
                # Enviar los datos del clima al cliente
                await websocket.send_json(weather_data)
                # Guardar el reporte en la base de datos
                await save_weather_data(weather_data, location["lat"], location["lon"])
                # Notificar al cliente que el reporte se guardó exitosamente
                await websocket.send_json({"event": "weather_saved", "message": "Reporte de clima guardado exitosamente."})
            logger.info("Datos del clima enviados y guardados.")
    except WebSocketDisconnect:
        logger.info("Conexión WebSocket cerrada por el cliente.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decodificando JSON: {e}")
        await websocket.send_json({"error": "Formato JSON inválido"})
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        await websocket.send_json({"error": "Internal server error"})
    finally:
        # Notificar al monitor que la conexión se libera
        await manager.disconnect(websocket)
        logger.info("Conexión liberada a través del monitor.")


@app.websocket("/ws/weather")
async def weather_endpoint(websocket: WebSocket):
    try:
        # El monitor (ConnectionManager) controla la conexión
        await manager.connect(websocket)
    except Exception as e:
        logger.error(f"Error al conectar: {e}")
        await websocket.close()
        return

    await handle_websocket(websocket)

@app.get("/status")
def status():
    return {"status": "API en ejecución"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
