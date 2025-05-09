"""
main.py – Heltec V3 ESP32‑S3
• Puente LoRa ↔ OLED ↔ SoftAP ↔ Web UI
• AP 172.16.0.1 (SSID LoRaMonitor) con servidor HTTP integrado.
"""

import time, gc, _thread, ure, ujson, usocket as socket
from machine import Pin, I2C
import network
from sx1262 import SX1262
import ssd1306

# ───────── Pines ────────────────────────────────────────────────────────
LORA_CS   = 8
LORA_SCK  = 9
LORA_MOSI = 10
LORA_MISO = 11
LORA_RESET = 12
LORA_BUSY  = 13
LORA_DIO1  = 14

VEXT      = 36
OLED_SCL  = 18
OLED_SDA  = 17
OLED_RST  = 21

USER_BUTTON = 0
LED_PIN     = 35

# ───────── Parámetros LoRa ──────────────────────────────────────────────
FREQUENCY        = 866.3
BANDWIDTH        = 250.0
SPREADING_FACTOR = 9
CODING_RATE      = 5
SYNC_WORD        = 0x12
TRANSMIT_POWER   = 0

# ───────── OLED ─────────────────────────────────────────────────────────
OLED_W   = 128
OLED_H   = 64
BRIGHT   = 255
LINE_H   = 12
MAX_LINE = 5

# ───────── SoftAP ───────────────────────────────────────────────────────
AP_SSID    = "LoRaMonitor"
AP_IP      = "172.16.0.1"
AP_MASK    = "255.255.255.0"
AP_GW      = "172.16.0.1"
AP_DNS     = "8.8.8.8"

# ───────── Historial ────────────────────────────────────────────────────
HIST_MAX = 50
# Inicializar variables globales para evitar errores
oled = None
led = None
btn = None
lora = None
display = [""] * MAX_LINE
history = []
rx_flag = False
rx_msg = ""
rx_rssi = 0.0
rx_snr = 0.0
lock = _thread.allocate_lock()

# Función para añadir elementos con límite
def append_with_limit(lst, item, maxlen):
    lst.append(item)
    if len(lst) > maxlen:
        lst.pop(0)

# ───────── Helpers ──────────────────────────────────────────────────────
def scroll(txt):
    global oled, display
    display.pop(0)
    display.append(txt)
    if oled:  # Verificar que oled existe
        oled.fill(0)
        for i, l in enumerate(display):
            oled.text(l, 0, i * LINE_H, 1)
        oled.show()
    print(txt)

def url_unquote(s):
    res = ""
    i = 0
    while i < len(s):
        c = s[i]
        if c == "+":
            res += " "
            i += 1
        elif c == "%" and i + 2 < len(s):
            res += chr(int(s[i+1:i+3], 16))
            i += 3
        else:
            res += c
            i += 1
    return res

# ───────── Hardware init ────────────────────────────────────────────────

def hw_init():
    global oled, led, btn, lora

    print("Inicializando hardware...")

    # Power OLED
    Pin(VEXT, Pin.OUT).value(0)

    led = Pin(LED_PIN, Pin.OUT)
    btn = Pin(USER_BUTTON, Pin.IN, Pin.PULL_UP)

    rst = Pin(OLED_RST, Pin.OUT)
    rst.value(0)
    time.sleep_ms(20)
    rst.value(1)

    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
    oled = ssd1306.SSD1306_I2C(OLED_W, OLED_H, i2c)
    oled.contrast(BRIGHT)

    lora = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
                  LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)

    err = lora.begin(FREQUENCY, BANDWIDTH, SPREADING_FACTOR,
                     CODING_RATE, TRANSMIT_POWER, SYNC_WORD,
                     8, False, False)  # blocking=False aquí

    if err:
        print("Error al inicializar SX1262:", err)
    else:
        lora.setBlockingCallback(False, lora_cb)
        print("LoRa inicializado correctamente")


def ap_init():
    global oled, led
    try:
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
        ap.ifconfig((AP_IP, AP_MASK, AP_GW, AP_DNS))
        print("AP inicializado:", AP_IP)
        scroll("AP {}".format(AP_IP))
    except Exception as e:
        print("Error al inicializar AP:", e)

# ───────── LoRa callback ────────────────────────────────────────────────
def lora_cb(events):
    global rx_flag, rx_msg, rx_rssi, rx_snr, lora
    try:
        if events & SX1262.RX_DONE:
            pkt, st = lora.recv()
            if st == 0 and pkt:
                with lock:
                    rx_flag = True
                    rx_msg = pkt.decode().strip()
                    rx_rssi = lora.getRSSI()
                    rx_snr = lora.getSNR()
    except Exception as e:
        print("Error en callback LoRa:", e)

# ───────── Enviar LoRa ──────────────────────────────────────────────────

def lora_send(text):
    global led, lora
    msg = "LoRa no inicializado" # Mensaje por defecto
    try:
        if lora: # Solo verifica si lora está inicializado
            led.on()
            # La biblioteca SX1262 debería manejar internamente la comprobación del pin BUSY
            # o devolver un código de error si el módulo está ocupado.
            _, st = lora.send(text.encode() + b"\n") # Asegúrate de que send() sea bloqueante o manejes el callback de TX_DONE si es no bloqueante
            led.off()
            if st == 0: # Asumiendo que 0 es éxito
                msg = "LoRa TX OK"
            else:
                msg = "TX err {}".format(st)
        else:
            msg = "LoRa no inicializado" # Este mensaje ya estaba cubierto arriba, pero es bueno ser explícito
        scroll(msg)
    except Exception as e:
        print("Error al enviar LoRa:", e)
        scroll("Error TX: {}".format(e))


def web():
    global history
    try:
        s = socket.socket()
        s.bind(("0.0.0.0", 80))
        s.listen(4)
        print("Servidor web iniciado en puerto 80")

        while True:
            try:
                cl, _ = s.accept()
                req = cl.recv(512).decode()
                path = req.split(" ")[1] if req else "/"

                if path.startswith("/api/msgs"):
                    cl.send("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
                    cl.send(ujson.dumps(history))
                elif path.startswith("/send"):
                    m = ure.search("msg=([^& ]+)", path)
                    if m:
                        lora_send(url_unquote(m.group(1)))
                    cl.send("HTTP/1.1 303 See Other\r\nLocation: /\r\n\r\n")
                else:
                    rows = "\n".join(
                        "<tr><td>{:.0f}</td><td>{}</td><td>{:.1f}</td><td>{:.1f}</td></tr>"
                        .format(ts, m, rssi, snr) for ts, m, rssi, snr in history[::-1]
                    )
                    cl.send(PAGE.format(rows=rows, n=HIST_MAX))

                cl.close()
            except Exception as e:
                print("Error en manejo de cliente web:", e)
                time.sleep_ms(100)
    except Exception as e:
        print("Error al iniciar servidor web:", e)

# ───────── Main ────────────────────────────────────────────────────────
def main():
    global rx_flag, rx_msg, rx_rssi, rx_snr, history, oled, led, lora

    print("Iniciando aplicación...")
    hw_init()
    print("Hardware inicializado")

    print("Mostrando 'Booting' en OLED")
    scroll("Booting")

    print("Iniciando punto de acceso")
    ap_init()

    print("Iniciando servidor web")
    _thread.start_new_thread(web, ())

    print("Enviando mensaje inicial 'Hello'")
    try:
        lora_send("Hello")
    except Exception as e:
        print("Error al enviar mensaje inicial:", e)

    print("Entrando en bucle principal")
    cnt = 0
    while True:
        try:
            if rx_flag:
                with lock:
                    flag = rx_flag
                    rx_flag = False
                if flag:
                    scroll("RX {}:{}".format(cnt, rx_msg[:16]))
                    scroll("RSSI {:.1f} SNR {:.1f}".format(rx_rssi, rx_snr))
                    append_with_limit(history, (time.time(), rx_msg, rx_rssi, rx_snr), HIST_MAX)
                    cnt += 1
            time.sleep_ms(50)
            gc.collect()
        except Exception as e:
            print("Error en bucle principal:", e)
            time.sleep_ms(1000)

# ───────── Entrypoint ──────────────────────────────────────────────────
print("Iniciando main.py...")
try:
    main()
except KeyboardInterrupt:
    print("Reiniciando por KeyboardInterrupt")
    import machine
    machine.reset()
except Exception as e:
    print("Error crítico:", e)
    print("Reiniciando en 5 segundos...")
    time.sleep(5)
    import machine
    machine.reset()