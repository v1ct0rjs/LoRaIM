# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import paho.mqtt.client as mqtt
from collections import deque
import json
import os

app = FastAPI()

# CORS para permitir acceso desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de conexión MQTT (pueden sobreescribirse con env vars)
MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "lorabridge/data")

# Almacén circular de mensajes recibidos
RECEIVED = deque(maxlen=100)

# Callbacks MQTT
def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    try:
        data = json.loads(payload)
    except Exception:
        data = {"raw": payload}
    RECEIVED.append({
        "topic": msg.topic,
        "payload": data
    })
    print(f"[MQTT] RX: {payload} on {msg.topic}")

# Cliente MQTT
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

# Endpoints
@app.get("/")
async def read_root():
    return {"message": "API funcionando correctamente"}

@app.get("/messages/")
async def get_messages(limit: int = 20):
    msgs = list(RECEIVED)[-limit:]
    return {
        "count": len(RECEIVED),
        "messages": msgs
    }

@app.post("/publish/")
async def publish_message(request: Request):
    data = await request.json()
    message = data.get("message")
    if not message:
        return {"error": "No message provided"}
    mqtt_client.publish(MQTT_TOPIC, message)
    return {"published": message}

@app.get("/info")
async def get_info():
    return {
        "nombre_api": "LoRaWAN FastAPI",
        "version": "1.1",
        "descripcion": "Ofrece endpoints para publicar y recibir mensajes via MQTT."
    }


