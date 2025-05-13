import serial
import threading
import datetime
import os
import glob
import time
from flask import Flask, request, render_template, redirect, url_for, jsonify

"""
app.py – Puente Web ⇄ USB ⇄ Heltec LoRa v3
-------------------------------------------------
Este archivo reemplaza al original y añade compatibilidad
con la Heltec LoRa v3 conectada por USB (CDC‑ACM).
• Detecta dinámicamente /dev/ttyUSB* o toma la ruta indicada en
  la variable de entorno LORA_SERIAL_PORT.
• Sube la velocidad a 115 200 bps (valor por defecto del firmware
  MicroPython Heltec).
• Mantiene reconexión automática cuando la placa se desconecta / reconecta.
No hay cambios en las rutas Flask ni en la plantilla; solo en la
capa de acceso serie.
"""

# ──────────────────────────── CONFIGURACIÓN ────────────────────────────

DEFAULT_USB_DEVICE = "/dev/ttyUSB0"  # Fallback si no se encuentra nada
BAUD_RATE = int(os.getenv("LORA_BAUDRATE", "115200"))
LOG_FILE_CONTAINER_PATH = "/app/logs/lora_messages.log"
MAX_LOG_MESSAGES_IN_MEMORY = 50


def resolve_serial_device() -> str:
    """Devuelve el primer dispositivo serie disponible.

    Prioridad:
        1. Variable de entorno LORA_SERIAL_PORT
        2. Primer /dev/ttyUSB* encontrado
        3. DEFAULT_USB_DEVICE
    """
    # 1️⃣ Variable de entorno explícita
    env_port = os.getenv("LORA_SERIAL_PORT")
    if env_port:
        return env_port

    # 2️⃣ Autodetección ttyUSB*
    usb_devices = sorted(glob.glob("/dev/ttyUSB*"))
    if usb_devices:
        return usb_devices[0]

    # 3️⃣ Fallback
    return DEFAULT_USB_DEVICE


SERIAL_PORT_INSIDE_CONTAINER = resolve_serial_device()

app = Flask(__name__)
ser = None
received_messages_log = []  # En memoria para el front‑end

# ──────────────────────────── FUNCIONES AUX ────────────────────────────


def initialize_serial() -> bool:
    """Intenta abrir el puerto serie (con autodetección cada vez)."""
    global ser, SERIAL_PORT_INSIDE_CONTAINER

    SERIAL_PORT_INSIDE_CONTAINER = resolve_serial_device()
    try:
        ser = serial.Serial(SERIAL_PORT_INSIDE_CONTAINER, BAUD_RATE, timeout=1)
        print(f"Puerto serial {SERIAL_PORT_INSIDE_CONTAINER} abierto a {BAUD_RATE} bps.")
        return True
    except serial.SerialException as e:
        print(f"Error al abrir {SERIAL_PORT_INSIDE_CONTAINER}: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al abrir {SERIAL_PORT_INSIDE_CONTAINER}: {e}")
        return False


def ensure_log_directory():
    try:
        log_dir = os.path.dirname(LOG_FILE_CONTAINER_PATH)
        os.makedirs(log_dir, exist_ok=True)
        print(f"Directorio de logs asegurado: {log_dir}")
    except Exception as e:
        print(f"Error creando directorio de logs: {e}")


def log_message(message_string: str, is_received: bool = True):
    """Añade un mensaje al log en memoria y a disco."""
    global received_messages_log
    prefix = "Recibido" if is_received else "Enviado"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"{prefix} [{timestamp}]: {message_string}"

    # Memoria
    received_messages_log.append(formatted_msg)
    if len(received_messages_log) > MAX_LOG_MESSAGES_IN_MEMORY * 2:
        received_messages_log = received_messages_log[-MAX_LOG_MESSAGES_IN_MEMORY:]

    # Disco
    try:
        with open(LOG_FILE_CONTAINER_PATH, "a") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"Error escribiendo en archivo de log ({LOG_FILE_CONTAINER_PATH}): {e}")


# ──────────────────────────── HILO UART RX ────────────────────────────


def read_from_uart_thread():
    global ser
    print("Hilo de lectura UART iniciado.")
    while True:
        if not ser or not ser.is_open:
            print("UART: puerto cerrado. Intentando inicializar…")
            time.sleep(2)
            if initialize_serial():
                print("UART: puerto reabierto.")
            else:
                continue  # Reintentar en siguiente iteración

        try:
            line_bytes = ser.readline()
            if line_bytes:
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if line:
                    print(f"UART <<< {line}")
                    log_message(line, is_received=True)
        except serial.SerialException as e:
            print(f"UART SerialException: {e}. Cerrando puerto…")
            if ser:
                ser.close()
            ser = None  # Forzar re‑apertura
        except Exception as e:
            print(f"UART error inesperado: {e}")
            time.sleep(1)


# ──────────────────────────── RUTAS FLASK ────────────────────────────


@app.route("/", methods=["GET", "POST"])
def index():
    global ser
    if request.method == "POST":
        text_to_send = request.form.get("mensaje", "")
        if text_to_send:
            if ser and ser.is_open:
                try:
                    ser.write((text_to_send + "\n").encode("utf-8"))
                    print(f"UART >>> {text_to_send}")
                    log_message(text_to_send, is_received=False)
                except serial.SerialException as e:
                    print(f"Error TX SerialException: {e}")
                    log_message(f"Error TX: {e}", is_received=False)
                except Exception as e_write:
                    print(f"Error TX inesperado: {e_write}")
                    log_message(f"Error TX inesperado: {e_write}", is_received=False)
            else:
                print("Error: puerto serie no disponible.")
                log_message("Error: puerto serie no disponible", is_received=False)
        return redirect(url_for("index"))
    else:
        # Últimos mensajes para la plantilla Jinja
        return render_template("index.html", messages=list(reversed(received_messages_log[-MAX_LOG_MESSAGES_IN_MEMORY:])))


# ──────────────────────────── ARRANQUE ────────────────────────────

if __name__ == "__main__":
    print("Iniciando aplicación LoRa‑Web…")
    ensure_log_directory()

    if initialize_serial():
        threading.Thread(target=read_from_uart_thread, daemon=True).start()
    else:
        print("ADVERTENCIA: sin puerto serie disponible al inicio. Se volverá a intentar automáticamente.")

    print("Servidor Flask listo en 0.0.0.0:5000 (Gunicorn maneja esto en Docker).")
