from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import os, paho.mqtt.client as mqtt

app = FastAPI()

# ─── Config via variables de entorno (mejor que literales) ──────────────
MQTT_BROKER = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT   = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "factory/cmd")

# ─── MQTT callbacks ─────────────────────────────────────────────────────
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        print("✔ Subscribed", MQTT_TOPIC)
    else:
        print("✖ MQTT connect error", rc)

def on_message(client, userdata, msg):
    print(f"[MQTT] {msg.topic}: {msg.payload.decode()}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect  = on_connect
mqtt_client.on_message  = on_message

# ─── Lanza el loop MQTT en un hilo al iniciar FastAPI ───────────────────
@app.on_event("startup")
def mqtt_start():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()

@app.on_event("shutdown")
def mqtt_end():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# ─── Modelo pydantic para el body POST (más limpio) ─────────────────────
class Msg(BaseModel):
    message: str

@app.post("/publish")
async def publish_message(body: Msg, bg: BackgroundTasks):
    # Publicamos en un hilo para no bloquear al cliente HTTP
    bg.add_task(mqtt_client.publish, MQTT_TOPIC, body.message)
    return {"published": body.message, "topic": MQTT_TOPIC}

@app.get("/")
async def root():
    return {"detail": "LoRaWAN FastAPI broker helper – OK"}

@app.get("/info")
async def info():
    return {
        "nombre_api": "LoRaWAN FastAPI",
        "version": "1.0",
        "descripcion": "Endpoints para publicar y escuchar mensajes vía MQTT",
        "topic": MQTT_TOPIC
    }
