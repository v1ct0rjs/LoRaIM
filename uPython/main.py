from machine import Pin, I2C, SPI
import time, network
from sx1262 import SX1262            # librería micropySX126X

# ---------- 1. CONFIGURACIÓN USUARIO ----------
SSID, PASSWORD = "p3sc4", "octopus8117flc24"

# Pines SX1262 para Heltec WiFi LoRa 32 V3
PIN_CS   = 8     # NSS
PIN_SCK  = 9
PIN_MOSI = 10
PIN_MISO = 11
PIN_RST  = 12
PIN_BUSY = 13
PIN_DIO1 = 14

# Parámetros LoRa (deben coincidir con la RPi / HAT E22)
LORA_FREQ_MHZ = 868          # MHz
LORA_BW_KHZ   = 125.0        # kHz
LORA_SF       = 7
LORA_CR       = 8            # 4/8
LORA_TX_DBM   = 14           # potencia máx. legal EU

# ---------- 2. Wi-Fi ---------------------------------------------------------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    wlan.connect(SSID, PASSWORD)
    for _ in range(100):                     # ~10 s de espera
        if wlan.isconnected():
            break
        time.sleep_ms(100)
ip = wlan.ifconfig()[0] if wlan.isconnected() else "Sin Wi-Fi"
print("Wi-Fi:", ip)

# ---------- 3. OLED 0.96" (SSD1306) -----------------------------------------
try:
    import ssd1306                         # driver oficial MicroPython
except ImportError:
    raise ImportError("Falta ssd1306.py junto a main.py")

Pin(36, Pin.OUT, value=0)                  # Vext ON (active-LOW)  Heltec docs
rst = Pin(21, Pin.OUT, value=0)            # RESET LOW
time.sleep_ms(20); rst.value(1)            # RESET HIGH

i2c = I2C(0, scl=Pin(18), sda=Pin(17), freq=400_000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
oled.fill(0)
oled.text("LoRa-MQTT Demo", 0, 0)
oled.text("IP: "+ip, 0, 10)
oled.show()

# ---------- 4. LoRa SX1262 ---------------------------------------------------
spi = SPI(2, baudrate=10_000_000, polarity=0, phase=0,
          sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI), miso=Pin(PIN_MISO))

sx = SX1262(spi_bus=2, clk=PIN_SCK, mosi=PIN_MOSI, miso=PIN_MISO,
            cs=PIN_CS, irq=PIN_DIO1, rst=PIN_RST, gpio=PIN_BUSY)

status = sx.begin(freq=LORA_FREQ_MHZ, bw=LORA_BW_KHZ, sf=LORA_SF,
                  cr=LORA_CR, syncWord=0x12, power=LORA_TX_DBM,
                  preambleLength=8, crcOn=True, blocking=False)
print("LoRa init status:", SX1262.STATUS[status])

# Callback: se dispara en RX _DONE y actualiza la OLED
def on_event(ev):
    if ev & SX1262.RX_DONE:
        payload, err = sx.recv()
        if err == 0 and payload:
            msg = payload.decode().strip()
            print(msg)
            oled.fill_rect(0, 36, 128, 28, 0)  # limpiar zona inferior
            oled.text("RX:"+msg[:16], 0, 40)
            oled.show()
    elif ev & SX1262.TX_DONE:
        print("   TX_DONE")

sx.setBlockingCallback(False, on_event)

# ---------- 5. Bucle principal ----------------------------------------------
counter = 0
while True:
    # enviar cada 10 s
    out = f"Ping {counter}\n"
    sx.send(out.encode())
    print(out.strip())

    # mostrar contador en OLED
    oled.fill_rect(0, 20, 128, 12, 0)
    oled.text(f"TX: {counter}", 0, 20)
    oled.show()

    counter += 1
    time.sleep(10)
