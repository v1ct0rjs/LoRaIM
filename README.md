# Proyecto: LoRaWAN

![Esquema](https://raw.githubusercontent.com/v1ct0rjs/lorawan_project/refs/heads/main/photo_2025-04-03_13-02-17.jpg)

*Figura: Arquitectura básica de un sistema LoRaWAN (nodos → gateway → servidor de red → servidor de aplicaciones).*

## Arquitectura general y flujo de datos

En esta arquitectura, una **Raspberry Pi** equipada con un **HAT LoRa** actúa como servidor central (gateway). La API **FastAPI** corre en la Raspberry Pi (dentro de un contenedor Docker) escuchando en el puerto 8000. Los **nodos ESP32** están distribuidos como nodos remotos: cada ESP32 funciona en modo *punto de acceso WiFi* (AP) para dar conectividad local a dispositivos de usuario (móviles, portátiles, etc.). Cuando un usuario realiza una solicitud a la API (por ejemplo, haciendo una petición HTTP a la IP del nodo ESP32), dicha petición es capturada por el ESP32 y **encapsulada en un mensaje LoRa**. El mensaje viaja inalámbricamente hasta la Raspberry Pi mediante el enlace LoRa de larga distancia.

En la Raspberry Pi, un proceso se encarga de recibir el mensaje LoRa. La infraestructura utiliza **MQTT** como protocolo de mensajería entre los ESP32 y el servidor: el nodo ESP32 convierte la petición en un mensaje que publica (vía LoRa) en un “tema” MQTT, y la Raspberry Pi actúa como *broker* o despachador de estos mensajes. Al recibir una petición, la Raspberry Pi la decodifica y la **reenvía internamente a la API FastAPI** (por ejemplo, llamando al endpoint correspondiente de FastAPI o invocando la lógica de negocio directamente). La respuesta de la API luego se envía de vuelta al nodo solicitante siguiendo el camino inverso: la Raspberry Pi publica un mensaje MQTT de respuesta que el nodo ESP32 destinatario recibe a través de LoRa, y el ESP32 entrega la respuesta al cliente original mediante HTTP sobre WiFi. Este flujo asegura una comunicación **bidireccional**: los nodos pueden tanto enviar solicitudes como recibir las respuestas de la API central, pese a no tener conectividad a Internet, gracias al enlace LoRa de largo alcance.

En resumen, el flujo de datos principal es:

1. **Dispositivo → ESP32 (WiFi):** Un cliente (ej. un teléfono conectado al AP WiFi del ESP32) realiza una solicitud HTTP a la dirección IP del nodo (p.ej. una consulta REST).
2. **ESP32 → Raspberry Pi (LoRa/MQTT):** El ESP32 toma esa solicitud y la publica como mensaje MQTT sobre la red LoRa hacia la Raspberry Pi (la cual hace de broker). En la práctica, esto implica serializar la petición (p. ej. en JSON ligero) y enviarla por LoRa.
3. **Procesamiento en Raspberry Pi:** El servidor central recibe el mensaje LoRa, lo pasa al broker MQTT local y éste entrega la solicitud a la instancia de FastAPI (por suscripción a un tema de “peticiones”). La API FastAPI procesa la solicitud (consulta bases de datos, lógica de negocio, etc.) y genera una respuesta.
4. **Raspberry Pi → ESP32 (LoRa/MQTT):** La respuesta se publica como mensaje MQTT en un tema al que estaba suscrito el nodo originador. El HAT LoRa transmite ese mensaje de vuelta vía radio LoRa.
5. **ESP32 → Dispositivo (WiFi):** El nodo ESP32 recibe el mensaje LoRa con la respuesta, lo decodifica y envía la respuesta al cliente a través de la conexión WiFi local (por ejemplo, formando una respuesta HTTP al socket del cliente). El dispositivo obtiene así la respuesta de la API central.

Esta arquitectura en estrella tiene a la Raspberry Pi como **nodo concentrador** y emplea LoRa para la **comunicación de largo alcance** con los nodos, superando las limitaciones de cobertura del WiFi. Cada nodo ESP32 sirve de *gateway* local para los usuarios cercanos (mediante WiFi), permitiendo consultas a la API sin requerir infraestructura de red celular ni internet en campo. El uso de **MQTT** proporciona un esquema flexible de publicación/suscripción para las comunicaciones entre nodos y servidor, facilitando la gestión de mensajes de forma desacoplada y la posibilidad de manejar múltiples nodos y temas.

## Componentes de hardware y software necesarios

A continuación se listan los componentes principales necesarios, tanto de hardware como de software, para implementar la solución:

### Hardware

| Componente                    | Descripción                                                  |
| ----------------------------- | ------------------------------------------------------------ |
| **Raspberry Pi 4** (o 3)      | Microcomputadora central que actuará como servidor. Debe contar con SPI habilitado para conectar el módulo LoRa. Se recomienda un modelo con buen rendimiento (Pi 3/4) para manejar Docker y la API. |
| **HAT LoRa Waveshare SX1262** | Módulo LoRa en forma de HAT para la Raspberry Pi. Usa el transceptor LoRa SX1262 conectado vía SPI, soporta comunicación bidireccional y múltiples frecuencias según modelo (868 MHz, 915 MHz, etc.). |
| **Módulos ESP32** (Nodos)     | Microcontroladores con WiFi integrados que actuarán como nodos remotos. Cada ESP32 se conecta a un módulo de radio LoRa (p.ej. un módulo con chip SX1276/SX1278) para comunicarse con la Pi. Alternativamente, se pueden usar placas ESP32 LoRa integradas (ej. Heltec WiFi LoRa 32, TTGO LoRa) que ya incorporan el radio LoRa. |
| **Módulos LoRa para ESP32**   | Si la placa ESP32 no lo trae integrado, se necesitan módulos LoRa externos (p. ej. RFM95/RFM98 o E32-433/868). Estos se conectan al ESP32 (vía SPI en caso de módulos SX127x, o vía UART en módulos LoRa seriales como E32). Se debe escoger la frecuencia adecuada (433 MHz, 868 MHz, 915 MHz) según la normativa regional. |
| **Antenas LoRa**              | Antenas sintonizadas a la frecuencia de operación de LoRa en cada nodo (tanto en la Pi como en los ESP32). Una buena antena es esencial para lograr el alcance máximo (varios km en condiciones ideales). |
| **Fuente de alimentación**    | Fuentes de alimentación estables para la Raspberry Pi y para cada ESP32. La Pi requiere una fuente de 5V 3A (usualmente USB-C). Los ESP32 pueden alimentarse con 5V (regulado a 3.3V a través del módulo o un regulador). Si los nodos estarán aislados, podría considerarse batería + panel solar. |

### Software

| Componente                                 | Descripción                                                  |
| ------------------------------------------ | ------------------------------------------------------------ |
| **Sistema Operativo (OS)** en Raspberry Pi | Una distro Linux ligera (Raspberry Pi OS o Ubuntu Server). Se debe habilitar SPI (por ejemplo, usando `raspi-config`) para la comunicación con el HAT LoRa. |
| **Docker** y **Docker Compose**            | Plataforma de contenedores para desplegar la aplicación FastAPI y otros servicios. Docker facilita la portabilidad y aislamiento de la API. (La Raspberry Pi soporta Docker; las imágenes deben ser arquitectura ARM). |
| **Aplicación FastAPI**                     | Implementación de la API (código Python) que se alojará en un contenedor Docker. Utiliza Uvicorn/Gunicorn como servidor ASGI. Escucha en el puerto 8000 dentro de la Pi. |
| **Broker MQTT (e.g. Mosquitto)**           | Servicio MQTT que puede correr en la Raspberry Pi (nativo o en contenedor). Maneja los mensajes entre Pi y nodos. Alternativamente, se puede usar la funcionalidad MQTT del servidor LoRaWAN (p. ej. ChirpStack) como broker de aplicación. |
| **Stack LoRaWAN**                          | Para un enfoque LoRaWAN estándar: un servidor de red LoRaWAN local como **ChirpStack** (open-source) desplegado en la Pi. Esto incluye componentes de gateway, network server, y aplicación (que suele integrar MQTT). *Nota:* Esto es opcional; los nodos también pueden comunicarse con un protocolo LoRa personalizado sin el overhead LoRaWAN. |
| **Firmware MicroPython** en ESP32          | El firmware MicroPython instalado en cada ESP32, que nos permite programarlos en Python. Se puede usar la última versión estable de MicroPython para ESP32. |
| **Librerías MicroPython**                  | - **network** (incluida) para configurar WiFi AP.  - **socket** (incluida) para implementar un servidor HTTP simple en el nodo.  - **Driver LoRa SX127x** (externa): se debe incluir un módulo Python para manejar el transceptor LoRa (por ejemplo, el driver `sx127x.py` de **uPyLoRa** |
| **Herramientas de desarrollo**             | IDE o entorno para cargar código en los ESP32 y desarrollar la API. Vscode, Pycharm o Neovim |

## Configuración de Docker en la Raspberry Pi (despliegue de FastAPI)

En la Raspberry Pi, instalamos Docker para contenerizar la aplicación FastAPI. Esto permite aislar la API y sus dependencias, y facilita la configuración del servicio en el puerto 8000. Dado que la Pi usa arquitectura ARM, debemos usar imágenes compatibles. Una buena práctica es construir la imagen de FastAPI basándose en la imagen oficial de Python (que es multi-arch) ([FastAPI in Containers - Docker - FastAPI](https://fastapi.tiangolo.com/deployment/docker/#:~:text=This is what you would,in most cases%2C for example)). Por ejemplo, se puede usar un `Dockerfile` como:

```Dockerfile
FROM python:3.13.3-bullseye
WORKDIR /app
COPY app/requirements.txt .
RUN pip install -r requirements.txt   
COPY app .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Este Dockerfile copia el código de la API (suponiendo que el módulo principal se llama `main.py` y crea un objeto `app`). La API se lanza con Uvicorn escuchando en todas las interfaces al puerto 8000. Construimos la imagen en la Raspberry Pi con `docker build -t fastapi-lora:latest .`. Luego, ejecutamos el contenedor mapeando el puerto: por ejemplo `docker run -d --restart unless-stopped -p 8000:8000 fastapi-lora:latest`. Con `-p 8000:8000` exponemos el puerto contenedor 8000 en el puerto 8000 de la Raspberry Pi. La opción `--restart unless-stopped` asegura que el contenedor se reinicie automáticamente al arrancar la Pi.

Es aconsejable utilizar **Docker Compose** para orquestar varios servicios. Podríamos definir un `docker-compose.yml` que levante: (1) el servicio `fastapi`, (2) un servicio `mqtt` usando la imagen oficial de Eclipse Mosquitto, y (3) servicios de ChirpStack si se opta por LoRaWAN completo. Por ejemplo, Mosquitto puede correr en el puerto 1883 para entregar mensajes MQTT. La API FastAPI podría también comunicarse con el broker (por ejemplo, usando Paho MQTT client) para publicar las respuestas a los nodos.

Tras desplegar, confirmamos que la API FastAPI esté accesible en la Raspberry Pi (por ejemplo, haciendo `curl localhost:8000/docs` se vería la documentación interactiva). Recuerde que en la arquitectura propuesta, los usuarios normalmente no accederán directamente por IP a la Raspberry (porque posiblemente no están en la misma red), sino a través de los nodos ESP32. Aún así, exponer el puerto 8000 permite acceder a la API desde la red local (útil para depuración o para un front-end conectado si existiera).

**Nota:** La Raspberry Pi debe tener configurada una red IP para fines administrativos (por ejemplo WiFi o Ethernet local) aunque los clientes no la usen directamente. Además, asegurarse de que Docker tenga permiso de acceder a SPI (en caso de querer interactuar directamente con el HAT LoRa desde un contenedor, se puede pasar el dispositivo /dev/spidev correspondiente al contenedor; aunque en nuestra solución el manejo LoRa lo haremos probablemente desde el host o un servicio especializado, no necesariamente dentro del contenedor FastAPI).

## Configuración del HAT LoRa en la Raspberry Pi (LoRaWAN y comunicación)

Para que la Raspberry Pi se comunique vía LoRa, debemos configurar el HAT conectado a sus pines. Este HAT utiliza la interfaz SPI de la Pi para interactuar con el chip de radio LoRa. Los pasos principales son:

- **Habilitar SPI en la Raspberry Pi:** Editar `/boot/config.txt` o usar `raspi-config` para activar la interfaz SPI (si no lo está ya). Tras habilitar y reiniciar, verificar que existe el dispositivo `/dev/spidev0.0` (SPI0, CE0). El HAT suele usar ese bus para el transceptor LoRa.
- **Instalar software de LoRaWAN Gateway:** Si seguimos el estándar LoRaWAN, podemos instalar un *packet forwarder* y un Network Server local. Una ruta recomendable es usar **ChirpStack** en la propia Pi. ChirpStack proporciona contenedores Docker para todos sus componentes (puente de gateway, network server, aplicación) ([Docker - ChirpStack open-source LoRaWAN® Network Server ...](https://www.chirpstack.io/docs/getting-started/docker.html#:~:text=,you getting started with ChirpStack)) ([Setup ChirpStack using Docker Compose - GitHub](https://github.com/chirpstack/chirpstack-docker#:~:text=Setup ChirpStack using Docker Compose,v4) using Docker Compose)). En un despliegue completo, correríamos: ChirpStack Gateway Bridge (para interactuar con el concentrador LoRa), ChirpStack Network Server (gestiona LoRaWAN MAC, datos), y ChirpStack Application Server (exponiendo datos vía MQTT/REST). 

- **Broker MQTT local:** Ya sea usando ChirpStack o un script casero, la idea es que los datos de los nodos lleguen a la Pi y se publiquen en MQTT internamente. Si se usa ChirpStack Application Server, éste por defecto publica los datos de uplinks en tópicos MQTT del tipo `application/+/device/+/rx` y escucha comandos de downlink en `application/+/device/+/tx` ([Storing Data locally in Raspberry-Pi with Lorawan Gateway - WisGate Connect RAK7391 - RAKwireless Forum](https://forum.rakwireless.com/t/storing-data-locally-in-raspberry-pi-with-lorawan-gateway/9729#:~:text=The simplest one ,MQTT instead of TTN’s MQTT)). Podemos aprovechar eso: los ESP32 enviarían su petición como carga de un uplink LoRaWAN, la recibiríamos vía MQTT local, y para la respuesta generaríamos un downlink MQTT que ChirpStack transmite cuando corresponda. Sin ChirpStack, podemos implementar nuestro propio protocolo MQTT sobre LoRa: por ejemplo, programar la Pi para leer datos crudos del HAT LoRa (usando una librería Python, como `pyLoRa` o incluso utilizando el demonio Meshtastic en modo cliente) y luego publicar esos datos en Mosquitto.

*NOTA*

*En caso de **no usar LoRaWAN completo**, se puede optar por ejecutar un **demonio Meshtastic** en la Raspberry Pi. Meshtastic es un firmware/protocolo de malla sobre LoRa. El MeshAdv-Pi HAT fue diseñado para funcionar con Meshtastic, ejecutando un programa llamado `meshtasticd` en Linux ([Meshtastic on Linux-Native Devices | Meshtastic](https://meshtastic.org/docs/hardware/devices/linux-native-hardware/#:~:text=Image%3A Meshtasticd Terminal Light)) ([Meshtastic on Linux-Native Devices | Meshtastic](https://meshtastic.org/docs/hardware/devices/linux-native-hardware/#:~:text=,pin conflicts when stacking hats)). Si cargáramos Meshtastic en los ESP32 en lugar de MicroPython, podríamos tener una red mesh LoRa funcionando de fábrica. Sin embargo, aquí preferimos MicroPython en los nodos para mayor control. Aun así, podríamos hacer que la Pi corra meshtasticd en modo “cliente mudo” para simplemente retransmitir mensajes. Esto excede el alcance, por lo que asumiremos mejor un esquema simpler de punto a punto o LoRaWAN.*

**Configuración:**

1. Conectar el HAT a la Raspberry Pi y verificar que esté reconocido. Algunos HATs pueden requerir habilitar alimentación a ciertos pines o instalar un overlay en config.txt
2. Probar comunicación básica con el transceptor. Por ejemplo, usar una librería de Python (existen forks de la librería RadioHead o examples con pigpio) para enviar/recibir un paquete LoRa desde la Pi. Asegurarse de configurar los mismos parámetros (freq, SF, BW, CR) que los nodos ESP32.
3. Instalar Mosquitto MQTT broker en la Pi (si no usamos ChirpStack’s MQTT). Configurarlo para que escuche en localhost (por seguridad, puede estar solo local ya que solo la FastAPI y procesos internos lo usan).
4. ChirpStack: registrar un **dispositivo** por cada nodo ESP32, usando DevAddr, NwkSKey y AppSKey precompartidas (modo ABP para simplificar, así los ESP32 transmiten directamente sin procedimiento de join). Configurar el **gateway** single-channel en ChirpStack. Verificar en logs que cuando el nodo envía, ChirpStack lo recibe.
5. Programar la **pasarela de mensajes**: ChirpStack Application MQTT if LoRaWAN). Al recibir una petición, ese servicio invocará la API FastAPI (por ejemplo usando una llamada HTTP local `http://localhost:8000/endpoint` o importando la función Python). Obtendrá la respuesta y la publicará en el topic de respuesta correspondiente para que llegue al nodo. Este componente puede integrarse dentro de la propia aplicación FastAPI (ej., con un background task que escuche MQTT), o como un servicio separado.

En resumen, la Raspberry Pi quedará ejecutando: *Docker (FastAPI)*, *Broker MQTT*, y *gateway LoRa*. El gateway LoRa puede ser ChirpStack+packet-forwarder o un script Python. De cualquier modo, el resultado es que la Pi puede **recibir y transmitir mensajes LoRa**. En la práctica, se está creando un **puente LoRa-MQTT** en la Raspberry.

*Consejo:* Durante la puesta a punto, es útil probar con un solo nodo ESP32 y la Pi cercanos, enviando mensajes simples. Por ejemplo, enviar un string “hello” desde el ESP32 y verificar en la Pi (vía logs del script o ChirpStack) que se recibe correctamente. Luego implementar la integración con FastAPI y respuestas.

## Programación de los nodos ESP32 (MicroPython): WiFi AP, servidor API y comunicación LoRa-MQTT

Cada nodo ESP32 debe realizar tres funciones clave: **crear un punto de acceso WiFi**, **atender solicitudes de dispositivos conectados** y **comunicarse por LoRa** con la Raspberry Pi usando MQTT como protocolo lógico. A continuación se detalla cómo lograr cada parte en MicroPython.

### Configuración del WiFi Access Point en MicroPython

Al iniciar, el ESP32 se configura en modo **AP** (access point) para que otros dispositivos puedan conectarse a él directamente vía WiFi sin necesitar router ([MicroPython: ESP32/ESP8266 Access Point (AP) | Random Nerd Tutorials](https://randomnerdtutorials.com/micropython-esp32-esp8266-access-point-ap/#:~:text=Learn how to set your,Fi without a wireless router)). En MicroPython se utiliza el módulo `network`:

```python
import network
ap = network.WLAN(network.AP_IF)       # interfaz WiFi en modo AP
ap.active(True)
ap.config(essid="LoRaNode1", password="miclave123")  # SSID y clave WPA2
```

Este código activa el AP con el SSID “LoRaNode1” y la contraseña proporcionada ([MicroPython: ESP32/ESP8266 Access Point (AP) | Random Nerd Tutorials](https://randomnerdtutorials.com/micropython-esp32-esp8266-access-point-ap/#:~:text=ap %3D network,password%3Dpassword)). Podemos configurar otros parámetros opcionales, como la dirección IP del AP (por defecto suele ser 192.168.4.1) y el canal WiFi. Tras esto, cualquier smartphone u ordenador podrá ver la red “LoRaNode1” y conectarse. El ESP32 puede aceptar múltiples clientes (por lo general hasta 4 o 5 clientes simultáneos es manejable).

**Servidor HTTP en el ESP32:** Para que los dispositivos puedan consultar la API, el nodo ESP32 hará de proxy local. Podemos implementar un pequeño **servidor web** en MicroPython que escuche peticiones HTTP entrantes. Usando el módulo `socket`, podemos hacer algo como:

```python
import socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]  # atender puerto 80 (HTTP)
s = socket.socket()
s.bind(addr)
s.listen(5)
print("Servidor HTTP escuchando en puerto 80")
while True:
    conn, client_addr = s.accept()
    print("Conexion desde", client_addr)
    request = conn.recv(1024)  # leer la petición (máx 1 KB)
    # Parsear la primera línea de la petición
    request_line = request.decode().split('\r\n')[0]
    print("Peticion:", request_line)
    # Ejemplo simple: asumir GET /dato
    if "GET /dato" in request_line:
        # Aquí en lugar de generar respuesta local, prepararemos mensaje LoRa/MQTT...
        pass
    # Enviar respuesta HTTP básica:
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nOK"
    conn.send(response.encode())
    conn.close()
```

Este es un esqueleto muy básico. En producción, querríamos extraer quizás la ruta solicitada (`/dato` en el ejemplo) y cualquier parámetro. También podríamos escuchar en otro puerto (por ejemplo 8000, igual que FastAPI, para transparencia, pero los dispositivos esperarían usar 80 a menos que les indiquemos puerto).

En este bucle, el ESP32 acepta conexiones entrantes, lee la petición HTTP y puede devolver una respuesta inmediata. **Sin embargo**, en nuestro caso la respuesta no se genera en el ESP32 sino que vendrá de la Raspberry Pi. Por tanto, al recibir la solicitud, el nodo debe **esperar la respuesta** de la Pi antes de responder al cliente. Esto implica que manejaremos la conexión en dos fases: recepción de la solicitud, y suspensión de la respuesta hasta obtener datos de la Pi.

Una estrategia es enviar al cliente alguna confirmación de recepción y usar *long polling* o websockets; pero para simplicidad, podemos bloquear brevemente mientras consultamos a la Pi y luego responder HTTP. Dado que LoRa es lento (latencias del orden de cientos de ms a segundos), es aceptable un pequeño retraso.

### Comunicación LoRa desde MicroPython (MQTT hacia la Pi)

Para retransmitir la consulta vía LoRa, el ESP32 en MicroPython utilizará el módulo de radio conectado (SX127x). Como MicroPython no incluye soporte LoRa nativo, incorporamos un **driver**. Por ejemplo, el proyecto *uPyLoRa* de LeMariva proporciona `sx127x.py` y clases auxiliares ([Tutorial: ESP32 running MicroPython sends data over LoRaWAN - LeMaRiva Tech](https://lemariva.com/blog/2020/02/tutorial-micropython-esp32-sends-data-over-lorawan#:~:text=In this case%2C the SX127x,In the example case)). Con ese driver, podemos inicializar el transceptor:

```python
from sx127x import SX127x
from controller_esp32 import ESP32Controller  # controla pines del ESP32 para LoRa

# Inicializar controlador y transceiver LoRa
controller = ESP32Controller()
lora = controller.add_transceiver(SX127x(name='LoRa'),
                                  pin_id_ss=5,       # pin CS del SX127x
                                  pin_id_RxDone=26)  # pin DIO0 (RxDone) del SX127x
# Configurar parámetros LoRa
lora.set_frequency(868000000)  # por ejemplo 868 MHz
lora.set_spreading_factor(7)
lora.set_bandwidth(125000)
```

*(Las configuraciones de pines dependen del wiring entre ESP32 y módulo LoRa; en este ejemplo CS=GPIO5, DIO0=GPIO26).*

Una vez inicializado, el objeto `lora` nos permite enviar datos. Muchos drivers definen métodos como `lora.println()` para mandar texto directamente ([[IoT\] LoRa with MicroPython on the ESP8266 and ESP32 | by German Gensetskiy | Go Wombat | Medium](https://medium.com/gowombat/iot-lora-with-micropython-on-the-esp8266-and-esp32-59d1a4b507ca#:~:text=import time)) ([[IoT\] LoRa with MicroPython on the ESP8266 and ESP32 | by German Gensetskiy | Go Wombat | Medium](https://medium.com/gowombat/iot-lora-with-micropython-on-the-esp8266-and-esp32-59d1a4b507ca#:~:text=counter %3D 0 print()). Por ejemplo:

```python
mensaje = "NODO1:GET /dato"
lora.println(mensaje)
```

Este envío LoRa se hará de forma asíncrona (no hay garantía de entrega, a menos que implementemos acuses). Podemos incluir en el mensaje algún identificador de nodo y quizás un ID de solicitud. En el ejemplo, enviamos `"NODO1:GET /dato"`, lo cual la Pi deberá interpretar como *“el nodo1 solicita GET /dato”*. Es aconsejable enviar en formato JSON compacto o una trama delimitada para separar campos (por ejemplo: `<id_nodo>|<id_req>|<payload>`). Recordemos que **LoRa tiene límite de payload** (unos ~240 bytes máximo en modo explícito, menos si SF alto), así que mantener los mensajes cortos es crucial.

El **protocolo MQTT sobre LoRa** en nuestro caso es ligero: podemos decidir que todos los mensajes de petición se publiquen en un tópico fijo (p.ej. `"peticiones"`) pero incluyan el identificador del nodo y la ruta. Alternativamente, cada nodo puede publicar en un tópico único (como `"nodo1/peticiones"`). Dado que los ESP32 no tienen un *broker* real, estamos simulando MQTT: en la práctica, el ESP32 envía por LoRa y la Pi, al recibir, hará un `mqtt.publish()` en Mosquitto en el tópico correspondiente.

Cuando la Pi procese y tenga la respuesta, hará el camino inverso: emitirá un mensaje LoRa dirigido al nodo (puede ser *broadcast* pero incluyendo ID del nodo destino en la payload). El ESP32 deberá entonces **escuchar** su radio LoRa para mensajes entrantes. Usando el driver, se puede checar periódicamente si hay paquetes recibidos, o configurar una interrupción en DIO0. Un pseudocódigo simple con polling:

```python
# En algún lugar del loop principal del ESP32:
if lora.received_packet():
    payload = lora.read_payload()
    print("LoRa recibido:", payload)
    # Parsear si es una respuesta para este nodo
    # Suponiendo formato "NODO1_RESP:{...}"
    text = payload.decode('utf-8')
    if text.startswith("NODO1_RESP:"):
        contenido = text.split(":", 1)[1]
        respuesta_api = contenido  # aquí estaría el resultado real de FastAPI
        # Enviar respuesta HTTP al cliente:
        http_response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + respuesta_api
        conn.send(http_response.encode())
        conn.close()
```

En este ejemplo, `lora.received_packet()` sería un método que indica si llegó un paquete (esto depende del driver específico). Luego, `lora.read_payload()` lee los bytes recibidos. Se decodifica a texto y si comienza con el identificador de respuesta del nodo (`"NODO1_RESP:"`), obtenemos el contenido JSON de la respuesta. Finalmente, construimos la respuesta HTTP con ese contenido y la enviamos por el socket abierto con el dispositivo. Así, se completa el ciclo petición-respuesta.

Cabe destacar que hay consideraciones de sincronización: el código del ESP32 debe probablemente esperar la respuesta tras enviar una petición. Se puede implementar esperando activa (polling LoRa) durante unos segundos. También es posible que se necesite reenviar la petición si no hay respuesta (manejo de reintentos) – esto aumenta la complejidad, pero es recomendable para confiabilidad.

### Uso de MQTT y manejo en los nodos

Aunque en los nodos no podemos correr un broker MQTT completo (ni sería útil), **sí podemos aplicar la lógica MQTT**: es decir, definimos “topics” lógicos y mensajes en formato JSON. Por ejemplo, una petición podría ser:

```json
{
  "topic": "consulta/temp",
  "node": "NODO1",
  "payload": null
}
```

y la respuesta:

```json
{
  "topic": "respuesta/temp",
  "node": "NODO1",
  "payload": {"temperatura": 23.5}
}
```

Estos JSON podrían enviarse como strings por LoRa. Sin embargo, añadir tanto texto overhead puede sobrecargar los pocos bytes de LoRa. Una alternativa es usar un **protocolo compacto**: por ejemplo, asignar códigos numéricos a cada tipo de petición. En entornos IoT se suele utilizar **MQTT-SN (MQTT for Sensor Networks)**, que está diseñado para enlaces no TCP como LoRa. MQTT-SN usa mensajes binarios breves y permite que un *gateway* (la Pi) traduzca a MQTT normal. No obstante, implementar MQTT-SN en MicroPython podría ser complejo.

Dado el alcance del proyecto, podemos *simplificar*: el ESP32 “publica” una petición enviando un mensaje LoRa, y la Pi la recibe y la pone en el broker. Similarmente, la Pi “publica” una respuesta enviando LoRa al nodo. El ESP32 no necesita tener una librería MQTT, solo necesita escuchar su respuesta. En esencia, **el nodo actúa como un cliente MQTT implícito**, donde la Pi hace el trabajo pesado de broker.

Por claridad, supongamos que manejamos dos tópicos lógicos por nodo: `"nodox/peticiones"` y `"nodox/respuestas"`. Entonces:

- Cuando el ESP32 recibe una petición HTTP de un cliente, formatea el contenido (p.ej. `"GET /dato"`) y lo envía por LoRa precedido por `"nodox/peticiones:"`. La Pi al ver esto publica el contenido en el tópico `nodox/peticiones` de Mosquitto.
- La FastAPI (o un handler) está suscrita a `nodox/peticiones`. Al llegar, procesa y publica la respuesta en `nodox/respuestas`.
- La Pi envía por LoRa el mensaje con prefijo `"nodox/respuestas:"` seguido del resultado. El ESP32 al recibirlo identifica que es del tópico de respuestas y entonces responde al cliente HTTP.

Esta separación por tópicos permite que múltiples nodos operen sin interferirse (un nodo solo procesa mensajes con su nombre). **¿Y si dos nodos transmiten a la vez?** En LoRa, eso causaría colisión y pérdida de paquetes. No hay colisión avoidance fácilmente (no es como WiFi). Para mitigar, podemos configurar que cada nodo transmita con un pequeño desfase aleatorio y que las peticiones de usuarios sean poco frecuentes. Si el canal se congestiona, quizás convenga usar diferentes frecuencias o SF por nodo (por ejemplo, nodo1 en 868.1MHz SF7, nodo2 en 868.3MHz SF7, etc.). Pero eso requeriría que la Pi tuviera múltiples transceptores o que cambie de canal dinámicamente (no trivial). En redes LoRaWAN reales, hasta 8 canales se escuchan simultáneamente mediante hardware específico (SX1301). En nuestra solución, mantener pocos nodos y tráfico bajo ayudará.

### Ejemplos de código y recursos útiles

Para apoyar el desarrollo, se listan algunos **recursos y ejemplos de código** relevantes:

- **Driver LoRa MicroPython:** Repositorio `uPyLoRaWAN` de Marconi (lemariva) ([[IoT\] LoRa with MicroPython on the ESP8266 and ESP32 | by German Gensetskiy | Go Wombat | Medium](https://medium.com/gowombat/iot-lora-with-micropython-on-the-esp8266-and-esp32-59d1a4b507ca#:~:text=Next step was in understanding,version for ESP32 named uPyLora)) que incluye un driver SX127x optimizado para ESP32. Confirmó envíos exitosos en ESP32 ([[IoT\] LoRa with MicroPython on the ESP8266 and ESP32 | by German Gensetskiy | Go Wombat | Medium](https://medium.com/gowombat/iot-lora-with-micropython-on-the-esp8266-and-esp32-59d1a4b507ca#:~:text=counter %2B%3D 1 time)). Este código puede ser adaptado para nuestra necesidad (ignorando la capa LoRaWAN si no se usa).
- **Tutorial MicroPython LoRaWAN:** LeMariva publicó un tutorial de cómo conectar un ESP32 (MicroPython) a The Things Network usando ABP ([Tutorial: ESP32 running MicroPython sends data over LoRaWAN - LeMaRiva Tech](https://lemariva.com/blog/2020/02/tutorial-micropython-esp32-sends-data-over-lorawan#:~:text=the original project to clean,1)). Ese ejemplo muestra cómo preparar `DEVADDR`, `NwkSKey`, `AppSKey` en MicroPython para enviar datos LoRaWAN uplink. Nuestro caso es similar si usamos ChirpStack (solo que apuntando al network server local en vez de TTN).
- **Ejemplo de Access Point y sockets:** Random Nerd Tutorials tiene ejemplos de configurar el ESP32 como AP ([MicroPython: ESP32/ESP8266 Access Point (AP) | Random Nerd Tutorials](https://randomnerdtutorials.com/micropython-esp32-esp8266-access-point-ap/#:~:text=Learn how to set your,Fi without a wireless router)) y de crear servidores web en MicroPython ([ESP32/ESP8266 MicroPython Web Server | Random Nerd Tutorials](https://randomnerdtutorials.com/esp32-esp8266-micropython-web-server/#:~:text=s %3D socket,listen(5)) ([ESP32/ESP8266 MicroPython Web Server | Random Nerd Tutorials](https://randomnerdtutorials.com/esp32-esp8266-micropython-web-server/#:~:text=led,n') conn.sendall(response) conn.close)). Esos ejemplos fueron la base para nuestro servidor HTTP en el nodo.
- **Proyecto LoRa MQTT Gateway (Arduino):** Instructable “MQTT Manager, LoRa and LoRa ‘Poor Man’ Gateway” – implementa una solución con dos ESP32 donde uno hace de gateway WiFi-LoRa y otro controla un relé en un garage ([MQTT Manager, Lora and Lora 'Poor Man' Gateway - Super Cheap : 11 Steps - Instructables](https://www.instructables.com/MQTT-Manager-Lora-and-Lora-Poor-Man-Gateway-Cheap-/#:~:text=Then%2C I came up with,mains when not at home)) ([MQTT Manager, Lora and Lora 'Poor Man' Gateway - Super Cheap : 11 Steps - Instructables](https://www.instructables.com/MQTT-Manager-Lora-and-Lora-Poor-Man-Gateway-Cheap-/#:~:text=Apartment)). Aunque usa Arduino C++, la arquitectura es muy parecida a la nuestra y puede servir de inspiración. La figura 1 presentada proviene de allí adaptada.
- **Repositorio LoRa-to-MQTT (ESP32 + EByte):** Proyecto en GitHub de ezcGman que construye un gateway LoRa <-> MQTT con ESP32 y módulos E32/E220 ([GitHub - ezcGman/lora-gateway: Gateway to create a bridge between your LoRa devices and Wi-Fi or Ethernet. Also comes with ready-to-use code to drop everything into your MQTT server!](https://github.com/ezcGman/lora-gateway#:~:text=This repository gives you everything,you should pick down below)). Útil para entender la encapsulación de mensajes y el manejo de tópicos.
- **ChirpStack & MQTT:** Documentación de ChirpStack sobre integraciones MQTT. También en foros de RAK se recomienda instalar un Network Server local para almacenar datos en la Pi y usar MQTT local en vez de TTN ([Storing Data locally in Raspberry-Pi with Lorawan Gateway - WisGate Connect RAK7391 - RAKwireless Forum](https://forum.rakwireless.com/t/storing-data-locally-in-raspberry-pi-with-lorawan-gateway/9729#:~:text=The simplest one ,MQTT instead of TTN’s MQTT)). Esto confirma la viabilidad de nuestra aproximación con un servidor LoRaWAN privado.

## Posibles retos técnicos y cómo mitigarlos

Implementar esta infraestructura conlleva varios desafíos. A continuación, enumeramos algunos de los principales retos técnicos junto con estrategias para mitigarlos:

- **Latencia y bajo ancho de banda de LoRa:** La comunicación LoRa es de baja velocidad (unos pocos kilobits por segundo en el mejor caso) y alta latencia (cada paquete puede tardar cientos de milisegundos en transmitirse, especialmente con spreading factors altos). Esto significa que las consultas API tendrán mayor retraso que en WiFi o Ethernet. **Mitigación:** Usar la **velocidad LoRa más alta posible** que cubra la distancia requerida. Esto implica elegir **Spreading Factor bajo (SF7)**, ancho de banda mayor (125 kHz o más) y coding rate bajo, siempre que el enlace siga siendo fiable. Además, enviar **paquetes pequeños** – limitar la información solicitada a lo esencial. En la aplicación, informar al usuario que las respuestas pueden tardar ~1-2 segundos, para manejar sus expectativas. Si es crítico, considerar implementar confirmaciones a nivel de aplicación (ACK) y reintentos en caso de pérdida, lo que añade algo de latencia pero asegura entrega.
- **Tamaño de mensaje limitado en LoRa:** Como se mencionó, LoRa (y especialmente LoRaWAN) limita la carga útil. Por ejemplo, en LoRaWAN a SF12 solo ~51 bytes por paquete ([Use Lora Shield and RPi to Build a LoRaWAN Gateway : 10 Steps (with Pictures) - Instructables](https://www.instructables.com/Use-Lora-Shield-and-RPi-to-Build-a-LoRaWAN-Gateway/#:~:text=,and will never be)). **Mitigación:** Diseñar la API de forma que las respuestas sean **concisas**. Evitar enviar datos voluminosos (imágenes, largas cadenas) a través de LoRa. Si se requiere transferir más datos de lo que cabe en un paquete, implementaremos una estrategia de fragmentación: dividir la respuesta en varios paquetes y reensamblarlos en el nodo (esto complica el protocolo y se debe hacer con cautela debido a mayor riesgo de pérdida). También se puede comprimir JSON o usar formatos binarios compactos. En casos extremos, habría que asumir la imposibilidad de ciertas operaciones por LoRa y limitarlas.
- **Colisiones y concurrencia en LoRa:** A diferencia de WiFi, LoRa no tiene un mecanismo robusto de acceder al medio (no hay carrier sense). Si dos nodos transmiten simultáneamente en la misma frecuencia/SF, habrá colisión y pérdida. **Mitigación:** Coordinar a nivel de aplicación para evitar transmisiones simultáneas. Por ejemplo, si los nodos están relativamente cerca entre sí, podrían escuchar antes de transmitir (LoRa no detecta portadora fácilmente, pero se podría medir RSSI). Más simple: asegurarse de que el tráfico es bajo (p. ej., que los usuarios no hagan spam de requests). Si hay muchos nodos, se podría asignar **ventanas de tiempo** o intervalos aleatorios a cada uno para reducir probabilidad de choque. Otra opción es usar diferentes **spreading factors** por nodo, ya que LoRa ortogonaliza diferentes SF (un nodo en SF7 y otro en SF8 pueden transmitir simultáneamente con menos interferencia). Esto requiere que la gateway Pi escuche múltiples SF, lo cual con un transceptor normal no es trivial (normalmente habría que fijarlo en uno, a menos que se implemente escucha continua y detección multi-SF muy avanzada). En redes sencillas, probablemente unos pocos nodos y tráfico bajo no presenten muchas colisiones.
- **Limitaciones de MicroPython en ESP32:** MicroPython es más lento que C/C++ nativo, y tiene limitaciones de memoria (unos ~100k RAM libres típicamente en ESP32). Ejecutar un AP WiFi, un bucle de servidor web y manejar LoRa simultáneamente es intensivo. **Mitigación:** Escribir código eficiente, evitando copias de datos grandes. Reutilizar buffers (por ejemplo, usar el mismo `bytearray` para recv de socket). Deshabilitar características innecesarias (p. ej., si no usamos debugging via USB, podemos desactivar prints, etc.). Si MicroPython no rinde, contemplar usar código C para partes críticas (MicroPython permite código nativo via `machine.CodeType` o incluso escribir módulos en C). Sin embargo, probablemente MicroPython sí pueda manejar unas pocas peticiones por minuto. También se puede aprovechar `uasyncio` para manejar la espera de LoRa de forma asíncrona en vez de bloquear completamente el bucle (así el AP puede seguir aceptando nuevas conexiones en paralelo si llega otro cliente).
- **Gestión de múltiples clientes en el nodo:** Si dos usuarios se conectan al mismo ESP32 AP y hacen consultas simultáneas, nuestro código de ejemplo (que es single-thread) atenderá de a uno. El segundo tendrá que esperar a que termine el primero. **Mitigación:** Utilizar **uasyncio** en MicroPython para manejar múltiples sockets concurrentemente sin bloquear, o al menos para permitir que el ESP32 escuche LoRa mientras espera una respuesta para el primer cliente. Dado que normalmente el volumen de usuarios por nodo será bajo, esto quizás no sea crítico. Otra solución es desplegar más nodos para distribuir la carga (aunque eso conlleva más colisiones potenciales en LoRa).
- **Cobertura WiFi del nodo ESP32:** El ESP32 como AP tiene un alcance limitado (~20m en interiores). Si los usuarios están muy dispersos, puede que deban acercarse al nodo. **Mitigación:** Asegurar línea de vista o instalar una antena WiFi externa al ESP32 (algunos boards permiten soldar una antena o usar módulos con conector U.FL). También se podría poner el ESP32 en modo repetidor, pero complica. Este reto es más de diseño físico: colocar los nodos estratégicamente donde se requiera acceso.
- **Regulaciones y duty cycle:** En bandas libres (868 MHz en Europa), existen restricciones de tiempo de transmisión (duty cycle ~1% típicamente). Esto significa que un dispositivo LoRa puede ocupar el canal sólo ~36 segundos por hora. **Mitigación:** Asegurarse de que la frecuencia elegida cumple normativa local (p.ej., 868.1 MHz tiene duty cycle 1%). Limitar la frecuencia de consultas para no exceder este duty cycle. Si un nodo o la Pi envían muchos datos, podrían violar la normativa. ChirpStack en modo LoRaWAN se encarga de respetar duty cycle en downlinks; si trabajamos en capa propia, debemos manualmente implementar pausas si se llega al límite. En la práctica, si las peticiones son esporádicas, no habrá problema.
- **Seguridad de las comunicaciones:** Los datos viajan por radio sin cifrado a menos que lo implementemos. Podría interceptarse la información. **Mitigación:** Utilizar **cifrado** en la capa de aplicación o usar LoRaWAN que ya incluye AES-128 en las cargas útiles. Por ejemplo, podríamos acordar una clave simétrica y cifrar el contenido JSON antes de enviarlo LoRa (aplicar XOR, AES u otro). Dado que tenemos control de ambos extremos, esto es factible. MQTT sobre LoRaWAN con ChirpStack ya estaría cifrado de extremo a extremo (solo la aplicación server lo ve descifrado). Para una versión simple, quizás no cifremos pero somos conscientes de la posible exposición. Si se envían datos sensibles, incluir cifrado es muy recomendable.
- **Integración FastAPI ↔ MQTT:** A nivel software, hay que asegurar que la API FastAPI pueda interactuar con la cola de mensajes. **Mitigación:** Podemos utilizar un hilo separado o tarea async en FastAPI que se suscriba a los tópicos MQTT (usando por ejemplo la librería `paho-mqtt` o `aiomqtt`). Cuando llegue un mensaje de petición, podríamos almacenarlo en una estructura y quizás usar `asyncio.Event` para notificar al endpoint correspondiente si está esperando. Otra opción es no involucrar FastAPI en la escucha MQTT, sino tener un bucle independiente que directamente llame a funciones de la lógica de FastAPI (importando el módulo). Esto rompe un poco la arquitectura REST, pero funciona internamente. En cualquier caso, debemos tener cuidado de no bloquear el server FastAPI (usar async apropiadamente).

Finalmente, probar el sistema de extremo a extremo es vital. Se pueden realizar pruebas con un único ESP32 y la Pi en corto alcance, luego ir incrementando distancia y número de nodos. Observar la calidad de señal (RSSI, SNR) que reportan los paquetes LoRa para entender hasta dónde llega la cobertura. Afinar parámetros de transmisión en función de eso (por ejemplo, subir SF si hace falta más alcance, sabiendo que penaliza la velocidad). También aprovechar las herramientas que nos da MQTT: por ejemplo, registrar en logs cada mensaje publicado y sus tiempos para medir latencias reales.

En síntesis, la solución propuesta combina **tecnologías IoT (LoRa, MQTT) con web (FastAPI)** para lograr consultas remotas de larga distancia. Aunque conlleva retos en tiempo real y limitaciones de enlace, con un buen diseño de protocolos ligeros y sincronización adecuada, es posible lograr un sistema funcional. Este enfoque habilita casos de uso como sensores en áreas rurales donde los usuarios pueden, mediante su móvil conectado a un nodo cercano, obtener datos o enviar comandos a un servidor central a kilómetros de distancia sin infraestructura de comunicaciones tradicional. Las consideraciones descritas arriba servirán para construir una infraestructura robusta y extensible.

**Referencias:** FastAPI Docker ([FastAPI in Containers - Docker - FastAPI](https://fastapi.tiangolo.com/deployment/docker/#:~:text=This is what you would,in most cases%2C for example)), Meshtastic Linux ([Meshtastic on Linux-Native Devices | Meshtastic](https://meshtastic.org/docs/hardware/devices/linux-native-hardware/#:~:text=,pin conflicts when stacking hats)), Proyecto LoRa MQTT ([MQTT Manager, Lora and Lora 'Poor Man' Gateway - Super Cheap : 11 Steps - Instructables](https://www.instructables.com/MQTT-Manager-Lora-and-Lora-Poor-Man-Gateway-Cheap-/#:~:text=Apartment)), Foro RAK/ChirpStack ([Storing Data locally in Raspberry-Pi with Lorawan Gateway - WisGate Connect RAK7391 - RAKwireless Forum](https://forum.rakwireless.com/t/storing-data-locally-in-raspberry-pi-with-lorawan-gateway/9729#:~:text=The simplest one ,MQTT instead of TTN’s MQTT)), Instructables Gateway ([Use Lora Shield and RPi to Build a LoRaWAN Gateway : 10 Steps (with Pictures) - Instructables](https://www.instructables.com/Use-Lora-Shield-and-RPi-to-Build-a-LoRaWAN-Gateway/#:~:text=,and will never be)), MicroPython WiFi AP ([MicroPython: ESP32/ESP8266 Access Point (AP) | Random Nerd Tutorials](https://randomnerdtutorials.com/micropython-esp32-esp8266-access-point-ap/#:~:text=ap %3D network,password%3Dpassword)), MicroPython LoRa (GoWombat) ([[IoT\] LoRa with MicroPython on the ESP8266 and ESP32 | by German Gensetskiy | Go Wombat | Medium](https://medium.com/gowombat/iot-lora-with-micropython-on-the-esp8266-and-esp32-59d1a4b507ca#:~:text=Next step was in understanding,version for ESP32 named uPyLora)) ([[IoT\] LoRa with MicroPython on the ESP8266 and ESP32 | by German Gensetskiy | Go Wombat | Medium](https://medium.com/gowombat/iot-lora-with-micropython-on-the-esp8266-and-esp32-59d1a4b507ca#:~:text=counter %2B%3D 1 time)).

