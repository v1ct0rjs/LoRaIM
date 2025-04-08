from fastapi import FastAPI
import paho.mqtt.client as mqtt

app = FastAPI()

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_TOPIC = "test/topic"

def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    print(f"Mensaje recibido: {msg.payload.decode()} en el tema {msg.topic}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.loop_start()

@app.get("/")
async def read_root():
    return {"message": "API funcionando correctamente"}

@app.post("/publish/")
async def publish_message(message: str):
    mqtt_client.publish(MQTT_TOPIC, message)
    return {"message": f"Publicado: {message}"}

