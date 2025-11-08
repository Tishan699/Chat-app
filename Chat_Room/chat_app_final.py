# chat_app_final.py - FIXED for new/old websockets API
import asyncio
import websockets
import json
from collections import defaultdict, deque
import datetime

# ==================== SERVER CODE ====================
class ChatServer:
    def __init__(self):
        self.connected_clients = set()
        self.username_to_websocket = {}
        self.room_users = defaultdict(set)
        self.user_room = {}
        self.message_history = defaultdict(lambda: deque(maxlen=5))
        
    # Accept path as optional to support both old and new websockets versions
    async def handle_client(self, websocket, path=None):
        # If path wasn't passed by the library, try to read it from the websocket object
        if path is None:
            # newer websockets put the HTTP request on websocket.request
            req = getattr(websocket, "request", None)
            try:
                path = req.path if req is not None else getattr(websocket, "path", None)
            except Exception:
                path = None

        print("🔥 New connection received", f"(path={path})")
        username = None
        room_name = None
        
        try:
            # Wait for client to join
            data = await websocket.recv()
            message_data = json.loads(data)
            
            if message_data.get('type') == 'join':
                username = message_data['username']
                room_name = message_data['room']
                
                # Check if username is taken
                if username in self.username_to_websocket:
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Username already taken!'
                    }))
                    return
                
                # Register client
                self.connected_clients.add(websocket)
                self.username_to_websocket[username] = websocket
                self.room_users[room_name].add(websocket)
                self.user_room[username] = room_name
                
                # Send join success with history
                await websocket.send(json.dumps({
                    'type': 'join_success',
                    'history': list(self.message_history[room_name])
                }))
                
                # Notify room
                await self.broadcast_message(room_name, f"{username} joined the room", "System")
                print(f"✅ {username} joined {room_name}")
                
                # Listen for incoming messages
                async for message in websocket:
                    try:
                        msg_data = json.loads(message)
                        if msg_data.get('type') == 'message':
                            await self.broadcast_message(room_name, msg_data['message'], username)
                    except Exception as e:
                        print(f"⚠️ Message handling error: {e}")
                        break
                        
        except Exception as e:
            print(f"❌ Connection error: {e}")
        finally:
            if username:
                await self.remove_client(websocket, username, room_name)
    
    async def broadcast_message(self, room_name, message, sender):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        history_msg = f"[{timestamp}] {sender}: {message}"
        self.message_history[room_name].append(history_msg)
        
        # Save to text file
        try:
            with open(f"{room_name}.txt", "a", encoding="utf-8") as f:
                f.write(history_msg + "\n")
        except Exception as e:
            print(f"⚠️ File save error: {e}")
        
        # Send to all clients in the room
        for client in list(self.room_users[room_name]):
            try:
                await client.send(json.dumps({
                    'type': 'message',
                    'username': sender,
                    'message': message,
                    'timestamp': timestamp
                }))
            except Exception:
                self.room_users[room_name].discard(client)
    
    async def remove_client(self, websocket, username, room_name):
        if username in self.username_to_websocket:
            del self.username_to_websocket[username]
        if username in self.user_room:
            del self.user_room[username]
        
        self.connected_clients.discard(websocket)
        if room_name:
            self.room_users[room_name].discard(websocket)
            await self.broadcast_message(room_name, f"{username} left the room", "System")
        print(f"❌ {username} left {room_name}")

async def start_server():
    server = ChatServer()
    # bind to localhost:2025
    async with websockets.serve(server.handle_client, "localhost", 2025, ping_interval=None):
        print("🚀 SERVER STARTED on ws://localhost:2025")
        print("💡 Keep this terminal open!")
        print("⏹️  Press Ctrl+C to stop\n")
        await asyncio.Future()  # keep server alive

# ==================== CLIENT CODE ====================
class ChatClient:
    def __init__(self):
        self.websocket = None
        self.connected = False
    
    async def connect(self, server_url, username, room_name):
        try:
            self.websocket = await websockets.connect(server_url, ping_interval=None)
            await self.websocket.send(json.dumps({
                'type': 'join',
                'username': username,
                'room': room_name
            }))
            
            asyncio.create_task(self.listen_for_messages())
            self.connected = True
            return True, "✅ Connected to chat room!"
            
        except Exception as e:
            return False, f"❌ Connection failed: {str(e)}"
    
    async def send_message(self, message):
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({
                'type': 'message',
                'message': message
            }))
    
    async def listen_for_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                if data.get('type') == 'message':
                    timestamp = data.get('timestamp', '')
                    username = data.get('username', '')
                    msg = data.get('message', '')
                    print(f"\n[{timestamp}] {username}: {msg}")
                    print("💬 Type your message: ", end="", flush=True)
                
                elif data.get('type') == 'join_success':
                    print("\n✅ Joined successfully!")
                    history = data.get('history', [])
                    for msg in history:
                        print(f"📜 {msg}")
                    print("💬 Type your message: ", end="", flush=True)
                
                elif data.get('type') == 'error':
                    print(f"\n❌ {data.get('message')}")
                    
        except Exception as e:
            print(f"\n❌ Disconnected from server ({e})")
            self.connected = False
    
    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
            self.connected = False

async def start_client():
    client = ChatClient()
    
    username = input("👤 Enter your username: ").strip()
    room = input("🏠 Enter room name: ").strip()
    
    print("🔄 Connecting...")
    success, message = await client.connect("ws://localhost:2025", username, room)
    print(message)
    
    if not success:
        return
    
    print("💬 Type your messages below (type /quit to exit):")
    print("💬 Type your message: ", end="", flush=True)
    
    try:
        while client.connected:
            message = input()
            if message.lower() in ['/quit', '/exit', '/q']:
                break
            await client.send_message(message)
            print("💬 Type your message: ", end="", flush=True)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        await client.disconnect()

# ==================== MAIN MENU ====================
def main():
    print("=" * 50)
    print("🎯 PYTHON CHAT APPLICATION")
    print("=" * 50)
    print("1. 🖥️  Start SERVER")
    print("2. 👤 Start CLIENT")
    print("3. ❌ Exit")
    print("=" * 50)
    
    try:
        choice = input("Choose (1-3): ").strip()
        if choice == "1":
            asyncio.run(start_server())
        elif choice == "2":
            asyncio.run(start_client())
        elif choice == "3":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice!")
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
