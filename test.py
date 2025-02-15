import asyncio
import websockets

async def connect_and_send():
    uri = "ws://localhost:8000/ws/weather"
    async with websockets.connect(uri) as websocket:
        # ejemplo coordenadas de new york 
        await websocket.send('{"lat": 40.7128, "lon": -74.0060}')
    
        response = await websocket.recv()
        print(f"Respuesta del servidor: {response}")

# simular conexiones simultáneas
async def main():
    tasks = [connect_and_send() for _ in range(2)]
    await asyncio.gather(*tasks)

asyncio.run(main())