"""main.py – merged version that shows TX/RX packets on the OLED, includes ACK logic
from main2 and powers the display with VEXT. Wi‑Fi support is optional.

Adapted from the user's original main.py and main2.py.
"""

import time, gc, _thread
from machine import Pin, I2C
import network
import ujson
from sx1262 import SX1262
import ssd1306

# ───────── Board pins (Heltec V3 ESP32‑S3) ──────────────────────────────────
#   LoRa
LORA_CS    = 8
LORA_SCK   = 9
LORA_MOSI  = 10
LORA_MISO  = 11
LORA_RESET = 12
LORA_BUSY  = 13
LORA_DIO1  = 14

#   OLED
VEXT       = 36   # power for display
OLED_SCL   = 18
OLED_SDA   = 17
OLED_RST   = 21

#   User I/O
USER_BUTTON = 0
LED         = 35

# ───────── LoRa settings — must match the peer node ────────────────────────
FREQUENCY        = 868.1      # MHz
BANDWIDTH        = 125.0      # kHz
SPREADING_FACTOR = 7
CODING_RATE      = 5          # 4/5
SYNC_WORD        = 0x34
TRANSMIT_POWER   = 14         # dBm
PAUSE            = 100        # s between automatic pings

# ───────── OLED constants ──────────────────────────────────────────────────
OLED_WIDTH  = 128
OLED_HEIGHT = 64
BRIGHTNESS  = 255
LINE_H      = 12
MAX_LINES   = 5

display_buffer = ["" for _ in range(MAX_LINES)]

NODE_NAME = "LoRaTester"  # Node name for display and packet payload


# ───────── Globals ─────────────────────────────────────────────────────────
tx_cnt = 0
rx_cnt = 0
last_tx = 0
minimum_pause = 0
rx_flag = False
rx_data = ""
rx_rssi = 0.0
rx_snr  = 0.0
rx_lock = _thread.allocate_lock()

# ───────── Display helpers ─────────────────────────────────────────────────
def lcd_scroll(text: str):
    display_buffer.pop(0)
    display_buffer.append(text)
    oled.fill(0)
    for i, line in enumerate(display_buffer):
        oled.text(line, 0, i * LINE_H, 1)
    oled.show()
    print(text)

# ───────── Hardware initialisation ─────────────────────────────────────────
def init_hardware():
    global oled, btn, led, lora

    # Power OLED (VEXT LOW = ON)
    Pin(VEXT, Pin.OUT, value=0)

    led = Pin(LED, Pin.OUT, value=0)
    btn = Pin(USER_BUTTON, Pin.IN, Pin.PULL_UP)

    rst = Pin(OLED_RST, Pin.OUT, value=0)
    time.sleep_ms(20)
    rst.value(1)

    i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400_000)
    if 0x3C not in i2c.scan():
        raise RuntimeError("OLED not found – check wiring")
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

# ───────── LoRa callbacks ──────────────────────────────────────────────────
def on_receive(events):
    global rx_flag, rx_data, rx_rssi, rx_snr
    if events & SX1262.RX_DONE:
        pkt, stat = lora.recv()
        if stat == 0 and pkt:
            with rx_lock:
                rx_flag = True
                rx_data = pkt.decode("utf-8", "ignore").strip()
                rx_rssi = lora.getRSSI()
                rx_snr  = lora.getSNR()

# ───────── Helpers ─────────────────────────────────────────────────────────
def button_pressed():
    if not btn.value():
        time.sleep_ms(30)
        return not btn.value()
    return False

def transmit(msg: str):
    global last_tx, minimum_pause, tx_cnt
    payload = f'{{"from": "{NODE_NAME}", "message": "{msg}"}}'
    led.on()
    t0 = time.ticks_ms()
    _, st = lora.send(payload.encode() + b"\n")
    dt = time.ticks_diff(time.ticks_ms(), t0)
    led.off()
    if st:
        lcd_scroll(f"TX error {st}")
    else:
        minimum_pause = dt * 100   # duty‑cycle guard
        last_tx = time.ticks_ms()
    lcd_scroll(f"TX {tx_cnt}:{msg}")
    tx_cnt += 1
    return dt

# ───────── Main loop ───────────────────────────────────────────────────────
def main():
    global rx_flag, rx_cnt, tx_cnt

    init_hardware()
    lcd_scroll("LoRa Tester")
    lcd_scroll(NODE_NAME)
    # Initial hello
    transmit("Hello Tester")

    while True:
        gc.collect()
        now = time.ticks_ms()
        legal = time.ticks_diff(now, last_tx) > minimum_pause

        if (PAUSE and legal and
            time.ticks_diff(now, last_tx) > PAUSE*1000) or button_pressed():
            if not legal:
                left = (minimum_pause - time.ticks_diff(now, last_tx))//1000 + 1
                lcd_scroll(f"Duty wait {left}s")
            else:
                transmit(f"Ping {tx_cnt}")

        if rx_flag:
            with rx_lock:
                rx_flag = False
                try:
                    rx_payload = ujson.loads(rx_data)
                    who = rx_payload.get("from", "?")[-6:]
                    msg = rx_payload.get("message", "")[:16]
                except:
                    who = "raw"
                    msg = rx_data[:16]
                lcd_scroll(f"RX {rx_cnt}:{who}:{msg}")
                lcd_scroll(f"RSSI {rx_rssi:.1f} SNR {rx_snr:.1f}")
                rx_cnt += 1

            if legal:
                transmit(f"ACK:{tx_cnt}")

        time.sleep_ms(20)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Re‑boot by keyboard")
