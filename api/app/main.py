from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import time
import paho.mqtt.client as paho
from paho import mqtt # For mqtt.client.ssl.PROTOCOL_TLS
import logging
from typing import Optional, List
import base64
import os

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# MQTT Configuration
MQTT_CLIENT_ID = f'fastapi_mqtt_{int(time.time())}' # Use int for time
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "akyvqaco") # Store credentials securely
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "iJ9JikQMjJkc") # Store credentials securely

MQTT_TOPIC_UP = "chat/up" # General messages from LoRa nodes/bridges
MQTT_TOPIC_DOWN = "chat/down" # General messages to LoRa nodes/bridges (e.g., text from web)
MQTT_TOPIC_NODES_STATUS = "nodes/status" # Node status updates
MQTT_TOPIC_BRIDGE_COMMAND_PREFIX = "lora_bridge" # e.g., lora_bridge/[BRIDGE_ID]/command

USER_DEFAULT_BRIDGE_ID = os.getenv("USER_DEFAULT_BRIDGE_ID", "default_bridge_node")

# Data Structures
RECEIVED_MESSAGES: List[dict] = [] # Store received messages for chat history
NODES_STATUS: dict = {} # Store status of known nodes

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections): # Iterate over a copy
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message to {connection.client}: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

# Pydantic Models
class PublishTextPayload(BaseModel): # For simple text messages from web to MQTT_TOPIC_DOWN
    message: str
    source_id: Optional[str] = "web_client"

class NodeStatusUpdate(BaseModel):
    id: str
    status: str # "online", "offline"
    last_seen: float
    rssi: Optional[int] = None
    snr: Optional[float] = None
    is_bridge: Optional[bool] = False

class BridgeCommandMetadata(BaseModel): # For commands from web to bridge via MQTT
    action: str # e.g., "send_lora_audio", "send_lora_text"
    original_content_type: Optional[str] = None # e.g., "audio/webm"
    filename: Optional[str] = None
    source_id: Optional[str] = "web_client"
    text_message: Optional[str] = None # For text messages to be sent via LoRa

# --- MQTT Callback Definitions ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"MQTT Connected successfully to {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC_UP, qos=1)
        client.subscribe(f"{MQTT_TOPIC_BRIDGE_COMMAND_PREFIX}/+/status", qos=1) # Status from all bridges
        client.subscribe(MQTT_TOPIC_NODES_STATUS, qos=1) # General node status topic
        # Add other necessary subscriptions here
    else:
        logger.error(f"MQTT Connection failed with result code {rc}")

def on_disconnect(client, userdata, rc, properties=None): # Added properties for MQTTv5
    logger.warning(f"MQTT Disconnected with result code {rc}. Will attempt to reconnect.")
    # Reconnect logic can be added here if needed, though paho-mqtt handles some of it.

def on_message(client, userdata, msg):
    """
    Callback for when a message is received from MQTT.
    """
    payload_str = ""
    try:
        payload_str = msg.payload.decode()
        data = json.loads(payload_str)
        logger.info(f"MQTT message received on topic '{msg.topic}': {data}")

        # Determine if it's a chat message or a status update
        is_chat_message = True

        # Node/Bridge Status Updates
        if msg.topic.startswith(MQTT_TOPIC_BRIDGE_COMMAND_PREFIX) and msg.topic.endswith("/status"):
            node_id = data.get("id", msg.topic.split('/')[-2]) # Get ID from payload or topic
            is_chat_message = False # This is a status message
        elif msg.topic == MQTT_TOPIC_NODES_STATUS:
            node_id = data.get("id")
            is_chat_message = False
        else: # Assumed to be a chat message from MQTT_TOPIC_UP
            node_id = data.get("node_id_lora", data.get("from", "desconocido"))

        # Update NODES_STATUS
        if node_id and node_id not in ["web_client", "sent", "?", "desconocido", "desconocido_raw"]:
            current_time = time.time()
            NODES_STATUS[node_id] = {
                "id": node_id,
                "last_seen": data.get("timestamp", current_time),
                "rssi": data.get("rssi"),
                "snr": data.get("snr"),
                "status": data.get("status", "online"),
                "is_bridge": data.get("is_bridge", False) or msg.topic.startswith(MQTT_TOPIC_BRIDGE_COMMAND_PREFIX)
            }
            # Consider broadcasting node status updates to websockets if needed
            # await manager.broadcast(json.dumps({"type": "node_update", "data": NODES_STATUS[node_id]}))

        if is_chat_message:
            # Prepare message for WebSocket clients
            chat_payload = {
                "topic": msg.topic,
                "payload": data.get("message", data.get("filename", "binary_data")),
                "source": data.get("from", "desconocido"), # Who sent it (bridge or node)
                "node_id_lora": data.get("node_id_lora", data.get("from", "desconocido")), # Original LoRa sender
                "rssi": data.get("rssi"),
                "snr": data.get("snr"),
                "content_type": data.get("content_type", "text/plain"),
                "data_b64": data.get("data_b64"),
                "filename": data.get("filename"),
                "timestamp": data.get("timestamp", time.time())
            }
            RECEIVED_MESSAGES.append(chat_payload)
            if len(RECEIVED_MESSAGES) > 100: # Keep buffer size limited
                RECEIVED_MESSAGES.pop(0)

            # Broadcast to WebSocket clients
            # This needs to be async, so we schedule it in the event loop
            # For simplicity, if on_message is not async, you might need another way
            # or make on_message async and handle it carefully.
            # A common pattern is to put messages into an asyncio.Queue and have another task process it.
            # For now, direct broadcast (will block if manager.broadcast is slow).
            # Consider making manager.broadcast put items in a queue for an async task.
            import asyncio
            async def do_broadcast():
                await manager.broadcast(json.dumps(chat_payload))

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(do_broadcast())
                else:
                    logger.warning("No running event loop to schedule broadcast.")
            except RuntimeError: # If no event loop is set
                 logger.warning("RuntimeError: No current event loop for broadcast.")


    except json.JSONDecodeError:
        logger.warning(f"MQTT message on topic '{msg.topic}' is not valid JSON: {payload_str[:100]}")
        # Handle as raw text if needed, or ignore
        chat_payload = {
            "topic": msg.topic, "payload": payload_str, "source": "unknown_raw_sender",
            "content_type": "text/plain", "timestamp": time.time()
        }
        RECEIVED_MESSAGES.append(chat_payload)
        # await manager.broadcast(json.dumps(chat_payload)) # Similar async consideration
    except Exception as e:
        logger.error(f"Error processing MQTT message on topic '{msg.topic}': {e}. Payload: {payload_str[:100]}")

# --- MQTT Client Setup ---
def mqtt_connect_client():
    client = paho.Client(client_id=MQTT_CLIENT_ID, protocol=paho.MQTTv5)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message # Assign the message callback HERE

    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # Configure TLS if your broker requires it (e.g., test.mosquitto.org often does)
    # For test.mosquitto.org, port 8883 is typically TLS, 1883 is non-TLS.
    # If using port 1883, TLS might not be needed or might be optional.
    # If using port 8883 (or your broker needs TLS on 1883), uncomment and configure:
    if MQTT_PORT == 8883 or MQTT_BROKER == "test.mosquitto.org": # common for test.mosquitto.org
         client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)


    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        logger.info(f"Attempting to connect to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
    except Exception as e:
        logger.error(f"MQTT connection failed: {e}")
        # Handle connection failure (e.g., retry logic or exit)
        raise # Reraise to stop app if MQTT is critical
    return client

mqtt_client = mqtt_connect_client()
mqtt_client.loop_start() # Start a background thread for MQTT network loop

# --- FastAPI Endpoints ---
@app.get("/")
async def get_root():
    # Simple HTML for testing, or serve your actual frontend
    return HTMLResponse("<h1>LoRaIM API Backend</h1><p>WebSocket at /ws</p>")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send recent message history to new client
    for msg_data in list(RECEIVED_MESSAGES)[-20:]: # Send last 20 messages
        await manager.send_personal_message(json.dumps(msg_data), websocket)
    # Send current node statuses
    await manager.send_personal_message(json.dumps({"type": "all_nodes_status", "nodes": NODES_STATUS}), websocket)
    try:
        while True:
            # Keep connection alive, or handle client messages if any
            data = await websocket.receive_text()
            logger.info(f"Received from WebSocket {websocket.client}: {data}")
            # Example: echo back or process client commands
            # await manager.send_personal_message(f"Echo: {data}", websocket)
    except WebSocketDisconnect:
        logger.info(f"WebSocket {websocket.client} disconnected (expected).")
    except Exception as e:
        logger.error(f"WebSocket error for {websocket.client}: {e}")
    finally:
        manager.disconnect(websocket)


@app.post("/publish_text") # For simple text messages from web to general chat
async def publish_text_message_endpoint(payload: PublishTextPayload):
    mqtt_payload = {
        "from": payload.source_id,
        "message": payload.message,
        "content_type": "text/plain",
        "timestamp": time.time()
    }
    mqtt_client.publish(MQTT_TOPIC_DOWN, json.dumps(mqtt_payload))
    # Add to local history for immediate feedback if desired, or wait for MQTT loopback
    # RECEIVED_MESSAGES.append(mqtt_payload)
    # await manager.broadcast(json.dumps(mqtt_payload)) # Async consideration
    return {"status": "text_message_published_to_mqtt_down", "data": mqtt_payload}

@app.post("/command_bridge/") # For sending files/commands to a specific user's bridge
async def command_bridge_endpoint(
    metadata_json: str = Form(...), # JSON string for BridgeCommandMetadata
    file: Optional[UploadFile] = File(None)
):
    try:
        metadata = BridgeCommandMetadata(**json.loads(metadata_json))
    except json.JSONDecodeError:
        return {"error": "Invalid metadata JSON"}, 400

    # Determine the target bridge ID. For now, using default.
    # In a multi-user system, this would be dynamic (e.g., from user session).
    target_bridge_id = USER_DEFAULT_BRIDGE_ID
    bridge_command_topic = f"{MQTT_TOPIC_BRIDGE_COMMAND_PREFIX}/{target_bridge_id}/command"

    mqtt_payload_to_bridge = {
        "command_action": metadata.action, # e.g., "transmit_lora_data"
        "from_user": metadata.source_id,
        "original_content_type": metadata.original_content_type,
        "filename": metadata.filename,
        "text_message": metadata.text_message, # For text to be sent via LoRa
        "timestamp": time.time()
    }

    if file and metadata.action in ["send_lora_audio", "send_lora_image", "send_lora_file"]:
        file_content = await file.read()
        mqtt_payload_to_bridge["data_b64"] = base64.b64encode(file_content).decode('utf-8')
    elif metadata.action == "send_lora_text" and not metadata.text_message:
         return {"error": "text_message is required for send_lora_text action"}, 400
    elif not file and metadata.action not in ["send_lora_text"]: # File required for these actions
        return {"error": f"File is required for action: {metadata.action}"}, 400


    logger.info(f"Publishing command to bridge topic {bridge_command_topic} for action {metadata.action}")
    result = mqtt_client.publish(bridge_command_topic, json.dumps(mqtt_payload_to_bridge), qos=1)
    if result.rc == paho.MQTT_ERR_SUCCESS:
        logger.info(f"Successfully published command to {bridge_command_topic}, mid: {result.mid}")
        return {"status": "instruction_sent_to_bridge", "action": metadata.action, "filename": metadata.filename, "bridge_topic": bridge_command_topic}
    else:
        logger.error(f"Failed to publish command to {bridge_command_topic}, rc: {result.rc}")
        return {"error": "Failed to send instruction to bridge via MQTT"}, 500


@app.get("/nodes_status")
async def get_nodes_status_endpoint():
    return NODES_STATUS

@app.get("/messages")
async def get_messages_endpoint(limit: int = 20):
    return list(RECEIVED_MESSAGES)[-limit:]


# Optional: A periodic task to publish all node statuses if needed,
# or to clean up old nodes.
# async def periodic_node_status_publisher():
#     while True:
#         await asyncio.sleep(60) # Every 60 seconds
#         logger.info("Broadcasting all node statuses...")
#         for node_id, node_data in list(NODES_STATUS.items()):
#             # Check if node is stale
#             if time.time() - node_data.get("last_seen", 0) > 300: # 5 minutes
#                 node_data["status"] = "offline"
#             # mqtt_client.publish(MQTT_TOPIC_NODES_STATUS, json.dumps(node_data), qos=1)
#         await manager.broadcast(json.dumps({"type": "all_nodes_status", "nodes": NODES_STATUS}))

# @app.on_event("startup")
# async def startup_event():
#    asyncio.create_task(periodic_node_status_publisher())
