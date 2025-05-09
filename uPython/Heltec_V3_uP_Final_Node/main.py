# --- START OF FILE main.py ---

"""
main.py – Heltec V3 ESP32‑S3
• Puente LoRa ↔ OLED ↔ SoftAP ↔ Web UI
• AP 172.16.0.1 (SSID LoRaMonitor) con servidor HTTP integrado.
"""

import time, gc, _thread, ure, ujson, usocket as socket
from machine import Pin, I2C
import network
from sx1262 import SX1262  # Asegúrate de que este archivo está en tu ESP32
import ssd1306

# ───────── Pines ────────────────────────────────────────────────────────
LORA_CS = 8
LORA_SCK = 9
LORA_MOSI = 10
LORA_MISO = 11
LORA_RESET = 12
LORA_BUSY = 13
LORA_DIO1 = 14

VEXT = 36
OLED_SCL = 18
OLED_SDA = 17
OLED_RST = 21

USER_BUTTON = 0
LED_PIN = 35

# ───────── Parámetros LoRa ──────────────────────────────────────────────
FREQUENCY = 866.3
BANDWIDTH = 250.0  # Ejemplo: 125.0, 250.0, 500.0
SPREADING_FACTOR = 9  # Ejemplo: 7 a 12
CODING_RATE = 5  # Ejemplo: 5 (4/5), 6 (4/6), 7 (4/7), 8 (4/8)
SYNC_WORD = 0x12
TRANSMIT_POWER = 14  # Potencia de transmisión en dBm (ajusta según necesidad y regulación)

# ───────── OLED ─────────────────────────────────────────────────────────
OLED_W = 128
OLED_H = 64
BRIGHT = 255
LINE_H = 12  # Altura de línea en píxeles para texto en OLED
MAX_LINE = 5  # Máximo de líneas a mostrar en OLED antes de scroll

# ───────── SoftAP ───────────────────────────────────────────────────────
AP_SSID = "LoRaMonitor"
AP_IP = "172.16.0.1"
AP_MASK = "255.255.255.0"
AP_GW = "172.16.0.1"
AP_DNS = "8.8.8.8"  # Opcional, puedes usar AP_GW como DNS también
AP_PASSWORD_DEFAULT = "loramonitor123"  # Contraseña por defecto si .env no existe o es inválida
AP_PASSWORD = AP_PASSWORD_DEFAULT

# ───────── Historial ────────────────────────────────────────────────────
HIST_MAX = 50
# Inicializar variables globales para evitar errores
oled = None
led = None
btn = None
lora = None
display = [""] * MAX_LINE  # Buffer para las líneas del OLED
history = []  # Historial de mensajes LoRa
rx_flag = False  # Flag para indicar recepción de LoRa
rx_msg = ""
rx_rssi = 0.0
rx_snr = 0.0
lock = _thread.allocate_lock()  # Lock para proteger acceso a recursos compartidos

# ───────── HTML Page Template ───────────────────────────────────────────
PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>LoRa Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #f0f2f5; color: #333; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .container {{ background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 90%; max-width: 700px; }}
        h1 {{ color: #007bff; text-align: center; margin-bottom: 20px; }}
        h2 {{ color: #555; margin-top: 30px; border-bottom: 2px solid #eee; padding-bottom: 10px;}}
        table {{ border-collapse: collapse; width: 100%; margin-top: 15px; font-size: 0.9em; }}
        th, td {{ border: 1px solid #ddd; padding: 10px 12px; text-align: left; }}
        th {{ background-color: #007bff; color: white; }}
        tr:nth-child(even) {{ background-color: #f8f9fa; }}
        tr:hover {{ background-color: #e9ecef; }}
        form {{ margin-bottom: 25px; padding: 20px; background-color: #f8f9fa; border-radius: 5px; border: 1px solid #ddd;}}
        input[type="text"] {{ padding: 12px; width: calc(100% - 120px); margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        input[type="submit"] {{ padding: 12px 18px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }}
        input[type="submit"]:hover {{ background-color: #218838; }}
        @media (max-width: 600px) {{
            input[type="text"] {{ width: calc(100% - 100px); margin-bottom: 10px; }}
            table, th, td {{ font-size: 0.8em; padding: 6px 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Monitor LoRa Heltec V3</h1>
        <form action="/send" method="get">
            <input type="text" name="msg" placeholder="Escribe un mensaje LoRa..." required>
            <input type="submit" value="Enviar">
        </form>
        <h2>Historial de Mensajes (últimos {n})</h2>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Mensaje</th>
                    <th>RSSI</th>
                    <th>SNR</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""


# Función para cargar variables de entorno desde .env
def load_env(filename=".env"):
    global AP_PASSWORD, AP_PASSWORD_DEFAULT
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                            (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    if key == "AP_PASSWORD":
                        if len(value) >= 8:
                            AP_PASSWORD = value
                            print(f"Contraseña AP cargada desde {filename}")
                        else:
                            print(
                                f"Advertencia: Contraseña en {filename} es demasiado corta. Usando contraseña por defecto.")
                            AP_PASSWORD = AP_PASSWORD_DEFAULT
                        return  # Salir después de encontrar y procesar AP_PASSWORD
            # Si AP_PASSWORD no se encontró en el archivo
            print(f"Advertencia: AP_PASSWORD no encontrada en {filename}. Usando contraseña por defecto.")
            AP_PASSWORD = AP_PASSWORD_DEFAULT

    except OSError:
        print(f"Advertencia: No se encontró el archivo {filename}. Usando contraseña por defecto.")
        AP_PASSWORD = AP_PASSWORD_DEFAULT
    except Exception as e:
        print(f"Error al leer {filename}: {e}. Usando contraseña por defecto.")
        AP_PASSWORD = AP_PASSWORD_DEFAULT


# Función para añadir elementos con límite al historial
def append_with_limit(lst, item, maxlen):
    lst.append(item)
    if len(lst) > maxlen:
        lst.pop(0)


# ───────── Helpers ──────────────────────────────────────────────────────
def scroll(txt):
    global oled, display, MAX_LINE, OLED_W, LINE_H
    # Limitar longitud del texto para que quepa en el OLED (aprox 8px por char)
    max_chars_per_line = OLED_W // 8
    display.pop(0)
    display.append(txt[:max_chars_per_line])

    if oled:
        oled.fill(0)
        for i, line_text in enumerate(display):
            oled.text(line_text, 0, i * LINE_H, 1)
        oled.show()
    print(txt)  # También imprimir en consola serial


def url_unquote(s):
    res = ""
    i = 0
    while i < len(s):
        c = s[i]
        if c == "+":
            res += " "
            i += 1
        elif c == "%" and i + 2 < len(s):
            try:
                hex_val = s[i + 1:i + 3]
                res += chr(int(hex_val, 16))
                i += 3
            except ValueError:  # Si no es un valor hexadecimal válido
                res += c  # Añadir el '%' tal cual
                i += 1
        else:
            res += c
            i += 1
    return res


# ───────── Hardware init ────────────────────────────────────────────────

def hw_init():
    global oled, led, btn, lora, VEXT, OLED_SCL, OLED_SDA, OLED_RST, OLED_W, OLED_H, BRIGHT
    global LORA_SCK, LORA_MOSI, LORA_MISO, LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY
    global FREQUENCY, BANDWIDTH, SPREADING_FACTOR, CODING_RATE, TRANSMIT_POWER, SYNC_WORD

    print("Inicializando hardware...")

    Pin(VEXT, Pin.OUT).value(0)  # Power ON for VEXT (OLED, LoRa on Heltec boards)
    time.sleep_ms(100)  # Dar tiempo a que VEXT se estabilice

    led = Pin(LED_PIN, Pin.OUT)
    btn = Pin(USER_BUTTON, Pin.IN, Pin.PULL_UP)

    # Inicializar OLED
    rst_pin_oled = Pin(OLED_RST, Pin.OUT)
    rst_pin_oled.value(0)
    time.sleep_ms(20)
    rst_pin_oled.value(1)
    time.sleep_ms(20)

    try:
        i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
        oled_devices = i2c.scan()
        if not oled_devices:
            print("Error: No se encontró dispositivo I2C para OLED en la dirección esperada.")
            oled = None
        else:
            print(
                f"Dispositivos I2C encontrados: {oled_devices}")  # Debería mostrar la dirección del SSD1306 (ej: 60 o 0x3C)
            oled = ssd1306.SSD1306_I2C(OLED_W, OLED_H, i2c)
            oled.contrast(BRIGHT)
            oled.fill(0)
            oled.show()
            scroll("OLED OK")
    except Exception as e:
        print(f"Error al inicializar OLED: {e}")
        oled = None

    # Inicializar LoRa
    try:
        # Asegúrate que los parámetros de SX1262 coincidan con tu librería
        # Común es: SX1262(spi_bus, clk, mosi, miso, cs, irq, rst, busy)
        lora = SX1262(spi_bus=1, clk=LORA_SCK, mosi=LORA_MOSI, miso=LORA_MISO,
                      cs=LORA_CS, irq=LORA_DIO1, rst=LORA_RESET, busy=LORA_BUSY)

        # Parámetros para begin: freq, bw, sf, cr, sync_word, power, preamble_len, implicit_header, crc_on, use_dma (varía por librería)
        # El método begin puede devolver un código de error o lanzar una excepción.
        # Un código de error 0 usualmente significa éxito.
        init_params = {
            'freq': FREQUENCY,
            'bw': BANDWIDTH,
            'sf': SPREADING_FACTOR,
            'cr': CODING_RATE,
            'sync_word': SYNC_WORD,
            'power': TRANSMIT_POWER,  # 'power' o 'tx_power'
            'preamble_length': 8,
            'implicit_header': False,
            'crc_on': True,
            # 'use_dma': False # Algunas librerías tienen esto
        }
        # Desempaquetar argumentos nombrados si tu librería los soporta así
        # err = lora.begin(**init_params)
        # O pasar posicionalmente si es necesario
        err = lora.begin(FREQUENCY, BANDWIDTH, SPREADING_FACTOR, CODING_RATE, SYNC_WORD,
                         TRANSMIT_POWER, 8, False, True)  # Ajusta el orden y parámetros según tu sx1262.py

        if err != 0:  # Asumiendo que 0 es éxito (SX1262.ERR_NONE)
            print(f"Error al inicializar SX1262: Código de error {err}")
            if oled: scroll(f"LoRa Err {err}")
            lora = None
        else:
            lora.setBlockingCallback(False, lora_cb)  # Configurar callback para modo no bloqueante
            print("Módulo LoRa SX1262 inicializado correctamente.")
            if oled: scroll("LoRa OK")
    except Exception as e:
        print(f"Excepción crítica al inicializar LoRa: {e}")
        if oled: scroll("LoRa Init EXCEPTION")
        lora = None


def ap_init():
    global oled, AP_PASSWORD, AP_SSID, AP_IP, AP_MASK, AP_GW, AP_DNS

    ap = network.WLAN(network.AP_IF)

    try:
        print("Configurando Punto de Acceso (AP)...")
        if ap.active():
            print("AP ya estaba activo, desactivando primero para reconfigurar.")
            ap.active(False)
            time.sleep_ms(500)

        print("Activando interfaz AP...")
        ap.active(True)

        activation_attempts = 0
        while not ap.active() and activation_attempts < 50:  # Esperar hasta 5 segundos
            time.sleep_ms(100)
            activation_attempts += 1

        if not ap.active():
            print("Error: No se pudo activar la interfaz AP.")
            if oled: scroll("AP Act Fail")
            return

        print("Interfaz AP activada.")

        if AP_PASSWORD == AP_PASSWORD_DEFAULT and len(AP_PASSWORD_DEFAULT) < 8:  # Check por si el default es inseguro
            print(f"ADVERTENCIA: La contraseña por defecto es insegura. Usando AP abierto.")
            auth_mode = network.AUTH_OPEN
            config_params = {'essid': AP_SSID}
        elif not AP_PASSWORD or len(AP_PASSWORD) < 8:
            print(f"ADVERTENCIA: Contraseña AP no válida o demasiado corta. Usando AP abierto.")
            auth_mode = network.AUTH_OPEN
            config_params = {'essid': AP_SSID}
        else:
            print(f"Configurando AP '{AP_SSID}' con seguridad WPA2-PSK.")
            auth_mode = network.AUTH_WPA2_PSK
            config_params = {'essid': AP_SSID, 'password': AP_PASSWORD}

        ap.config(authmode=auth_mode, **config_params)
        time.sleep_ms(200)

        print(f"Configurando IP estática para el AP: {AP_IP}")
        ap.ifconfig((AP_IP, AP_MASK, AP_GW, AP_DNS))
        time.sleep_ms(1000)

        current_config = ap.ifconfig()
        print(
            f"Configuración actual del AP: IP={current_config[0]}, Subnet={current_config[1]}, GW={current_config[2]}, DNS={current_config[3]}")
        print(f"Estado AP: Activo={ap.active()}")

        if ap.active() and current_config[0] == AP_IP:
            print(f"AP '{AP_SSID}' inicializado en {current_config[0]}. El servidor DHCP debería estar operativo.")
            if oled: scroll(f"AP: {current_config[0]}")
        elif not ap.active():
            print("Error: AP se desactivó después de la configuración.")
            if oled: scroll("AP FAILED (inactive)")
        else:
            print(f"Error: La IP del AP es {current_config[0]}, pero se esperaba {AP_IP}.")
            if oled: scroll(f"AP IP ERR: {current_config[0][:OLED_W // 8 - 8]}")  # Truncar IP si es larga

    except Exception as e:
        print(f"Error crítico durante la inicialización del AP: {e}")
        if oled: scroll("AP Init CRITICAL")
        if ap and ap.active():  # Intentar desactivar en caso de error
            ap.active(False)


# ───────── LoRa callback ────────────────────────────────────────────────
def lora_cb(events):
    global rx_flag, rx_msg, rx_rssi, rx_snr, lora, lock
    if not lora: return

    try:
        if events & SX1262.RX_DONE:
            # El formato de recv() puede variar: (payload, err_code) o solo payload si no hay error
            # Asumimos que tu librería devuelve (payload, error_code) o (payload, None)
            pkt, err = lora.recv()

            # Ajusta la condición de éxito según tu librería:
            # Si err es None en éxito: if pkt and err is None:
            # Si err es 0 en éxito: if pkt and err == 0:
            if pkt and (err == 0 or err is None):  # Condición común
                with lock:
                    rx_flag = True
                    try:
                        rx_msg = pkt.decode('utf-8').strip()
                    except UnicodeError:
                        rx_msg = f"Bytes: {pkt}"  # Si no es utf-8 válido
                    rx_rssi = lora.getRSSI()
                    rx_snr = lora.getSNR()
                    print(f"LoRa RX: '{rx_msg}', RSSI: {rx_rssi}, SNR: {rx_snr}")
            elif err is not None and err != 0:  # Si hay un código de error
                print(f"Error en recepción LoRa (callback): Código {err}")

        if events & SX1262.TX_DONE:
            print("LoRa TX Done event (callback)")
            # Aquí podrías apagar el LED si lo encendiste al inicio de una TX no bloqueante, etc.

    except Exception as e:
        print(f"Error en lora_cb: {e}")


# ───────── Enviar LoRa ──────────────────────────────────────────────────
def lora_send(text):
    global led, lora, lock
    msg_display = "LoRa no init"
    if not lora:
        print("Intento de enviar LoRa, pero el módulo no está inicializado.")
        scroll(msg_display)
        return

    try:
        # Considerar bloquear otras operaciones LoRa mientras se envía si es necesario
        # with lock: # Podría ser demasiado restrictivo si send es bloqueante
        if led: led.on()

        payload_to_send = text.encode('utf-8')  # No añadir \n a menos que el receptor lo espere explícitamente

        # El método send() puede ser bloqueante o no, y devolver un código de error o lanzar excepción.
        # Asumimos que devuelve un código de error (0 para éxito) o None para éxito.
        status = lora.send(payload_to_send)

        if led: led.off()

        # Interpretar el 'status' devuelto por lora.send()
        # Esto es muy dependiente de tu librería sx1262.py
        if status == 0 or status is None:  # Común para éxito
            msg_display = f"TX: {text[:10]}..." if len(text) > 10 else f"TX: {text}"
            print(f"LoRa TX OK: '{text}'")
        elif hasattr(status, '__iter__') and (
                status[1] == 0 or status[1] is None):  # si devuelve (datos_enviados, err_code)
            msg_display = f"TX: {text[:10]}..." if len(text) > 10 else f"TX: {text}"
            print(f"LoRa TX OK (tuple): '{text}'")
        else:  # Error
            msg_display = f"TX Err {status}"
            print(f"Error al enviar LoRa: Código/Estado {status}")

        scroll(msg_display)

    except Exception as e:
        if led: led.off()
        print(f"Excepción al enviar LoRa: {e}")
        scroll(f"TX Exc: {str(e)[:OLED_W // 8 - 8]}")


# ───────── Servidor Web ───────────────────────────────────────────────────
def web_server_thread():
    global history, lock, PAGE, HIST_MAX

    try:
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(addr)
        s.listen(3)  # Aumentado a 3 para un poco más de backlog
        print(f"Servidor web iniciado en {AP_IP}:80")
    except Exception as e:
        print(f"Error fatal al iniciar servidor web: {e}")
        if oled: scroll("WebSrv FATAL")
        return  # No continuar si el socket no se puede crear/bindear

    while True:
        cl = None
        try:
            cl, addr_info = s.accept()
            # print(f"Cliente conectado desde: {addr_info[0]}:{addr_info[1]}")

            req_data_bytes = b""
            try:
                cl.settimeout(2.0)
                while True:
                    chunk = cl.recv(512)
                    if not chunk:  # Conexión cerrada por el cliente
                        break
                    req_data_bytes += chunk
                    if len(req_data_bytes) > 2048:  # Limitar tamaño de la petición
                        print("Petición demasiado grande. Cerrando conexión.")
                        cl.sendall(b"HTTP/1.1 413 Payload Too Large\r\nConnection: close\r\n\r\nToo Large")
                        req_data_bytes = b""  # Marcar para no procesar
                        break
                    if b"\r\n\r\n" in req_data_bytes:  # Fin de las cabeceras HTTP
                        break

                if req_data_bytes:  # Solo procesar si se recibieron datos
                    req_str = req_data_bytes.decode('utf-8', 'ignore')  # 'ignore' para caracteres no válidos
                else:
                    req_str = ""

            except socket.timeout:  # usocket.timeout
                print("Timeout recibiendo datos del cliente.")
                if cl: cl.close()  # Asegurar cierre
                continue  # Esperar nueva conexión
            except Exception as e_recv:
                print(f"Error recibiendo datos del cliente: {e_recv}")
                if cl: cl.close()
                continue

            if not req_str or "HTTP/" not in req_str:  # Petición inválida o vacía
                if cl: cl.close()
                continue

            # Extraer path
            path_match = ure.search("GET (.*?) HTTP/", req_str)
            path = path_match.group(1) if path_match else "/"

            # Preparar respuesta
            response_headers_base = "HTTP/1.1 {}\r\nContent-Type: {}\r\nConnection: close\r\n\r\n"
            status_code = "200 OK"
            content_type = "text/html; charset=utf-8"
            response_body = ""

            if path.startswith("/api/msgs"):
                content_type = "application/json"
                with lock:  # Acceso seguro a history
                    response_body = ujson.dumps(history)
            elif path.startswith("/send?"):
                msg_match = ure.search("msg=([^& ]+)", path)
                if msg_match:
                    msg_to_send = url_unquote(msg_match.group(1))
                    if msg_to_send:  # Solo enviar si el mensaje no está vacío
                        lora_send(msg_to_send)
                # Redirigir a la página principal después de enviar
                status_code = "303 See Other"
                # La cabecera Location debe ser parte de las cabeceras, no del cuerpo
                response_headers_base = "HTTP/1.1 303 See Other\r\nLocation: /\r\nConnection: close\r\n\r\n"
                # El cuerpo de una respuesta 303 suele estar vacío o ser un breve mensaje.
                response_body = "Redirigiendo..."  # Opcional
            else:  # Servir la página principal
                with lock:
                    rows_html_list = [
                        "<tr><td>{:.0f}</td><td>{}</td><td>{:.1f}</td><td>{:.1f}</td></tr>"
                        .format(ts, m, rssi, snr) for ts, m, rssi, snr in reversed(history)
                    ]
                    rows_html = "\n".join(rows_html_list)
                response_body = PAGE.format(rows=rows_html, n=HIST_MAX)

            # Enviar respuesta
            full_response_headers = response_headers_base.format(status_code, content_type).encode('utf-8')
            cl.sendall(full_response_headers)
            if response_body:  # Solo enviar cuerpo si existe
                cl.sendall(response_body.encode('utf-8'))

        except OSError as e:
            # Códigos de error comunes: 104 (ECONNRESET), 113 (EHOSTUNREACH), 128 (ENOTCONN)
            print(f"OSError en web_server_thread (código {e.args[0]}): {e}")
        except Exception as e:
            print(f"Error general en web_server_thread: {e}")
            # Intentar enviar error 500 si el socket aún parece usable
            if cl:
                try:
                    err_resp = b"HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\nError interno del servidor."
                    cl.sendall(err_resp)
                except Exception as e_send_500:
                    print(f"No se pudo enviar respuesta 500: {e_send_500}")
        finally:
            if cl:
                try:
                    cl.close()
                except Exception as e_close:
                    print(f"Excepción al cerrar socket del cliente: {e_close}")
            gc.collect()


# ───────── Main ────────────────────────────────────────────────────────
def main():
    global rx_flag, rx_msg, rx_rssi, rx_snr, history, oled, led, lora, lock, btn

    print("Iniciando LoRaMonitor...")

    load_env()  # Cargar configuración de .env

    hw_init()  # Inicializar componentes de hardware

    if oled:
        scroll("Booting...")
    else:
        print("Booting... (OLED no disponible)")

    ap_init()  # Inicializar Punto de Acceso Wi-Fi

    print("Iniciando servidor web en un nuevo hilo...")
    try:
        _thread.start_new_thread(web_server_thread, ())
    except Exception as e:
        print(f"Error crítico al iniciar hilo del servidor web: {e}")
        if oled: scroll("WebSrv THREAD FAIL")
        # Considerar si el programa puede continuar sin el servidor web

    time.sleep_ms(500)  # Pequeña pausa para que los hilos/servicios se estabilicen

    if lora:
        print("Enviando mensaje LoRa inicial 'Hello LoRaMonitor'")
        lora_send("Hello LoRaMonitor")
    else:
        print("Módulo LoRa no inicializado. No se envía mensaje de prueba.")
        if oled: scroll("LoRa No TX (NoInit)")

    print("Entrando en bucle principal de la aplicación...")
    cnt = 0  # Contador de mensajes recibidos
    last_led_toggle_ms = time.ticks_ms()
    led_state_blinking = False

    while True:
        try:
            current_ms = time.ticks_ms()

            # Parpadeo del LED como indicador de actividad (no bloqueante)
            if led and time.ticks_diff(current_ms, last_led_toggle_ms) > 1000:  # Cada segundo
                led_state_blinking = not led_state_blinking
                led.value(led_state_blinking)
                last_led_toggle_ms = current_ms

            # Procesar datos recibidos por LoRa
            if rx_flag:
                local_rx_msg, local_rx_rssi, local_rx_snr = "", 0.0, 0.0
                # Copiar datos y resetear flag bajo lock para minimizar tiempo de bloqueo
                with lock:
                    if rx_flag:  # Doble check por si cambia entre el if y el lock
                        local_rx_msg, local_rx_rssi, local_rx_snr = rx_msg, rx_rssi, rx_snr
                        rx_flag = False

                if local_rx_msg:  # Procesar solo si realmente había un mensaje copiado
                    cnt += 1
                    display_msg = f"RX{cnt}: {local_rx_msg[:OLED_W // 8 - 6]}"  # Truncar para OLED
                    display_stats = f"R{local_rx_rssi:.1f} S{local_rx_snr:.1f}"

                    print(f"Mensaje LoRa Recibido #{cnt}: '{local_rx_msg}'")
                    print(f"  RSSI: {local_rx_rssi:.1f} dBm, SNR: {local_rx_snr:.1f} dB")
                    if oled:
                        scroll(display_msg)
                        scroll(display_stats)

                    with lock:  # Proteger acceso a 'history'
                        append_with_limit(history, (time.time(), local_rx_msg, local_rx_rssi, local_rx_snr), HIST_MAX)

            # Comprobar botón de usuario (si está conectado y configurado)
            if btn and btn.value() == 0:  # Botón presionado (activo bajo)
                if oled: scroll("BTN Presionado")
                print("Botón de usuario presionado.")
                if lora:
                    lora_send(f"TestMsg:{cnt}")
                else:
                    if oled: scroll("LoRa No TX (NoInit)")
                    print("Botón presionado, pero LoRa no está listo para transmitir.")
                time.sleep_ms(250)  # Debounce simple para el botón

            time.sleep_ms(50)  # Pausa corta para no saturar la CPU
            gc.collect()  # Recolectar basura periódicamente

        except Exception as e:
            print(f"Error en el bucle principal: {e}")
            if oled: scroll("Main Loop ERROR")
            # En caso de error grave, un breve retardo antes de reintentar
            time.sleep_ms(1000)

        # ───────── Entrypoint ──────────────────────────────────────────────────


if __name__ == "__main__":
    print(f"--- Iniciando ESP32 LoRa Monitor ({time.localtime()}) ---")
    try:
        main()
    except KeyboardInterrupt:
        print("Programa detenido por el usuario (KeyboardInterrupt). Reiniciando...")
        time.sleep(1)  # Dar tiempo para que los mensajes se impriman
        machine.reset()
    except Exception as e:
        print(f"Error crítico no capturado en el nivel superior: {e}")
        # Aquí podrías intentar guardar el error en un archivo si tienes un sistema de archivos
        # import sys
        # with open("crash.log", "a") as f:
        #    sys.print_exception(e, f)
        print("Reiniciando el dispositivo en 5 segundos debido a error crítico...")
        time.sleep(5)
        machine.reset()

# --- END OF FILE main.py ---