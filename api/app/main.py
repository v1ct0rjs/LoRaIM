import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket
from collections import deque
from paho.mqtt import client as mqtt_client
from pydantic import BaseModel
import logging
import asyncio
import time
from datetime import datetime

# Configuración MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC_UP = os.getenv("MQTT_TOPIC_UP", "lorachat/up")
MQTT_TOPIC_DOWN = os.getenv("MQTT_TOPIC_DOWN", "lorachat/down")
MQTT_TOPIC_NODES = os.getenv("MQTT_TOPIC_NODES", "lorachat/nodes")

# Buffer circular de mensajes
RECEIVED = deque(maxlen=100)
clients = []

# Registro de nodos activos
NODES = {}
NODE_TIMEOUT = 60  # segundos para considerar un nodo offline

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PublishPayload(BaseModel):
    message: str


class NodeInfo(BaseModel):
    id: str
    last_seen: float
    rssi: float = None
    snr: float = None
    status: str = "online"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"MQTT Broker: {MQTT_BROKER}")
logger.info(f"MQTT Port: {MQTT_PORT}")
logger.info(f"MQTT Topic: {MQTT_TOPIC_UP}")


# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    """
    Callback de conexión MQTT. Se llama cuando el cliente se conecta al broker.
    :param client:
    :param userdata:
    :param flags:
    :param rc:
    :return:
    """
    client.subscribe(MQTT_TOPIC_UP)


def on_message(client, userdata, msg):
    """
    Callback de mensaje MQTT. Se llama cuando se recibe un mensaje en un topic suscrito.
    :param client:
    :param userdata:
    :param msg:
    :return:
    """
    payload_str = msg.payload.decode()
    try:
        data = json.loads(payload_str)
        message = data.get("message", payload_str)
        sender = data.get("from", "desconocido")

        # Extraer métricas LoRa si están disponibles
        rssi = data.get("rssi")
        snr = data.get("snr")
        message_type = data.get("type")

        # Actualizar registro de nodos
        if sender != "sent":
            node_id = sender
            # Determinar si es el nodo puente (los nodos que empiezan con "Node-" son candidatos)
            is_bridge = node_id.startswith("Node-") and message_type == "bridge"

            NODES[node_id] = {
                "id": node_id,
                "last_seen": time.time(),
                "rssi": rssi,
                "snr": snr,
                "status": "online",
                "is_bridge": is_bridge  # Marcar explícitamente si es un nodo puente
            }

            # Publicar actualización de nodos
            publish_nodes_status()

        # Si es un mensaje de tipo "bridge" o solo contiene "online", no lo enviamos al chat
        if message_type == "bridge" or message == "online":
            return

    except Exception as e:
        message = payload_str
        sender = "desconocido"
        logger.error(f"Error processing message: {e}")

    RECEIVED.append({
        "topic": msg.topic,
        "payload": message,
        "source": sender,
        "rssi": rssi if 'rssi' in locals() else None,
        "snr": snr if 'snr' in locals() else None,
        "timestamp": time.time()
    })
    logger.info(f"Received message: {data} from topic: {msg.topic}")

    # Notificar a todos los clientes WebSocket
    notify_clients()


def publish_nodes_status():
    """
    Publica el estado de todos los nodos a través de MQTT
    """
    # Actualizar estado de nodos (online/offline)
    now = time.time()
    nodes_list = []

    for node_id, info in list(NODES.items()):
        # Verificar si el nodo está activo
        if now - info["last_seen"] > NODE_TIMEOUT:
            info["status"] = "offline"
        else:
            info["status"] = "online"

        # Asegurarse de que la propiedad is_bridge esté presente
        if "is_bridge" not in info:
            info["is_bridge"] = node_id.startswith("Node-")

        nodes_list.append(info)

    # Publicar estado de nodos
    try:
        mqtt.publish(MQTT_TOPIC_NODES, json.dumps({
            "nodes": nodes_list,
            "timestamp": now
        }))
    except Exception as e:
        logger.error(f"Error publishing nodes status: {e}")


async def check_nodes_status():
    """
    Tarea periódica para verificar el estado de los nodos
    """
    while True:
        publish_nodes_status()
        await asyncio.sleep(15)  # Verificar cada 15 segundos


def notify_clients():
    """
    Notifica a todos los clientes WebSocket sobre nuevos mensajes
    """
    if RECEIVED and clients:
        last_msg = RECEIVED[-1]
        for client in clients:
            try:
                asyncio.create_task(client.send_json(last_msg))
            except Exception as e:
                logger.error(f"Error notifying client: {e}")


# Crear cliente MQTT
mqtt = mqtt_client.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message
try:
    mqtt.connect(MQTT_BROKER, MQTT_PORT)
    mqtt.loop_start()
except Exception as e:
    logger.error(f"Failed to connect to MQTT broker: {e}")
    raise


# Endpoints
@app.get("/")
async def root():
    """
    Endpoint de prueba. Devuelve un mensaje de estado.
    :return:
    """
    return {"status": "ok"}


@app.get("/messages/")
async def get_messages(limit: int = 20, offset: int = 0):
    """
    Devuelve 'limit' mensajes *anteriores* al índice 'offset'
    (0 = el más reciente). Sirve para paginación inversa.
    """
    total = len(RECEIVED)
    start = max(total - offset - limit, 0)
    end = total - offset
    msgs = list(RECEIVED)[start:end]
    return {"count": total, "messages": msgs}


@app.get("/nodes/")
async def get_nodes():
    """
    Devuelve la lista de nodos y su estado
    """
    # Actualizar estado de nodos
    now = time.time()
    nodes_list = []

    for node_id, info in list(NODES.items()):
        # Verificar si el nodo está activo
        if now - info["last_seen"] > NODE_TIMEOUT:
            info["status"] = "offline"
        else:
            info["status"] = "online"

        nodes_list.append(info)

    return {"nodes": nodes_list}


@app.post("/publish/")
async def publish_message(payload: PublishPayload):
    """
    Endpoint para publicar un mensaje en el topic MQTT.
    :param payload:
    :return:
    """
    out = {
        "from": "sent",
        "message": payload.message
    }
    json_msg = json.dumps(out)
    mqtt.publish(MQTT_TOPIC_DOWN, json_msg)
    RECEIVED.append({
        "topic": MQTT_TOPIC_DOWN,
        "payload": payload.message,
        "source": "sent",
        "timestamp": time.time()
    })
    return {"published": out}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para recibir mensajes en tiempo real.
    :param websocket:
    :return:
    """
    await websocket.accept()
    clients.append(websocket)
    try:
        # Enviar estado inicial de nodos
        await websocket.send_json({"type": "nodes_update", "nodes": list(NODES.values())})

        while True:
            await asyncio.sleep(1)
            if RECEIVED:
                last_msg = RECEIVED[-1]
                await websocket.send_json(last_msg)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        clients.remove(websocket)


@app.on_event("startup")
async def startup_event():
    """
    Evento de inicio de la aplicación
    """
    # Iniciar tarea de verificación de nodos
    asyncio.create_task(check_nodes_status())
