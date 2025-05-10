from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from lib.Connection import Connection
from stores.connections import CONNECTIONS

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

    async def handle_ping(connection_id: str):
        print(f"[{connection_id}] got ping")
        return {"pong": True, "connection_id": connection_id}
    
    connection.on("ping", handle_ping)

    try:
        await connection.start()
    finally:
        CONNECTIONS.pop(connection.id, None)
        print(f"[Connection {connection.id}] Removed from registry")
