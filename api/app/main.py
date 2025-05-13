import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
from paho.mqtt import client as mqtt_client
from pydantic import BaseModel
import logging

# Configuración MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "lorabridge/data")

# Buffer circular de mensajes
RECEIVED = deque(maxlen=100)

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
logger.info(f"MQTT Topic: {MQTT_TOPIC}")


# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    payload_str = msg.payload.decode()
    try:
        data = json.loads(payload_str)
    except Exception:
        data = {"raw": payload_str}
    RECEIVED.append({
        "topic": msg.topic,
        "payload": data,
        "source": "received"
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
    return {"status": "ok"}

@app.get("/messages/")
async def get_messages(limit: int = 20):
    msgs = list(RECEIVED)[-limit:]
    return {"count": len(RECEIVED), "messages": msgs}

@app.post("/publish/")
async def publish_message(payload: PublishPayload):
    mqtt.publish(MQTT_TOPIC, payload.message)
    RECEIVED.append({
        "topic": MQTT_TOPIC,
        "payload": payload.message,
        "source": "sent"
    })
    return {"published": payload.message}