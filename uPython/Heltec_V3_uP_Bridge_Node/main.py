"""
HeltecV3ESP32‑S3  –  LoRa↔MQTTbridge

✓ Lee TODOS los parámetros de /.env (Wi‑Fi, MQTT, LoRa, OLED…)
✓ Genera automáticamente NODE_NAME = "Node‑XXXXXX" con la MAC
✓ Topics MQTT:
      • MQTT_TOPIC_DOWN  (LoRa⬅backend)   [por defecto lorachat/down]
      • MQTT_TOPIC_UP    (LoRa➡backend)   [por defecto lorachat/up]
✓ Funciones:
      – Mensajes que llegan a MQTT_TOPIC_DOWN  →  se envían por LoRa como
        {"from": NODE_NAME, "message": "..."}.
      – Paquetes LoRa recibidos  →  se publican sin tocar en MQTT_TOPIC_UP.
"""
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

# ─────────── Imports ───────────
import time, gc, ubinascii, ujson
from machine  import Pin, I2C
import network
from simple   import MQTTClient
from sx1262   import SX1262
import ssd1306

# ─────────── 1. Leer .env ───────────
def load_env(path="/.env"):
    env = {}
    try:
        with open(path) as f:
            for raw in f:
                line = raw.strip()
                if line and not line.startswith("#"):
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

# ─────────── 2. Pines Heltec V3 ───────────
LORA_CS, LORA_SCK, LORA_MOSI, LORA_MISO = 8, 9, 10, 11
LORA_RESET, LORA_BUSY, LORA_DIO1        = 12, 13, 14
VEXT, OLED_SCL, OLED_SDA, OLED_RST      = 36, 18, 17, 21

# ─────────── 3. Parámetros desde .env ───────────
WIFI_SSID     = getenv(ENV, "WIFI_SSID", str, "MySSID")
WIFI_PASSWORD = getenv(ENV, "WIFI_PASSWORD", str, "password")

MQTT_HOST       = getenv(ENV, "MQTT_HOST", str, "192.168.1.40")
MQTT_PORT       = getenv(ENV, "MQTT_PORT", int, 1883)
MQTT_USER       = getenv(ENV, "MQTT_USER", str, None)
MQTT_PASSWORD   = getenv(ENV, "MQTT_PASSWORD", str, None)
MQTT_TOPIC_DOWN = getenv(ENV, "MQTT_TOPIC_DOWN", str, "lorachat/down").encode()
MQTT_TOPIC_UP   = getenv(ENV, "MQTT_TOPIC_UP",   str, "lorachat/up").encode()

FREQUENCY        = getenv(ENV, "FREQUENCY",        float, 866.3)
BANDWIDTH        = getenv(ENV, "BANDWIDTH",        float, 250.0)
SPREADING_FACTOR = getenv(ENV, "SPREADING_FACTOR", int,   9)
CODING_RATE      = getenv(ENV, "CODING_RATE",      int,   5)
SYNC_WORD        = getenv(ENV, "SYNC_WORD",  lambda x: int(x,0), 0x12)
TRANSMIT_POWER   = getenv(ENV, "TRANSMIT_POWER",   int,   0)

BRIGHTNESS = getenv(ENV, "BRIGHTNESS", int, 200)

# ─────────── 4. OLED helpers ───────────
LINE_H, MAX_LINES = 12, 5
_lines = [""] * MAX_LINES
def oled_log(txt):
    _lines.pop(0); _lines.append(txt)
    oled.fill(0)
    for i,l in enumerate(_lines):
        oled.text(l, 0, i*LINE_H, 1)
    oled.show()
    print(txt)

# ─────────── 5. Init hardware ───────────
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
        for _ in range(60):
            if wlan.isconnected(): break
            oled_log("WiFi…"); time.sleep_ms(200)
    return wlan.ifconfig()[0] if wlan.isconnected() else "NO‑WIFI"

def init_lora():
    l = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
               LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)
    err = l.begin(freq=FREQUENCY, bw=BANDWIDTH, sf=SPREADING_FACTOR,
                  cr=CODING_RATE, power=TRANSMIT_POWER, syncWord=SYNC_WORD,
                  blocking=True)
    if err: raise RuntimeError("LoRa init error %d" % err)
    return l

# ─────────── 6. Generar NODE_NAME único ───────────
mac = network.WLAN(network.STA_IF).config('mac')
NODE_NAME = "Node-" + ubinascii.hexlify(mac).decode()[-6:].upper()

# ─────────── 7. MQTT → LoRa callback ───────────
def make_downlink_cb(lora):
    def _cb(topic, msg):
        try:
            data = ujson.loads(msg)
            text = data.get("message", msg.decode())
        except:
            text = msg.decode()
        if not text: return
        pkt = ujson.dumps({"from": NODE_NAME, "message": text})
        lora.send(pkt.encode()+b"\n")
        oled_log("TX LoRa: "+text[:10])
    return _cb

# ─────────── 8. Main ───────────
def main():
    init_oled();          oled_log("Booting")
    ip = wifi_connect();  oled_log(ip)
    lora = init_lora();   oled_log("LoRa OK")
    oled_log(NODE_NAME)

    # MQTT client
    cid = ubinascii.hexlify(mac).decode()
    mqttc = MQTTClient(cid, MQTT_HOST, MQTT_PORT,
                       user=MQTT_USER, password=MQTT_PASSWORD, keepalive=60)
    mqttc.set_callback(make_downlink_cb(lora))
    mqttc.connect(); mqttc.subscribe(MQTT_TOPIC_DOWN)
    oled_log("MQTT OK")

    PING_MS, last_ping = 15000, time.ticks_ms()

    while True:
        #1) MQTT downlink → LoRa
        try: mqttc.check_msg()
        except OSError as e:
            oled_log("MQTT err"); time.sleep(2)
            try:
                mqttc.connect(); mqttc.subscribe(MQTT_TOPIC_DOWN)
                oled_log("MQTT re‑OK")
            except: pass

        #2) LoRa → MQTT uplink
        try:
            pkt, status = lora.recv(timeout_en=True, timeout_ms=200)
            if status == 0 and pkt:
                mqttc.publish(MQTT_TOPIC_UP, pkt)
                try:
                    pl = ujson.loads(pkt)
                    oled_log("RX "+pl.get("from","")[-6:]+":"
                                   +pl.get("message","")[:8])
                except: oled_log("RX LoRa pkt")
        except Exception:
            pass

        #Ping keep‑alive
        if time.ticks_diff(time.ticks_ms(), last_ping) > PING_MS:
            try: mqttc.ping()
            except: pass
            last_ping = time.ticks_ms()

        gc.collect(); time.sleep_ms(50)

# ─────────── Ejecutar ───────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        oled_log("Reboot by KB")
