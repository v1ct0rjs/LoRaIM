from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import time
import paho.mqtt.client as paho
from paho import mqtt
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ... (otros imports)
from fastapi import File, UploadFile, Form
from typing import Optional
import base64
import os  # Para obtener variables de entorno

app = FastAPI()

# MQTT Configuration
MQTT_CLIENT_ID = f'fastapi_mqtt_{time.time()}'
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")  # Use environment variable or default
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))  # Use environment variable or default
MQTT_TOPIC_UP = "chat/up"
MQTT_TOPIC_DOWN = "chat/down"
MQTT_TOPIC_NODES = "nodes/status"

# Asumir que el ID del nodo puente del usuario se conoce o se configura
# Para este ejemplo, lo leeremos de una variable de entorno o usaremos un default.
# En una aplicación real, esto podría venir de la autenticación del usuario.
USER_BRIDGE_ID = os.getenv("USER_DEFAULT_BRIDGE_ID", "default_bridge_node")  # El ID del nodo puente local del usuario

# Data Structures
RECEIVED = []
NODES = {}
CONNECTIONS = []


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message to a client: {e}")
                self.disconnect(connection)  # Remove problematic connection


manager = ConnectionManager()


# Pydantic Models
class PublishPayload(BaseModel):
    topic: str
    message: str
    source: str


class NodeStatus(BaseModel):
    id: str
    status: str
    last_seen: float
    rssi: Optional[int] = None
    snr: Optional[float] = None
    is_bridge: Optional[bool] = False


class PublishMetadata(BaseModel):
    action: str  # e.g., "send_lora_audio", "send_lora_image", "send_text"
    original_content_type: Optional[str] = None
    filename: Optional[str] = None
    source_id: Optional[str] = "web_client"
    # Podrías añadir target_node_id si quieres enviar a un nodo LoRa específico


# MQTT Client Setup
def on_connect(client, userdata, flags, rc, properties=None):
    logger.info("MQTT Connected with result code " + str(rc))
    client.subscribe(MQTT_TOPIC_UP, qos=1)
    # client.subscribe("lora_bridge/+/status", qos=1) # Suscribirse a todos los estados de los puentes


def on_disconnect(client, userdata, rc):
    logger.info("MQTT Disconnected with result code " + str(rc))


def mqtt_connect():
    client = paho.Client(client_id=MQTT_CLIENT_ID, userdata=None, protocol=paho.MQTTv5)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message  # Assign the message callback
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    client.username_pw_set("akyvqaco", "iJ9JikQMjJkc")
    client.connect(MQTT_BROKER, MQTT_PORT)
    return client


mqtt = mqtt_connect()
mqtt.loop_start()


# FastAPI Endpoints
@app.get("/")
async def get():
    return HTMLResponse(open("api/app/index.html").read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    CONNECTIONS.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"Client says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        CONNECTIONS.remove(websocket)
        logger.info("Client disconnected")


@app.post("/publish")
async def publish_message(payload: PublishPayload):
    mqtt.publish(payload.topic, payload.message)
    RECEIVED.append(
        {"topic": payload.topic, "payload": payload.message, "source": payload.source, "timestamp": time.time()})
    notify_clients()
    return {"status": "published"}


# Modificar el endpoint /publish para manejar FormData
@app.post("/publish/")
async def publish_message_formdata(
        metadata: Optional[str] = Form(None),  # JSON string con metadatos
        file: Optional[UploadFile] = File(None)
):
    """
    Endpoint para publicar un mensaje (texto, audio o imagen).
    Audio/imagen se envían como 'file'.
    Texto y otros comandos se envían en 'metadata'.
    """
    parsed_metadata: PublishMetadata
    if metadata:
        try:
            parsed_metadata = PublishMetadata(**json.loads(metadata))
        except json.JSONDecodeError:
            return {"error": "Invalid metadata JSON"}
    elif file:  # Si hay archivo pero no metadata, inferir
        parsed_metadata = PublishMetadata(action="send_lora_file", filename=file.filename,
                                          original_content_type=file.content_type)
    else:  # Si no hay ni file ni metadata con mensaje de texto
        # Permitir enviar mensajes de texto simples sin 'file'
        # Esto requiere que el cliente envíe metadata con action="send_text" y message=".."
        # O modificar el PublishPayload original para que sea parte de metadata
        return {"error": "No file or text message metadata provided"}

    source_id = parsed_metadata.source_id or "web_client"
    action = parsed_metadata.action

    mqtt_payload_to_bridge = {}
    # El topic para instruir al nodo puente local del usuario
    # En una app multiusuario, USER_BRIDGE_ID sería dinámico.
    bridge_command_topic = f"lora_bridge/{USER_BRIDGE_ID}/command"

    if action in ["send_lora_audio", "send_lora_image", "send_lora_file"] and file:
        file_content = await file.read()
        # El backend podría comprimir aquí a ADPCM si es audio WAV/Opus
        # Por ahora, pasamos el contenido tal cual (o como base64) al puente.
        # El puente se encargará de la compresión final a ADPCM si es necesario.

        mqtt_payload_to_bridge = {
            "command": "transmit_lora_data",
            "from_user": source_id,  # Quién originó esto en la web
            "content_type": parsed_metadata.original_content_type,  # ej: "audio/webm", "image/png"
            "filename": parsed_metadata.filename or file.filename,
            "data_b64": base64.b64encode(file_content).decode('utf-8'),
            "timestamp": time.time()
            # Podrías añadir 'target_lora_node_id' aquí si quieres enviar a un nodo específico
        }
        logger.info(
            f"Publishing command to bridge topic {bridge_command_topic} for file {mqtt_payload_to_bridge['filename']}")
        mqtt.publish(bridge_command_topic, json.dumps(mqtt_payload_to_bridge))

        # No añadir a RECEIVED localmente, ya que esto es una instrucción para el puente.
        # El mensaje real en el chat aparecerá cuando el puente lo envíe por LoRa y vuelva.
        # Opcionalmente, podrías añadir un mensaje local "enviando..."
        return {"status": "instruction_sent_to_bridge", "filename": mqtt_payload_to_bridge['filename']}

    elif action == "send_text":
        # Asumimos que el mensaje de texto está dentro de parsed_metadata
        # Necesitaríamos añadir un campo 'message' a PublishMetadata
        # Por ahora, este flujo de texto se manejaría como antes (publicación a MQTT_TOPIC_DOWN)
        # o también podría ir por el bridge_command_topic si el texto es para LoRa.
        # Para simplificar, mantendremos el flujo de texto como estaba (publicar a MQTT_TOPIC_DOWN general).
        # Esto requeriría que el cliente envíe texto de forma diferente.
        # Reutilizando el PublishPayload anterior para texto:
        text_message = getattr(parsed_metadata, 'message', None)  # Suponiendo que 'message' está en metadata
        if not text_message:
            return {"error": "No text message in metadata for send_text action"}

        out_payload = {
            "from": source_id,
            "message": text_message,
            "content_type": "text/plain",
            "timestamp": time.time()
        }
        mqtt.publish(MQTT_TOPIC_DOWN, json.dumps(out_payload))
        RECEIVED.append({
            "topic": MQTT_TOPIC_DOWN, "payload": text_message, "source": source_id,
            "content_type": "text/plain", "timestamp": time.time()
        })
        notify_clients()
        return {"published_text": out_payload}
    else:
        return {"error": f"Unknown action or missing file: {action}"}


@app.get("/nodes")
async def get_nodes():
    return NODES


def publish_nodes_status():
    """Publish the status of all known nodes to MQTT."""
    for node_id, node_data in NODES.items():
        status_payload = NodeStatus(**node_data).json()
        mqtt.publish(MQTT_TOPIC_NODES, status_payload)
        logger.info(f"Published node status: {status_payload}")


def notify_clients():
    """
    Notifies all connected WebSocket clients about new messages.
    """
    for connection in CONNECTIONS:
        try:
            message = json.dumps(RECEIVED[-1])  # Send only the latest message
            mqtt.publish("chat/updates", message)  # Publicar también por MQTT
            # await connection.send_text(message) # No enviar directamente por WS, sino por MQTT
        except Exception as e:
            logger.error(f"Error notifying client: {e}")
            manager.disconnect(connection)


def on_message(client, userdata, msg):
    """
    Callback de mensaje MQTT. Se llama cuando se recibe un mensaje en un topic suscrito.
    """
    payload_str = msg.payload.decode()
    try:
        data = json.loads(payload_str)

        # Extraer campos comunes
        message_text = data.get("message")
        sender = data.get("from", "desconocido")  # Puede ser el ID del nodo LoRa o el ID del puente
        content_type = data.get("content_type", "text/plain")
        rssi = data.get("rssi")
        snr = data.get("snr")
        # ID del nodo LoRa original que envió el mensaje, si es diferente del 'from' (que podría ser el puente)
        node_id_lora = data.get("node_id_lora", sender)
        data_b64 = data.get("data_b64")
        filename = data.get("filename")
        timestamp = data.get("timestamp", time.time())

        # Actualizar registro de nodos (si es un mensaje de un nodo LoRa o estado del puente)
        # Usar node_id_lora para la clave si está presente, sino 'sender'
        node_key_for_status = node_id_lora if node_id_lora and node_id_lora != "desconocido" else sender

        # Solo actualizar si node_key_for_status es un ID de nodo válido (no web_client, etc.)
        # y no es un mensaje enviado por el propio web_client (evitar bucles de estado)
        if node_key_for_status not in ["web_client", "sent", "?"]:
            NODES[node_key_for_status] = {
                "id": node_key_for_status,
                "last_seen": timestamp,
                "rssi": rssi,  # Puede ser None si es estado del puente
                "snr": snr,  # Puede ser None
                "status": "online",
                "is_bridge": data.get("is_bridge", False) or msg.topic.startswith("lora_bridge/")
                # Marcar como puente si viene de su topic de estado
            }
            publish_nodes_status()  # Notificar a los clientes sobre el estado de los nodos

        # Si es un mensaje de tipo "bridge_status" o solo contiene "online" y es texto plano, no lo enviamos al chat.
        # Estos son para mantener el estado del nodo.
        if data.get("type") == "bridge_status" or \
                (content_type == "text/plain" and message_text == "online" and data.get("is_bridge")):
            logger.info(f"Bridge/Node status update from {sender} (key: {node_key_for_status})")
            return  # No añadir a RECEIVED ni notificar a clientes de chat

        # Determinar el payload para la UI
        display_payload = message_text
        if content_type.startswith("audio/") or content_type.startswith("image/"):
            display_payload = filename or content_type

        RECEIVED.append({
            "topic": msg.topic,
            "payload": display_payload,
            "source": sender,  # Quién lo envió (puede ser el puente)
            "node_id_lora": node_id_lora,  # El nodo LoRa original
            "rssi": rssi,
            "snr": snr,
            "content_type": content_type,
            "data_b64": data_b64,
            "filename": filename,
            "timestamp": timestamp
        })
        logger.info(f"Received message for chat: {data} from topic: {msg.topic}")

        notify_clients()  # Notificar a todos los clientes WebSocket

    except json.JSONDecodeError:
        message_text = payload_str
        sender = "desconocido_raw"
        content_type = "text/plain"
        RECEIVED.append({
            "topic": msg.topic, "payload": message_text, "source": sender,
            "content_type": content_type, "timestamp": time.time()
        })
        logger.info(f"Received raw message for chat: {message_text} from topic: {msg.topic}")
        notify_clients()
    except Exception as e:
        logger.error(f"Error processing message: {e}, payload: {payload_str}")

# En mqtt_connect, el puente también debería suscribirse a su topic de comando
# Esto es conceptual, ya que el backend no sabe los IDs de todos los puentes
# A menos que los puentes se registren.
# Por ahora, el backend publica y el puente específico debe estar suscrito.
# El puente también debe publicar su propio estado (ej. "online", "is_bridge": True)
# a MQTT_TOPIC_UP para que el backend lo conozca.
