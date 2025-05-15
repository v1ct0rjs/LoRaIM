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


# Configuración MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC_UP   = os.getenv("MQTT_TOPIC_UP",   "lorachat/up")
MQTT_TOPIC_DOWN = os.getenv("MQTT_TOPIC_DOWN", "lorachat/down")


# Buffer circular de mensajes
RECEIVED = deque(maxlen=100)
clients = []

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
    except Exception:
        message = payload_str
        sender = "desconocido"

    RECEIVED.append({
        "topic": msg.topic,
        "payload": message,
        "source": sender
    })
    logger.info(f"Received message: {data} from topic: {msg.topic}")

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
    end   = total - offset
    msgs  = list(RECEIVED)[start:end]
    return {"count": total, "messages": msgs}


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
        "source": "sent"
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
        while True:
            await asyncio.sleep(1)
            if RECEIVED:
                last_msg = RECEIVED[-1]
                await websocket.send_json(last_msg)
    except:
        clients.remove(websocket)