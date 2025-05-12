# app.py
# ... (importaciones) ...
app = Flask(__name__)

# 1. Inicializar la conexión serial (UART) con el Heltec
# Asegúrate que el dispositivo serial /dev/serial0 sea accesible DESDE DENTRO DEL CONTENEDOR
# Esto requerirá mapear el dispositivo al contenedor en docker-compose.yml
try:
    ser = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1) # '/dev/ttyAMA0' es común para UART de pines GPIO en RPi.
                                                                # Si usas USB-Serial al ESP32, podría ser '/dev/ttyUSB0' o '/dev/ttyACM0'
                                                                # Ajusta según tu conexión física y cómo se mapea al contenedor.
    print("Puerto serial /dev/ttyAMA0 abierto exitosamente.")
except serial.SerialException as e:
    print(f"Error al abrir el puerto serial: {e}. La aplicación podría no funcionar correctamente con LoRa.")
    ser = None # Para que la app no crashee si el serial no está disponible

# Path para el archivo de log DENTRO del contenedor.
# Mapearemos este path a un directorio en el host usando docker-compose.yml
log_file_container_path = "/app/logs/lora_messages.log"
# Asegurarse de que el directorio de logs exista
import os
os.makedirs(os.path.dirname(log_file_container_path), exist_ok=True)


# ... (resto del código de app.py, usando log_file_container_path en lugar de log_file) ...
# Ejemplo de cambio en la función read_from_uart:
# with open(log_file_container_path, "a") as f:
#     f.write(msg + "\n")
# Y en la ruta index para POST:
# with open(log_file_container_path, "a") as f:
#     f.write(sent_msg + "\n")

# Hilo de lectura continua desde UART
received_messages = []
def read_from_uart():
    """Lee continuamente desde la UART y guarda los datos recibidos."""
    global ser # Necesario para acceder a la variable global
    if not ser:
        print("Hilo UART: Puerto serial no inicializado. El hilo no leerá.")
        return # Salir del hilo si el serial no está disponible

    while True:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"Recibido [{timestamp}]: {line}"
                received_messages.append(msg)
                with open(log_file_container_path, "a") as f: # Usar la nueva variable
                    f.write(msg + "\n")
        except serial.SerialException as e: # Manejar errores específicos del serial
            print(f"UART read error (SerialException): {e}. Intentando reabrir puerto...")
            if ser: ser.close()
            time.sleep(5) # Esperar antes de reintentar
            try:
                ser = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1) # Reintentar abrir
                print("Puerto serial reabierto exitosamente.")
            except serial.SerialException as e_reopen:
                print(f"Fallo al reabrir puerto serial: {e_reopen}. El hilo de lectura se detendrá.")
                ser = None # Marcar como no disponible
                break # Salir del bucle while
        except Exception as e:
            print(f"UART read error (General Exception): {e}")
            # No romper el bucle por errores genéricos, solo por SerialException si no se puede reabrir
            time.sleep(1) # Pequeña pausa

if ser: # Solo iniciar el hilo si el puerto serial se abrió correctamente
    thread = threading.Thread(target=read_from_uart, daemon=True)
    thread.start()
else:
    print("ADVERTENCIA: El puerto serial no pudo ser abierto. El hilo de lectura UART no se iniciará.")


@app.route('/', methods=['GET', 'POST'])
def index():
    global ser # Necesario para acceder a la variable global
    if request.method == 'POST':
        text = request.form.get('mensaje', '')
        if text:
            if ser and ser.is_open: # Verificar que el puerto esté abierto antes de escribir
                try:
                    ser.write((text + "\n").encode('utf-8'))
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sent_msg = f"Enviado [{timestamp}]: {text}"
                    with open(log_file_container_path, "a") as f: # Usar la nueva variable
                        f.write(sent_msg + "\n")
                    received_messages.append(sent_msg)
                except serial.SerialException as e:
                    print(f"Error al escribir en UART: {e}")
                    # Podrías añadir un mensaje de error para el usuario aquí
                    received_messages.append(f"Error TX UART: {e}")
                except Exception as e_write:
                    print(f"Error inesperado al escribir en UART: {e_write}")
                    received_messages.append(f"Error TX UART Inesperado: {e_write}")

            else:
                print("Error: Intento de enviar mensaje pero el puerto serial no está disponible.")
                received_messages.append("Error: Puerto serial no disponible para enviar.")
        return redirect(url_for('index'))
    else:
        # Cargar mensajes del log al inicio si la lista en memoria está vacía (opcional)
        # if not received_messages and os.path.exists(log_file_container_path):
        #     try:
        #         with open(log_file_container_path, "r") as f:
        #             # Leer las últimas N líneas, por ejemplo
        #             # Esto es solo un ejemplo, podría ser más complejo
        #             tail_lines = f.readlines()[-50:] # Cargar las últimas 50 líneas
        #             for line_from_log in tail_lines:
        #                 received_messages.append(line_from_log.strip())
        #     except Exception as e_log_read:
        #         print(f"Error leyendo log al inicio: {e_log_read}")

        return render_template('index.html', messages=list(reversed(received_messages[-50:]))) # Mostrar los últimos 50

if __name__ == '__main__':
    # El host 0.0.0.0 es importante para que sea accesible desde fuera del contenedor
    app.run(host='0.0.0.0', port=5000)