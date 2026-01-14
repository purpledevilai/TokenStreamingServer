from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from handlers.connect_to_context import connect_to_context
from handlers.add_message import add_message
from handlers.stop_invocation import stop_invocation
from handlers.set_last_messages import set_last_messages

app = FastAPI()

# Optional: Add CORS if you expect to call from other domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend origin if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "num_connections": len(CONNECTIONS),
    }

@app.get("/reset")
async def reset(key: str = Query(default=None)):
    # Check that key in query params is correct
    if key != os.environ.get("RESET_KEY"):
        return
    global CONNECTIONS
    CONNECTIONS = {}
    return {
        "status": "ok",
        "message": "Connections reset successfully",
        "num_connections": len(CONNECTIONS),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection = Connection(websocket)
    CONNECTIONS[connection.id] = connection
    
    connection.on("connect_to_context", connect_to_context)
    connection.on("add_message", add_message)
    connection.on("stop_invocation", stop_invocation)
    connection.on("set_last_messages", set_last_messages)

    try:
        await connection.start()
    finally:
        CONNECTIONS.pop(connection.id, None)
        print(f"[Connection {connection.id}] Removed from registry")
