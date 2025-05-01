import serial
import paho.mqtt.client as mqtt

# Configuraciones
SERIAL_PORT = "/dev/ttyS0"       # Puerto serial hacia el HAT LoRa
BAUD_RATE = 9600                # baudios de comunicación UART con el módulo LoRa
MQTT_BROKER = "localhost"       # Broker MQTT (la Pi misma)
TOPIC_UPLINK = "lora/uplink"    # Tópico para mensajes entrantes de LoRa
TOPIC_DOWNLINK = "lora/downlink"# Tópico para mensajes salientes hacia LoRa

# Inicializar puerto serie
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

# Callback cuando llega un mensaje MQTT en el tópico downlink
def on_mqtt_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        print(f"[MQTT] Mensaje recibido en {msg.topic}: {payload}")
        # Enviar este payload por LoRa (a través del serial)
        data = payload.encode('utf-8')
        ser.write(data + b'\n')  # enviamos con newline como terminador
        print("[LoRa] Enviado mensaje al ESP32 via LoRa.")
    except Exception as e:
        print("Error en on_mqtt_message:", e)

# Configurar cliente MQTT
client = mqtt.Client()
client.on_message = on_mqtt_message
client.connect(MQTT_BROKER, 1883)
client.subscribe(TOPIC_DOWNLINK)
client.loop_start()  # iniciar loop en segundo plano para manejar MQTT

print("Gateway LoRa<->MQTT iniciado. Esperando mensajes...")

try:
    # Bucle principal: leer del LoRa y publicar en MQTT
    while True:
        if ser.in_waiting:  # hay datos en el buffer serial
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"[LoRa] Recibido por LoRa: {line}")
                # Publicar en MQTT el mensaje recibido
                client.publish(TOPIC_UPLINK, line)
                print(f"[MQTT] Publicado en {TOPIC_UPLINK}: {line}")
except KeyboardInterrupt:
    print("Terminando gateway...")
finally:
    client.loop_stop()
    client.disconnect()
    ser.close()

