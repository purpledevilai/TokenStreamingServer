import uuid
from typing import Callable, Dict, Any, Optional, Awaitable
from fastapi import WebSocket
from lib.JSONRPCPeer import JSONRPCPeer


class Connection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.id = str(uuid.uuid4())
        self.peer = JSONRPCPeer(sender=self.send)

    async def send(self, message: str):
        await self.websocket.send_text(message)

    async def receive_loop(self):
        try:
            while True:
                message = await self.websocket.receive_text()
                await self.peer.handle_message(message)
        except Exception as e:
            print(f"[Connection {self.id}] WebSocket error:", e)
        finally:
            await self.websocket.close()

    def on(self, method: str, handler: Callable[..., Awaitable[Any]]):
        async def wrapped_handler(**params):
            return await handler(connection_id=self.id, **params)

        self.peer.on(method, wrapped_handler)

    async def call(
        self,
        method: str,
        params: Dict[str, Any],
        await_response: bool = False,
        timeout: int = 5
    ) -> Optional[Dict[str, Any]]:
        return await self.peer.call(method, params, await_response, timeout)

    async def start(self):
        await self.websocket.accept()
        print(f"[Connection {self.id}] Connection accepted")
        await self.receive_loop()
