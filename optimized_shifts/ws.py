import asyncio
from fastapi import WebSocket
from starlette.websockets import WebSocketState

class ConnectionManager:
    def __init__(self):
        self.__MAX_TIMEOUT = 5
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        await websocket.close()
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def is_websocket_active(self, ws: WebSocket) -> bool:
        if not (ws.application_state == WebSocketState.CONNECTED and ws.client_state == WebSocketState.CONNECTED):
            return False
        try:
            await asyncio.wait_for(ws.send_json({'type': 'ping'}), self.__MAX_TIMEOUT)
            message = await asyncio.wait_for(ws.receive_json(), self.__MAX_TIMEOUT)
            assert message['type'] == 'pong'
        except BaseException: 
            return False
        return True