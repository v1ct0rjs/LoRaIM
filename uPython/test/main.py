# main.py  – Heltec Wi-Fi LoRa 32 V3  (ESP32-S3 + OLED)
from machine import Pin, I2C
import time, sys, network

# ------------ CONFIGURACIÓN -----------------
SSID, PASSWORD = "p3sc4", "octopus8117flc24"

# ---- 1. Wi-Fi ---------------------------------------------------------------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    wlan.connect(SSID, PASSWORD)
    for _ in range(100):                      # ~10 s de espera
        if wlan.isconnected():
            break
        time.sleep_ms(100)
print("Wi-Fi:", wlan.ifconfig()[0] if wlan.isconnected() else "sin conexión")

# ---- 2. Instala / importa ssd1306 solo si falta ----------------------------
def ensure_ssd1306():
    try:
        import ssd1306          # ¿ya presente?
        return ssd1306
    except ImportError:
        import mip
        for src in ("ssd1306",
                    "https://raw.githubusercontent.com/stlehmann/micropython-ssd1306/master/ssd1306.py"):
            try:
                print("Instalando:", src)
                mip.install(src)
                if "ssd1306" in sys.modules:
                    del sys.modules["ssd1306"]
                import ssd1306
                return ssd1306
            except Exception as e:
                print("mip:", e)
        raise
ssd1306 = ensure_ssd1306()

# ---- 3. ¡ENCENDER!  Vext + RESET  ------------------------------------------
Pin(36, Pin.OUT, value=0)      # Vext ON  (active-LOW)&#8203;:contentReference[oaicite:3]{index=3}
rst = Pin(21, Pin.OUT, value=0) # RESET LOW
time.sleep_ms(20)
rst.value(1)                   # RESET HIGH -> display listo

# ---- 4. I²C y SSD1306 -------------------------------------------------------
i2c = I2C(0, scl=Pin(18), sda=Pin(17), freq=400_000)  # pines fijos V3&#8203;:contentReference[oaicite:4]{index=4}
print("I2C scan:", i2c.scan())                        # debe dar [60]

oled = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
oled.fill(0)
oled.text("Hola mundo", 0, 0)
oled.text(wlan.ifconfig()[0] if wlan.isconnected() else "Sin Wi-Fi", 0, 10)
oled.show()
