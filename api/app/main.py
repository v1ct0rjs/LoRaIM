import os
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
from paho.mqtt import client as mqtt_client

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
    print(f"[MQTT RX] {payload_str}")

# Crear cliente MQTT
mqtt = mqtt_client.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message
mqtt.connect(MQTT_BROKER, MQTT_PORT)
mqtt.loop_start()

# Endpoints
@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/messages/")
async def get_messages(limit: int = 20):
    msgs = list(RECEIVED)[-limit:]
    return {"count": len(RECEIVED), "messages": msgs}

@app.post("/publish/")
async def publish_message(request: Request):
    body = await request.json()
    message = body.get("message")
    if not message:
        return {"error": "No message provided"}

    mqtt.publish(MQTT_TOPIC, message)
    RECEIVED.append({
        "topic": MQTT_TOPIC,
        "payload": message,
        "source": "sent"
    })
    return {"published": message}