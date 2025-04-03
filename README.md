# Proyecto: Gateway LoRaWAN

## Descripción general del proyecto

Este proyecto consiste en crear una **pasarela LoRaWAN** En otras palabras, la Raspberry Pi actuará como un **gateway** que recibe datos inalámbricos de largo alcance desde sensores (nodos LoRaWAN) y los envía a una aplicación de red. Los nodos serán pequeños dispositivos con ESP32 que transmitirán información mediante el protocolo LoRaWAN, y la pasarela (con un módulo concentrador LoRa) reenviará esos datos a un servidor de red LoRaWAN (en este caso, **The Things Stack**, ejecutándose en la Raspberry Pi mediante Docker). Finalmente, la información podrá consultarse en una aplicación a través de Internet o la red local (por ejemplo, mediante MQTT o HTTP).

En términos simples, **LoRaWAN** es un protocolo de comunicación inalámbrica de largo alcance y baja potencia. Permite que sensores envíen pequeños paquetes de datos a varios kilómetros de distancia. Las **pasarelas LoRaWAN** funcionan como puentes: reciben los mensajes de los sensores cercanos y los retransmiten por Internet a un servidor. El servidor de red (Network Server) procesa esos mensajes y los pone a disposición de las aplicaciones. La arquitectura típica incluye: dispositivos finales (nodos), pasarelas, servidor de red, y servidor de aplicaciones ([LoRaWAN Architecture | The Things Network](https://www.thethingsnetwork.org/docs/lorawan/architecture/#:~:text=End devices communicate with nearby,is known as message deduplication)).

En la figura a continuación se ilustra este concepto:



*Figura: Arquitectura básica de un sistema LoRaWAN (nodos → gateway → servidor de red → servidor de aplicaciones).*

En nuestro proyecto, todo estará en una escala pequeña y local: los nodos (ESP32 con sensores) enviarán datos LoRa que recibirá la pasarela (Raspberry Pi 3 + módulo LoRa). La Raspberry Pi, además de llevar el módulo de radio LoRa, ejecutará en Docker **The Things Stack (TTS)**, que es una implementación del servidor de red LoRaWAN (es la misma tecnología utilizada por The Things Network). TTS gestionará los dispositivos, claves de seguridad y el reenvío de los datos hacia la aplicación final. La aplicación final también podrá ejecutarse en la misma Raspberry Pi (por ejemplo, otro contenedor Docker que procese los datos vía MQTT).

En resumen, con este proyecto podrás montar una red LoRaWAN **completa y privada** en tu casa o laboratorio, visualizando los datos enviados por tus sensores a través de una aplicación. No se requiere experiencia técnica avanzada: en esta guía encontrarás paso a paso desde la instalación del sistema hasta ejemplos de código, usando un lenguaje sencillo.

## Hardware necesario 🔧

Para implementar el gateway y los nodos, necesitaremos algunos componentes electrónicos. A continuación se lista el hardware esencial, con sugerencias y enlaces de referencia para su adquisición:

- **Raspberry Pi 3** (modelo B o B+), con tarjeta microSD (8 GB o más) y conectividad a Internet (por Ethernet o WiFi). Es el computador principal que actuará como gateway y servidor.
- **Módulo concentrador LoRaWAN de 8 canales** para Raspberry Pi. Por ejemplo, la placa *RAK2245 Pi HAT* de RAKwireless, que se conecta directamente al puerto GPIO de la Raspberry P ([Meet the Device That LoRa® Developers Can't Resist Having: RAK2245 - IoT Made Easy](https://www.rakwireless.com/en-us/products/lpwan-gateways-and-concentrators/rak2245-pihat#:~:text=LPWAN Gateway Concentrator Module The,as the Raspberry Pi 3B))】. Este módulo incluye el chip concentrador (Semtech SX1301/SX1308) y permite a la Pi recibir/transmitir en la banda LoRaWAN. Viene normalmente con antena LoRa y GPS. **Alternativas:** otros concentradores similares (RAK2246, RAK2287, iC880a, etc.) también son válidos, siempre que sean compatibles con Raspberry Pi.
  - **Enlace sugerido:** [RAK2245 Pi HAT – Concentrador LoRaWAN 8 canales](https://store.rakwireless.com/products/rak2245-pi-hat) (ver descripción en la tienda de RAK).
- **Antena LoRa** adecuada a la frecuencia de tu región. Por ejemplo, en Europa se usa 868 MHz y en América 915 MHz. Asegúrate de adquirir una antena que coincida con la frecuencia del módulo concentrador. Muchos kits de pasarela (como el RAK2245) ya incluyen una antena LoRa apropiada.
- **Fuente de alimentación** de 5V para la Raspberry Pi (al menos 2 A de corriente). Una fuente oficial o de buena calidad garantizará estabilidad, sobre todo al alimentar también el módulo concentrador.
- **Tarjeta microSD** de al menos 8 GB (se recomienda 16 GB) para instalar el sistema operativo de la Raspberry Pi.
- **Placas de desarrollo ESP32 con radio LoRa integrada** para usarlas como nodos. Por ejemplo, las placas **Heltec WiFi LoRa 32** o **LILYGO TTGO LoRa32**, que incluyen un microcontrolador ESP32, un transceptor LoRa (SX1276/SX1278 o similares) y en algunos casos una pequeña pantalla OLED. Estas placas son ideales porque soportan MicroPython y ya traen la radio LoRa incorporada.
  - **Enlace sugerido:** [Heltec LoRa 32 V2 (ESP32 + LoRa 868 MHz)](https://heltec.org/project/wifi-lora-32/) o buscar en Amazon por "ESP32 LoRa 868 Heltec/TTGO".
  - **Alternativa:** un ESP32 normal más un módulo LoRa externo (por ejemplo Ra-02, RFM95) conectados por SPI. Sin embargo, las placas integradas hacen más sencilla la implementación.
- **Antenas LoRa para los nodos** ESP32: suelen venir incluidas con las placas Heltec/TTGO (pueden ser pequeñas antenas helicoidales o de hilo). Conectarlas correctamente es importante para buen alcance.
- **Cable microUSB** para programar los ESP32 desde el PC.
- (Opcional) **Sensor(es)** para conectar a los ESP32 (p.ej. sensor de temperatura, humedad, etc.), según los datos que quieras enviar. También opcionalmente **cajas o carcasas** si deseas empotrar la pasarela o los nodos.

**Nota:** Verifica que la banda de frecuencia LoRaWAN de todos los componentes coincida (pasarela y nodos). En España y la mayor parte de Europa se utiliza la banda EU868 (868 MHz), mientras que en Norteamérica es US915 (915 MHz). Muchos de estos módulos vienen en versiones específicas para cada banda.

## Instalación del sistema operativo en la Raspberry Pi

Comenzaremos preparando la Raspberry Pi 3 con su sistema operativo. Usaremos **Raspberry Pi OS Lite** (una versión ligera de Linux basada en Debian), ya que no necesitamos entorno gráfico y así ahorramos recursos. Sigue estos pasos:

1. **Descargar Raspberry Pi OS:** Visita la página oficial de Raspberry Pi y descarga la herramienta **Raspberry Pi Imager* ([Deploy The Things Stack  in your local network](https://www.thethingsnetwork.org/article/deploy-the-things-stack-in-your-local-network#:~:text=Install the Raspberry Pi Operating,org%2Fsoftware))】. Con ella puedes instalar fácilmente el sistema en la tarjeta SD.

2. **Flashear la tarjeta microSD:** Inserta la microSD en tu PC (con un adaptador si es necesario). Abre Raspberry Pi Imager:

   - Selecciona *Raspberry Pi OS Lite (32 bits)* como sistema operativo (es suficiente para nuestro propósito).
   - Selecciona la tarjeta SD de destino.
   - Haz clic en *Write* para grabar el OS en la tarjeta. Espera a que finalice.

3. **Configuración inicial de la Raspberry Pi:** Una vez grabada la tarjeta, insértala en la Raspberry Pi 3. Conéctala a un monitor y teclado, o prepárala para acceso SSH. En el primer arranque, el sistema puede reiniciarse una vez automáticamente. Finalmente aparecerá el prompt de login.

   - Inicia sesión con el usuario por defecto: **usuario:** `pi`, **contraseña:** `raspberry`. Te recomendamos cambiar esta contraseña más adelante (puedes hacerlo con el comando `passwd`).
   - Opcional: Ejecuta `sudo raspi-config` para configurar algunas opciones básicas:
     - En *System Options > Wireless LAN*, configura el **Wi-Fi** (país, SSID y contraseña) si usarás WiFi.
     - En *Interface Options*, activa **SSH** para permitir acceso remoto segur ([Deploy The Things Stack  in your local network](https://www.thethingsnetwork.org/article/deploy-the-things-stack-in-your-local-network#:~:text=Configure WiFi and enable SSH%2C,config)) ([Deploy The Things Stack  in your local network](https://www.thethingsnetwork.org/article/deploy-the-things-stack-in-your-local-network#:~:text=To enable SSH%3A Go to,192.168.178.43))】. Esto facilitará mucho la instalación, pues podrás copiar y pegar comandos desde tu PC.
     - En *Interface Options*, activa **SPI** e **I2C** (estas interfaces son necesarias para comunicar la Pi con el módulo LoRa RAK2245 vía GPIO ([GitHub - RAKWireless/rak_common_for_gateway](https://github.com/RAKWireless/rak_common_for_gateway#:~:text=step2 %3A Use "sudo raspi,and enable serial port hardware))】. Al activar SPI/I2C, probablemente `raspi-config` te preguntará si quieres habilitar la interfaz – elige "Sí".
     - Desactiva la consola serial por el puerto UART si se te pregunta (esto libera el puerto serial para otros usos, a veces relevante para ciertos módulos).
     - Finalmente selecciona *Finish* y permite que la Raspberry Pi se reinicie si así lo indica.
   - Si configuraste WiFi y SSH, a partir de ahora puedes desconectar monitor/teclado y conectarte a la Pi vía SSH desde tu PC (`ssh pi@<IP_de_tu_RPi>`). Para encontrar la IP, puedes usar `ifconfig` en la Pi o mirar en tu router.

4. **Actualizar el sistema:** Es buena práctica asegurarse de tener los últimos paquetes. Ejecuta en la Raspberry Pi:

   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

   Esto actualizará la lista de paquetes y aplicará cualquier actualización disponible. Puede tardar unos minutos.

Llegados a este punto, tu Raspberry Pi 3 está operativa con Raspberry Pi OS. Mantén la Pi encendida y conectada a Internet para proceder con la instalación de Docker y del software de la pasarela.

## Instalación de Docker y Docker Compose

Usaremos **Docker** para desplegar fácilmente The Things Stack (servidor LoRaWAN) y potencialmente otras aplicaciones en contenedores. Docker permite “empaquetar” software en unidades independientes que se ejecutan en la Pi sin necesidad de instalaciones complicadas. También instalaremos **Docker Compose** para manejar múltiples contenedores con un solo archivo de configuración.

Sigue estos pasos en la Raspberry Pi (puedes copiarlos y pegarlos vía SSH):

1. **Instalar Docker Engine:** Ejecuta el script automático proporcionado por Docker, que detecta tu sistema (en este caso ARM/Raspberry Pi) e instala la última versión. En la terminal de la Pi, ingresa:

   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh
   ```

   Esto descargará y ejecutará el script de instalación de Docker (puedes ver que es un comando muy similar al sugerido oficialment ([How To Install Docker and Docker-Compose On Raspberry Pi - DEV Community](https://dev.to/elalemanyo/how-to-install-docker-and-docker-compose-on-raspberry-pi-1mo#:~:text=Now is time to install,script for that%2C just run))】). Durante el proceso, se instalarán los paquetes `docker-ce` (Community Edition) y sus dependencias. Si todo va bien, al finalizar podrás ejecutar `docker --version` para verificar la instalación.

2. **Configurar permisos de Docker:** Por defecto, Docker requiere privilegios de superusuario (root) para funcionar. Podemos permitir que el usuario “pi” use Docker sin sudo añadiéndolo al grupo “docker”:

   ```bash
   sudo usermod -aG docker pi
   ```

   Después, cierra la sesión y vuelve a entrar (o ejecuta `newgrp docker`) para aplicar los nuevos permiso ([How To Install Docker and Docker-Compose On Raspberry Pi - DEV Community](https://dev.to/elalemanyo/how-to-install-docker-and-docker-compose-on-raspberry-pi-1mo#:~:text=3. Add a Non,to the Docker Group)) ([How To Install Docker and Docker-Compose On Raspberry Pi - DEV Community](https://dev.to/elalemanyo/how-to-install-docker-and-docker-compose-on-raspberry-pi-1mo#:~:text=To add the permissions to,the current user run))】. Este paso es opcional pero conveniente, así no tendrás que escribir `sudo` antes de cada comando docker.

3. **Instalar Docker Compose:** Docker Compose es una herramienta para definir y correr aplicaciones multi-contenedor. Para instalarla en Raspberry Pi:

   - Primero asegúrate de tener Python 3 y pip instalados:

     ```bash
     sudo apt-get install -y python3 python3-pip
     ```

   - Luego instala Docker Compose usando pip:

     ```bash
     sudo pip3 install docker-compose
     ```

     Esto descargará la última versión compatible de Compose. Alternativamente, en Raspberry Pi OS Bullseye o posterior, podrías instalar con apt (`sudo apt-get install docker-compose`), pero la versión vía pip suele estar más actualizad ([How To Install Docker and Docker-Compose On Raspberry Pi - DEV Community](https://dev.to/elalemanyo/how-to-install-docker-and-docker-compose-on-raspberry-pi-1mo#:~:text=Using `pip`%3A Docker,can run the following commands)) ([How To Install Docker and Docker-Compose On Raspberry Pi - DEV Community](https://dev.to/elalemanyo/how-to-install-docker-and-docker-compose-on-raspberry-pi-1mo#:~:text=Once python3 and pip3 are,Compose using the following command))】.

   - Comprueba la instalación con `docker-compose --version`. Deberías obtener un número de versión si todo fue correcto.

4. **Verificación rápida:** Ejecuta `docker run hello-world`. Esto descargará una pequeña imagen de prueba y la ejecutará. Si ves un mensaje de "Hello from Docker!" significa que Docker está funcionando correctamente.

Ya tenemos Docker instalado en la Raspberry Pi. Ahora podremos desplegar servicios en contenedores de forma sencilla.

## Instalación de The Things Stack (servidor LoRaWAN) en Docker

The Things Stack (TTS) es la plataforma que gestionará la red LoRaWAN local. Actuará como **Network Server**, encargado de recibir los datos de la pasarela, aplicar las claves de seguridad LoRaWAN, y ofrecer los datos a las aplicaciones. Vamos a instalar la edición open source de TTS en la Raspberry Pi usando contenedores Docker. Afortunadamente, The Things Stack proporciona imágenes multiplataforma, incluyendo ARM, por lo que es posible ejecutarlo en una Raspberry P ([Deploy The Things Stack  in your local network](https://www.thethingsnetwork.org/article/deploy-the-things-stack-in-your-local-network#:~:text=The Things Stack now offers,such as the Raspberry Pi))】.

**Pasos para desplegar TTS:**

1. **Crear un archivo de configuración Docker Compose:** En la Raspberry Pi, crea un directorio de trabajo y dentro un archivo llamado `docker-compose.yml`. Por ejemplo:

   ```bash
   mkdir -p ~/tts-stack && cd $_
   nano docker-compose.yml
   ```

   Copia y pega el siguiente contenido en `docker-compose.yml`:

   ```yaml
   version: '3'
   services:
     # Base de datos PostgreSQL (almacena información de TTS)
     postgres:
       image: postgres:14-alpine
       container_name: tts-postgres
       restart: unless-stopped
       environment:
         - POSTGRES_PASSWORD=ttspostgres
         - POSTGRES_USER=tts
         - POSTGRES_DB=ttn_lorawan
       volumes:
         - postgres-data:/var/lib/postgresql/data
   
     # Base de datos Redis (cache para TTS)
     redis:
       image: redis:6-alpine
       container_name: tts-redis
       restart: unless-stopped
       command: redis-server --appendonly yes
       volumes:
         - redis-data:/data
   
     # The Things Stack (LoRaWAN Network Server)
     stack:
       image: xoseperez/the-things-stack:latest
       container_name: tts-stack
       restart: unless-stopped
       depends_on:
         - redis
         - postgres
       volumes:
         - stack-blob:/srv/ttn-lorawan/public/blob
         - stack-data:/srv/data
       environment:
         # Dominio o IP donde estará accesible la consola TTS
         TTS_DOMAIN: "127.0.0.1"       # en este caso, usaremos la propia IP local de la Raspberry Pi
         TTN_LW_BLOB_LOCAL_DIRECTORY: /srv/ttn-lorawan/public/blob
         TTN_LW_REDIS_ADDRESS: redis:6379
         TTN_LW_IS_DATABASE_URI: postgres://tts:ttspostgres@postgres:5432/ttn_lorawan?sslmode=disable
         # Puedes añadir más variables de config si es necesario
       ports:
         # Puertos del servidor LoRaWAN (API, Consola, MQTT, etc.)
         - "1700:1700/udp"   # Puerto UDP para tráfico LoRaWAN (Semtech UDP Packet Forwarder)
         - "1885:1885"       # Consola web (HTTP) de TTS 
         - "8885:8885"       # Consola web (HTTPS) de TTS
         - "1883:1883"       # MQTT (publicación de datos)
   volumes:
     postgres-data:
     redis-data:
     stack-blob:
     stack-data:
   ```

   Vamos a explicar brevemente esta configuración:

   - Se definen tres servicios: **postgres** (base de datos SQL), **redis** (almacenamiento en memoria) y **stack** (el servicio principal The Things Stack). Cada uno usa una imagen Docker oficial o de la comunidad.
   - Asignamos variables de entorno para que TTS sepa cómo conectarse a la base de datos y otras configuraciones. `TTS_DOMAIN` lo hemos puesto como `127.0.0.1` (localhost) por simplicidad; idealmente debería ser la IP local de tu Raspberry Pi o un nombre de host si has configurado uno. Esto se usa para generar certificados y URLs de la consola. Puedes reemplazar "127.0.0.1" por la IP fija de tu Pi en la red local, o un dominio local si tienes (por ejemplo `lorawan-gateway.local`).
   - Mapeamos los **puertos** necesarios:
     - UDP/1700: es el puerto por el que llegan los datos LoRaWAN desde la pasarela (usa el protocolo Semtech UDP Packet Forwarder).
     - TCP/1885 y 8885: puertos HTTP y HTTPS para la interfaz web (Consola) de The Things Stack. Los hemos ligado a 1885 (en lugar del 1885 interno) y mapeado 443 a 8885 si quisieras acceder por HTTPS. En el ejemplo, accederemos por `http://IP_de_RPi:1885/` para usar la consola (o por `https://IP_de_RPi:8885/` con certificado autosignado).
     - TCP/1883: puerto estándar MQTT, que TTS usa para publicar los datos de las aplicaciones. Así podremos conectar clientes MQTT a la Raspberry Pi para leer los datos de sensores.
   - Usamos la imagen Docker de **xoseperez/the-things-stack**, que es una adaptación de TTS Community Edition para ARM (Raspberry Pi). Esta imagen nos simplifica la vida creando certificados y un usuario administrador por defecto. *Nota:* La primera vez que se ejecute, la imagen generará un usuario admin con contraseña por defecto, que cambiaremos luego por seguridad.

   Guarda el archivo y cierra nano (Ctrl+O, Enter para guardar; Ctrl+X para salir).

2. **Lanzar The Things Stack:** Con Docker Compose configurado, iniciemos los contenedores:

   ```bash
   docker-compose up -d
   ```

   La opción `-d` los ejecuta en segundo plano (modo *detached*). Docker descargará las imágenes necesarias (Postgres, Redis y TTS). Este paso puede tardar varios minutos la primera vez, dependiendo de tu conexión, ya que la imagen de TTS es algo pesada (contiene varios componentes). Ten paciencia.

3. **Verificar que los servicios estén corriendo:** Ejecuta `docker-compose ps`. Deberías ver tres contenedores en estado "Up". También puedes ver los registros (logs) con `docker-compose logs -f stack` para monitorear el arranque de The Things Stack. Este, al inicializar por primera vez, creará la base de datos, las tablas necesarias, un usuario administrador, etc. Si todo va bien, después de unos instantes la consola web estará lista.

4. **Acceder a la consola web de TTS:** Abre un navegador web en un dispositivo conectado a la misma red (puede ser tu PC) y entra a la dirección de la Raspberry Pi. Por ejemplo, si la Pi tiene IP `192.168.1.100` y usaste el puerto 1885, ve a: **http://192.168.1.100:1885/**. Debería cargar la interfaz de The Things Stack (The Things Industries).

   - Inicia sesión con las **credenciales por defecto** que trae esta instalación: **usuario:** `admin`, **contraseña:** `changeme ([the-things-stack-docker/README.md at master · xoseperez/the-things-stack-docker · GitHub](https://github.com/xoseperez/the-things-stack-docker/blob/master/README.md#:~:text=Point your browser to the,to log in as administrator))】. *(Estas credenciales son creadas automáticamente por la imagen xoseperez/the-things-stack para facilitar el inicio.)*
   - Importante: por seguridad, **cambia la contraseña del usuario administrador inmediatamente**. Para hacerlo, ve al menú de la console (esquina superior derecha) donde aparece "admin", entra en *User Management* o *Profile* y define una nueva contraseña segura. Así evitarás que alguien más acceda con la contraseña conocida.

5. **Configurar parámetros básicos en The Things Stack:** Ahora estás dentro de la consola web de TTS. Algunas configuraciones que puedes hacer:

   - Verifica en la sección *Network* que la instancia esté funcionando en modo single-tenant sin necesidad de licencias (debería, ya que es la versión open source).
   - Puedes ajustar la información de servidor (por ejemplo, habilitar/inhabilitar el registro de Packet Broker, pero para una red local privada no es necesario tocar eso).
   - Lo más importante vendrá más adelante: registrar los **Gateways** y **Devices** (nodos) en la consola, una vez tengamos el gateway configurado y las claves de los dispositivos. Esto lo haremos en las siguientes secciones.

¡Felicidades! Ya tienes un servidor LoRaWAN funcionando localmente en tu Raspberry Pi. En términos de uso de recursos, ten en cuenta que TTS es una aplicación pesada (incluye servidor web, APIs, gestión de dispositivos, etc.), por lo que en una Raspberry Pi 3 puede consumir una buena parte de la CPU y memoria. Sin embargo, para un laboratorio con pocos dispositivos debe funcionar adecuadament ([GitHub - xoseperez/the-things-stack-docker: The Things Stack LoRaWAN Network Server (Open Source Edition) on a Raspberry Pi using docker](https://github.com/xoseperez/the-things-stack-docker#:~:text=Introduction))】.

Antes de poder enviar/recibir datos, necesitamos poner en marcha el **gateway LoRa** (el módulo RAK2245 en la Raspberry Pi) y registrar ese gateway en The Things Stack.

## Configuración de la pasarela LoRaWAN en la Raspberry Pi

En este paso, configuraremos la Raspberry Pi con el módulo concentrador LoRa (RAK2245 u otro) para que funcione como gateway y se comunique con nuestro servidor TTS. Básicamente, debemos instalar el software de **packet forwarder** (reenvío de paquetes LoRa) y apuntarlo a nuestro servidor local.

RAKwireless proporciona una herramienta que facilita esta configuración en Raspberry Pi OS. Usaremos el instalador **rak_common_for_gateway** de RAK, que detecta el modelo (RAK2245) y configura automáticamente el packet forwarder (basado en Semtech UDP) y utilidades como `gateway-config`.

Sigue los pasos a continuación **en la Raspberry Pi** (con el módulo RAK2245 ya montado sobre los pines GPIO y su antena conectada):

1. **Habilitar interfaces de hardware:** (Este paso lo hicimos en raspi-config, pero por si acaso) Asegúrate de haber activado SPI e I2C en la Raspberry Pi (ya se indicó en la sección anterior). Sin SPI habilitado, la Pi no podrá comunicarse con el concentrador LoRa vía GPIO.

2. **Instalar dependencias e instalador RAK:** Ejecuta los siguientes comandos para clonar el repositorio de RAK y lanzar su instalado ([GitHub - RAKWireless/rak_common_for_gateway](https://github.com/RAKWireless/rak_common_for_gateway#:~:text=step3 %3A Clone the installer,help))】:

   ```bash
   sudo apt update && sudo apt install -y git
   git clone https://github.com/RAKWireless/rak_common_for_gateway.git ~/rak_common_for_gateway
   cd ~/rak_common_for_gateway
   sudo ./install.sh
   ```

   El script `install.sh` te guiará por una serie de menús en la terminal:

   - Primero te preguntará el modelo de gateway: en nuestro caso, elige **RAK2245** (probablemente la opción "1" ([GitHub - RAKWireless/rak_common_for_gateway](https://github.com/RAKWireless/rak_common_for_gateway#:~:text=step4 %3A Next you will,select the corresponding hardware model))】. Esto asegura que instale el software específico para RAK2245 Pi HAT.
   - El instalador configurará los paquetes necesarios (como el forwarder LoRa Semtech) y podrá instalar también ChirpStack si uno lo elige. Por defecto, RAK suele habilitar un servidor LoRaWAN ChirpStack local, pero **nosotros planeamos usar The Things Stack**, así que luego ajustaremos eso.
   - Espera a que complete la instalación (step5/step6 en los mensajes). Finalmente, el sistema se reiniciará o te sugerirá reiniciar (step6: "reboot your gateway ([GitHub - RAKWireless/rak_common_for_gateway](https://github.com/RAKWireless/rak_common_for_gateway#:~:text=Please enter 1,the model))】).

3. **Configurar la pasarela con `gateway-config`:** Tras reiniciar, vuelve a conectarte a la Raspberry Pi. RAK provee la herramienta `gateway-config` para configurar parámetros de la pasarela. Ejecútala con:

   ```bash
   sudo gateway-config
   ```

   Aparecerá un menú de texto interactivo (usa las flechas y Enter para navegar). Las opciones principales incluyen cambiar contraseña, configurar el concentrador LoRa, reiniciar servicios, editar archivos, configurar WiFi, et ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=1. Set pi password ,settings in order to connect))】. Realiza lo siguiente:

   - **Set up RAK Gateway LoRa Concentrator (opción 2):** Dentro de esta opción podrás seleccionar la **banda de frecuencia** y el **servidor LoRaWAN** al que conectars ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=You can choose one of,Servers here%3A TTN or ChirpStack))】.
     - Elige la banda correspondiente a tu región (por ejemplo **EU868** para Europa, **US915** para EE.UU., etc.).
     - Luego te preguntará el servidor: las dos opciones típicas son **TTN (The Things Network)** o **ChirpStack (local)* ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=You can choose one of,Servers here%3A TTN or ChirpStack))】. Puesto que estamos usando The Things Stack local (que es similar a tener un servidor privado), puedes seleccionar **ChirpStack** para indicar que usarás un servidor privado. Esta opción suele configurar la pasarela para apuntar a `localhost` (la propia Raspberry Pi) en el puerto UDP 1700. Si eliges TTN, intentaría conectarse a los servidores públicos de The Things Network (no es lo que queremos en este caso).
     - Confirma la configuración. El menú mostrará un mensaje de éxito al guardar la nueva frecuencia y servidor.
   - **Configurar conexión de red del gateway:** Asegúrate de que la Raspberry Pi esté conectada a Internet (por Ethernet o configurando WiFi en la opción 5 del menú si lo necesitas). Esto es necesario si quisieras conectar a TTN. En nuestro caso, al ser servidor local, basta con que la Pi tenga conectividad consigo misma (lo cual siempre tiene). Pero si planeas monitorear o administrar la Pi remotamente, conviene que esté en tu red WiFi doméstica (puedes configurar la WiFi en *Configure Wi-Fi* desde este menú).
   - Sal del menú y elige la opción de **Restart packet-forwarder** para reiniciar el servicio de forwarder (o simplemente reinicia la Raspberry Pi). Esto aplicará los cambios.

4. **Verificar que el packet forwarder esté enviando datos:** El packet forwarder de Semtech típicamente corre como un servicio del sistema. Puedes ver su log con:

   ```bash
   sudo journalctl -f -u ttn-gateway
   ```

   (En algunas imágenes el servicio se llama `ttn-gateway` o `packet-forwarder`.) Deberías ver líneas indicando que el concentrador está encendido, y mensajes del tipo “GPS module” o “SX130X” inicializados. Cuando los nodos empiecen a transmitir, aquí verás los paquetes recibidos.

   Si algo falla en este punto (por ejemplo, que el concentrador no inicie), revisa que el módulo RAK esté bien colocado y que habilitaste SPI/I2C correctamente. La herramienta `gateway-config` simplifica mucho este proceso de configuración del concentrador en la Raspberr ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=Assuming you have successfully logged,command in the command line)) ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=You can choose one of,Servers here%3A TTN or ChirpStack))】.

Ahora el gateway LoRaWAN (pasarela) debería estar operativo en la Raspberry Pi. **Pero aún falta registrar el gateway en The Things Stack** para que el servidor lo reconozca y acepte sus paquetes.

1. **Registrar el Gateway en The Things Stack (TTS):** Ve a la consola web de The Things Stack (http://IP_RPi:1885/) que dejamos funcionando. Inicia sesión si no lo hiciste.

   - Navega a la sección **Gateways** (en el menú principal). Haz clic en "**Register Gateway**" para añadir una nueva pasarel ([Adding Gateways | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/hardware/gateways/concepts/adding-gateways/#:~:text=,Console))】.
   - Completa el formulario de registro del gateway:
     - **Gateway EUI:** es el identificador único de la pasarela. Debes obtenerlo del gateway. Puedes encontrarlo ejecutando `gateway-version` en la Raspberry Pi, como sugiere RAK (este comando suele mostrar el EUI ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=There is also another way,below in the command line))】. También aparece en el menú de `gateway-config` o en los logs de inicio. Será un número hexadecimal de 16 dígitos (por ejemplo, **B827EBFFFE123456**). Introdúcelo en el campo EUI (sin guiones).
     - **Gateway ID:** un nombre identificador a tu elección (ejemplo: "raspi-gateway-1"). Este es un nombre amigable sin espacios.
     - **Frequency Plan:** selecciona el plan de frecuencias correspondiente (ej: EU_863_870 para EU868, US_902_928_FSB_2 para US915, etc.). Debe coincidir con lo que configuraste en el gateway.
     - **Gateway Server address:** si pregunta (en TTS open source puede que no pregunte explícitamente), sería la dirección del servidor a donde conectará. En nuestro caso, es la misma Raspberry Pi. Si TTS está en la misma máquina, "localhost" o la IP local valen. Pero dado que el forwarder ya está apuntando a localhost, este ajuste puede no ser necesario en la consola (TTS simplemente espera paquetes en su puerto).
     - Deja las otras opciones por defecto a menos que sepas cambiarlas (p.ej., el gateway no tiene autenticación específica de servidor UDP).
     - Guarda/crea el gateway.
   - Una vez registrado, en la consola de TTS el gateway aparecerá con su EUI y como **conectado** (Connected) si todo está bien. Puede tardar unos segundos en reflejar el estado. Básicamente, cuando el packet forwarder envía paquetes "PUSH_DATA" al servidor TTS, éste reconoce el EUI y lo marca en línea. En la sección de **Live Data** del gateway en la consola de TTS deberías ver los paquetes uplink cuando los nodos comiencen a transmitir.

   > 💡 *Consejo:* The Things Stack Community Edition (open source) **no requiere autenticación para gateways usando el protocolo Semtech UDP**. A diferencia del protocolo LNS (Basics Station) que sí usa una clave, el Semtech UDP forwarder simplemente identifica por EUI. Por ello, asegúrate de que el EUI esté correcto y registrado. En un despliegue local cerrado, esta simplicidad está bien, pero ten en cuenta que no hay cifrado en el enlace Gateway <-> Server con este protocolo. Para mayor seguridad se podría usar el protocolo Basics Station, pero es más complejo de configurar. En nuestro caso, mantener Semtech UDP es suficiente para iniciar pruebas.

Llegados a este punto, tenemos nuestra infraestructura LoRaWAN local completa: la **pasarela** (Raspberry Pi + RAK2245) comunicándose con el **Network Server** (The Things Stack en Docker). Cuando los nodos LoRaWAN envíen mensajes, llegarán a la Pi, el packet forwarder los pasará a TTS, y podremos verlos en la consola. Resta configurar y programar los **nodos ESP32 (dispositivos finales)** para que se unan a la red y envíen datos útiles.

## Programación de los módulos ESP32 como nodos LoRaWAN (MicroPython)

Para los nodos utilizaremos placas ESP32 con módulo LoRa incorporado. Las programaremos con **MicroPython**, un lenguaje de scripting (derivado de Python) muy adecuado para prototipos y educación, que corre en microcontroladores. MicroPython nos permite escribir código de forma rápida sin necesidad de compilar, y es más fácil de entender para principiantes que el código C/C++ típico del Arduino.

En esta sección haremos lo siguiente:

- Instalar MicroPython en las placas ESP32 LoRa.
- Escribir un script de ejemplo que envíe datos mediante LoRaWAN al servidor (nuestra pasarela).
- Explicar cómo “provisionar” o configurar los nodos de forma cómoda, incluso inalámbricamente (vía Bluetooth o WiFi AP), para no tener que reprogramar el código cada vez que cambie una clave o parámetro.

### Instalación de MicroPython en el ESP32

**¿Por qué MicroPython?** Porque nos permite usar Python (un lenguaje sencillo) en el ESP32. Esto es genial si no estás familiarizado con C/C++. Por ejemplo, un autor señala: *"como no estoy muy familiarizado con C(++), preferí usar MicroPython; pero antes de poder copiar archivos .py al dispositivo, necesitas flashear el firmware MicroPython en el ESP32 ([How I sent my first LoRaWAN message to The Things Network using a TTGO ESP32 & Micropython | by Joost Buskermolen | Medium](https://medium.com/@JoooostB/how-i-send-my-first-lorawan-message-to-the-things-network-using-a-ttgo-esp32-micropython-a3fe447fff82#:~:text=As I’m not too familiar,flash storage of the ESP32))9】. Esa es la idea: primero cargaremos el firmware MicroPython en cada ESP32, luego subiremos nuestros scripts Python.

Los pasos para instalar MicroPython en una placa ESP32 son:

1. **Descargar el firmware MicroPython:** Ve a la página oficial de MicroPython y busca la sección de descargas para ESP32. Puedes usar el firmware genérico para ESP32. Por ejemplo, un archivo `.bin` llamado `esp32-<version>.bin` (elige la última versión estable, y si tu placa tiene 4MB de flash, la estándar es suficiente; si tiene SPIRAM, quizá haya un firmware específico “spiram”).

   - Página de descargas: https://micropython.org/download/esp32/ (busca un .bin apropiado, e.g. *ESP32 Generic ([How I sent my first LoRaWAN message to The Things Network using a TTGO ESP32 & Micropython | by Joost Buskermolen | Medium](https://medium.com/@JoooostB/how-i-send-my-first-lorawan-message-to-the-things-network-using-a-ttgo-esp32-micropython-a3fe447fff82#:~:text=flashing MicroPython,should take about a minute))9】.

2. **Conectar el ESP32 al PC:** Usa un cable USB para conectar la placa de desarrollo ESP32 a tu ordenador. Debería detectarse como un puerto serie (en Windows un COMx, en Linux/macOS algo como `/dev/ttyUSB0` o `/dev/tty.SLAB_USBtoUART` dependiendo del chip USB->Serial de la placa).

3. **Borrar flash (opcional pero recomendado):** Abre una terminal/símbolo del sistema en tu PC y ejecuta el comando de **esptool.py** para borrar la flash del ESP32:

   ```bash
   esptool.py --chip esp32 --port <PUERTO> erase_flash
   ```

   Reemplaza `<PUERTO>` por el nombre del puerto detectado (ej: `COM3` en Windows, `/dev/ttyUSB0` en Linux). `esptool.py` es una herramienta de Python para programar ESP32; si no la tienes instalada, instálala con `pip3 install esptoo ([How I sent my first LoRaWAN message to The Things Network using a TTGO ESP32 & Micropython | by Joost Buskermolen | Medium](https://medium.com/@JoooostB/how-i-send-my-first-lorawan-message-to-the-things-network-using-a-ttgo-esp32-micropython-a3fe447fff82#:~:text=Installing the tool is as,installed both Python and pip))5】. Borrar la flash asegura que no queden restos de firmwares anteriores.

4. **Flashear MicroPython:** Ahora carga el firmware .bin de MicroPython al ESP32 con esptool:

   ```bash
   esptool.py --chip esp32 --port <PUERTO> --baud 460800 write_flash -z 0x1000 esp32-X.Y.Z.bin
   ```

   (Cambia `esp32-X.Y.Z.bin` por el nombre exacto del archivo que descargaste, p. ej. `esp32-20230117-v1.19.1.bin`). La dirección `0x1000` es la posición típica de arranque para ESP32. La velocidad 460800 acelera la transferencia (puedes usar 115200 si tienes problemas). Si todo va bien, verás un mensaje de que se escribió exitosamente. Ahora la placa debería reiniciar con MicroPython instalado.

5. **Verificar prompt de MicroPython:** Para confirmar, puedes abrir un terminal serial a la placa (con programa como PuTTY, TeraTerm o screen). Configura el puerto y velocidad 115200 baudios. Al conectarte, deberías ver un prompt que dice `>>>` (el REPL de MicroPython). Si escribes `print("hola")` y presionas Enter, debería responder con `hola`. ¡Tu ESP32 ya ejecuta MicroPython!

   Otra manera más cómoda: puedes utilizar el **IDE Thonny** ([https://thonny.org](https://thonny.org/)). Thonny es un entorno Python para PC que reconoce microcontroladores con MicroPython. Desde Thonny puedes abrir una consola interactiva del ESP32 y también transferir archivos fácilmente. Si eres principiante, Thonny puede simplificar mucho las cosas (selecciona MicroPython/ESP32 en la esquina inferior derecha y el puerto correspondiente, luego abre la consola).

### Script de ejemplo: envío de datos LoRaWAN en MicroPython

Ahora viene la parte importante: hacer que el ESP32 se una a la red LoRaWAN y envíe datos. Para ello, necesitaremos:

- Las **credenciales LoRaWAN** del dispositivo (DevAddr, NwkSKey, AppSKey si usamos ABP; o AppKey, DevEUI, AppEUI si usamos OTAA).
- Un código en MicroPython que configure la radio LoRa y envíe un paquete usando esas claves.

Para simplificar, usaremos el método **ABP (Activation By Personalization)** en nuestros nodos. ABP nos permite definir directamente la dirección del dispositivo y las claves de sesión, evitando el proceso de join OTAA. Es menos seguro a largo plazo (porque las claves son fijas), pero para pruebas locales es más fácil y rápido (no dependemos de mensajes de join accept). Podemos deshabilitar los checks de frame counter para no tener problemas si reiniciamos el nodo durante pruebas.

**Paso 1: Registrar el dispositivo en TTS (ABP)** – Ve a la consola de The Things Stack, sección **Applications**. Crea una aplicación (ej: "mi-app-sensores"). Dentro de la aplicación, elige **+ Add end device**. Puedes cargar una plantilla LoRaWAN, pero aquí hazlo manual:

- Elige LoRaWAN version MAC 1.0.3 (por ejemplo) y Regional Parameters PHY correspondiente (e.g. EU868).
- Marca la opción de **Activation by Personalization (ABP)** en lugar de OTAA.
- Deja que genere automáticamente un DevAddr (o pon uno, asegurándote que los primeros bits correspondan a la red privada, típicamente DevAddr empieza con 0x26 algo para redes TTN, pero en una privada puedes usar cualquier rango no conflictivo).
- Obtén el **DevAddr**, **NwkSKey** y **AppSKey** que asigna. Apunta estos valores en formato hexadecimal (los verás en la consola al completar el registro). También anota el **DevEUI** (aunque para ABP no se usa en la comunicación, pero sirve de identificador en la consola).
- En la configuración del dispositivo en la consola TTS, busca ajustes como “Frame counter checks” y **desactívalos** (esto está en la pestaña de *Network Layer*, disable frame counter checks). Así evitas que el servidor ignore tus mensajes si reseteas el contador al reiniciar el nodo durante prueb ([How I sent my first LoRaWAN message to The Things Network using a TTGO ESP32 & Micropython | by Joost Buskermolen | Medium](https://medium.com/@JoooostB/how-i-send-my-first-lorawan-message-to-the-things-network-using-a-ttgo-esp32-micropython-a3fe447fff82#:~:text=Immediately after creating the device%2C,to modify the following values))8】.
- Guarda la configuración. Ya tienes las claves necesarias para el nodo.

**Paso 2: Código MicroPython en el ESP32** – Ahora vamos a cargar un script al ESP32 con MicroPython que use esas claves para enviar un paquete. Para manejar LoRaWAN en MicroPython, aprovecharemos una biblioteca llamada **uLoRa** (micro LoRa) que es un port de la librería TinyLoRa de Adafru ([GitHub - fantasticdonkey/uLoRa: LoRa / LoRaWAN + TTN for MicroPython (ESP32)](https://github.com/fantasticdonkey/uLoRa#:~:text=Objecive))1】. Esta librería se compone de un par de módulos Python (`ulora.py`, `ulora_encryption.py`, etc.) que se ocupan de la comunicación LoRaWAN de bajo nivel (configurar el radio SX1276, formar el paquete LoRaWAN con las cabeceras correctas, cifrar el payload con AES128, etc.).

En concreto, uLoRa permite hacer envío de tipo **unconfirmed uplink** en ABP fácilmente. Vamos a usarla.

**Obtén la librería uLoRa:** Puedes encontrar el código en GitHub (repositorio "fantasticdonkey/uLoRa"). Para no complicarnos, aquí proporcionamos un script completo que incluye lo necesario. Podrás copiarlo tal cual a tu ESP32.

A continuación un **ejemplo de script MicroPython** para un nodo LoRaWAN ABP. Este script envía periódicamente (cada minuto) un mensaje con un valor de ejemplo (por ejemplo, lectura de un sensor simulada). Asegúrate de reemplazar las claves por las tuyas de TTS:

```python
# LoRaWAN ABP node example for ESP32 (MicroPython)

from machine import SPI, Pin
import time
import ubinascii

# --- Configura los pines según tu placa ESP32 LoRa ---
# Estos valores son para Heltec WiFi LoRa 32 V2 (pueden variar en otra placa):
LORA_CS  = 18    # Chip select del SX1276
LORA_RST = 14    # Reset del SX1276
LORA_MOSI = 27   # SPI MOSI
LORA_MISO = 19   # SPI MISO
LORA_SCK = 5     # SPI SCK
LORA_IRQ = 26    # DIO0 pin del SX1276 (indica fin de TX/RX)

# --- Claves LoRaWAN (ABP) proporcionadas por The Things Stack ---
DEV_ADDR = bytearray([0x26, 0x01, 0x1A, 0xXX])  # Reemplaza por tu DevAddr (4 bytes en hex MSB)
NWK_SKEY = bytearray([0xAA, 0xBB, 0xCC, 0x... ])  # Reemplaza con tu Network Session Key (16 bytes)
APP_SKEY = bytearray([0x11, 0x22, 0x33, 0x... ])  # Reemplaza con tu App Session Key (16 bytes)

# (Puedes copiar/pegar los valores hexadecimales tal como los da la consola TTN, separándolos con comas)

# --- Configura la región ---
LORA_REGION = 'EU'   # 'EU' para EU868, 'US' para US915, etc.

# Importa la librería uLoRa (deberás tener los módulos ulora.py y ulora_encryption.py en la placa)
from ulora import TTN, uLoRa

# Configuración de TTN/LoRaWAN con las claves
ttn_config = TTN(DEV_ADDR, NWK_SKEY, APP_SKEY, country=LORA_REGION)

# Inicializa SPI
spi = SPI(1, baudrate=10000000, polarity=0, phase=0, bits=8,
          firstbit=SPI.MSB, sck=Pin(LORA_SCK, Pin.OUT),
          mosi=Pin(LORA_MOSI, Pin.OUT), miso=Pin(LORA_MISO, Pin.IN))

# Pin para Chip Select (CS) del LoRa
cs = Pin(LORA_CS, Pin.OUT, value=1)
# Pin de Reset del LoRa
rst = Pin(LORA_RST, Pin.OUT, value=1)
# Pin de interrupción DIO0
irq = Pin(LORA_IRQ, Pin.IN)

# Crea instancia LoRa (usando la config de TTN y los pines)
lora = uLoRa(spi=spi, cs=cs, irq=irq, rst=rst, ttn_config=ttn_config)

# Contador de tramas (frame counter)
frame_counter = 0

# Bucle principal: enviar un mensaje cada 60 segundos
while True:
    # Ejemplo: payload con un número incremental (2 bytes) 
    # (En un caso real podría ser una lectura de sensor)
    value = frame_counter & 0xFFFF  # solo 2 bytes inferiores
    payload = value.to_bytes(2, 'big')  # convierte int a bytes (2 bytes, big-endian)
    
    # Enviar por LoRaWAN
    try:
        lora.send_data(payload, len(payload), frame_counter)
        print("Paquete enviado:", ubinascii.hexlify(payload), "Contador:", frame_counter)
        frame_counter += 1
    except Exception as e:
        print("Error al enviar:", e)
    
    # Esperar 60 segundos antes del siguiente envío
    time.sleep(60)
```

Algunas notas sobre este código:

- Definimos los pines basándonos en una placa Heltec LoRa. Si usas TTGO LoRa32 v1/v2, los pines podrían ser distintos. Consulta la documentación de tu placa para SPI y DIO0. Por ejemplo, en algunas TTGO, DIO0 está en GPIO 35. Asegúrate de ajustarlo.
- Usamos las claves en formato **MSB** (most significant byte first). TTS entrega las claves en MSB por defec ([How I sent my first LoRaWAN message to The Things Network using a TTGO ESP32 & Micropython | by Joost Buskermolen | Medium](https://medium.com/@JoooostB/how-i-send-my-first-lorawan-message-to-the-things-network-using-a-ttgo-esp32-micropython-a3fe447fff82#:~:text=will be shown,later in our code))9】. Si las tienes en formato LSB, inviértelas o presiona el botón de intercambio en la consola de TTS.
- La librería uLoRa (debe estar cargada en la placa). ¿Cómo cargarla? Puedes obtener los archivos `ulora.py` y `ulora_encryption.py` del repositorio GitHub y subirlos a tu ESP32 (por FTP, Thonny o ampy). Por simplicidad, podrías copiar el contenido de esos archivos y pegarlos al principio de tu script, pero lo mejor es cargarlos como módulos separados para reutilización. En Thonny, puedes arrastrar los archivos al sistema de archivos de la placa.
- El objeto `TTN` es inicializado con DevAddr, NwkSKey, AppSKey y la región. Luego creamos el objeto `uLoRa` pasando la configuración TTN y los pines/SPI. Internamente esto configura el chip de radio SX1276 a la frecuencia, potencia y SF predeterminados para esa región (por defecto SF7BW125, que está bien para empezar).
- **frame_counter:** en ABP, es crucial llevar la cuenta del contador de trama manualmente. En el ejemplo, usamos una variable `frame_counter` que incrementamos en cada envío y pasamos a `send_data()`. The Things Stack espera que cada paquete ABP tenga contador incrementado (salvo que desactivamos el check, pero igual lo incrementamos para buen hábito).
- El payload que enviamos es un número de 2 bytes (podría ser, por ejemplo, una lectura de sensor simulada). Lo convertimos a bytes y lo enviamos. En TTS, puedes definir un *Payload Formatter* para decodificar esos bytes a valores legibles si quieres (por ahora, veremos los datos en hex).
- Ponemos el código en un bucle infinito con `time.sleep(60)` para enviar cada minuto. Puedes ajustarlo a tu necesidad (pero recuerda que LoRaWAN tiene duty cycle y fairness: no envíes con intervalos demasiado cortos).

**Paso 3: Cargar y ejecutar el código en el ESP32** – Usa tu método preferido (Thonny IDE, por ejemplo):

- Conecta a la consola MicroPython de la placa.
- Crea un nuevo archivo, pega el código, modifica las claves y pines según corresponda.
- Guarda el archivo en la placa, por ejemplo como `main.py`. (En MicroPython, si guardas el script como `main.py`, se ejecutará automáticamente al reiniciar la placa).
- Reinicia el ESP32 (pulsa reset o en Thonny selecciona *Stop/Restart*). Deberías ver en la consola mensajes indicando "Paquete enviado: ..." cada minuto.

Si todo está configurado correctamente, el nodo debería comenzar a transmitir sus paquetes LoRaWAN. La pasarela los recibirá y los pasará a TTS, donde se asociarán con tu dispositivo registrado (gracias al DevAddr y las claves coincidentes). Puedes verificar en la consola de TTS:

- Ve a tu aplicación, entra en el dispositivo correspondiente y abre la pestaña de **Live data**. Deberías ver eventos de **up-link** con los datos en hexadecimal. Por ejemplo, `payload: 0005` (cada vez con un número diferente en hex, que corresponde a tu contador) y `FCnt` (frame counter) incrementándose.
- También en la vista del gateway en TTS verás los uplinks llegando, con la indicación del EUI del gateway, RSSI, SNR, etc.

¡Enhorabuena! Has conseguido que un nodo ESP32 envíe datos vía LoRaWAN a tu propia pasarela y servidor. Desde aquí, podrías conectar esos datos a tu aplicación final.

### Provisión y configuración de nodos (Bluetooth / Wi-Fi AP)

Cuando tienes pocos dispositivos, configurar las claves en el código (como hicimos con ABP) es manejable. Pero en escenarios más grandes o en producción, querrás una forma más cómoda de **provisionar** dispositivos sin reprogramarlos uno por uno. Aquí discutimos brevemente dos métodos posibles con ESP32:

- **Vía Bluetooth (BLE):** El ESP32 puede actuar como dispositivo Bluetooth Low Energy. Podrías programar un modo de configuración en el que el ESP32 se anuncie por BLE, y mediante una app móvil enviarle parámetros (por ejemplo, las claves LoRaWAN, o credenciales WiFi si necesitara). MicroPython tiene soporte básico de BLE (usando el módulo `bluetooth`). Podrías, por ejemplo, implementar un servicio GATT donde escribiendo ciertas características almacenes el DevAddr, NwkSKey, AppSKey en la NVM (por ejemplo en la memoria Flash del ESP32, quizás en un archivo de configuración). Una vez enviados, el dispositivo sale del modo configuración y comienza a operar normalmente. Este proceso permitiría a un usuario final configurar un nodo vía smartphone sin tocar el código.
- **Vía Wi-Fi AP (Access Point):** Otra alternativa es hacer que el ESP32, al inicio, si detecta por ejemplo un botón presionado o que no tiene claves guardadas, levante una red Wi-Fi propia (el ESP32 puede crear un AP). El dispositivo crearía una Wi-Fi llamada, por ejemplo, "NodoLoRaWAN-Config", a la que el usuario se conecta con su teléfono. Luego, el ESP32 podría servir una pequeña página web (usando sockets TCP en MicroPython) donde el usuario introduce los parámetros (claves LoRaWAN, etc.). Al enviar el formulario, el ESP32 guarda esos datos y reinicia en modo normal. Este método de “config portal” es común en IoT para configurar Wi-Fi; aquí lo reutilizamos para LoRaWAN. La ventaja es que no requiere una app móvil especializada, solo un navegador web. La desventaja es que consume más energía y es más complejo en el microcontrolador.

Ambas opciones requieren algo más de programación, pero son viables. En nuestro contexto educativo, mencionamos esto para conocer que existen caminos para no tener que **hardcodear** las claves siempre. Por simplicidad en este proyecto, hemos configurado directamente en código las claves del nodo.

En un entorno real, también podrías combinar LoRaWAN OTAA con alguna forma de provisionado de AppKeys más segura. Pero OTAA en MicroPython es más complicado porque tendrías que implementar la recepción del join-accept. La librería uLoRa por ahora se enfoca en ABP (a fecha de la referencia, solo uplinks no confirmado ([GitHub - fantasticdonkey/uLoRa: LoRa / LoRaWAN + TTN for MicroPython (ESP32)](https://github.com/fantasticdonkey/uLoRa#:~:text=The project is currently being,in a limited capacity using))2】.

## Integración de The Things Stack con la aplicación mediante MQTT/HTTP

Hasta ahora hemos logrado la comunicación **nodo -> pasarela -> servidor (TTS)**. Los datos llegan a The Things Stack, pero seguramente querrás utilizarlos en tu propia aplicación (por ejemplo, mostrar medidas en una base de datos, dashboard, enviarlos a un servicio web, etc.). Para esto, The Things Stack ofrece **integraciones** muy prácticas, principalmente:

- **Servidor MQTT integrado:** The Things Stack actúa como un broker MQTT al que te puedes suscribir para recibir los datos de los dispositivos en tiempo re ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=The Things Stack exposes an,to uplinks or publish downlinks))9】. MQTT es un protocolo ligero de publicación/suscripción usado mucho en IoT. Usando MQTT, cualquier aplicación tuya puede recibir mensajes de los sensores (uplinks) o incluso enviar comandos de bajada (downlinks) publicando en ciertos topics.
- **Integraciones HTTP/Webhooks:** Alternativamente, TTS permite configurar webhooks que envían una petición HTTP POST a tu servidor cada vez que llega un dato. También podrías usar la API HTTP/REST de TTS para consultar datos, aunque MQTT suele ser más sencillo para streaming.

Nos centraremos en MQTT, por ser muy directo en despliegues locales.

**Usando MQTT para obtener los datos:**

La instancia The Things Stack que instalamos ya expone un broker MQTT en el puerto 1883 (lo mapeamos en Docker). Vamos a suscribirnos a los mensajes:

1. **Crear credenciales MQTT (API Key):** En la consola de TTS, ve a tu aplicación y en la pestaña *Integrations > MQTT* encontrarás la información para conect ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=Creating an API Key))6】. Por defecto en TTS open source, el **servidor MQTT** es la misma dirección de tu instalación (ejemplo: `192.168.1.100` puerto `1883`). El **usuario** de MQTT será el ID de la aplicación. Necesitarás generar una **API Key** para autenticar. En esa página, haz clic en "Generate new API key" y selecciona permisos de al menos `Read` en dispositivos y aplicaciones (en Community Edition suele generar una con todos los permisos por simplicida ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=Image%3A MQTT connection information))3】. Copia el API Key generado (un string largo) y guárdalo.

2. **Conectarse con un cliente MQTT:** Puedes usar cualquier cliente. Por ejemplo, desde la Raspberry Pi misma (o tu PC) instalar **Mosquitto** cliente:

   - En Raspberry Pi: `sudo apt-get install -y mosquitto-clients`. Esto proporciona el comando `mosquitto_sub` y `mosquitto_pub`.

   - Para probar, suscríbete a todos los tópicos de la aplicación:

     ```bash
     mosquitto_sub -h 127.0.0.1 -p 1883 -u "<AppID>" -P "<API_KEY>" -t "#" -v
     ```

     Donde `<AppID>` es el ID de tu aplicación en TTS, y `<API_KEY>` la clave generada. `-t "#"` indica suscripción a *todos los topics*. `-v` hace que muestre tanto el tópico como el mensaje.

   - Si todo va bien, verás aparecer mensajes cada vez que llega un uplink. El tópico tendrá una forma parecida a:
      `v3/<AppID>@<tenant>/devices/<DeviceID>/up` (en la edición open source sin multi-tenant, probablemente sea `v3//devices//up ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=For example%2C for an application,ID for The Things Network))9】. El payload del mensaje es un JSON con toda la información del uplink: datos en base64, puertas de enlace que lo oyeron, potencias, etc. Por ejemplo:

     ```json
     {
       "end_device_ids": { ... },
       "uplink_message": {
         "frm_payload": "ABCD", 
         "decoded_payload": { ... },
         "rx_metadata": [ {... gateway_ids... rssi... snr...} ],
         ...
       }
     }
     ```

     Lo importante es `frm_payload`, que es el payload en base64. Ese "ABCD" por ejemplo corresponde a los bytes enviados. Puedes decodificarlo o, mejor, usar un **payload formatter** en TTS para que ya te envíe `decoded_payload` con valores numéricos. En la consola TTS, en tu aplicación > Payload Formatters, puedes añadir una función decoder (en JavaScript) que decodifique los bytes. Por ejemplo, si el payload son 2 bytes que representan un número, un decoder JS podría convertirlo a un entero.

   - Tu aplicación puede en lugar de mosquitto_sub, usar una librería MQTT en el lenguaje que prefieras (Python paho-mqtt, Node.js mqtt, etc.) y suscribirse al mismo topic. Con eso, integras los datos en tiempo real. Por ejemplo, podrías tener un script Python que cada vez que llega un mensaje lo inserta en una base de datos o lo muestra en pantalla.

3. **Integración HTTP (webhook) – alternativa:** Si no quieres mantener una conexión MQTT abierta, puedes configurar en TTS un **Webhook** (Integrations > Webhooks) que envíe un POST a tu servidor. Por ejemplo, si tienes un server local en Node-RED o en una aplicación web, configuras la URL y TTS enviará el JSON allí. TTS incluso tiene plantillas para integraciones con ThingsBoard, Datacake, InfluxDB, etc., pero en un comienzo MQTT es más universal.

**Enviar comandos a los nodos (downlink):** MQTT también permite publicar mensajes hacia los dispositivos (por ejemplo para encender un LED, etc.). El topic para downlink sería algo como `v3/<AppID>/devices/<DeviceID>/down/push` con un JSON que incluya el payload que quieres enviar en base64 y el fport. Esto está documentado en The Things Stack docs. Ten en cuenta que para que el nodo reciba downlinks, debe escuchar después de sus uplinks (ventanas RX1/RX2). Nuestra implementación ABP básica envía uplinks unconfirmed, y podría recibir downlinks (por ejemplo, podrías enviar un mensaje al nodo para cambiar un parámetro). Implementar la recepción en MicroPython requeriría leer interrupciones DIO1/DIO2 y decodificar, lo cual es avanzado. Para propósitos iniciales, nos centramos en los uplinks (sensor -> servidor).

Resumiendo, con MQTT tienes una **integración en tiempo real** muy cómoda: tu servidor local de TTS hace de broker y tu aplicación se suscribe para obtener los dat ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=The Things Stack exposes an,to uplinks or publish))4】. No necesitas terceros, todo ocurre dentro de tu red local, lo cual además es bueno por privacidad y latencia mínima.

## Seguridad básica recomendada 🔒

Al montar cualquier sistema IoT, especialmente uno conectado a una red, es importante considerar la seguridad. A continuación, algunas prácticas básicas que deberías aplicar en este proyecto:

- **Cambiar credenciales por defecto:** Ya lo mencionamos, pero vale reiterar: no dejes la contraseña por defecto del usuario **pi** en la Raspberry (cámbiala con `passwd`). Asimismo, cambia la contraseña del usuario **admin** de The Things St ([the-things-stack-docker/README.md at master · xoseperez/the-things-stack-docker · GitHub](https://github.com/xoseperez/the-things-stack-docker/blob/master/README.md#:~:text=Point your browser to the,to log in as administrator))07】. Estas contraseñas por defecto son bien conocidas, y cualquiera en la red podría acceder si las detecta.
- **Mantener el sistema actualizado:** Ejecuta `sudo apt update && sudo apt upgrade` periódicamente en la Raspberry Pi para aplicar parches de seguridad del sistema operativo. Igualmente, mantener Docker y las imágenes actualizadas (puedes recrear los contenedores con versiones nuevas de TTS cuando salgan).
- **Red cerrada o VPN:** Si tu pasarela/servidor TTS no necesita ser accedido desde fuera de tu red local, mantenlo en una red local cerrada (por ejemplo, solo accesible dentro de tu WiFi doméstica). Evita exponer la interfaz de The Things Stack directamente a Internet si no es necesario. Si requieres acceso remoto, considera montar una VPN o túnel seguro.
- **Cifrado de comunicación:** Ten en cuenta que el protocolo Semtech UDP que usamos entre gateway y servidor **no cifra el enlace**. Dado que aquí todo ocurre dentro de tu LAN, el riesgo es bajo. Pero en entornos críticos se preferiría usar LoRa Basics Station (LNS) con wss:// (TLS) para la pasarela, o al menos tunelar el tráfico UDP por VPN. En nuestro caso, la carga útil LoRaWAN ya viene cifrada a nivel de aplicación de extremo a extremo con AES-128, lo cual es una tranquilidad (solo el servidor y el dispositivo tienen las claves para descifrar los datos). Aún así, los metadatos (EUI, frecuencia, etc.) viajan sin cifrar en UDP.
- **Seguridad MQTT:** Si vas a aprovechar MQTT, utiliza las autenticaciones. En TTS, el broker MQTT requiere usuario (AppID) y API Key, así que ya tienes una capa de autenticac ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=Creating an API Key))66】. Aun así, por defecto la conexión MQTT aquí es TCP sin cifrar (puesto que es todo local). Podrías configurar MQTT con TLS si lo desearas, pero para LAN no es crítico.
- **Firewalls:** Si tu Raspberry Pi está también conectada a Internet, podrías emplear `ufw` (uncomplicated firewall) para bloquear puertos no necesarios. Por ejemplo, podrías bloquear accesos externos al puerto 1885/8885 (console) si no deseas que nadie más entre, etc.
- **Bluetooth y WiFi en nodos:** Si implementas provisión por Bluetooth o WiFi AP en los nodos, protégelo. Por ejemplo, si usas WiFi AP, ponle una contraseña al AP para que un vecino no se conecte inadvertidamente. Si usas BLE, quizá pide un PIN de emparejamiento simple.
- **Claves LoRaWAN seguras:** Aunque en nuestro ejemplo las hemos escrito en el código (lo cual en entornos de producción no es ideal), asegúrate de no compartir las AppSKey/NwkSKey públicamente. Si reusas este proyecto, genera tus propias claves únicas por dispositivo desde TTS. Recuerda que la AppSKey cifra la carga útil de aplicación punto a pu ([LoRaWAN Architecture | The Things Network](https://www.thethingsnetwork.org/docs/lorawan/architecture/#:~:text=A typical LoRaWAN Network Server,has the following features))43】, por lo que ni siquiera un tercero que capture los datos (sin la AppSKey) podría leer el contenido. Mantener estas keys secretas garantiza la privacidad de los datos de sensores.

En resumen, **no dejes accesos abiertos con contraseñas por defecto**, segmenta la red si es posible (por ejemplo, podrías tener la Raspberry Pi en una subred para IoT separada de la red principal de PCs), y aprovecha las capas de seguridad que ya ofrece LoRaWAN (cifrado de las tramas). Para un entorno casero de pruebas, con estos cuidados mínimos estarás bastante seguro.

## Automatización mediante scripts 📑

A medida que construyas este proyecto, posiblemente querrás **automatizar** algunos pasos para no tener que repetir comandos manualmente en cada despliegue. Algunas ideas de scripts útiles:

- **Script de instalación en Raspberry Pi:** Podrías crear un script bash que realice la instalación completa en una Pi nueva. Por ejemplo, que actualice el sistema, instale Docker, Docker Compose, clone el repo de RAK e instale el gateway, copie el archivo docker-compose.yml y levante TTS. Muchas de esas tareas las hicimos manualmente, pero es perfectamente posible escribir un bash que las ejecute secuencialmente. Incluso hay usuarios que han compartido guiones para instalar TTN Stack en RPi automáticam ([GitHub - RAKWireless/rak_common_for_gateway](https://github.com/RAKWireless/rak_common_for_gateway#:~:text=step1 %3A Download and install,latest Raspberry Pi OS Lite)) ([GitHub - RAKWireless/rak_common_for_gateway](https://github.com/RAKWireless/rak_common_for_gateway#:~:text=Please enter 1,the model))307】.
- **Scripts para configurar TTS por CLI:** The Things Stack incluye una herramienta CLI (`ttn-lw-cli`) que se puede usar dentro del contenedor TTS. Con ella podrías automatizar la creación de gateways y dispositivos en lote. Por ejemplo, un script que registre 10 dispositivos ABP con sus DevAddr consecutivos. En la documentación oficial hay ejemplos de uso del CLI. Nuestro contenedor incluso permite `docker exec stack ttn-lw-cli  ([the-things-stack-docker/README.md at master · xoseperez/the-things-stack-docker · GitHub](https://github.com/xoseperez/the-things-stack-docker/blob/master/README.md#:~:text=CLI Auto Login))463】. Si vas a desplegar muchos nodos, esto ahorra hacerlo a mano en la consola web.
- **Script para decodificar logs:** Mientras pruebas, podrías tener un pequeño script Python en la Pi que suscrito al MQTT imprima solo los valores decodificados interesantes, en vez de todo el JSON. Esto es útil para debugging rápido.
- **Script de arranque:** Si quieres que al encender la Raspberry Pi se levante todo automáticamente (Docker ya se configuró para iniciar los contenedores a menos que estén parados con `unless-stopped` en docker-compose), pero quizás quieras que los logs se guarden, etc. Podrías usar un pequeño script en `/etc/rc.local` o un servicio systemd personalizado que verifique que Docker está corriendo y tu stack levantado.
- **Scripts en los nodos para provisión:** En MicroPython, podrías escribir un modo de configuración (como discutimos) que se active con cierto evento. Eso sería un script embebido en el firmware del nodo para facilitar reconfiguración sin tocar código.

Por ahora, con las instrucciones dadas, **no es necesario un script complejo**: ya has lanzado todo y debería reiniciarse solo tras un reboot (la pasarela configura en crontab o systemd el forwarder, y Docker Compose con `restart: unless-stopped` hará que TTS suba solo). Pero tener estos pasos documentados te servirá en el futuro.

## Conclusión y siguientes pasos

Hemos construido un sistema LoRaWAN casero: una Raspberry Pi 3 con un HAT RAK2245 actuando de gateway, corriendo The Things Stack en Docker para gestionar la red, y unos nodos ESP32 con MicroPython enviando datos. Esto demuestra el concepto de una red IoT larga distancia privada. A partir de aquí podrías:

- Añadir más sensores (p. ej. sensores de temperatura, humedad, movimiento) a tus nodos ESP32 y enviar esos datos.
- Crear una interfaz web (dashboard) para visualizar los datos en tiempo real usando las integraciones (por ejemplo, suscribiendo con Node-RED o Grafana).
- Explorar el envío de comandos a los nodos (downlink) quizás para encender un LED o controlar algo remotamente.
- Probar el modo OTAA en los nodos para ver cómo realizar el join (puede ser un reto divertido implementar el join in MicroPython, o alternar y usar Arduino C++ solo para comparar).
- Montar una caja y antena exterior para tu gateway si quieres mayor cobertura – recuerda que LoRa puede alcanzar varios km con línea vista. Con una antena exterior podrías dar cobertura a tus alrededores.
- Experimentar con ajustes de LoRa: SF (Spreading Factor), potencias, etc., para ver cómo afectan el alcance y la velocidad de datos.

¡Las posibilidades son muchas! Lo importante es que ya tienes la infraestructura y el conocimiento básico para manejarlas.

Antes de terminar, a continuación te dejamos algunos **enlaces a documentación oficial** y recursos que te serán útiles para ampliar o resolver dudas.

## Recursos y documentación externa útil 📚

- **Documentación oficial de The Things Stack (v3)** – Guía completa de The Things Stack, incluyendo instalación, uso de la consola, CLI, integraciones, etc. (en inglés): . En particular, la sección de Integraciones MQTT de The Things St ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=The Things Stack exposes an,to uplinks or publish downlinks)) ([MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/other-integrations/mqtt/#:~:text=Creating an API Key))-L66】. También el artículo *"Deploy The Things Stack in your local network"* (The Things Network blog) donde Hylke Visser muestra cómo instalarlo en una Raspber ([Deploy The Things Stack  in your local network](https://www.thethingsnetwork.org/article/deploy-the-things-stack-in-your-local-network#:~:text=The Things Stack now offers,such as the Raspberry Pi))-L26】.
- **Centro de documentación de RAKwireless** – Manuales de los módulos LoRa. Por ejemplo, la *Guía de inicio rápido del RAK2245* (en inglés) detalla la instalación del software en Raspber ([Meet the Device That LoRa® Developers Can't Resist Having: RAK2245 - IoT Made Easy](https://www.rakwireless.com/en-us/products/lpwan-gateways-and-concentrators/rak2245-pihat#:~:text=LPWAN Gateway Concentrator Module The,as the Raspberry Pi 3B))-L95】 y el uso de gateway-c ([Configuring Your Gateway | The Things Network](https://www.thethingsnetwork.org/docs/gateways/rak2245/configuring-gateway/#:~:text=You can choose one of,Servers here%3A TTN or ChirpStack))L121】: .
- **MicroPython (ESP32) – Documentación oficial** – Tutorial oficial para iniciarse con MicroPython en ESP32 (en ingl ([1. Getting started with MicroPython on the ESP32 — MicroPython latest documentation](https://docs.micropython.org/en/latest/esp32/tutorial/intro.html#:~:text=1)) ([1. Getting started with MicroPython on the ESP32 — MicroPython latest documentation](https://docs.micropython.org/en/latest/esp32/tutorial/intro.html#:~:text=The first thing you need,particular board on this page))L112】. Explica cómo instalar firmware, usar el REPL, manejar WiFi, GPIO, etc. Útil para comprender más allá de LoRa.
- **uLoRa – Proyecto LoRaWAN MicroPython** – Repositorio de la librería uLoRa utilizada en este proye ([GitHub - fantasticdonkey/uLoRa: LoRa / LoRaWAN + TTN for MicroPython (ESP32)](https://github.com/fantasticdonkey/uLoRa#:~:text=Objecive))L261】 (GitHub: *LoRaWAN + TTN for MicroPython*). Incluye ejemplos y notas sobre sus capacidades (por ejemplo, indica que solo hace uplinks no confirmados con ABP, que es justo nuestro caso de uso básico).
- **The Things Network – Conceptos LoRaWAN** – La documentación comunitaria de TTN tiene explicaciones de la arquitectura Lo ([LoRaWAN Architecture | The Things Network](https://www.thethingsnetwork.org/docs/lorawan/architecture/#:~:text=End devices communicate with nearby,is known as message deduplication))-L77】, conceptos de dispositivos, gateways, etc., en un lenguaje senci ([LoRaWAN Architecture | The Things Network](https://www.thethingsnetwork.org/docs/lorawan/architecture/#:~:text=Each gateway is registered ,4 GHz radio links))-L97】. Ideal para entender términos como DevAddr, AppKey, ADR, SF, etc.
- **Mosquitto MQTT** – Página oficial del proyecto Eclipse Mosquitto, con descargas y documentación de los clientes MQTT  ([Data API (MQTT) | The Things Network](https://www.thethingsnetwork.org/docs/applications/mqtt/#:~:text=,client with a nice GUI))-L77】. Útil si quieres saber más de cómo usar mosquitto_sub o montar tu propio broker (aunque en este proyecto aprovechamos el integrado en TTS).
- **Seguridad LoRaWAN** – Documento *The Things Network Security* (si quieres profundizar en cómo LoRaWAN garantiza la seguridad de las tramas, con las dos capas de cifrado NwkSKey/AppSK ([LoRaWAN Architecture | The Things Network](https://www.thethingsnetwork.org/docs/lorawan/architecture/#:~:text=A typical LoRaWAN Network Server,has the following features))L143】.
- **Foros de la comunidad** – Si encuentras obstáculos, los foros de The Things Network y RAKWireless son excelentes lugares para buscar soluciones:
  - Foro TTN: preguntas y respuestas de usuarios sobre gateways DIY, problemas de conexión, etc. (por ejemplo *“How to install TTN Stack v3 on RPi?”*: experiencias de otros usu ([How to install TTN stack V3 on RPI? - The Things Network](https://www.thethingsnetwork.org/forum/t/how-to-install-ttn-stack-v3-on-rpi/27135#:~:text=How to install TTN stack,instruction on their github%2C))-L13】).
  - Foro RAKWireless: dedicado a hardware RAK; útil si tienes algún inconveniente específico con el RAK2245 o su software (por ejemplo, hilos sobre RAK2245 no conectando y soluciones).
- **Código fuente de ejemplo** – Nuestro código MicroPython de ejemplo se basó en la adaptación de TinyLoRa. Adafruit tiene un tutorial CircuitPython LoRaWAN con TinyLoRa (que es similar a MicroPy ([GitHub - fantasticdonkey/uLoRa: LoRa / LoRaWAN + TTN for MicroPython (ESP32)](https://github.com/fantasticdonkey/uLoRa#:~:text=This is an experimental port,TTN))L252】 y explica el procedimiento de registro en TTN, formateo de payload, etc. (aunque usando su hardware Feather M0). Puede servir para comparar enfoques.

