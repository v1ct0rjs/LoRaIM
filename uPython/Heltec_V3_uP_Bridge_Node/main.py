"""
main.py  – Heltec V3  (ESP32‑S3 + SX1262 + OLED)
Wi‑Fi ➜ MQTT ➜ LoRa  *bridge*

• Lee TODOS los ajustes de un fichero /.env (si existe).
• Se conecta a Wi‑Fi, escucha un topic MQTT y retransmite cada payload
  por radio LoRa.
• Mantiene log en la pantalla OLED de 0,96 ʺ.

Coloca un archivo “.env” en la raíz del flash con, por ejemplo:

# Wi‑Fi
WIFI_SSID=SSID
WIFI_PASSWORD=password

# MQTT
MQTT_HOST=hostname or IP
MQTT_PORT=1883
MQTT_TOPIC=test/topic

# LoRa
FREQUENCY=866.3
BANDWIDTH=250.0
SPREADING_FACTOR=9
CODING_RATE=5
SYNC_WORD=0x12
TRANSMIT_POWER=0

# OLED
BRIGHTNESS=200
"""
# main.py  – Heltec V3 (ESP32‑S3 + SX1262 + OLED)
# Wi‑Fi → MQTT → LoRa bridge y LoRa → MQTT receiver

import time, gc, ubinascii
from machine import Pin, I2C
import network
from simple import MQTTClient
from sx1262 import SX1262
import ssd1306

# ───────────────────────────────────────────────────────────
# 1. utilidades .env
# ───────────────────────────────────────────────────────────

def load_env(path="/.env"):
    env = {}
    try:
        with open(path) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"): continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    except OSError:
        pass
    return env


def getenv(env, key, cast=str, default=None):
    try:
        return cast(env[key])
    except (KeyError, ValueError):
        return default

ENV = load_env()

# ───────────────────────────────────────────────────────────
# 2. Pines Heltec V3
# ───────────────────────────────────────────────────────────
LORA_CS, LORA_SCK, LORA_MOSI, LORA_MISO = 8, 9, 10, 11
LORA_RESET, LORA_BUSY, LORA_DIO1        = 12, 13, 14
VEXT, OLED_SCL, OLED_SDA, OLED_RST      = 36, 18, 17, 21

# ───────────────────────────────────────────────────────────
# 3. Parámetros
# ───────────────────────────────────────────────────────────
WIFI_SSID     = getenv(ENV, "WIFI_SSID", str, "MySSID")
WIFI_PASSWORD = getenv(ENV, "WIFI_PASSWORD", str, "password")

MQTT_HOST  = getenv(ENV, "MQTT_HOST", str, "192.168.1.40")
MQTT_PORT  = getenv(ENV, "MQTT_PORT", int, 1883)
MQTT_TOPIC = getenv(ENV, "MQTT_TOPIC", str, "lorabridge/data").encode()

FREQUENCY        = getenv(ENV, "FREQUENCY",        float, 866.3)
BANDWIDTH        = getenv(ENV, "BANDWIDTH",        float, 250.0)
SPREADING_FACTOR = getenv(ENV, "SPREADING_FACTOR", int,   9)
CODING_RATE      = getenv(ENV, "CODING_RATE",      int,   5)
SYNC_WORD        = getenv(ENV, "SYNC_WORD",  lambda x: int(x,0), 0x12)
TRANSMIT_POWER   = getenv(ENV, "TRANSMIT_POWER",   int,   0)

BRIGHTNESS = getenv(ENV, "BRIGHTNESS", int, 255)

# ───────────────────────────────────────────────────────────
# 4. OLED helpers
# ───────────────────────────────────────────────────────────
LINE_H, MAX_LINES = 12, 5
buffer = [""] * MAX_LINES

def oled_scroll(text):
    buffer.pop(0); buffer.append(text)
    oled.fill(0)
    for i, line in enumerate(buffer):
        oled.text(line, 0, i * LINE_H, 1)
    oled.show()
    print(text)

# ───────────────────────────────────────────────────────────
# 5. Hardware init
# ───────────────────────────────────────────────────────────

def init_oled():
    Pin(VEXT, Pin.OUT, value=0)
    rst = Pin(OLED_RST, Pin.OUT, value=0)
    time.sleep_ms(20); rst.value(1)
    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400_000)
    global oled
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.contrast(BRIGHTNESS)


def wifi_connect():
    wlan = network.WLAN(network.STA_IF); wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(50):
            if wlan.isconnected(): break
            oled_scroll("Conectando WiFi…"); time.sleep_ms(200)
    return wlan.ifconfig()[0] if wlan.isconnected() else "No Wi‑Fi"


def init_lora():
    l = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
               LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)
    err = l.begin(freq=FREQUENCY, bw=BANDWIDTH, sf=SPREADING_FACTOR,
                  cr=CODING_RATE, power=TRANSMIT_POWER, syncWord=SYNC_WORD,
                  blocking=True)
    if err: raise RuntimeError(f"LoRa init err {err}")
    return l

# ───────────────────────────────────────────────────────────
# 6. MQTT→LoRa callback
# ───────────────────────────────────────────────────────────

def make_mqtt_cb(lora):
    def _cb(topic, msg):
        oled_scroll("MQTT→LoRa:" + msg.decode()[:8])
        lora.send(msg + b"\n")
        oled_scroll("LoRa TX OK")
    return _cb

# ───────────────────────────────────────────────────────────
# 7. Main loop
# ───────────────────────────────────────────────────────────

def main():
    init_oled(); oled_scroll("Booting…")
    ip = wifi_connect(); oled_scroll("WiFi:" + ip)
    lora = init_lora(); oled_scroll("LoRa OK")

    # MQTT setup
    cid = b"bridge-" + ubinascii.hexlify(network.WLAN().config('mac')[-3:])
    mqtt = MQTTClient(cid, MQTT_HOST, MQTT_PORT)
    mqtt.set_callback(make_mqtt_cb(lora))
    mqtt.connect(); mqtt.subscribe(MQTT_TOPIC)
    oled_scroll("MQTT OK")

    PING_MS, last_ping = 10000, time.ticks_ms()
    mqtt_ok = True

    while True:
        now = time.ticks_ms()
        # keep-alive ping
        if mqtt_ok and time.ticks_diff(now, last_ping) > PING_MS:
            try:
                mqtt.ping(); last_ping = now
            except OSError:
                mqtt_ok = False

        # recepcionar MQTT y reenviar a LoRa
        if mqtt_ok:
            try:
                mqtt.check_msg()
            except OSError:
                mqtt_ok = False

        # reconexión silenciosa
        if not mqtt_ok:
            try:
                mqtt.connect(); mqtt.subscribe(MQTT_TOPIC); mqtt_ok = True
                oled_scroll("MQTT reconnected")
            except OSError:
                oled_scroll("MQTT err")

        # ── NUEVO: recibir LoRa y publicar en MQTT
        try:
            packet, status = lora.recv(timeout_en=True, timeout_ms=200)
            if status == 0 and packet:
                data = packet.strip()
                oled_scroll("LoRa RX")
                mqtt.publish(MQTT_TOPIC, data)
                oled_scroll("MQTT Pub")
        except Exception:
            pass

        gc.collect(); time.sleep_ms(50)

# Ejecutar
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        oled_scroll("Reboot by KB")
