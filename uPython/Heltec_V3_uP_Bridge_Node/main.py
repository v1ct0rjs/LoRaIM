"""
LoRaIM Bridge – Heltec V3 (ESP32-S3 + SX1262 + OLED)
====================================================

Este firmware convierte una placa Heltec WiFi LoRa V3 en un puente bidireccional LoRa ↔ MQTT, facilitando la comunicación
transparente entre nodos LoRa y una infraestructura MQTT.

Características Principales:
----------------------------
- Configuración Modular: Lee parámetros desde un archivo `.env`, incluyendo ajustes de Wi-Fi, MQTT, LoRa y OLED,
facilitando personalización sin modificaciones de código.
- Identificador Único Automático: Genera un `NODE_NAME` único del tipo `"Node-XXXXXX"`, garantizando la identificación
automática de cada dispositivo desplegado.
- Inicialización Integrada: Conecta automáticamente a Wi-Fi, inicializa el módulo LoRa SX1262 y muestra información
crítica (estado, IP asignada, mensajes transmitidos y recibidos) en la pantalla OLED.

Flujo de Mensajes:
------------------
1. MQTT → LoRa
   - Se suscribe al tópico MQTT definido en `MQTT_TOPIC_DOWN` (p. ej., `lorachat/down`).
   - Cada mensaje MQTT recibido se convierte en un JSON estructurado:
     {"from": NODE_NAME, "message": "texto"}
   - Este paquete JSON se transmite por LoRa hacia los nodos en rango.

2. LoRa → MQTT
   - Escucha continuamente los mensajes LoRa entrantes.
   - Al recibir paquetes LoRa válidos, publica su contenido en el topic definido por `MQTT_TOPIC_UP`
   (p. ej., `lorachat/up`) con calidad de servicio (QoS) 1 y retención configurable.
   - Si la conexión MQTT no está disponible, los mensajes entrantes se almacenan temporalmente en un buffer circular
   (`pending[]`) y se retransmiten automáticamente al restablecerse la conexión.

Robustez y Fiabilidad MQTT:
---------------------------
- QoS Nivel 1: Asegura la entrega fiable de mensajes.
- Keep-alive 30 s: Mantiene activa y supervisada la conexión con el broker MQTT.
- Aviso de caída (Last-Will): Publica un estado "offline" retenido para alertar inmediatamente ante desconexiones
inesperadas.
- Reconexión Automática: Implementa un mecanismo de reintentos con espera incremental (back-off exponencial)
desde 2 s hasta 30 s máx.
- Buffering inteligente: Publica automáticamente mensajes pendientes tras reconexiones.

Interfaz Visual (OLED):
-----------------------
- Pantalla OLED SSD1306 de 128×64 píxeles, mostrando:
  • Dirección IP obtenida tras arranque y conexión Wi-Fi.
  • Estado en tiempo real de la conexión MQTT.
  • Mensajes enviados y recibidos por LoRa claramente diferenciados.

Personalización Avanzada:
-----------------------
- Parámetros ajustables directamente desde `.env`:
  • Frecuencia, potencia, ancho de banda, spreading factor (SF), etc.
  • Brillo de la pantalla OLED.
- Extensible mediante las bibliotecas adjuntas:
  • sx1262.py (control módulo LoRa SX1262)
  • ssd1306.py (control pantalla OLED)
  • simple.py (cliente MQTT simplificado)

English Version:

Main Features:
--------------
- Modular Configuration:** Reads settings from a `.env` file, including Wi-Fi, MQTT, LoRa, and OLED parameters,
allowing easy customization without changing the code.
- Automatic Unique Identifier:** Generates a unique `NODE_NAME` in the form `"Node-XXXXXX"` for automatic device
identification.
- Integrated Initialization:** Automatically connects to Wi-Fi, initializes the LoRa SX1262 module, and displays
critical status information (connection status, IP address, transmitted/received messages) on the OLED screen.

Message Flow:
-------------
1. **MQTT → LoRa**
   - Subscribes to the MQTT topic defined in `MQTT_TOPIC_DOWN` (e.g., `lorachat/down`).
   - Every received MQTT message is converted to a structured JSON payload:
          {"from": NODE_NAME, "message": "text"}
   - This JSON payload is then transmitted over LoRa to nodes within range.

2. **LoRa → MQTT**
   - Continuously listens for incoming LoRa packets.
   - Upon receiving valid LoRa messages, publishes them to the MQTT topic defined by `MQTT_TOPIC_UP`
   (e.g., `lorachat/up`) with Quality of Service (QoS) level 1 and optional retention.
   - If the MQTT connection is unavailable, messages are temporarily stored in a circular buffer (`pending[]`)
   and automatically retransmitted upon reconnection.

MQTT Reliability and Robustness:
--------------------------------
- QoS Level 1:** Ensures reliable message delivery.
- Keep-alive 30s:** Maintains and supervises an active connection to the MQTT broker.
- Last-Will Notification:** Publishes a retained `"offline"` status to immediately notify clients of
unexpected disconnections.
- Automatic Reconnection:** Implements exponential back-off reconnection attempts starting from 2 seconds up to a
maximum of 30 seconds.
- Intelligent Buffering:** Automatically publishes pending messages after reconnection.

OLED Visual Interface:
----------------------
- Uses a 128×64 pixel SSD1306 OLED display to show:
  • Device IP address after Wi-Fi connection.
  • Real-time MQTT connection status.
  • Clearly differentiated incoming/outgoing LoRa messages.

Advanced Customization:
-----------------------
- Adjustable parameters directly from `.env`:
  • LoRa frequency, power, bandwidth, spreading factor (SF), etc.
  • OLED brightness.
- Extendable through included libraries:
  • `sx1262.py` (LoRa SX1262 module control)
  • `ssd1306.py` (OLED display control)
  • `simple.py` (Simplified MQTT client)

Licencia y Créditos:
--------------------
LoRaIM es un proyecto de código abierto bajo la licencia GPL v3.
2025 LoRaIM.
"""
# ───────── Imports ─────────────────────────────────────────────────────────
import time, gc, ubinascii, ujson
from machine  import Pin, I2C
import network
from simple   import MQTTClient
from sx1262   import SX1262
import ssd1306

# ───────── 1. Leer .env ───────────────────────────────────────────────────
def load_env(path="/.env"):
    """
    Carga las variables de entorno desde un archivo `.env` y devuelve un diccionario con los valores.
    :param path:
    :return:
    """
    env = {}
    try:
        with open(path) as f:
            for raw in f:
                raw = raw.strip()
                if raw and not raw.startswith("#"):
                    k, v = raw.split("=", 1)
                    env[k.strip()] = v.strip()
    except OSError:
        pass
    return env

def getenv(env, key, cast=str, default=None):
    """
    Obtiene el valor de una variable de entorno, aplicando un tipo de conversión y un valor por defecto si no existe.
    :param env:
    :param key:
    :param cast:
    :param default:
    :return:
    """
    try:    return cast(env[key])
    except (KeyError, ValueError): return default

ENV = load_env()

# ───────── 2. Pines Heltec V3 ─────────────────────────────────────────────
LORA_CS, LORA_SCK, LORA_MOSI, LORA_MISO = 8, 9, 10, 11
LORA_RESET, LORA_BUSY, LORA_DIO1        = 12, 13, 14
VEXT, OLED_SCL, OLED_SDA, OLED_RST      = 36, 18, 17, 21

# ───────── 3. Parámetros de configuración ────────────────────────────────
WIFI_SSID     = getenv(ENV, "WIFI_SSID", str, "MySSID")
WIFI_PASS     = getenv(ENV, "WIFI_PASSWORD", str, "password")

MQTT_HOST     = getenv(ENV, "MQTT_HOST", str, "192.168.1.40")
MQTT_PORT     = getenv(ENV, "MQTT_PORT", int, 1883)
MQTT_USER     = getenv(ENV, "MQTT_USER", str, None)
MQTT_PASS     = getenv(ENV, "MQTT_PASSWORD", str, None)
MQTT_TOPIC_UP   = getenv(ENV, "MQTT_TOPIC_UP",   str, "lorachat/up").encode()
MQTT_TOPIC_DOWN = getenv(ENV, "MQTT_TOPIC_DOWN", str, "lorachat/down").encode()
MQTT_QOS      = getenv(ENV, "MQTT_QOS", int, 1)
MQTT_RETAIN_UP= bool(getenv(ENV, "MQTT_RETAIN_UP", int, 0))
MQTT_RECON_MAX= getenv(ENV, "MQTT_RECONNECT_MAX", int, 30000)  # ms

FREQ       = getenv(ENV, "FREQUENCY", float, 866.3)
BW         = getenv(ENV, "BANDWIDTH", float, 250.0)
SF         = getenv(ENV, "SPREADING_FACTOR", int, 9)
CR         = getenv(ENV, "CODING_RATE", int, 5)
SYNC_WORD  = getenv(ENV, "SYNC_WORD", lambda x:int(x,0), 0x12)
TX_POWER   = getenv(ENV, "TRANSMIT_POWER", int, 14)

BRIGHTNESS = getenv(ENV, "BRIGHTNESS", int, 200)

# ───────── 4. OLED helpers ───────────────────────────────────────────────
LINE_H, MAX_LINES = 12, 5
_lines = [""] * MAX_LINES
def oled_log(txt):
    """
    Muestra un mensaje en la pantalla OLED y lo imprime en la consola.
    :param txt:
    :return:
    """
    _lines.pop(0); _lines.append(txt)
    oled.fill(0)
    for i,l in enumerate(_lines):
        oled.text(l, 0, i*LINE_H, 1)
    oled.show()
    print(txt)

# ───────── 5. Init hardware ──────────────────────────────────────────────
def init_oled():
    """
    Inicializa la pantalla OLED y la configura.
    :return:
    """
    Pin(VEXT, Pin.OUT, value=0)
    rst = Pin(OLED_RST, Pin.OUT, value=0)
    time.sleep_ms(20); rst.value(1)
    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400_000)
    global oled
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)
    oled.contrast(BRIGHTNESS)

def wifi_connect():
    """
    Conecta a la red Wi-Fi y devuelve la dirección IP asignada.
    :return:
    """
    wlan = network.WLAN(network.STA_IF); wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        for _ in range(60):
            if wlan.isconnected(): break
            oled_log("WiFi…"); time.sleep_ms(200)
    return wlan.ifconfig()[0] if wlan.isconnected() else "NO-WIFI"

def init_lora():
    """
    Inicializa el módulo LoRa SX1262 y lo configura con los parámetros especificados.
    :return:
    """
    l = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
               LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)
    err = l.begin(freq=FREQ, bw=BW, sf=SF, cr=CR, power=TX_POWER, syncWord=SYNC_WORD, blocking=True)
    if err: raise RuntimeError("LoRa init err %d" % err)
    return l

# ───────── 6. Node name ─────────────────────────────────────────────────
mac = network.WLAN(network.STA_IF).config('mac')
NODE_NAME = "Node-" + ubinascii.hexlify(mac).decode()[-6:].upper()

# ───────── 7. MQTT → LoRa callback ──────────────────────────────────────
def make_downlink_cb(lora):
    """
    Crea un callback para recibir mensajes MQTT y enviarlos por LoRa.
    :param lora:
    :return:
    """
    def _cb(topic, msg):
        """
        Callback para recibir mensajes MQTT y enviarlos por LoRa.
        :param topic:
        :param msg:
        :return:
        """
        try:
            js  = ujson.loads(msg)
            txt = js.get("message", "")
        except: txt = msg.decode()
        if not txt: return
        pkt = ujson.dumps({"from": NODE_NAME, "message": txt})
        lora.send(pkt.encode()+b"\n")
        oled_log("TX LoRa: "+txt[:10])
    return _cb

# ───────── 8. Buffer de pendientes (lista circular) ─────────────────────
PENDING_MAX = 200
pending = []
def pend_append(pkt):
    """
    Añade un paquete al buffer de pendientes y elimina el más antiguo si se supera el límite.
    :param pkt:
    :return:
    """
    pending.append(pkt)
    if len(pending) > PENDING_MAX:
        pending.pop(0)
def pend_popleft():
    """
    Elimina y devuelve el primer paquete del buffer de pendientes.
    :return:
    """
    return pending.pop(0)

# ───────── 9. Main loop ─────────────────────────────────────────────────
def main():
    """
    Función principal que inicializa el sistema y gestiona la comunicación entre LoRa y MQTT.
    :return:
    """
    init_oled();
    oled_log("Booting")

    ip = wifi_connect();
    oled_log(ip)

    lora = init_lora();
    oled_log("LoRa OK")

    oled_log(NODE_NAME)

    cid = ubinascii.hexlify(mac).decode()
    mqttc = MQTTClient(cid, MQTT_HOST, MQTT_PORT, user=MQTT_USER, password=MQTT_PASS, keepalive=30)
    # Last Will message removed to prevent reconnection issues
    mqttc.set_callback(make_downlink_cb(lora))

    backoff = 2000      # ms
    mqtt_ok = False

    while True:
        # ── reconexión MQTT ───────────────────────────
        if not mqtt_ok:
            try:
                mqttc.connect()
                mqttc.subscribe(MQTT_TOPIC_DOWN, MQTT_QOS)
                oled_log("MQTT OK")
                mqtt_ok = True
                backoff = 2000
                mqttc.publish(MQTT_TOPIC_UP, ujson.dumps({"from": NODE_NAME, "message": "online"}), True, MQTT_QOS)
                if not mqtt_ok:
                    try:
                        mqttc.disconnect()  # <-- evita falso 'offline'
                    except OSError:
                        pass
                # vaciar pendientes
                while pending and mqtt_ok:
                    pkt = pend_popleft()
                    try:
                        mqttc.publish(MQTT_TOPIC_UP, pkt, MQTT_RETAIN_UP, MQTT_QOS)
                    except OSError:
                        pend_append(pkt)
                        mqtt_ok = False
                        break
            except OSError:
                oled_log(f"MQTT retry…({len(pending)})")
                time.sleep_ms(backoff)
                backoff = min(backoff*2, MQTT_RECON_MAX)
                continue

        # ── downlink MQTT → LoRa ─────────────────────
        try:
            mqttc.check_msg()
        except OSError:
            mqtt_ok = False

        # ── uplink LoRa → MQTT ───────────────────────
        pkt, st = lora.recv(timeout_en=True, timeout_ms=200)
        if st == 0 and pkt:
            if mqtt_ok:
                try:
                    mqttc.publish(MQTT_TOPIC_UP, pkt, MQTT_RETAIN_UP, MQTT_QOS)
                except OSError:
                    mqtt_ok = False
                    pend_append(pkt)
            else:
                pend_append(pkt)
            try:
                js = ujson.loads(pkt)
                oled_log("RX "+js.get("from","")[-6:]+":"+js.get("message","")[:8])
            except: oled_log("RX pkt")
        if mqtt_ok:
            try: mqttc.ping()
            except OSError: mqtt_ok = False

        gc.collect()
        time.sleep_ms(50)

if __name__ == "__main__":
    main()
