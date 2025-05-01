#!/usr/bin/env python3
"""
gateway_pi.py
Pasarela LoRa (UART E22-SX1262 868 MHz)  ↔  MQTT (Mosquitto en localhost)

— Raspberry Pi con HAT Waveshare SX1262 —
  • UART 9600 bps → módulo E22 en modo transparente
  • Publica en  lora/uplink   lo que recibe por LoRa
  • Envía por LoRa todo lo que llega al tópico lora/downlink
"""

import time, sys, traceback
import serial
import paho.mqtt.client as mqtt

# ───── CONFIGURACIÓN ──────────────────────────────────────────────────────────
SERIAL_PORT    = "/dev/tty0"   # ó /dev/serial0 según tu Pi
BAUD_RATE      = 9600           # UART del módulo E22
MQTT_BROKER    = "localhost"
TOPIC_UPLINK   = "lora/uplink"     # Pi → MQTT
TOPIC_DOWNLINK = "lora/downlink"   # MQTT → Pi → LoRa
MQTT_QOS       = 0
# -----------------------------------------------------------------------------

# ───── UART ───────────────────────────────────────────────────────────────────
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.2)
except serial.SerialException as e:
    sys.exit(f"ERROR abriendo {SERIAL_PORT}: {e}")

# ───── Callbacks MQTT ────────────────────────────────────────────────────────
def on_connect(client, _userdata, _flags, rc, _properties=None):
    if rc == 0:
        print("[MQTT] Conectado ✔")
        client.subscribe(TOPIC_DOWNLINK, qos=MQTT_QOS)
    else:
        print("[MQTT] Falló la conexión, código:", rc)

def on_message(_client, _userdata, msg):
    try:
        payload = msg.payload.decode("utf-8").strip()
        if payload:
            print(f"[MQTT] ▼ {payload}")
            ser.write(payload.encode("utf-8") + b"\n")
            time.sleep(0.05)  # tiempo para conmutar a TX
            print("[LoRa]  ▲ enviado")
    except Exception:
        traceback.print_exc()

def on_disconnect(client, _userdata, rc, _properties=None):
    print("[MQTT] Desconectado (rc=%s) → reintento en 5 s" % rc)
    time.sleep(5)
    try:
        client.reconnect()
    except Exception:
        pass

# ───── Cliente MQTT ──────────────────────────────────────────────────────────
client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect
client.connect_async(MQTT_BROKER, 1883)
client.loop_start()

print("Gateway LoRa ↔ MQTT listo. Esperando tráfico ...")

# ───── Bucle principal ───────────────────────────────────────────────────────
try:
    while True:
        if ser.in_waiting:
            line = ser.readline().decode("utf-8", "ignore").strip()
            if line:
                print(f"[LoRa]  ▼ {line}")
                client.publish(TOPIC_UPLINK, line, qos=MQTT_QOS)
        else:
            time.sleep(0.05)
except KeyboardInterrupt:
    print("\nDetenido por usuario.")
finally:
    client.loop_stop()
    client.disconnect()
    ser.close()

