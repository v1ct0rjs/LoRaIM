from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import time
import paho.mqtt.client as paho
from paho import mqtt  # For mqtt.client.ssl.PROTOCOL_TLS
import logging
from typing import Optional, List, Dict
import base64
import os
import asyncio  # Added for async operations

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# MQTT Configuration
MQTT_CLIENT_ID = f'fastapi_mqtt_{int(time.time())}'
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")  # Default to local mosquitto service
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
# Only use MQTT_USERNAME and MQTT_PASSWORD if MQTT_USERNAME is explicitly set
MQTT_USERNAME = os.getenv("MQTT_USERNAME")  # No default username
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")  # No default password

MQTT_TOPIC_UP = "chat/up"
MQTT_TOPIC_DOWN = "chat/down"
MQTT_TOPIC_NODES_STATUS = "nodes/status"
MQTT_TOPIC_BRIDGE_COMMAND_PREFIX = "lora_bridge"

USER_DEFAULT_BRIDGE_ID = os.getenv("USER_DEFAULT_BRIDGE_ID", "default_bridge_node")

# Data Structures
RECEIVED_MESSAGES: List[Dict] = []
NODES_STATUS: Dict[str, Dict] = {}


# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.broadcast_queue = asyncio.Queue()  # Queue for broadcasting messages


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
        logger.error(f"Error sending personal message to {websocket.client}: {e}")
        self.disconnect(websocket)


async def schedule_broadcast(self, message: str):  # Renamed from broadcast
    await self.broadcast_queue.put(message)


async def broadcast_processor(self):  # Task to process broadcast queue
    logger.info("Broadcast processor started.")
    while True:
        message = await self.broadcast_queue.get()
        for connection in list(self.active_connections):  # Iterate over a copy
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message to {connection.client}: {e}")
                self.disconnect(connection)
        self.broadcast_queue.task_done()


manager = ConnectionManager()


# Pydantic Models
class PublishTextPayload(BaseModel):
    message: str


source_id: Optional[str] = "web_client"


class NodeStatusUpdate(BaseModel):
    id: str


status: str
last_seen: float
rssi: Optional[int] = None
snr: Optional[float] = None
is_bridge: Optional[bool] = False


class BridgeCommandMetadata(BaseModel):
    action: str


original_content_type: Optional[str] = None
filename: Optional[str] = None
source_id: Optional[str] = "web_client"
text_message: Optional[str] = None


# --- MQTT Callback Definitions ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"MQTT Connected successfully to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC_UP, qos=1)
        client.subscribe(f"{MQTT_TOPIC_BRIDGE_COMMAND_PREFIX}/+/status", qos=1)
        client.subscribe(MQTT_TOPIC_NODES_STATUS, qos=1)
    else:
        logger.error(f"MQTT Connection failed for {MQTT_BROKER}:{MQTT_PORT} with result code {rc}")


def on_disconnect(client, userdata, rc, properties=None):
    logger.warning(f"MQTT Disconnected from {MQTT_BROKER}:{MQTT_PORT} with result code {rc}.")


def on_message(client, userdata, msg):
    payload_str = ""


try:
    payload_str = msg.payload.decode()
    data = json.loads(payload_str)
    logger.debug(f"MQTT message received on topic '{msg.topic}': {data}")

    is_chat_message = True
    node_id_from_message = None  # To store the determined node ID

    if msg.topic.startswith(MQTT_TOPIC_BRIDGE_COMMAND_PREFIX) and msg.topic.endswith("/status"):
        node_id_from_message = data.get("id", msg.topic.split('/')[-2])
        is_chat_message = False
    elif msg.topic == MQTT_TOPIC_NODES_STATUS:
        node_id_from_message = data.get("id")
        is_chat_message = False
    else:  # Assumed to be a chat message from MQTT_TOPIC_UP
        node_id_from_message = data.get("node_id_lora", data.get("from", "desconocido"))

    if node_id_from_message and node_id_from_message not in ["web_client", "sent", "?", "desconocido",
                                                             "desconocido_raw"]:
        current_time = time.time()
        NODES_STATUS[node_id_from_message] = {
            "id": node_id_from_message,
            "last_seen": data.get("timestamp", current_time),
            "rssi": data.get("rssi"),
            "snr": data.get("snr"),
            "status": data.get("status", "online"),
            "is_bridge": data.get("is_bridge", False) or msg.topic.startswith(MQTT_TOPIC_BRIDGE_COMMAND_PREFIX)
        }
        # Schedule node status update broadcast
        asyncio.run_coroutine_threadsafe(
            manager.schedule_broadcast(json.dumps({"type": "node_update", "data": NODES_STATUS[node_id_from_message]})),
            asyncio.get_event_loop()
        )

    if is_chat_message:
        chat_payload = {
            "topic": msg.topic,
            "payload": data.get("message", data.get("filename", "binary_data")),
            "source": data.get("from", "desconocido"),
            "node_id_lora": data.get("node_id_lora", data.get("from", "desconocido")),
            "rssi": data.get("rssi"),
            "snr": data.get("snr"),
            "content_type": data.get("content_type", "text/plain"),
            "data_b64": data.get("data_b64"),
            "filename": data.get("filename"),
            "timestamp": data.get("timestamp", time.time())
        }
        RECEIVED_MESSAGES.append(chat_payload)
        if len(RECEIVED_MESSAGES) > 100:
            RECEIVED_MESSAGES.pop(0)

        asyncio.run_coroutine_threadsafe(
            manager.schedule_broadcast(json.dumps(chat_payload)),
            asyncio.get_event_loop()
        )

except json.JSONDecodeError:
    logger.warning(f"MQTT message on topic '{msg.topic}' is not valid JSON: {payload_str[:100]}")
    chat_payload = {
        "topic": msg.topic, "payload": payload_str, "source": "unknown_raw_sender",
        "content_type": "text/plain", "timestamp": time.time()
    }
    RECEIVED_MESSAGES.append(chat_payload)
    asyncio.run_coroutine_threadsafe(
        manager.schedule_broadcast(json.dumps(chat_payload)),
        asyncio.get_event_loop()
    )
except Exception as e:
    logger.error(f"Error processing MQTT message on topic '{msg.topic}': {e}. Payload: {payload_str[:100]}")


# --- MQTT Client Setup ---
def mqtt_connect_client():
    client = paho.Client(client_id=MQTT_CLIENT_ID, protocol=paho.MQTTv5)


client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

# Only set username and password if MQTT_USERNAME is provided
if MQTT_USERNAME:
    logger.info(f"MQTT authentication enabled with username: {MQTT_USERNAME}")
    if not MQTT_PASSWORD:
        logger.warning("MQTT_USERNAME is set, but MQTT_PASSWORD is not. Connection might fail.")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
else:
    logger.info("MQTT authentication not enabled (MQTT_USERNAME not set). Attempting anonymous connection.")

# Corrected TLS logic:
# This logic should primarily apply if connecting to an external broker that might use TLS.
# For the internal 'mosquitto' service, TLS is typically not used unless explicitly configured.
if MQTT_BROKER == "test.mosquitto.org" and MQTT_PORT == 8883:
    logger.info(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}, enabling TLS.")
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
elif MQTT_BROKER != "mosquitto" and MQTT_PORT == 8883:  # General rule for other brokers on 8883
    logger.info(f"MQTT Port is {MQTT_PORT} for external broker {MQTT_BROKER}, enabling TLS.")
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
else:
    logger.info(f"Connecting to {MQTT_BROKER}:{MQTT_PORT}. TLS not enabled by default for this setup.")

try:
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    logger.info(f"Attempting to connect to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
except Exception as e:
    logger.error(f"MQTT connection failed during connect() call for {MQTT_BROKER}:{MQTT_PORT}: {e}")
    raise
return client

mqtt_client = mqtt_connect_client()  # This will raise an exception if connect fails, stopping app startup
mqtt_client.loop_start()


# --- FastAPI Event Handlers ---
@app.on_event("startup")
async def startup_event():


# Start the broadcast processor task
asyncio.create_task(manager.broadcast_processor())
# Ensure MQTT client is connected, or attempt reconnect if loop_start allows
# loop_start() handles reconnections for network issues, but not initial connect failure here.
if not mqtt_client.is_connected():
    logger.warning("MQTT client not connected at startup. loop_start() will attempt to reconnect.")


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Application shutdown: stopping MQTT client.")


mqtt_client.loop_stop()
mqtt_client.disconnect()


# --- FastAPI Endpoints ---
@app.get("/")
async def get_root():
    return HTMLResponse("<h1>LoRaIM API Backend</h1><p>WebSocket at /ws</p>")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)


for msg_data in list(RECEIVED_MESSAGES)[-20:]:
    await manager.send_personal_message(json.dumps(msg_data), websocket)
await manager.send_personal_message(json.dumps({"type": "all_nodes_status", "nodes": NODES_STATUS}), websocket)
try:
    while True:
        data = await websocket.receive_text()  # Keep alive or handle client messages
        logger.debug(f"Received from WebSocket {websocket.client}: {data}")
except WebSocketDisconnect:
    logger.info(f"WebSocket {websocket.client} disconnected (expected).")
except Exception as e:
    logger.error(f"WebSocket error for {websocket.client}: {e}")
finally:
    manager.disconnect(websocket)


@app.post("/publish_text")
async def publish_text_message_endpoint(payload: PublishTextPayload):
    mqtt_payload = {
        "from": payload.source_id,
        "message": payload.message,
        "content_type": "text/plain",
        "timestamp": time.time()
    }


result = mqtt_client.publish(MQTT_TOPIC_DOWN, json.dumps(mqtt_payload), qos=1)
if result.rc == paho.MQTT_ERR_SUCCESS:
    return {"status": "text_message_published_to_mqtt_down", "data": mqtt_payload}
else:
    logger.error(f"Failed to publish text to {MQTT_TOPIC_DOWN}, rc: {result.rc}")
    return {"error": "Failed to publish text message via MQTT"}, 500


@app.post("/command_bridge/")
async def command_bridge_endpoint(
        metadata_json: str = Form(...),
        file: Optional[UploadFile] = File(None)
):
    try:
        metadata = BridgeCommandMetadata(**json.loads(metadata_json))
    except json.JSONDecodeError:
        return {"error": "Invalid metadata JSON"}, 400


target_bridge_id = USER_DEFAULT_BRIDGE_ID
bridge_command_topic = f"{MQTT_TOPIC_BRIDGE_COMMAND_PREFIX}/{target_bridge_id}/command"

mqtt_payload_to_bridge = {
    "command_action": metadata.action,
    "from_user": metadata.source_id,
    "original_content_type": metadata.original_content_type,
    "filename": metadata.filename,
    "text_message": metadata.text_message,
    "timestamp": time.time()
}

if file and metadata.action in ["send_lora_audio", "send_lora_image", "send_lora_file"]:
    file_content = await file.read()
    mqtt_payload_to_bridge["data_b64"] = base64.b64encode(file_content).decode('utf-8')
elif metadata.action == "send_lora_text" and not metadata.text_message:
    return {"error": "text_message is required for send_lora_text action"}, 400
elif not file and metadata.action not in ["send_lora_text", "some_other_fileless_action"]:
    return {"error": f"File is required for action: {metadata.action}"}, 400

logger.info(f"Publishing command to bridge topic {bridge_command_topic} for action {metadata.action}")
result = mqtt_client.publish(bridge_command_topic, json.dumps(mqtt_payload_to_bridge), qos=1)
if result.rc == paho.MQTT_ERR_SUCCESS:
    return {"status": "instruction_sent_to_bridge", "action": metadata.action, "filename": metadata.filename,
            "bridge_topic": bridge_command_topic}
else:
    logger.error(f"Failed to publish command to {bridge_command_topic}, rc: {result.rc}")
    return {"error": "Failed to send instruction to bridge via MQTT"}, 500


@app.get("/nodes_status")
async def get_nodes_status_endpoint():
    return NODES_STATUS


@app.get("/messages")
async def get_messages_endpoint(limit: int = 20):
    return list(RECEIVED_MESSAGES)[-limit:]
