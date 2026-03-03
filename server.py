import asyncio
import websockets
import json
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)

class PoEServer:
    def __init__(self):
        self.clients = {}
        self.client_names = defaultdict(list)
    
    async def is_open(self, ws):
        """✅ websockets 16.0 проверка соединения"""
        try:
            await ws.ping()
            return True
        except:
            return False
    
    async def handler(self, websocket):
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        print(f"🔌 Подключение с IP: {client_ip}")
        
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"📨 {client_ip}: {data}")
                
                if data["type"] == "register":
                    client_type = data["client_type"]
                    name = data["name"]
                    
                    self.clients[websocket] = {
                        "type": client_type, 
                        "name": name, 
                        "ip": client_ip,
                        "listening": True
                    }
                    self.client_names[client_type].append(name)
                    
                    print(f"✅ {client_type.upper()}: {name} ({client_ip})")
                    await self.broadcast_status()
                    
                    asyncio.create_task(self.ping_client(websocket))
                    
                elif data["type"] == "pong":
                    continue
                
                elif data["type"] == "command" and self.clients.get(websocket, {}).get("type") == "client":
                    print(f"🎮 Команда от клиента {data.get('from', 'unknown')}: {data['command']}")
                    await self.forward_to_bots(websocket, data)
                    
                elif data["type"] == "command_result" and self.clients.get(websocket, {}).get("type") == "bot":
                    print(f"✅ Результат от бота: {data['result']}")
                    await self.forward_to_client(websocket, data)
                    
                elif data["type"] == "status_request":
                    await self.send_status(websocket)
                    
                elif data["type"] == "status_update":
                    if websocket in self.clients:
                        self.clients[websocket]["listening"] = data.get("listening", True)
                        await self.broadcast_status()
                        
        except websockets.ConnectionClosed:
            print(f"🔌 {client_ip} отключился")
        except Exception as e:
            print(f"❌ Ошибка {client_ip}: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def ping_client(self, websocket):
        while True:
            try:
                await asyncio.sleep(30)
                await websocket.ping()
                await websocket.send(json.dumps({"type": "ping"}))
                print("🏓 PING отправлен")
            except:
                print("❌ Ping failed")
                break
    
    async def forward_to_bots(self, source_ws, data):
        for ws, info in list(self.clients.items()):
            if info["type"] == "bot" and await self.is_open(ws):
                try:
                    await ws.send(json.dumps(data))
                    print(f"📤 Команда → бот {info['name']}")
                except:
                    pass
    
    async def forward_to_client(self, source_ws, data):
        target = data.get("to")
        if not target:
            return
        for ws, info in list(self.clients.items()):
            if info["type"] == "client" and info["name"] == target and await self.is_open(ws):
                try:
                    await ws.send(json.dumps(data))
                    print(f"📤 Результат → клиент {target}")
                except:
                    pass
    
    async def send_status(self, target_ws):
        status = {"type": "status_response", "clients": {}}
        for ws, info in list(self.clients.items()):
            if await self.is_open(ws):
                status["clients"][info["name"]] = {
                    "type": info["type"],
                    "status": "🟢 онлайн" if info.get("listening", True) else "⏸️ пауза",
                    "ip": info["ip"]
                }
        try:
            await target_ws.send(json.dumps(status))
        except:
            pass
    
    async def broadcast_status(self):
        status = {"type": "status_response", "clients": {}}
        for ws, info in list(self.clients.items()):
            if await self.is_open(ws):
                status["clients"][info["name"]] = {
                    "type": info["type"],
                    "status": "🟢 онлайн" if info.get("listening", True) else "⏸️ пауза",
                    "ip": info.get("ip", "unknown")
                }
        
        disconnected = []
        for ws in list(self.clients):
            try:
                await ws.send(json.dumps(status))
            except:
                disconnected.append(ws)
        
        for ws in disconnected:
            await self.unregister_client(ws)
    
    async def unregister_client(self, websocket):
        if websocket in self.clients:
            info = self.clients[websocket]
            name = info["name"]
            client_type = info["type"]
            ip = info.get("ip", "unknown")
            
            del self.clients[websocket]
            if name in self.client_names[client_type]:
                self.client_names[client_type].remove(name)
            
            print(f"❌ {client_type.upper()}: {name} ({ip})")
            await self.broadcast_status()

async def main():
    print("🚀 PoE Server УНИВЕРСАЛЬНЫЙ v2.1")
    print("📡 Слушает: 0.0.0.0:8765")
    print("🌐 poe.vpn.ru:8765 | 95.131.147.28:8765 | 192.168.1.187:8765")
    print("-" * 50)
    
    server = PoEServer()
    async with websockets.serve(server.handler, "0.0.0.0", 8765):
        print("✅ СЕРВЕР ГОТОВ 24/7!")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
