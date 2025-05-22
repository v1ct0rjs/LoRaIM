"""
Nodo Tester LoRa – Heltec LoRa V3 (ESP32-S3 + SX1262 + OLED)
================================================================
Este firmware convierte la placa en un nodo de prueba LoRa que
envía periódicamente paquetes "Ping" y muestra todo en su OLED.

Mejoras:
- Mejor manejo de la recepción de mensajes
- Mejor sincronización entre transmisión y recepción
- Mejor visualización de estados en la OLED
"""

import time, gc, _thread
from machine import Pin, I2C
import ujson
from sx1262 import SX1262
import ssd1306

# ───────── Pines de la placa (Heltec V3 ESP32‑S3) ──────────────────────────────────
#   LoRa
LORA_CS    = 8
LORA_SCK   = 9
LORA_MOSI  = 10
LORA_MISO  = 11
LORA_RESET = 12
LORA_BUSY  = 13
LORA_DIO1  = 14

#   OLED
VEXT       = 36   # alimentación para la pantalla
OLED_SCL   = 18
OLED_SDA   = 17
OLED_RST   = 21

#   E/S de usuario
USER_BUTTON = 0
LED         = 35

# ───────── Configuración LoRa — debe coincidir con el nodo par ────────────────────────
FREQUENCY        = 868.1      # MHz
BANDWIDTH        = 125.0      # kHz
SPREADING_FACTOR = 7
CODING_RATE      = 5          # 4/5
SYNC_WORD        = 0x34
TRANSMIT_POWER   = 0         # dBm
PAUSE            = 100        # s entre pings automáticos

# ───────── Constantes OLED ──────────────────────────────────────────────────
OLED_WIDTH  = 128
OLED_HEIGHT = 64
BRIGHTNESS  = 0
LINE_H      = 12
MAX_LINES   = 5

display_buffer = ["" for _ in range(MAX_LINES)]

NODE_NAME = "LoRaTester"  # Nombre del nodo para la pantalla y carga útil del paquete

# ───────── Variables globales ─────────────────────────────────────────────────────────
tx_cnt = 0
rx_cnt = 0
last_tx = 0
minimum_pause = 0
rx_flag = False
rx_data = ""
rx_rssi = 0.0
rx_snr  = 0.0
rx_lock = _thread.allocate_lock()

# ───────── Funciones auxiliares de pantalla ─────────────────────────────────────────────────
def lcd_scroll(text: str):
    """
    Desplaza el buffer de la pantalla OLED y muestra el texto.
    :param text:
    :return:
    """
    display_buffer.pop(0)
    display_buffer.append(text)
    oled.fill(0)
    for i, line in enumerate(display_buffer):
        oled.text(line, 0, i * LINE_H, 1)
    oled.show()
    print(text)

# ───────── Inicialización del hardware ─────────────────────────────────────────────
def init_hardware():
    """
    Inicializa el hardware: OLED, LoRa, botón y LED.
    :return:
    """
    global oled, btn, led, lora

    # Alimentar OLED (VEXT LOW = ON)
    Pin(VEXT, Pin.OUT, value=0)

    led = Pin(LED, Pin.OUT, value=0)
    btn = Pin(USER_BUTTON, Pin.IN, Pin.PULL_UP)

    rst = Pin(OLED_RST, Pin.OUT, value=0)
    time.sleep_ms(20)
    rst.value(1)

    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400_000)
    if 0x3C not in i2c.scan():
        raise RuntimeError("OLED no encontrado – compruebe el cableado")
    oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c)
    oled.contrast(BRIGHTNESS)

    # SX1262
    lora = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
                  LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)
    err = lora.begin(freq=FREQUENCY, bw=BANDWIDTH, sf=SPREADING_FACTOR,
                     cr=CODING_RATE, power=TRANSMIT_POWER, syncWord=SYNC_WORD,
                     preambleLength=8, implicit=False, blocking=True)
    if err:
        raise RuntimeError(f"SX1262 begin err {err}")
    lora.setBlockingCallback(False, on_receive)

# ───────── Devoluciones de llamada LoRa ──────────────────────────────────────────────
def on_receive(events):
    """
    Devolución de llamada para el evento RX done. Se llama cuando se recibe un paquete.
    :param events:
    :return:
    """
    global rx_flag, rx_data, rx_rssi, rx_snr
    if events & SX1262.RX_DONE:
        pkt, stat = lora.recv()
        if stat == 0 and pkt:
            with rx_lock:
                rx_flag = True
                rx_data = pkt.decode("utf-8", "ignore").strip()
                rx_rssi = lora.getRSSI()
                rx_snr  = lora.getSNR()

# ───────── Funciones auxiliares ─────────────────────────────────────────────────
def button_pressed():
    """
    Comprueba si el botón está presionado con anti-rebote.
    :return: True si el botón está presionado, False en caso contrario
    """
    if not btn.value():
        time.sleep_ms(30)  # Anti-rebote
        return not btn.value()
    return False

def transmit(msg: str):
    """
    Transmite un mensaje a través de LoRa.
    :param msg: Mensaje a transmitir
    :return: (tiempo_transmisión, estado)
    """
    global last_tx, minimum_pause, tx_cnt

    # Crear la carga útil con un ID único para cada mensaje
    payload = f'{{"from": "{NODE_NAME}", "message": "{msg}", "id": {tx_cnt}}}'

    # Transmitir el mensaje
    led.on()
    t0 = time.ticks_ms()
    _, st = lora.send(payload.encode() + b"\n")
    dt = time.ticks_diff(time.ticks_ms(), t0)
    led.off()

    if st == 0:  # Éxito
        # Calcular el tiempo mínimo de pausa para el ciclo de trabajo
        # Añadimos un pequeño margen de seguridad (10%)
        minimum_pause = int(dt * 100 * 1.1)
        last_tx = time.ticks_ms()
        lcd_scroll(f"TX {tx_cnt}:{msg}")
    else:
        # Error de transmisión
        lcd_scroll(f"Error TX {st}")

    tx_cnt += 1
    return dt, st

def process_received_message():
    """
    Procesa un mensaje recibido desde rx_flag y rx_data.
    :return: None
    """
    global rx_flag, rx_cnt

    if not rx_flag:
        return

    with rx_lock:
        rx_flag = False
        try:
            rx_payload = ujson.loads(rx_data)
            who = rx_payload.get("from", "?")[-6:]
            msg = rx_payload.get("message", "")[:16]

            lcd_scroll(f"RX {rx_cnt}:{who}:{msg}")
            lcd_scroll(f"RSSI {rx_rssi:.1f} SNR {rx_snr:.1f}")

            # Enviar ACK si es legal (respetando el ciclo de trabajo)
            now = time.ticks_ms()
            legal = time.ticks_diff(now, last_tx) > minimum_pause

            if legal:
                transmit(f"ACK:{rx_cnt}")

            rx_cnt += 1

        except Exception as e:
            # Manejar errores de análisis
            lcd_scroll(f"Error análisis RX: {e}")
            lcd_scroll(f"Raw: {rx_data[:20]}")

# ───────── Bucle principal ───────────────────────────────────────────────
def main():
    """
    Bucle principal del programa. Maneja la transmisión y
    recepción LoRa.
    :return:
    """
    global rx_flag, rx_cnt, tx_cnt

    init_hardware()
    lcd_scroll("LoRa Tester")
    lcd_scroll(NODE_NAME)
    # Saludo inicial
    transmit("Hello Tester")

    while True:
        gc.collect()
        now = time.ticks_ms()
        legal = time.ticks_diff(now, last_tx) > minimum_pause

        # Comprobar transmisión automática o manual
        if (PAUSE and legal and
            time.ticks_diff(now, last_tx) > PAUSE*1000) or button_pressed():
            if not legal:
                left = (minimum_pause - time.ticks_diff(now, last_tx))//1000 + 1
                lcd_scroll(f"Espera ciclo {left}s")
            else:
                transmit(f"Ping {tx_cnt}")

        # Procesar cualquier mensaje recibido
        if rx_flag:
            process_received_message()

        time.sleep_ms(20)

if __name__ == "__main__":
    main()