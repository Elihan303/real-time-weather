from fastapi import FastAPI, WebSocket
import requests
import asyncio

app = FastAPI()
API_KEY = ""  # OpenWeatherMap API Key

async def get_weather(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/weather")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        try:
            location = await websocket.receive_json()
            lat, lon = location.get("lat"), location.get("lon")

            if lat is None or lon is None:
                await websocket.send_json({"error": "Ubicación no válida"})
                continue

            weather_data = await get_weather(lat, lon)
            await websocket.send_json(weather_data)
            await asyncio.sleep(5) 
        except Exception as e:
            await websocket.send_json({"error": str(e)})

@app.get("/status")
def status():
    return {"status": "API en ejecución"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
