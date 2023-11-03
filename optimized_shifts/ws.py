""" Módulo que contiene las especificaciones para websocket de la aplicación """

import asyncio
from fastapi import WebSocket
from starlette.websockets import WebSocketState

class ConnectionManager:
    """ Administrador de conexiones vía WebSocket """
    def __init__(self):
        self.__MAX_TIMEOUT = 5
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """ Inicia la conexión con un cliente y lo almacena en un estado interno """
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        """ Cierra la conexión con un cliente y lo elimina del estado interno """
        await websocket.close()
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """ Envia un mensaje a todos los clientes conectados """
        for connection in self.active_connections:
            await connection.send_text(message)

    async def is_websocket_active(self, ws: WebSocket) -> bool:
        """ Comprueba si un cliente sigue conectado, para esto
            envía un mensaje de tipo 'ping', si recibe una respuesta de tipo 'pong' entonces
            retornará True, de lo contrario, retornará false
        """
        if not (ws.application_state == WebSocketState.CONNECTED and ws.client_state == WebSocketState.CONNECTED):
            return False
        try:
            await asyncio.wait_for(ws.send_json({'type': 'ping'}), self.__MAX_TIMEOUT)
            message = await asyncio.wait_for(ws.receive_json(), self.__MAX_TIMEOUT)
            assert message['type'] == 'pong'
        except BaseException: 
            return False
        return True