"""
main.py  – FastAPI + MQTT + alert_ai
------------------------------------
* /publish  ➜  publica en test/topic
* /info     ➜  info básica API
* En startup:
      – conecta al broker MQTT
      – arranca alert_ai (feeds RSS + GPT + puente alert/in → alert/out)
"""

import os, logging
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import paho.mqtt.client as mqtt

# ────────────────── Config por variables de entorno ────────────────
MQTT_BROKER = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT   = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "test/topic")

# ────────────────── MQTT client ------------------------------------
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(MQTT_TOPIC)
        logging.info("Subscrito a %s", MQTT_TOPIC)
    else:
        logging.error("MQTT connect rc=%s", rc)

def on_message(client, userdata, msg):
    print(f"[MQTT] {msg.topic}: {msg.payload.decode(errors='ignore')}")

mqtt_client.on_connect  = on_connect
mqtt_client.on_message  = on_message

# ────────────────── alert_ai hook ----------------------------------
try:
    from alert_ai import start as ia_start, stop as ia_stop
except ImportError:
    # si no quieres IA simplemente omite alert_ai.py
    def ia_start(): ...
    def ia_stop(): ...

# ────────────────── FastAPI ----------------------------------------
app = FastAPI(title="LoRaWAN FastAPI")

class PublishBody(BaseModel):
    message: str

@app.on_event("startup")
def startup():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()
    ia_start()                      # ← lanza el hilo IA
    logging.info("FastAPI + MQTT listos")

@app.on_event("shutdown")
def shutdown():
    ia_stop()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

# ───────────── Endpoints ───────────────────────────────────────────
@app.get("/")
async def read_root():
    return {"message": "API funcionando correctamente"}

@app.post("/publish")
async def publish_message(body: PublishBody, bt: BackgroundTasks):
    bt.add_task(mqtt_client.publish, MQTT_TOPIC, body.message)
    return {"message": f"Publicado: {body.message}", "topic": MQTT_TOPIC}

@app.get("/info")
async def get_info():
    return {
        "nombre_api": "LoRaWAN FastAPI",
        "version": "1.0",
        "descripcion": "Endpoints para publicar y recibir mensajes via MQTT + IA de alertas"
    }
