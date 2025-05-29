"""
LoRaIM Bridge – Heltec V3 (ESP32-S3 + SX1262 + OLED)
====================================================

Este firmware convierte una placa Heltec WiFi LoRa V3 en un puente bidireccional LoRa ↔ MQTT, facilitando la comunicación
transparente entre nodos LoRa y una infraestructura MQTT.

Versión optimizada con protector de pantalla OLED y activación por botón.
"""
# ───────── Imports ─────────────────────────────────────────────────────────
import time, gc, ubinascii, ujson
from machine import Pin, I2C, WDT
import network
from umqtt.robust import MQTTClient
from sx1262 import SX1262
import ssd1306
import micropython
import machine

# Reservamos buffer para excepciones
micropython.alloc_emergency_exception_buf(100)

# ───────── 1. Leer .env ───────────────────────────────────────────────────
def load_env(path="/.env"):
  """
  Carga las variables de entorno desde un archivo `.env` y devuelve un diccionario con los valores.
  :param path:
  :return:
  """
  env = {}
  try:
      with open(path) as f:
          for raw in f:
              raw = raw.strip()
              if raw and not raw.startswith("#"):
                  k, v = raw.split("=", 1)
                  env[k.strip()] = v.strip()
  except OSError:
      pass
  return env

def getenv(env, key, cast=str, default=None):
  """
  Obtiene el valor de una variable de entorno, aplicando un tipo de conversión y un valor por defecto si no existe.
  :param env:
  :param key:
  :param cast:
  :param default:
  :return:
  """
  try:    return cast(env[key])
  except (KeyError, ValueError): return default

ENV = load_env()

# ───────── 2. Pines Heltec V3 ─────────────────────────────────────────────
LORA_CS, LORA_SCK, LORA_MOSI, LORA_MISO = 8, 9, 10, 11
LORA_RESET, LORA_BUSY, LORA_DIO1        = 12, 13, 14
VEXT, OLED_SCL, OLED_SDA, OLED_RST      = 36, 18, 17, 21
BUTTON_PIN                              = 0   # Pin del botón integrado

# ───────── 3. Parámetros de configuración ────────────────────────────────
WIFI_SSID     = getenv(ENV, "WIFI_SSID", str, "MySSID")
WIFI_PASS     = getenv(ENV, "WIFI_PASSWORD", str, "password")

MQTT_HOST     = getenv(ENV, "MQTT_HOST", str, "192.168.1.40")
MQTT_PORT     = getenv(ENV, "MQTT_PORT", int, 1883)
MQTT_USER     = getenv(ENV, "MQTT_USER", str, None)
MQTT_PASS     = getenv(ENV, "MQTT_PASSWORD", str, None)
MQTT_TOPIC_UP   = getenv(ENV, "MQTT_TOPIC_UP",   str, "lorachat/up").encode()
MQTT_TOPIC_DOWN = getenv(ENV, "MQTT_TOPIC_DOWN", str, "lorachat/down").encode()
MQTT_TOPIC_NODES = getenv(ENV, "MQTT_TOPIC_NODES", str, "lorachat/nodes").encode()
MQTT_QOS      = getenv(ENV, "MQTT_QOS", int, 1)
MQTT_RETAIN_UP= bool(getenv(ENV, "MQTT_RETAIN_UP", int, 0))
MQTT_RECON_MAX= getenv(ENV, "MQTT_RECONNECT_MAX", int, 30000)  # ms

FREQ       = getenv(ENV, "FREQUENCY", float, 866.3)
BW         = getenv(ENV, "BANDWIDTH", float, 250.0)
SF         = getenv(ENV, "SPREADING_FACTOR", int, 9)
CR         = getenv(ENV, "CODING_RATE", int, 5)
SYNC_WORD  = getenv(ENV, "SYNC_WORD", lambda x:int(x,0), 0x12)
TX_POWER   = getenv(ENV, "TRANSMIT_POWER", int, 14)

BRIGHTNESS = getenv(ENV, "BRIGHTNESS", int, 200)

# Tiempo de inactividad antes de apagar la pantalla (5 minutos en ms)
SCREEN_TIMEOUT = 5 * 60 * 1000

# Intervalo para publicar estado de nodos (30 segundos)
NODES_STATUS_INTERVAL = 30 * 1000

# ───────── 4. Variables globales ───────────────────────────────────────────
LINE_H, MAX_LINES = 12, 5
_lines = [""] * MAX_LINES
last_activity_time = time.ticks_ms()
last_nodes_publish = time.ticks_ms()
screen_active = True
button = None
oled = None
mqttc = None
lora = None

# Registro de nodos activos
nodes = {}
NODE_TIMEOUT = 60 * 1000  # 60 segundos para considerar un nodo offline

# Buffer para fragmentos pendientes
pending_chunks = {}
PENDING_CHUNKS_MAX_AGE = 60 * 1000 # Eliminar fragmentos incompletos después de 60 segundos

# Podrías necesitar una librería ADPCM simple o implementarla.
# Placeholder para la función de compresión ADPCM:
def compress_to_adpcm(pcm_data):
  # Esta es una función placeholder.
  # La compresión ADPCM real es más compleja.
  # Deberías implementar o portar un codec ADPCM (ej. IMA ADPCM).
  # Por ahora, simplemente trunca o devuelve como está para probar el flujo.
  oled_log("ADPCM Comp: TODO")
  # Ejemplo: si pcm_data es WAV, extraer los datos PCM y comprimir.
  # Por simplicidad, si no hay compresión, se enviarán más datos.
  return pcm_data # Placeholder

# ───────── 5. OLED helpers ───────────────────────────────────────────────
def activate_screen():
  """
  Activa la pantalla OLED si estaba apagada.
  """
  global last_activity_time, screen_active

  # Actualizar tiempo de última actividad
  last_activity_time = time.ticks_ms()

  # Reactivar pantalla si estaba apagada
  if not screen_active:
      oled.poweron()
      screen_active = True
      oled.fill(0)
      for i,l in enumerate(_lines):
          oled.text(l, 0, i*LINE_H, 1)
      oled.show()

def oled_log(txt):
  """
  Muestra un mensaje en la pantalla OLED y lo imprime en la consola.
  También reactiva la pantalla si estaba apagada.
  :param txt:
  :return:
  """
  global _lines

  # Activar pantalla
  activate_screen()

  _lines.pop(0); _lines.append(txt)
  oled.fill(0)
  for i,l in enumerate(_lines):
      oled.text(l, 0, i*LINE_H, 1)
  oled.show()
  print(txt)

def check_screen_timeout(current_time):
  """
  Verifica si ha pasado el tiempo de inactividad y apaga la pantalla si es necesario.
  :param current_time: Tiempo actual en ms
  :return:
  """
  global screen_active
  if screen_active and time.ticks_diff(current_time, last_activity_time) > SCREEN_TIMEOUT:
      oled.poweroff()
      screen_active = False

def button_callback(pin):
  """
  Callback para el botón. Activa la pantalla cuando se pulsa el botón.
  :param pin: Pin que generó la interrupción
  :return:
  """
  # Debounce simple
  time.sleep_ms(50)
  if pin.value() == 0:  # Botón presionado (lógica negativa)
      activate_screen()
      # No mostramos ningún mensaje al pulsar el botón

# ───────── 6. Init hardware ──────────────────────────────────────────────
def init_oled():
  """
  Inicializa la pantalla OLED y la configura.
  :return:
  """
  Pin(VEXT, Pin.OUT, value=0)
  rst = Pin(OLED_RST, Pin.OUT, value=0)
  time.sleep_ms(20); rst.value(1)
  i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400_000)
  global oled
  oled = ssd1306.SSD1306_I2C(128, 64, i2c)
  oled.contrast(BRIGHTNESS)

def init_button():
  """
  Inicializa el botón y configura la interrupción.
  :return:
  """
  global button
  button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
  button.irq(trigger=Pin.IRQ_FALLING, handler=button_callback)

def wifi_connect():
  """
  Conecta a la red Wi-Fi y devuelve la dirección IP asignada.
  :return:
  """
  wlan = network.WLAN(network.STA_IF)
  wlan.active(True)

  # Configurar WiFi para mayor estabilidad
  wlan.config(reconnects=5)  # Intentar reconectar automáticamente

  if not wlan.isconnected():
      try:
          oled_log("Conectando WiFi")
          wlan.connect(WIFI_SSID, WIFI_PASS)

          # Esperar hasta 30 segundos para la conexión
          max_wait = 30
          while max_wait > 0:
              if wlan.isconnected():
                  break
              max_wait -= 1
              oled_log(f"WiFi... {max_wait}")
              time.sleep(1)

          # Si no se conectó, reiniciar el adaptador WiFi
          if not wlan.isconnected():
              oled_log("Reintentando WiFi")
              wlan.active(False)
              time.sleep(1)
              wlan.active(True)
              time.sleep(1)
              wlan.connect(WIFI_SSID, WIFI_PASS)

              # Esperar otros 30 segundos
              max_wait = 30
              while max_wait > 0:
                  if wlan.isconnected():
                      break
                  max_wait -= 1
                  oled_log(f"WiFi... {max_wait}")
                  time.sleep(1)
      except Exception as e:
          oled_log(f"WiFi err: {str(e)[:10]}")

  return wlan.ifconfig()[0] if wlan.isconnected else "NO-WIFI"

def init_lora():
  """
  Inicializa el módulo LoRa SX1262 y lo configura con los parámetros especificados.
  :return:
  """
  global lora
  lora = SX1262(1, LORA_SCK, LORA_MOSI, LORA_MISO,
             LORA_CS, LORA_DIO1, LORA_RESET, LORA_BUSY)
  err = lora.begin(freq=FREQ, bw=BW, sf=SF, cr=CR, power=TX_POWER, syncWord=SYNC_WORD, blocking=False)
  if err: raise RuntimeError("LoRa init err %d" % err)
  lora.setBlockingCallback(False, on_receive)
  return lora

# ───────── 7. Node name ─────────────────────────────────────────────────
mac = network.WLAN(network.STA_IF).config('mac')
NODE_NAME = "Node-" + ubinascii.hexlify(mac).decode()[-6:].upper()
BRIDGE_ID = NODE_NAME # Usar el NODE_NAME como ID único del puente
MQTT_TOPIC_BRIDGE_COMMAND = f"lora_bridge/{BRIDGE_ID}/command".encode()

# ───────── 8. MQTT → LoRa callback ──────────────────────────────────────
def make_downlink_cb(lora):
  """
  Crea un callback para recibir mensajes MQTT y enviarlos por LoRa.
  :param lora:
  :return:
  """
  def _cb(topic, msg):
      """
      Callback para recibir mensajes MQTT y enviarlos por LoRa.
      :param topic:
      :param msg:
      :return:
      """
      try:
          js = ujson.loads(msg)
          txt = js.get("message", "")
      except:
          txt = msg.decode()

      if not txt:
          return

      try:
          pkt = ujson.dumps({"from": NODE_NAME, "message": txt})
          lora.send(pkt.encode()+b"\n")
          oled_log("TX LoRa: "+txt[:10])
      except Exception as e:
          oled_log(f"TX err: {str(e)[:10]}")

  return _cb

# MQTT -> LoRa callback (modificado para ser el callback de comandos al puente)
def on_bridge_command(topic, msg_bytes):
  """
  Callback para recibir comandos dirigidos a este puente.
  Principalmente para transmitir datos LoRa originados desde la web.
  """
  global lora
  try:
      msg_str = msg_bytes.decode()
      data = ujson.loads(msg_str)
      oled_log(f"Cmd RX: {data.get('command','?')}")

      command = data.get("command")
      if command == "transmit_lora_data":
          content_type = data.get("original_content_type") # ej. "audio/webm"
          filename = data.get("filename", "audio.dat")
          b64_data = data.get("data_b64")
          from_user = data.get("from_user", "web") # Quién lo originó en la web

          if not b64_data:
              oled_log("No data in cmd")
              return

          binary_data = ubinascii.a2b_base64(b64_data)

          # Compresión si es necesario (ej. si es audio WAV/Opus y queremos ADPCM para LoRa)
          # Aquí es donde el puente haría la compresión agresiva.
          # El content_type final para LoRa sería "audio/adpcm".
          final_lora_content_type = "audio/adpcm" # Asumimos que siempre comprimimos a esto para LoRa

          # Placeholder: si es webm/opus, necesitarías un decodificador a PCM y luego ADPCM.
          # Esto es muy complejo para un ESP32 sin librerías C.
          # Simplificación: Asumimos que el backend ya envió algo "casi" listo o el puente
          # solo puede manejar formatos muy simples o ya pre-comprimidos.
          # Para este ejemplo, si es audio, intentaremos "comprimir" (placeholder).
          if content_type and content_type.startswith("audio/"):
              # Aquí deberías decodificar Opus/WebM a PCM si es necesario, luego comprimir a ADPCM.
              # Esto es un gran desafío en MicroPython.
              # Una solución más simple sería que el frontend envíe WAV, y el puente convierta WAV a ADPCM.
              # O que el backend convierta a WAV y el puente a ADPCM.
              # Por ahora, usamos el placeholder compress_to_adpcm.
              compressed_data = compress_to_adpcm(binary_data)
              oled_log(f"Audio comp. {len(binary_data)}->{len(compressed_data)}B")
          else: # Para otros tipos de archivo, o si ya está comprimido
              compressed_data = binary_data
              final_lora_content_type = content_type # Usar el tipo original si no es audio a comprimir

          # Segmentación
          chunk_size = 180 # Ajustar según payload LoRa y overhead JSON
          msg_id = ubinascii.hexlify(machine.unique_id()[:4] + str(time.ticks_us()).encode()).decode()[-12:]
          num_chunks = (len(compressed_data) + chunk_size - 1) // chunk_size

          oled_log(f"TX LoRa {filename[:6]}:{num_chunks}cks")

          for i in range(num_chunks):
              chunk_payload_data = compressed_data[i*chunk_size : (i+1)*chunk_size]
              chunk_pkt_dict = {
                  "from": from_user, # El originador web, no el ID del puente
                  "type": "data_chunk",
                  "content_type": final_lora_content_type,
                  "filename": filename,
                  "msg_id": msg_id,
                  "chunk_idx": i + 1,
                  "total_chunks": num_chunks,
                  # Enviar el fragmento binario como base64 para que sea JSON válido
                  "payload_b64": ubinascii.b2a_base64(chunk_payload_data).decode().strip()
              }

              lora_pkt_bytes = ujson.dumps(chunk_pkt_dict).encode() + b"\n"
              # Antes de enviar, asegurar que LoRa no esté ocupado (si es half-duplex)
              # lora.standby() o similar si es necesario
              err = lora.send(lora_pkt_bytes)
              if err:
                  oled_log(f"LoRa TX Err {err}")
                  break # Salir si hay error de transmisión
              else:
                  oled_log(f"Sent Ck {i+1}/{num_chunks}")

              # Pequeña pausa para permitir que otros nodos transmitan y para el ciclo de trabajo.
              # Esto debe calcularse según el tiempo en el aire.
              time.sleep_ms(500) # Ajustar esto cuidadosamente!
          oled_log(f"TX {filename[:6]} done")
      elif command == "send_text_message":
          text_message = data.get("text_message", "")
          from_user = data.get("from_user", "web")

          if not text_message:
              oled_log("No text in cmd")
              return

          lora_pkt = ujson.dumps({"from": from_user, "message": text_message}).encode() + b"\n"
          lora.send(lora_pkt)
          oled_log(f"TX LoRa txt: {text_message[:10]}")
      else:
          oled_log(f"Cmd desc: {command}")

  except Exception as e:
      oled_log(f"Cmd Proc Err: {str(e)[:15]}")
      print(f"Error processing bridge command: {e}, msg: {msg_bytes}")

# ───────── 9. Buffer de pendientes (lista circular) ─────────────────────
PENDING_MAX = 200
pending = []
def pend_append(pkt):
  """
  Añade un paquete al buffer de pendientes y elimina el más antiguo si se supera el límite.
  :param pkt:
  :return:
  """
  pending.append(pkt)
  if len(pending) > PENDING_MAX:
      pending.pop(0)
def pend_popleft():
  """
  Elimina y devuelve el primer paquete del buffer de pendientes.
  :return:
  """
  return pending.pop(0)

# ───────── 10. Funciones de gestión de nodos ─────────────────────────────
def update_node_status(node_id, rssi=None, snr=None, is_bridge_node=False):
  """
  Actualiza el estado de un nodo en el registro.
  :param node_id: Identificador del nodo
  :param rssi: Valor RSSI (opcional)
  :param snr: Valor SNR (opcional)
  :return: None
  """
  current_time = time.ticks_ms()
  if node_id in nodes:
      nodes[node_id]["last_seen"] = current_time
      if rssi is not None: nodes[node_id]["rssi"] = rssi
      if snr is not None: nodes[node_id]["snr"] = snr
      nodes[node_id]["status"] = "online"
      if is_bridge_node: nodes[node_id]["is_bridge"] = True
  else:
      nodes[node_id] = {
          "id": node_id, "last_seen": current_time,
          "rssi": rssi, "snr": snr, "status": "online",
          "is_bridge": is_bridge_node
      }
  # oled_log(f"Node {node_id} upd") # Puede ser muy verboso

def check_nodes_status():
  """
  Verifica el estado de todos los nodos y actualiza su estado.
  :return: None
  """
  current_time = time.ticks_ms()

  # Verificar cada nodo
  for node_id, info in nodes.items():
      # Si el nodo no se ha visto en NODE_TIMEOUT, marcarlo como offline
      if time.ticks_diff(current_time, info["last_seen"]) > NODE_TIMEOUT:
          info["status"] = "offline"
      else:
          info["status"] = "online"

  # Publicar estado de nodos si es necesario
  publish_nodes_status()

def publish_nodes_status():
  """
  Publica el estado de todos los nodos a través de MQTT.
  :return: None
  """
  global last_nodes_publish, mqttc
  current_time = time.ticks_ms()
  if time.ticks_diff(current_time, last_nodes_publish) < NODES_STATUS_INTERVAL:
      return
  last_nodes_publish = current_time
  nodes_list = []
  for node_id, info in nodes.items():
      last_seen_sec = time.time() - (time.ticks_diff(current_time, info["last_seen"]) / 1000)
      nodes_list.append({
          "id": node_id, "last_seen": last_seen_sec,
          "rssi": info.get("rssi"), "snr": info.get("snr"),
          "status": info.get("status", "unknown"),
          "is_bridge": info.get("is_bridge", False) # Asegurar que se envíe
      })

  # No es necesario añadir el nodo puente aquí si ya está en `nodes` por update_node_status
  # Pero si no, añadirlo explícitamente:
  # if BRIDGE_ID not in nodes:
  #    nodes_list.append({ "id": BRIDGE_ID, "last_seen": time.time(), "status": "online", "is_bridge": True })

  try:
      payload = ujson.dumps({"nodes": nodes_list, "timestamp": time.time()})
      mqttc.publish(MQTT_TOPIC_NODES, payload, False, MQTT_QOS)
      # oled_log(f"Nodes sent ({len(nodes_list)})")
  except Exception as e:
      oled_log(f"Nodes Pub Err: {str(e)[:10]}")

# ───────── 11. LoRa callback ─────────────────────────────────────────────
def on_receive(events):
  """
  Callback para recibir mensajes LoRa.
  :param events: Eventos LoRa
  :return:
  """
  global mqttc, lora
  if events & SX1262.RX_DONE:
      try:
          pkt_bytes, stat = lora.recv()
          # El ID del nodo LoRa que envió este paquete físico
          lora_sender_node_id = NODE_NAME # Placeholder, en un escenario real, esto vendría de la capa LoRa si es un ACK o similar
                                        # o si los nodos se identifican en cada paquete.
                                        # Para mensajes de otros nodos, el 'from' dentro del JSON es el importante.

          if stat == 0 and pkt_bytes:
              rssi = lora.getRSSI()
              snr = lora.getSNR()

              try:
                  pkt_str = pkt_bytes.decode().strip()
                  data = ujson.loads(pkt_str)

                  # El 'from' aquí es el ID del nodo LoRa que originó el mensaje (puede ser otro nodo, no el puente)
                  # o el 'from_user' si es un chunk originado desde la web.
                  actual_sender_id = data.get("from", "?")
                  msg_type = data.get("type", "text")

                  # Actualizar estado del nodo LoRa que transmitió este paquete
                  # Esto es un poco confuso: si el paquete es de otro nodo LoRa, 'actual_sender_id' es ese nodo.
                  # Si es un paquete que el *propio puente* envió (ej. un ACK o un mensaje originado por el puente),
                  # entonces no deberíamos actualizar el estado del puente basado en sus propias transmisiones.
                  # Asumimos que los mensajes RX son de *otros* nodos LoRa.
                  if actual_sender_id != BRIDGE_ID and actual_sender_id != "?":
                    update_node_status(actual_sender_id, rssi, snr)


                  if msg_type == "data_chunk":
                      msg_id = data.get("msg_id")
                      chunk_idx = data.get("chunk_idx")
                      total_chunks = data.get("total_chunks")
                      chunk_payload_b64 = data.get("payload_b64")
                      content_type = data.get("content_type")
                      filename = data.get("filename")
                      # El 'from' en data es el originador (ej. web_user), no necesariamente el nodo LoRa que lo retransmitió.
                      original_source = data.get("from", "unknown_lora_node")


                      if not all([msg_id, chunk_idx, total_chunks, chunk_payload_b64, content_type]):
                          oled_log("Chunk RX Incomp.")
                          return

                      if msg_id not in pending_chunks:
                          pending_chunks[msg_id] = {
                              "total": total_chunks,
                              "received_mask": [False] * total_chunks,
                              "chunks": [None] * total_chunks,
                              "meta": {"content_type": content_type, "filename": filename,
                                       "from_lora_node": actual_sender_id, # Nodo LoRa que envió este chunk
                                       "original_source": original_source, # Quién lo originó (ej. web_user)
                                       "rssi": rssi, "snr": snr},
                              "timestamp": time.ticks_ms()
                          }

                      if 1 <= chunk_idx <= total_chunks:
                          if not pending_chunks[msg_id]["received_mask"][chunk_idx - 1]:
                              pending_chunks[msg_id]["chunks"][chunk_idx - 1] = ubinascii.a2b_base64(chunk_payload_b64)
                              pending_chunks[msg_id]["received_mask"][chunk_idx - 1] = True
                              pending_chunks[msg_id]["timestamp"] = time.ticks_ms()
                              oled_log(f"RX Ck {chunk_idx}/{total_chunks} fr {actual_sender_id[-4:]}")
                      else:
                          oled_log(f"Chunk idx err {chunk_idx}")
                          if msg_id in pending_chunks: del pending_chunks[msg_id]
                          return

                      if all(pending_chunks[msg_id]["received_mask"]):
                          full_binary_data = b"".join(pending_chunks[msg_id]["chunks"])
                          meta = pending_chunks[msg_id]["meta"]

                          mqtt_payload = {
                              "from": meta["original_source"], # El originador web o de otro nodo
                              "node_id_lora": meta["from_lora_node"], # El nodo LoRa que lo envió al puente
                              "content_type": meta["content_type"],
                              "filename": meta.get("filename", "file"),
                              "data_b64": ubinascii.b2a_base64(full_binary_data).decode().strip(),
                              "rssi": meta["rssi"], "snr": meta["snr"],
                              "timestamp": time.time()
                          }

                          topic_suffix = "unknown_media"
                          if "audio" in meta["content_type"]: topic_suffix = "audio"
                          elif "image" in meta["content_type"]: topic_suffix = "image"

                          mqttc.publish(f"{MQTT_TOPIC_UP}/{topic_suffix}", ujson.dumps(mqtt_payload), MQTT_RETAIN_UP, MQTT_QOS)
                          oled_log(f"Pub MQTT: {meta['filename'][:8]} ({len(full_binary_data)}B)")
                          del pending_chunks[msg_id]

                  elif msg_type == "text":
                      message = data.get("message", "")
                      mqtt_payload = {
                          "from": actual_sender_id, # El nodo LoRa que envió el texto
                          "node_id_lora": actual_sender_id,
                          "message": message,
                          "content_type": "text/plain",
                          "rssi": rssi, "snr": snr, "timestamp": time.time()
                      }
                      mqttc.publish(MQTT_TOPIC_UP, ujson.dumps(mqtt_payload), MQTT_RETAIN_UP, MQTT_QOS)
                      oled_log(f"RX Txt fr {actual_sender_id[-6:]}:{message[:8]}")
                  else:
                      oled_log(f"RX tipo desc: {msg_type}")
              # ... (resto del manejo de errores y no JSON)
              except ValueError as e:
                  oled_log(f"RX no JSON: {str(e)[:10]}")
                  # Podrías intentar procesar como texto plano si es relevante
              except Exception as e:
                  oled_log(f"RX Proc err: {str(e)[:10]}")
                  print(f"Error processing LoRa RX: {e}, pkt: {pkt_bytes}")
      except Exception as e:
          oled_log(f"LoRa RX err: {str(e)[:10]}")
          print(f"Outer LoRa RX error: {e}")

# ───────── 12. Main loop ─────────────────────────────────────────────────
def main():
  """
  Función principal que inicializa el sistema y gestiona la comunicación entre LoRa y MQTT.
  :return:
  """
  # Inicializar watchdog
  try:
      wdt = WDT(timeout=30000)  # 30 segundos
      has_watchdog = True
  except:
      has_watchdog = False
      print("No WDT support")

  # Inicializar hardware
  init_oled()
  init_button()  # Inicializar el botón
  oled_log("Booting")

  ip = wifi_connect()
  oled_log(ip)

  # Si no hay conexión WiFi, reintentar o reiniciar
  if ip == "NO-WIFI":
      oled_log("WiFi fallido")
      time.sleep(5)
      import machine
      machine.reset()

  global lora
  lora = init_lora()
  oled_log("LoRa OK")

  oled_log(NODE_NAME)

  # Variables para control de tiempo
  last_ping_time = time.ticks_ms()
  start_time = time.time()
  ping_interval = 15000  # 15 segundos
  reset_interval = 86400  # 24 horas en segundos

  # Inicializar MQTT con la biblioteca robusta - PARÁMETROS SIMPLIFICADOS
  cid = ubinascii.hexlify(mac).decode()

  # Crear cliente MQTT robusto con parámetros mínimos
  global mqttc
  mqttc = MQTTClient(cid, MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASS, keepalive=60)
  mqttc.DEBUG = True  # Habilitar depuración
  # mqttc.set_callback(make_downlink_cb(lora))

  # Intentar conectar MQTT
  try:
      mqttc.connect()
      # mqttc.subscribe(MQTT_TOPIC_DOWN, MQTT_QOS)
      oled_log("MQTT OK")

      # Suscribirse al topic de comandos específico del puente
      mqttc.set_callback(on_bridge_command) # Establecer el nuevo callback para comandos
      mqttc.subscribe(MQTT_TOPIC_BRIDGE_COMMAND, MQTT_QOS)
      oled_log(f"Sub BridgeCmd OK")

      # También suscribirse al topic general de downlink si el puente aún debe reenviar mensajes generales
      # Esto requeriría un dispatcher en el callback o múltiples callbacks si la librería lo permite.
      # Por simplicidad, el callback ahora solo maneja comandos al puente.
      # Si necesitas que el puente también reciba mensajes de MQTT_TOPIC_DOWN para reenviar,
      # necesitarás una lógica de dispatch en on_bridge_command basada en el topic,
      # o una forma más avanzada de manejar callbacks por topic.
      # Ejemplo de dispatch (conceptual):
      # def universal_mqtt_callback(topic, msg):
      #   if topic == MQTT_TOPIC_BRIDGE_COMMAND:
      #     on_bridge_command(topic, msg)
      #   elif topic == MQTT_TOPIC_DOWN:
      #     on_general_downlink(topic, msg) # on_general_downlink sería tu make_downlink_cb original
      #   else:
      #     oled_log(f"Msg en topic desc: {topic}")
      # mqttc.set_callback(universal_mqtt_callback)
      # mqttc.subscribe(MQTT_TOPIC_DOWN, MQTT_QOS)


      # Publicar estado online del puente, indicando que es un puente
      bridge_status_payload = {
          "from": BRIDGE_ID, # Usar el ID del puente
          "node_id_lora": BRIDGE_ID, # Para consistencia con otros mensajes
          "message": "online",
          "type": "bridge_status", # Un tipo específico para el estado del puente
          "is_bridge": True,
          "timestamp": time.time()
      }
      mqttc.publish(MQTT_TOPIC_UP, ujson.dumps(bridge_status_payload), False, MQTT_QOS)
      oled_log("Bridge Status Sent")

      # Registrar el propio nodo puente en el registro de nodos local
      update_node_status(BRIDGE_ID, is_bridge_node=True) # Nueva función o parámetro
      publish_nodes_status() # Publicar estado de nodos (incluyendo el puente)

  except Exception as e:
      oled_log(f"MQTT Sub/Pub Err: {str(e)[:10]}")

  # Configurar callback para LoRa
  lora.setBlockingCallback(False, on_receive)

  # Bucle principal
  while True:
      current_time = time.ticks_ms()

      # Alimentar watchdog
      if has_watchdog:
          wdt.feed()

      # Verificar si hay que apagar la pantalla
      check_screen_timeout(current_time)

      # Verificar estado de nodos
      check_nodes_status()

      # Reinicio programado cada 24 horas
      if time.time() - start_time > reset_interval:
          oled_log("Reinicio programado")
          time.sleep_ms(1000)
          import machine
          machine.reset()

      # Comprobar conexión MQTT y reconectar si es necesario
      try:
          # Comprobar mensajes MQTT (downlink)
          mqttc.check_msg()

          # Ping periódico para mantener la conexión
          if time.ticks_diff(current_time, last_ping_time) > ping_interval:
              mqttc.ping()
              last_ping_time = current_time

          # Procesar mensajes pendientes
          if pending:
              pkt = pend_popleft()
              try:
                  mqttc.publish(MQTT_TOPIC_UP, pkt, MQTT_RETAIN_UP, MQTT_QOS)
                  oled_log(f"Sent pending ({len(pending)})")
              except Exception as e:
                  pend_append(pkt)
                  oled_log(f"Pend err: {str(e)[:10]}")
                  # La biblioteca robusta manejará la reconexión
      except Exception as e:
          oled_log(f"MQTT err: {str(e)[:10]}")
          # La biblioteca robusta manejará la reconexión

      # Limpiar fragmentos pendientes antiguos
      cleanup_pending_chunks()

      # Pequeña pausa para evitar saturar la CPU
      time.sleep_ms(10)

def cleanup_pending_chunks():
  """
  Elimina los fragmentos pendientes que no se han completado en un tiempo razonable.
  """
  current_time = time.ticks_ms()
  chunks_to_delete = []
  for msg_id, chunk_data in pending_chunks.items():
      if time.ticks_diff(current_time, chunk_data["timestamp"]) > PENDING_CHUNKS_MAX_AGE:
          chunks_to_delete.append(msg_id)

  for msg_id in chunks_to_delete:
      oled_log(f"Del Incomp Ck {msg_id[:8]}")
      del pending_chunks[msg_id]

# ───────── 13. Manejo de errores y punto de entrada ─────────────────────
if __name__ == "__main__":
  try:
      main()
  except Exception as e:
      # En caso de error fatal, registrar y reiniciar
      error_msg = f"ERROR FATAL: {str(e)}"
      print(error_msg)
      time.sleep(5)
      import machine
      machine.reset()
