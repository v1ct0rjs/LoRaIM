from machine import Pin, I2C, SPI
import time, network, sys
from sx1262 import SX1262           # librería micropySX126X (instálala vía mip)

# ---------- PARÁMETROS DE USUARIO ----------
SSID, PASSWORD = "p3sc4", "octopus8117flc24"

# ---------- Pines SX1262 (Heltec V3) ----------
PIN_CS, PIN_SCK, PIN_MOSI, PIN_MISO = 8, 9, 10, 11
PIN_RST, PIN_BUSY, PIN_DIO1         = 12, 13, 14

# ---------- Radio / Potencia ----------
LORA_FREQ_MHZ   = 868
AIR_SPEED_KBPS  = 2.4     # 2 400 bps (= E22 por defecto, modo LoRa)
TX_POWER_DBM    = 13       # 13 dBm ≈ 20 mW EIRP (legal ≤ 25 mW)

# ---------- Wi-Fi ----------
def wifi_connect():
    wlan = network.WLAN(network.STA_IF); wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        for _ in range(100):
            if wlan.isconnected():
                break
            time.sleep_ms(100)
    return wlan.ifconfig()[0] if wlan.isconnected() else "Sin Wi-Fi"

ip = wifi_connect()
print("Wi-Fi:", ip)

# ---------- OLED ----------
try:
    import ssd1306
except ImportError:
    sys.exit("Falta ssd1306.py en el FS de la Heltec")

Pin(36, Pin.OUT, value=0)      # Vext ON
rst = Pin(21, Pin.OUT, value=0); time.sleep_ms(20); rst.value(1)
i2c  = I2C(0, scl=Pin(18), sda=Pin(17), freq=400_000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0); oled.text("LoRa ↔ MQTT", 0, 0); oled.text(ip, 0, 10); oled.show()

# ---------- LoRa SX1262 ----------
spi = SPI(2, baudrate=10_000_000, polarity=0, phase=0,
          sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=Pin(PIN_MISO))

sx = SX1262(spi_bus=2, clk=PIN_SCK, mosi=PIN_MOSI, miso=PIN_MISO,
            cs=PIN_CS, irq=PIN_DIO1, rst=PIN_RST, gpio=PIN_BUSY)

# ---- Configurar para 2.4 kbps LoRa compatible con E22 ---------------
status = sx.begin(freq=LORA_FREQ_MHZ,
                  bw=62.5, sf=10, cr=8,   # equivalencia ~2.4 kbps
                  syncWord=0x12, power=TX_POWER_DBM,
                  preambleLength=8, crcOn=True, blocking=False)

print("SX1262 init:", SX1262.STATUS[status])

# ---------- Callback RX ----------
rx_counter = 0
def on_event(ev):
    global rx_counter
    if ev & SX1262.RX_DONE:
        data, err = sx.recv()
        if err == 0 and data:
            msg = data.decode().strip()
            print("[RX]", msg)
            oled.fill_rect(0, 40, 128, 24, 0)
            oled.text("RX:"+msg[:16], 0, 40)
            rx_counter += 1
            oled.text("RXcnt:"+str(rx_counter), 0, 52)
            oled.show()
    elif ev & SX1262.TX_DONE:
        print("   TX_DONE")

sx.setBlockingCallback(False, on_event)

# ---------- Bucle principal ----------
tx_counter = 0
while True:
    payload = f"Ping {tx_counter}"
    sx.send(payload.encode() + b"\n")   # '\n' delimita la trama
    print("[TX]", payload)

    oled.fill_rect(0, 20, 128, 12, 0)
    oled.text("TX:"+str(tx_counter), 0, 20)
    oled.show()

    tx_counter += 1
    time.sleep(10)
