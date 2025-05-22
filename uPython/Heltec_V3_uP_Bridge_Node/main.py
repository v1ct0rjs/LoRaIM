"""
LoRaIM Bridge – Heltec V3 (ESP32-S3 + SX1262 + OLED)
====================================================

Este firmware convierte una placa Heltec WiFi LoRa V3 en un puente bidireccional LoRa ↔ MQTT, facilitando la comunicación
transparente entre nodos LoRa y una infraestructura MQTT.

Versión optimizada con protector de pantalla OLED y activación por botón.
"""
# ───────── Imports ─────────────────────────────────────────────────────────
import time, gc, ubinascii, ujson
from machine import Pin, I2C, WDT
import network
from umqtt.robust import MQTTClient
from sx1262 import SX1262
import ssd1306
import micropython

# Reservamos buffer para excepciones
micropython.alloc_emergency_exception_buf(100)

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
BUTTON_PIN                              = 0   # Pin del botón integrado

# ───────── 3. Parámetros de configuración ────────────────────────────────
WIFI_SSID     = getenv(ENV, "WIFI_SSID", str, "MySSID")
WIFI_PASS     = getenv(ENV, "WIFI_PASSWORD", str, "password")

MQTT_HOST     = getenv(ENV, "MQTT_HOST", str, "192.168.1.40")
MQTT_PORT     = getenv(ENV, "MQTT_PORT", int, 1883)
MQTT_USER     = getenv(ENV, "MQTT_USER", str, None)
MQTT_PASS     = getenv(ENV, "MQTT_PASSWORD", str, None)
MQTT_TOPIC_UP   = getenv(ENV, "MQTT_TOPIC_UP",   str, "lorachat/up").encode()
MQTT_TOPIC_DOWN = getenv(ENV, "MQTT_TOPIC_DOWN", str, "lorachat/down").encode()
MQTT_TOPIC_NODES = getenv(ENV, "MQTT_TOPIC_NODES", str, "lorachat/nodes").encode()
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

# Tiempo de inactividad antes de apagar la pantalla (5 minutos en ms)
SCREEN_TIMEOUT = 5 * 60 * 1000

# Intervalo para publicar estado de nodos (30 segundos)
NODES_STATUS_INTERVAL = 30 * 1000

# ───────── 4. Variables globales ───────────────────────────────────────────
LINE_H, MAX_LINES = 12, 5
_lines = [""] * MAX_LINES
last_activity_time = time.ticks_ms()
last_nodes_publish = time.ticks_ms()
screen_active = True
button = None
oled = None
mqttc = None
lora = None

# Registro de nodos activos
nodes = {}
NODE_TIMEOUT = 60 * 1000  # 60 segundos para considerar un nodo offline

# ───────── 5. OLED helpers ───────────────────────────────────────────────
def activate_screen():
    """
    Activa la pantalla OLED si estaba apagada.
    """
    global last_activity_time, screen_active

    # Actualizar tiempo de última actividad
    last_activity_time = time.ticks_ms()

    # Reactivar pantalla si estaba apagada
    if not screen_active:
        oled.poweron()
        screen_active = True
        oled.fill(0)
        for i,l in enumerate(_lines):
            oled.text(l, 0, i*LINE_H, 1)
        oled.show()

def oled_log(txt):
    """
    Muestra un mensaje en la pantalla OLED y lo imprime en la consola.
    También reactiva la pantalla si estaba apagada.
    :param txt:
    :return:
    """
    global _lines

    # Activar pantalla
    activate_screen()

    _lines.pop(0); _lines.append(txt)
    oled.fill(0)
    for i,l in enumerate(_lines):
        oled.text(l, 0, i*LINE_H, 1)
    oled.show()
    print(txt)

def check_screen_timeout(current_time):
    """
    Verifica si ha pasado el tiempo de inactividad y apaga la pantalla si es necesario.
    :param current_time: Tiempo actual en ms
    :return:
    """
    global screen_active
    if screen_active and time.ticks_diff(current_time, last_activity_time) > SCREEN_TIMEOUT:
        oled.poweroff()
        screen_active = False

def button_callback(pin):
    """
    Callback para el botón. Activa la pantalla cuando se pulsa el botón.
    :param pin: Pin que generó la interrupción
    :return:
    """
    # Debounce simple
    time.sleep_ms(50)
    if pin.value() == 0:  # Botón presionado (lógica negativa)
        activate_screen()
        # No mostramos ningún mensaje al pulsar el botón

# ───────── 6. Init hardware ──────────────────────────────────────────────
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

def init_button():
    """
    Inicializa el botón y configura la interrupción.
    :return:
    """
    global button
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    button.irq(trigger=Pin.IRQ_FALLING, handler=button_callback)

def wifi_connect():
    """
    Conecta a la red Wi-Fi y devuelve la dirección IP asignada.
    :return:
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Configurar WiFi para mayor estabilidad
    wlan.config(reconnects=5)  # Intentar reconectar automáticamente

    if not wlan.isconnected():
        try:
            oled_log("Conectando WiFi")
            wlan.connect(WIFI_SSID, WIFI_PASS)

            # Esperar hasta 30 segundos para la conexión
            max_wait = 30
            while max_wait > 0:
                if wlan.isconnected():
                    break
                max_wait -= 1
                oled_log(f"WiFi... {max_wait}")
                time.sleep(1)

            # Si no se conectó, reiniciar el adaptador WiFi
            if not wlan.isconnected():
                oled_log("Reintentando WiFi")
                wlan.active(False)
                time.sleep(1)
                wlan.active(True)
                time.sleep(1)
                wlan.connect(WIFI_SSID, WIFI_PASS)

                # Esperar otros 30 segundos
                max_wait = 30
                while max_wait > 0:
                    if wlan.isconnected():
                        break
                    max_wait -= 1
                    oled_log(f"WiFi... {max_wait}")
                    time.sleep(1)
        except Exception as e:
            oled_log(f"WiFi err: {str(e)[:10]}")

    return wlan.ifconfig()[0] if wlan.isconnected() else "NO-WIFI"

def init_lora():
    """
    Inicializa el módulo LoRa SX1262 y lo configura con los parámetros especificados.
    :return:
    """
    global lora
    lora = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
               LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)
    err = lora.begin(freq=FREQ, bw=BW, sf=SF, cr=CR, power=TX_POWER, syncWord=SYNC_WORD, blocking=False)
    if err: raise RuntimeError("LoRa init err %d" % err)
    lora.setBlockingCallback(False, on_receive)
    return lora

# ───────── 7. Node name ─────────────────────────────────────────────────
mac = network.WLAN(network.STA_IF).config('mac')
NODE_NAME = "Node-" + ubinascii.hexlify(mac).decode()[-6:].upper()

# ───────── 8. MQTT → LoRa callback ──────────────────────────────────────
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
            js = ujson.loads(msg)
            txt = js.get("message", "")
        except:
            txt = msg.decode()

        if not txt:
            return

        try:
            pkt = ujson.dumps({"from": NODE_NAME, "message": txt})
            lora.send(pkt.encode()+b"\n")
            oled_log("TX LoRa: "+txt[:10])
        except Exception as e:
            oled_log(f"TX err: {str(e)[:10]}")

    return _cb

# ───────── 9. Buffer de pendientes (lista circular) ─────────────────────
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

# ───────── 10. Funciones de gestión de nodos ─────────────────────────────
def update_node_status(node_id, rssi=None, snr=None):
    """
    Actualiza el estado de un nodo en el registro.
    :param node_id: Identificador del nodo
    :param rssi: Valor RSSI (opcional)
    :param snr: Valor SNR (opcional)
    :return: None
    """
    current_time = time.ticks_ms()

    # Actualizar o crear entrada para el nodo
    if node_id in nodes:
        nodes[node_id]["last_seen"] = current_time
        if rssi is not None:
            nodes[node_id]["rssi"] = rssi
        if snr is not None:
            nodes[node_id]["snr"] = snr
        nodes[node_id]["status"] = "online"
    else:
        nodes[node_id] = {
            "id": node_id,
            "last_seen": current_time,
            "rssi": rssi,
            "snr": snr,
            "status": "online"
        }

    oled_log(f"Node {node_id} updated")

def check_nodes_status():
    """
    Verifica el estado de todos los nodos y actualiza su estado.
    :return: None
    """
    current_time = time.ticks_ms()

    # Verificar cada nodo
    for node_id, info in nodes.items():
        # Si el nodo no se ha visto en NODE_TIMEOUT, marcarlo como offline
        if time.ticks_diff(current_time, info["last_seen"]) > NODE_TIMEOUT:
            info["status"] = "offline"
        else:
            info["status"] = "online"

    # Publicar estado de nodos si es necesario
    publish_nodes_status()

def publish_nodes_status():
    """
    Publica el estado de todos los nodos a través de MQTT.
    :return: None
    """
    global last_nodes_publish, mqttc

    current_time = time.ticks_ms()

    # Solo publicar si ha pasado el intervalo
    if time.ticks_diff(current_time, last_nodes_publish) < NODES_STATUS_INTERVAL:
        return

    # Actualizar timestamp
    last_nodes_publish = current_time

    # Preparar lista de nodos
    nodes_list = []
    for node_id, info in nodes.items():
        # Convertir tiempo de ticks a segundos desde epoch (aproximado)
        last_seen_sec = time.time() - (time.ticks_diff(current_time, info["last_seen"]) / 1000)

        nodes_list.append({
            "id": node_id,
            "last_seen": last_seen_sec,
            "rssi": info.get("rssi"),
            "snr": info.get("snr"),
            "status": info.get("status", "unknown")
        })

    # Añadir el propio nodo puente con la marca is_bridge
    nodes_list.append({
        "id": NODE_NAME,
        "last_seen": time.time(),
        "status": "online",
        "is_bridge": True
    })

    # Publicar en MQTT
    try:
        payload = ujson.dumps({
            "nodes": nodes_list,
            "timestamp": time.time()
        })
        mqttc.publish(MQTT_TOPIC_NODES, payload, False, MQTT_QOS)
        oled_log(f"Nodes status sent ({len(nodes_list)})")
    except Exception as e:
        oled_log(f"Nodes pub err: {str(e)[:10]}")

# ───────── 11. LoRa callback ─────────────────────────────────────────────
def on_receive(events):
    """
    Callback para recibir mensajes LoRa.
    :param events: Eventos LoRa
    :return:
    """
    global mqttc, lora
    if events & SX1262.RX_DONE:
        try:
            pkt, st = lora.recv()
            if st == 0 and pkt:
                try:
                    # Obtener métricas LoRa
                    rssi = lora.getRSSI()
                    snr = lora.getSNR()

                    # Procesar el paquete
                    try:
                        js = ujson.loads(pkt)
                        sender = js.get("from", "?")
                        message = js.get("message", "")

                        # Añadir métricas LoRa al paquete
                        js["rssi"] = rssi
                        js["snr"] = snr

                        # Actualizar estado del nodo
                        update_node_status(sender, rssi, snr)

                        # Publicar en MQTT con métricas incluidas
                        enhanced_pkt = ujson.dumps(js)
                        mqttc.publish(MQTT_TOPIC_UP, enhanced_pkt, MQTT_RETAIN_UP, MQTT_QOS)

                        oled_log(f"RX {sender[-6:]}:{message[:8]}")
                        oled_log(f"RSSI:{rssi:.1f} SNR:{snr:.1f}")
                    except ValueError:
                        # Si no es JSON, enviar como texto plano con métricas
                        payload = {
                            "from": "unknown",
                            "message": pkt.decode("utf-8", "ignore").strip(),
                            "rssi": rssi,
                            "snr": snr
                        }
                        mqttc.publish(MQTT_TOPIC_UP, ujson.dumps(payload), MQTT_RETAIN_UP, MQTT_QOS)
                        oled_log(f"RX raw: {pkt.decode()[:10]}")
                except Exception as e:
                    oled_log(f"Pub err: {str(e)[:10]}")
                    pend_append(pkt)
        except Exception as e:
            oled_log(f"RX err: {str(e)[:10]}")

# ───────── 12. Main loop ─────────────────────────────────────────────────
def main():
    """
    Función principal que inicializa el sistema y gestiona la comunicación entre LoRa y MQTT.
    :return:
    """
    # Inicializar watchdog
    try:
        wdt = WDT(timeout=30000)  # 30 segundos
        has_watchdog = True
    except:
        has_watchdog = False
        print("No WDT support")

    # Inicializar hardware
    init_oled()
    init_button()  # Inicializar el botón
    oled_log("Booting")

    ip = wifi_connect()
    oled_log(ip)

    # Si no hay conexión WiFi, reintentar o reiniciar
    if ip == "NO-WIFI":
        oled_log("WiFi fallido")
        time.sleep(5)
        import machine
        machine.reset()

    global lora
    lora = init_lora()
    oled_log("LoRa OK")

    oled_log(NODE_NAME)

    # Variables para control de tiempo
    last_ping_time = time.ticks_ms()
    start_time = time.time()
    ping_interval = 15000  # 15 segundos
    reset_interval = 86400  # 24 horas en segundos

    # Inicializar MQTT con la biblioteca robusta - PARÁMETROS SIMPLIFICADOS
    cid = ubinascii.hexlify(mac).decode()

    # Crear cliente MQTT robusto con parámetros mínimos
    global mqttc
    mqttc = MQTTClient(cid, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS, keepalive=60)
    mqttc.DEBUG = True  # Habilitar depuración
    mqttc.set_callback(make_downlink_cb(lora))

    # Intentar conectar MQTT
    try:
        mqttc.connect()
        mqttc.subscribe(MQTT_TOPIC_DOWN, MQTT_QOS)
        oled_log("MQTT OK")

        # Publicar estado online - MODIFICADO: Ahora publicamos un mensaje especial para identificar el nodo puente
        bridge_status = {
            "from": NODE_NAME,
            "message": "online",
            "type": "bridge"  # Marcar explícitamente como nodo puente
        }
        mqttc.publish(MQTT_TOPIC_UP, ujson.dumps(bridge_status), False, MQTT_QOS)
        oled_log("Bridge status sent")

        # Registrar el nodo en el registro de nodos
        update_node_status(NODE_NAME)

        # Publicar inmediatamente el estado de los nodos para notificar que el puente está online
        publish_nodes_status()
    except Exception as e:
        oled_log(f"MQTT err: {str(e)[:10]}")

    # Configurar callback para LoRa
    lora.setBlockingCallback(False, on_receive)

    # Bucle principal
    while True:
        current_time = time.ticks_ms()

        # Alimentar watchdog
        if has_watchdog:
            wdt.feed()

        # Verificar si hay que apagar la pantalla
        check_screen_timeout(current_time)

        # Verificar estado de nodos
        check_nodes_status()

        # Reinicio programado cada 24 horas
        if time.time() - start_time > reset_interval:
            oled_log("Reinicio programado")
            time.sleep_ms(1000)
            import machine
            machine.reset()

        # Comprobar conexión MQTT y reconectar si es necesario
        try:
            # Comprobar mensajes MQTT (downlink)
            mqttc.check_msg()

            # Ping periódico para mantener la conexión
            if time.ticks_diff(current_time, last_ping_time) > ping_interval:
                mqttc.ping()
                last_ping_time = current_time

            # Procesar mensajes pendientes
            if pending:
                pkt = pend_popleft()
                try:
                    mqttc.publish(MQTT_TOPIC_UP, pkt, MQTT_RETAIN_UP, MQTT_QOS)
                    oled_log(f"Sent pending ({len(pending)})")
                except Exception as e:
                    pend_append(pkt)
                    oled_log(f"Pend err: {str(e)[:10]}")
                    # La biblioteca robusta manejará la reconexión
        except Exception as e:
            oled_log(f"MQTT err: {str(e)[:10]}")
            # La biblioteca robusta manejará la reconexión

        # Pequeña pausa para evitar saturar la CPU
        time.sleep_ms(10)

# ───────── 13. Manejo de errores y punto de entrada ─────────────────────
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # En caso de error fatal, registrar y reiniciar
        error_msg = f"ERROR FATAL: {str(e)}"
        print(error_msg)
        time.sleep(5)
        import machine
        machine.reset()
