from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from lib.Connection import Connection
from stores.connections import CONNECTIONS
from handlers.connect_to_context import connect_to_context
from handlers.add_message import add_message

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
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    connection = Connection(websocket)
    CONNECTIONS[connection.id] = connection
    
    connection.on("connect_to_context", connect_to_context)
    connection.on("add_message", add_message)

    try:
        await connection.start()
    finally:
        CONNECTIONS.pop(connection.id, None)
        print(f"[Connection {connection.id}] Removed from registry")
