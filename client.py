import json
import asyncio
import websockets

async def hello():
    uri = "ws://localhost:8000/api/v1/trips/live"
    async with websockets.connect(uri) as websocket:
        while True:
            message = json.loads(await websocket.recv())
            if message["type"] == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
                continue
            elif message["type"] == "notification":
                print(message["data"])

if __name__ == "__main__":
    asyncio.run(hello())