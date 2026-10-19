import asyncio
import datetime
import sys
from typing import List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class TerminalBroadcaster:
    def __init__(self, max_history: int = 200):
        self.active_connections: List[Any] = []
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history

    async def connect(self, websocket: Any):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send historical logs to the newly connected client
        for item in self.history:
            try:
                await websocket.send_json(item)
            except Exception:
                pass

    def disconnect(self, websocket: Any):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, level: str, message: str, details: Dict[str, Any] = None):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "type": "log",
            "timestamp": now_str,
            "level": level.upper(),
            "message": message,
            "details": details or {}
        }

        self.history.append(log_entry)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Print to standard stdout safely for Windows
        try:
            print(f"[{now_str}] [{level.upper()}] {message}")
        except UnicodeEncodeError:
            print(f"[{now_str}] [{level.upper()}] {message.encode('utf-8', errors='replace').decode('ascii', errors='replace')}")

        # Send to all connected web sockets
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(log_entry)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    async def broadcast_event(self, event_name: str, payload: Any):
        packet = {
            "type": "event",
            "event": event_name,
            "payload": payload,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(packet)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def log_sync(self, level: str, message: str, details: Dict[str, Any] = None):
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast(level, message, details))
            else:
                loop.run_until_complete(self.broadcast(level, message, details))
        except RuntimeError:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now_str}] [{level.upper()}] {message}")

broadcaster = TerminalBroadcaster()
