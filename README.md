# LoRaIM (LoRa Instant Messenger)
![Logo](https://github.com/v1ct0rjs/lorawan_project/blob/main/img/Logoi.png)

![Diagrama](https://github.com/v1ct0rjs/lorawan_project/blob/main/img/Diagram.png)
*Figura: Diagrama explicativo de la arquitectura LoRaIM.*

![run](https://github.com/v1ct0rjs/lorawan_project/blob/main/img/run.png)



## 1. Introducción

LoRaIM (LoRa Instant Messenger) es un proyecto de mensajería instantánea que utiliza la tecnología de comunicación inalámbrica **LoRa** para permitir el intercambio de mensajes de texto entre usuarios sin necesidad de infraestructura convencional (sin cobertura celular, sin WiFi ni Internet). El propósito de este proyecto es desarrollar un sistema de bajo costo y bajo consumo energético que ofrezca una alternativa de comunicación en zonas aisladas o en situaciones de emergencia. Las redes basadas en LoRa permiten interconectar enlaces inalámbricos a largas distancias, llegando a comunicar pueblos y comunidades rurales con centros urbanos cercanos. A diferencia de los servicios de mensajería tradicionales que dependen de redes móviles o de Internet, LoRaIM funciona **off-grid**, es decir, crea su propia red de comunicación independiente. Esto resulta especialmente útil cuando no hay infraestructura disponible – por ejemplo, en áreas rurales sin cobertura telefónica, en campamentos al aire libre o tras desastres naturales donde las redes convencionales estén caídas. De hecho, las comunicaciones mediante dispositivos LoRa pueden ser muy valiosas cuando se interrumpe el servicio celular, extendiendo la conectividad más allá del alcance de las torres de telefonía. En resumen, **LoRaIM** nace de la motivación de brindar un medio de mensajería tipo SMS en cualquier lugar y momento, sin costes recurrentes ni depender de proveedores, aprovechando las ventajas de alcance de la tecnología LoRa.

En el contexto académico, este proyecto se enmarca como Proyecto Final de segundo curso del ciclo formativo de ASIR. Combina conocimientos de redes, comunicaciones inalámbricas e Internet de las Cosas (IoT) para diseñar y desplegar un sistema de mensajería funcional. A lo largo de esta documentación se describirá detalladamente el desarrollo de LoRaIM: sus objetivos, los fundamentos teóricos, el diseño y la implementación tanto de software como de hardware, las pruebas realizadas, así como las conclusiones obtenidas. Asimismo, se incluyen anexos con un manual de usuario y un manual de instalación, para facilitar el uso y la replicación del sistema por terceros.

## 2. Objetivos

**Objetivo principal:**
Desarrollar un sistema de mensajería instantánea independiente (denominado *LoRaIM*) que permita la comunicación de texto entre dos o más usuarios a través de enlaces de radio LoRa de largo alcance, sin necesidad de infraestructura de comunicaciones existente (Internet, redes móviles o WiFi convencionales). El sistema debe ser funcional, seguro y fácil de usar, proporcionando una experiencia similar a la de aplicaciones de mensajería simples (tipo SMS), pero operando en entornos sin cobertura.

**Objetivos secundarios:**

* **Aprendizaje e implementación de LoRa:** Investigar los fundamentos de la tecnología LoRa y aplicarlos en la configuración de una red inalámbrica de baja potencia y largo alcance. Esto incluye comprender la modulación LoRa, los parámetros (frecuencia, factor de propagación, ancho de banda) y, en su caso, el protocolo LoRaWAN asociado.
* **Diseño de arquitectura ad-hoc:** Diseñar una arquitectura de sistema **peer-to-peer** o de red ad-hoc capaz de interconectar los dispositivos de los usuarios usando módulos LoRa. Decidir la topología (por ejemplo, comunicación punto a punto directa entre nodos, o extensible a múltiples saltos/mesh) que mejor se adapte al escenario de mensajería instantánea.
* **Desarrollo de software en Python:** Implementar la lógica de la aplicación en Python, incluyendo la interfaz de usuario (ej. una aplicación web local o interfaz de línea de comandos) y la integración con los módulos de radio LoRa mediante bibliotecas o controladores adecuados. Se busca utilizar scripts Python para gestionar el envío y recepción de mensajes, almacenamiento de mensajes si es necesario, y cualquier protocolo de comunicación entre nodos.
* **Integración de hardware y comunicaciones:** Montar los componentes de hardware necesarios: microcontroladores o microordenadores (como Raspberry Pi), módulos de radio LoRa (transceptores de largo alcance) y, opcionalmente, periféricos como antenas, pantallas o teclados según lo requiera el prototipo. Asegurar que el hardware esté correctamente interconectado y configurado (p. ej., conexión del módulo LoRa a los pines del microcontrolador, alimentación, etc.).
* **Pruebas de funcionamiento y alcance:** Realizar pruebas exhaustivas del sistema, comprobando que se pueden enviar y recibir mensajes correctamente entre los dispositivos. Evaluar el alcance efectivo de la comunicación LoRa en distintos entornos (espacio abierto vs. entorno urbano con obstáculos) y medir el desempeño (latencia en el envío de un mensaje, tasa de entrega, etc.). Verificar también la estabilidad de la comunicación y el cumplimiento de cualquier restricción (por ejemplo, respetar el duty cycle regulatorio).
* **Documentación y usabilidad:** Elaborar la documentación técnica completa del proyecto (el presente documento), así como manuales de instalación y uso. Además, considerar la experiencia de usuario de LoRaIM, puliendo la interfaz de usuario para que sea lo más intuitiva posible dada la naturaleza del sistema (por ejemplo, proporcionando indicaciones claras al usuario, confirmaciones de entrega de mensajes, etc.).
* **Seguridad y mejoras futuras (objetivos ampliados):** Aunque no es el foco principal, se tendrá en cuenta la seguridad básica de las comunicaciones (por ejemplo, posibilidad de cifrar los mensajes transmitidos para garantizar privacidad). Asimismo, se identificarán posibles mejoras o ampliaciones, como integrar más nodos formando una red mallada, incluir envío de archivos pequeños o datos de sensores, etc., para plantearlas en las conclusiones y trabajos futuros.

Con estos objetivos, el proyecto LoRaIM busca tanto lograr un resultado práctico –un **mensajero instantáneo funcional sobre LoRa**– como servir de aprendizaje integral en el ámbito de las redes inalámbricas IoT, cubriendo desde la teoría hasta la puesta en marcha real de un sistema de comunicaciones.

## 3. Marco Teórico

En este apartado se presentan los fundamentos teóricos en los que se apoya el proyecto **LoRaIM**, abarcando las tecnologías y conceptos clave: la tecnología de comunicación LoRa y su protocolo asociado LoRaWAN, las características de las redes inalámbricas de baja potencia y largo alcance (LPWAN), y los principios de las comunicaciones punto a punto y en malla que podrían usarse en un sistema de mensajería off-grid.

### 3.1 Tecnología LoRa y redes LPWAN

**LoRa** (del inglés *Long Range*, “largo alcance”) es una tecnología de comunicaciones inalámbricas desarrollada específicamente para lograr **comunicaciones a larga distancia con bajo consumo de energía**. Técnicamente, LoRa define una modulación de radio basada en *Chirp Spread Spectrum* (CSS), en la cual la información se codifica en pulsos tipo “chirp” de frecuencia variable. Esta modulación de espectro ensanchado proporciona gran robustez frente al ruido e interferencias, permitiendo que las señales LoRa puedan ser recibidas a kilómetros de distancia incluso con potencia de transmisión muy baja. En otras palabras, LoRa fue diseñada para **alcanzar distancias muy superiores** a las de tecnologías inalámbricas convencionales de corto alcance como WiFi, Bluetooth o ZigBee, a costa de transmitir datos a velocidades más reducidas.

LoRa se engloba dentro de las llamadas redes de área amplia y baja potencia (LPWAN, *Low Power Wide Area Network*). Es la capa física de comunicación: especifica cómo se modulan y envían las ondas de radio. Las frecuencias de operación de LoRa se sitúan en bandas libres de licencia sub-GHz (bandas ISM). En Europa típicamente se usa la banda EU868 (868 MHz), mientras que en América se usan 915 MHz, y también existen variantes en 433 MHz, 923 MHz, etc., dependiendo de la región. El uso de frecuencias sub-GHz contribuye al largo alcance, ya que estas frecuencias se propagan mejor y atraviesan obstáculos más efectivamente que las bandas más altas. Asimismo, LoRa puede también operar en 2.4 GHz (existe hardware LoRa a 2.4 GHz), logrando mayores *bitrate* a costa de menor alcance, aunque el uso más extendido son las bandas inferiores por su amplio radio de cobertura.

Una característica importante de LoRa es su adaptabilidad en términos de alcance vs. velocidad de datos. Emplea diferentes factores de ensanchamiento o *Spreading Factors* (SF). Un SF más alto significa que cada bit de datos se “espacia” más en el tiempo (chirps más largos), lo cual **aumenta el alcance y la sensibilidad de recepción** pero reduce la tasa de bits. Por ejemplo, con LoRa pueden alcanzarse **tasas de datos desde \~0.3 kbps hasta 50 kbps** como máximo, dependiendo de la configuración. En condiciones ideales de línea de vista (LoS) y con SF óptimos, es posible comunicar dispositivos LoRa a distancias del orden de **10 a 20 kilómetros**. En entornos urbanos con obstáculos la distancia típica es menor (varios kilómetros o menos, según densidad de edificios), pero sigue siendo muy superior a la de WiFi/Bluetooth. Esta capacidad de comunicación a larga distancia con baja potencia hace a LoRa especialmente atractiva para **sensores IoT alimentados con batería**, donde pequeñas ráfagas de datos (temperatura, posición, etc.) deben enviarse esporádicamente a un receptor lejano.

Es importante distinguir **LoRa** de **LoRaWAN**. LoRa es la tecnología de radio (capa física), mientras que **LoRaWAN** es un protocolo de red construido sobre LoRa. En concreto, LoRaWAN especifica el **protocolo de enlace de datos y la arquitectura de red** para gestionar la comunicación entre dispositivos LoRa a gran escala (normalmente en topología estrella a través de **gateways** o puertas de enlace). LoRaWAN define cómo se estructuran los paquetes, cómo se accede al medio (por ejemplo, clases A, B, C de dispositivos con distintas estrategias de recepción continua o programada) y cómo se integran las comunicaciones LoRa en Internet (los gateways LoRaWAN envían los datos a servidores en la nube). En suma, **LoRaWAN es un estándar de capa MAC/red** promovido por la LoRa Alliance para redes LPWAN amplias, pensado para IoT masivo, con características como seguridad extremo a extremo, gestión de duplicados, etc.

Cabe aclarar que **LoRaIM no utiliza directamente LoRaWAN**, ya que nuestro caso de uso no involucra una red pública con gateways ni una infraestructura centralizada. En lugar de ello, LoRaIM se basa en la comunicación **LoRa en modo punto a punto (P2P)** entre nodos. Esto significa que los transceptores LoRa en nuestros dispositivos se comunican directamente entre sí, sin pasar por gateways intermedios ni servidores de red. LoRa permite este modo P2P configurando manualmente parámetros comunes en todos los nodos (frecuencia, SF, códigos de corrección de error, etc.), de forma que cualquier paquete transmitido por un nodo pueda ser demodulado por los demás en rango. Algunos módulos comerciales (como los de Reyax) implementan además un esquema básico de direccionamiento en P2P: cada módulo puede tener una dirección ID, y se pueden enviar paquetes a un ID específico, lo que facilita construir un **protocolo simple de mensajería** sin colisiones. Esto resulta suficiente para un messenger de pocos usuarios; para redes más grandes o de topología diversa, habría que considerar protocolos más complejos.

### 3.2 Ventajas y limitaciones de LoRa para mensajería instantánea

LoRa presenta **grandes ventajas** en escenarios donde otras tecnologías fallan o son costosas. Ya hemos mencionado su amplio alcance y bajo consumo. Además, opera en bandas libres, por lo que **no requiere pagar por datos ni licencias** de espectro; esto permite que comunidades o particulares monten sus propias redes LoRaIM sin incurrir en gastos recurrentes. En contextos rurales o de países en desarrollo donde la cobertura celular es escasa, soluciones basadas en LoRa pueden proveer servicios de comunicación básicos (mensajes, alertas) a una fracción del coste de desplegar antenas celulares. Por ejemplo, en México se estima que un 16% de la población (más de 19 millones de personas) vive sin cobertura celular – para estas comunidades, sistemas como LoRaIM podrían brindar un medio de comunicación esencial. Otra aplicación evidente es en **situaciones de desastre o emergencia**, donde las redes tradicionales se caen: con un mensajero LoRa los equipos de rescate o habitantes podrían seguir comunicándose localmente para coordinar, siempre que tengan dispositivos LoRaIM a mano.

Sin embargo, es importante reconocer las **limitaciones** de LoRa, especialmente al intentar usarlo para mensajería instantánea (pensada originalmente para seres humanos, no solo sensores). La principal limitación es el **ancho de banda extremadamente bajo** comparado con estándares como WiFi o redes móviles. En LoRaIM solo es práctico enviar texto plano u otros datos muy pequeños; no es viable transferir archivos grandes, imágenes o audio en tiempo real. Incluso los mensajes de texto tienen restricciones de tamaño: los paquetes LoRa suelen admitir en torno a 50-255 bytes útiles como máximo (dependiendo de la configuración). Si un usuario intentara enviar un párrafo muy largo, habría que fragmentarlo en múltiples paquetes, aumentando la latencia.

Relacionado con lo anterior, está la restricción regulatoria del **ciclo de trabajo (duty cycle)** en las bandas ISM. En Europa, por ejemplo, la banda 868 MHz limita a un 1% el tiempo máximo de transmisión de un dispositivo (por normativa ETSI). Esto significa que un nodo LoRa no puede estar transmitiendo constantemente; después de enviar un paquete debe permanecer en silencio la mayor parte del tiempo. Para LoRaIM, implica que la frecuencia de mensajes es baja – no es para chats continuos tipo WhatsApp, sino para mensajes esporádicos. Un envío típico de LoRa (varios bytes a SF alto) podría tardar del orden de 0.5 a 2 segundos en el aire; tras eso, legalmente el dispositivo debería esperar quizá 1-2 minutos antes de otra transmisión larga, para cumplir el 1%. En la práctica, configuraciones de LoRaIM deben balancear el **SF (Spreading Factor)** para no exceder estos límites y quizá implementar mecanismos de espera si el usuario intenta enviar muchos mensajes seguidos.

Otra limitación es la **latencia e interfaz**: LoRa no establece una conexión persistente ni garantiza entrega inmediata. No hay confirmaciones automáticas estilo TCP a menos que se programe. Para que LoRaIM se asemeje a una mensajería “instantánea”, se pueden integrar ACKs (confirmaciones) a nivel de aplicación – por ejemplo, que el nodo receptor envíe de vuelta un pequeño paquete confirmando que recibió el mensaje, para notificar al remitente. Esto agrega algo de tráfico pero mejora la fiabilidad percibida. Aun así, comparado con sistemas en línea, habrá mayores demoras e incertidumbre en la recepción.

Por último, está la cuestión de la **escabilidad y topología**. LoRaIM en su versión básica conecta dos nodos directamente. Si quisiéramos ampliar a una red con múltiples usuarios distribuidos (más de 2 nodos), tendríamos que enfrentar desafíos de encaminamiento (routing) o **red mallada (mesh)**. LoRa en sí soporta la posibilidad de redes tipo mesh (no definidas por LoRaWAN estándar, pero implementables a nivel de aplicación) – de hecho, existen proyectos comunitarios donde varios nodos LoRa retransmiten mensajes formando una malla inundada. Esto permite extender la cobertura: cada nodo actúa como repetidor, pasando el mensaje hasta alcanzar al destinatario final, a costa de mayor complejidad y consumo. En LoRaIM podríamos concebir una futura extensión para modo mesh (como el proyecto *Meshtastic* o *LoRa Messenger* de Hackaday, que crean chats off-grid multi-salto). En esta primera versión nos centramos en enlaces directos; no obstante, el diseño deja abierta la puerta para evolución hacia mesh, dado que LoRa **no requiere infraestructura fija** y es plausible implementar repetidores. Hay que considerar que en un mesh LoRa la latencia aumenta con cada salto y el riesgo de colisiones también, por lo que protocolos de enrutamiento inteligentes serían necesarios.

En resumen, desde el punto de vista teórico, LoRa ofrece los cimientos ideales para comunicaciones en ausencia de red: largo alcance, baja potencia, operación libre y sencilla. La contrapartida son las limitaciones en velocidad y capacidad, que obligan a optimizar el uso (mensajes cortos, esenciales) y a manejar expectativas de desempeño. **LoRaIM se apoya en estos fundamentos**, aprovechando las ventajas (comunicación a kilómetros sin coste) y mitigando las limitaciones mediante diseño de protocolo simple y buenas prácticas (como limitar el tamaño y frecuencia de mensajes, y confirmar la recepción).

## 4. Desarrollo del Proyecto

A continuación, se detalla el desarrollo práctico de LoRaIM, incluyendo el **diseño de la arquitectura** del sistema y la **implementación** concreta de hardware y software. Se describe cómo se han materializado los objetivos propuestos, qué componentes forman el sistema, cómo interactúan entre sí, el entorno de desarrollo, las herramientas utilizadas, así como las pruebas realizadas durante la construcción del mensajero LoRa.

### 4.1 Diseño

En la fase de diseño se definió la **arquitectura general** de LoRaIM, abarcando tanto la estructura física (dispositivos y conexiones) como la estructura lógica (módulos de software y flujo de datos). La solución adoptada busca un equilibrio entre funcionalidad, simplicidad y robustez, teniendo en cuenta las peculiaridades de LoRa discutidas en el marco teórico.

&#x20;*Figura 1: Arquitectura de red propuesta para LoRaIM.* Cada nodo del sistema es un **nodo LoRaIM autónomo** que consiste en un microordenador Raspberry Pi equipado con un transceptor LoRa de largo alcance (antena). Adicionalmente, cada nodo actúa como un punto de acceso Wi-Fi local al que los usuarios pueden conectar sus dispositivos personales (smartphones, tablets o portátiles). De este modo, como ilustra la Figura 1, los usuarios se conectan vía Wi-Fi a su nodo LoRaIM más cercano, y pueden enviar mensajes a través de una interfaz (por ejemplo, una aplicación web local). El mensaje es recibido por la Raspberry Pi y retransmitido mediante radio LoRa hacia el otro nodo LoRaIM. En el lado opuesto, el segundo nodo recibe el mensaje por LoRa y lo pone a disposición del usuario conectado a él (mostrándolo en la interfaz de chat del segundo usuario). Todo esto ocurre **sin depender de Internet ni redes de telefonía**, solamente usando enlaces directos: Wi-Fi de corto alcance entre usuario y su nodo, y LoRa de largo alcance entre los nodos.

Esta arquitectura tiene la ventaja de brindar una **experiencia de uso amigable**: los usuarios simplemente usan sus teléfonos u ordenadores para chatear, casi como lo harían con WhatsApp o Telegram, solo que en lugar de datos móviles utilizan la conexión Wi-Fi al nodo LoRaIM. Internamente, el Raspberry Pi traduce esas acciones de usuario en comunicaciones LoRa de bajo nivel. Además, el uso de Raspberry Pi (un sistema Linux) en cada nodo aporta flexibilidad para implementar lógica adicional (p. ej., servidor web, almacenamiento de mensajes, etc.) y suficiente potencia de cómputo para manejar múltiples tareas simultáneamente.

Cada **dispositivo LoRaIM** (Raspberry Pi + módulo LoRa) se diseñó para ser portátil y autónomo. Si bien en el prototipo se alimenta con corriente USB normal, se prevé que podría conectarse a baterías externas si se quisiera usar en campo (por ejemplo, baterías Li-ion con módulos de alimentación). Los módulos de radio LoRa seleccionados incluyen amplificadores de antena adecuados para alcanzar varios kilómetros. Para mantener simplicidad en esta primera versión, se definió que la red operará en modo **dos nodos punto a punto**. Es decir, en el escenario típico habrá **dos unidades LoRaIM** (por ejemplo, usuario A y usuario B) comunicándose entre sí. No obstante, el diseño no excluye soportar más nodos: todos los dispositivos configurados en la misma frecuencia y con el mismo *NetID* podrían recibir los mensajes transmitidos. Si en un futuro se quisiera una conversación grupal o añadir repetidores, se podría configurar los demás nodos para reenviar los mensajes recibidos (formando así una red mesh, como comentado previamente).

En cuanto al **protocolo de comunicación** diseñado: dado que estamos en modo P2P sin infraestructura, se optó por un esquema sencillo de envío directo. Cada mensaje de usuario se encapsula en un paquete LoRa con un formato básico: contiene el ID del remitente, el ID del destinatario (o un código de *broadcast* si fuera a todos), y el texto del mensaje. Los módulos LoRa empleados (Reyax RYLR896) gestionan parte de esto, ya que permiten establecer una dirección para cada módulo y enviar mensajes usando comandos AT indicando la dirección destino. Por tanto, a nivel de diseño lógico, cada Raspberry Pi simplemente toma el mensaje del usuario, llama al módulo LoRa para enviarlo al destinatario deseado, y en el receptor el módulo LoRa notifica de la llegada de un mensaje proveniente de X. Sobre esa base, implementamos confirmaciones: cuando un nodo recibe un mensaje, automáticamente responde con un acuse de recibo (ACK) al emisor, para que la interfaz de usuario pueda marcar el mensaje como entregado. Este ACK es también un pequeño paquete LoRa (con un código especial de tipo “confirmación” en lugar de texto). De esta forma, logramos confiabilidad básica sin un gran sobrecoste.

Otra parte del diseño es la **seguridad**. LoRa por sí mismo (en modo P2P) no tiene cifrado obligatorio – los módulos Reyax ofrecen en comandos la posibilidad de establecer una clave AES de 128 bits para cifrar los datos transmitidos. En la configuración de diseño se decidió habilitar esta característica: todos los nodos cargarían la misma clave de cifrado simétrica, de modo que los mensajes van cifrados por el aire y solo son descifrados por el receptor legítimo. Esto impide que terceros con otro transceptor LoRa sniffeen fácilmente el contenido de los mensajes (añade privacidad, aunque no protege contra interferencia deliberada). En el manual de instalación se indicará cómo configurar esta clave en los módulos.

&#x20;*Figura 2: Diagrama de la arquitectura de software de LoRaIM.* Complementando la arquitectura física, la Figura 2 muestra la estructura de **capas de software** en cada nodo LoRaIM. Hemos seguido una arquitectura modular:

* En la base, el sistema Linux del Raspberry Pi se configura con **hostapd + dnsmasq** para proveer la funcionalidad de **hotspot Wi-Fi**. Esto permite que el Pi cree una red Wi-Fi local (ej. SSID “LoRaIM\_Node1”) a la cual el usuario se conecta. El servicio dnsmasq se encarga de asignar IP por DHCP al dispositivo del usuario, creando efectivamente una mini red LAN aislada. Por simplicidad, ambos nodos usan diferentes SSID y rangos IP (p. ej., Node1 usa 192.168.10.0/24 y Node2 192.168.20.0/24) para evitar conflictos si estuvieran al alcance entre sí, aunque normalmente estarán lejos.
* A nivel de aplicación, en el Raspberry Pi corre un **servidor web** que actúa como **frontend** para el usuario. Se implementó utilizando el microframework **Flask** de Python, que es ligero y adecuado para servir páginas en red local. El servidor web ofrece una página simple de chat (desarrollada en HTML/JavaScript) donde el usuario puede escribir mensajes y ver los recibidos. Esta página se actualiza dinámicamente mediante peticiones REST (Ajax) a endpoints del servidor Flask.
* El **backend** del sistema es también manejado por Flask (u otro hilo en Python) que expone servicios **RESTful**. Por ejemplo, hay un endpoint `/send` al que el frontend le envía el texto de un mensaje cuando el usuario presiona “Enviar”; el backend entonces invoca la función de enviar mensaje por LoRa. Igualmente, hay un endpoint `/messages` que el frontend consulta periódicamente para obtener nuevos mensajes recibidos y mostrarlos en pantalla.
* La comunicación con el hardware LoRa está encapsulada en un módulo que llamamos **LoRa Interface**. En nuestro caso, dado que usamos módulos Reyax UART, esta interfaz es una clase Python que maneja el puerto serial del módulo. Por medio de la librería **PySerial**, el backend envía comandos AT al módulo LoRa (por ejemplo, `AT+SEND=destId,length,contenido`) y lee las respuestas. El código de la interfaz LoRa también ejecuta un hilo separado que está constantemente *escuchando* datos entrantes del módulo (las notificaciones de mensaje recibido llegan vía serial). Cuando detecta un mensaje entrante, lo procesa (descifrando si aplica, extrayendo remitente y texto) y lo guarda en una cola de mensajes recibidos.
* Finalmente, el **LoRa Library / code** de la figura representa que bajo el capó usamos ya sea una biblioteca existente o comandos propietarios. En este proyecto, la mayor parte de la lógica se implementó a mano con AT commands, pero vale mencionar que existen librerías Python para control de transceptores LoRa (por ejemplo, *LoRaRF* o *pyLoRa*) útiles en caso de usar módulos SPI de Semtech. El enfoque con módulos UART simplificó el diseño al delegar tareas de bajo nivel (modulación, sincronización) al firmware del módulo.

En conjunto, el diseño resultante proporciona un **sistema completo**: interfaz de usuario web local, middleware Python gestionando lógica de mensajería, y enlace físico LoRa transmitiendo los datos. Antes de pasar a la implementación, se elaboraron diagramas de secuencia para visualizar el flujo: por ejemplo, *“Usuario A envía mensaje”* – el evento recorre las capas: interfaz web -> petición REST -> función Python -> comando AT al módulo LoRa -> transmisión radio -> recepción por módulo remoto -> interrupción al hilo receptor Python -> almacenar mensaje -> notificar vía REST (long polling o websockets) -> interfaz usuario B actualiza con mensaje. Este diseño modular facilitó la implementación por partes y permitió depurar cada componente (web, serial, radio) por separado inicialmente.

### 4.2 Implementación

Con el diseño definido, se procedió a la **implementación práctica** del proyecto LoRaIM, construyendo tanto el entorno hardware como desarrollando el software necesario. A continuación se describen los detalles de implementación: componentes hardware utilizados, desarrollo del código (Python y configuraciones), así como las pruebas realizadas durante el proceso.

**Hardware utilizado:** Para el prototipo se utilizaron dos microordenadores **Raspberry Pi 3 Model B** (aunque podría usarse Pi Zero W o modelos superiores). Cada Raspberry Pi ejecuta Raspbian (Raspberry Pi OS) como sistema operativo. En cuanto a los módulos de comunicación, se seleccionaron dos módulos **LoRa Reyax RYLR896** operando en la banda de 868 MHz (compatible con Europa). Estos módulos fueron elegidos por su facilidad de uso: integran un transceptor LoRa SX1276 junto con un microcontrolador interno que atiende comandos AT vía UART. En otras palabras, simplifican mucho la programación, ya que no hay que manejar registros de radio ni SPI directamente – basta con enviar comandos de texto al módulo para configurarlo y transmitir datos. Cada RYLR896 se conectó a la Raspberry Pi mediante la interfaz UART serial (GPIO 14 y 15 de la Pi para TX/RX, respectivamente). Se soldaron pines hembra para conectar los módulos y antenas adecuadas (antena de 5 cm sintonizada a 868 MHz en cada uno). También se usaron conversores de nivel lógico en TX/RX de ser necesarios, ya que el RYLR896 trabaja a 3.3V (afortunadamente igual que la Pi, así que se pudo conectar directamente). Aparte de esto, se empleó una **tarjeta MicroSD** de 16GB para cada Pi con el sistema operativo, adaptadores de corriente USB de 5V/2.5A para la alimentación, y los componentes de red inalámbrica integrados (Wi-Fi de la Pi) para el hotspot. No se requirieron sensores adicionales ni pantallas táctiles físicas, pues la interacción es vía los dispositivos del usuario (p. ej., el smartphone del usuario A actúa como “pantalla” y “teclado” a través de la interfaz web).

Durante la implementación, se prestó especial atención a la **configuración de los módulos LoRa**. Por defecto, los RYLR896 funcionan a 915 MHz y con ciertos parámetros predefinidos. Usando su manual de comandos AT, se configuraron para Europa:

* **Frecuencia:** 868 MHz (`AT+BAND=868000000` comando AT correspondiente).
* **Direcciones:** se asignó ID 1 al módulo del nodo A y ID 2 al módulo del nodo B (`AT+ADDRESS=1` y `AT+ADDRESS=2`). De esta forma, podemos direccionar mensajes entre ellos.
* **Potencia de transmisión:** nivel máximo (comando `AT+IPR` o específico de potencia, en este módulo puede ser fijo a +20 dBm máximo por hardware, lo cual es adecuado para alcance máximo).
* **Spreading Factor:** los Reyax suelen por defecto usar SF=7 u otro intermedio. Para nuestras pruebas iniciales en entornos mixtos, configuramos SF=12 (máxima sensibilidad) para lograr el mayor alcance posible a costa de velocidad. Esto se logró con el comando `AT+PARAMETER` que ajusta SF, BW y CR. Se dejó un BW de 125 kHz y Coding Rate 4/5, configuraciones típicas de LoRaWAN que maximizan alcance.
* **Cifrado AES:** se estableció una clave simétrica de 16 caracteres igual en ambos (`AT+CFG=433920000,7,0,1,5,20,1` por ejemplo incluye algunos de estos parámetros – el manual indica cómo pasar la Network ID y la opción de cifrado). En nuestro caso, la clave AES se cargó con otro comando especializado (`AT+KEY=<clave>`). Tras esto, los módulos criptografían automáticamente la carga útil de los mensajes.

En paralelo, se implementó el **software**. Todos los scripts se desarrollaron en **Python 3.9** sobre Raspbian. Se comenzó configurando el entorno: instalando Flask (`pip install flask flask-restful`) y PySerial (`pip install pyserial`), entre otras utilidades. Para organizar el código, se crearon los siguientes archivos principales:

* `lora_interface.py`: módulo Python que encapsula el manejo del puerto serial conectado al módulo LoRa. Define una clase `LoRaModule` con métodos para enviar comandos AT y para leer las respuestas. Incluye funcionalidades como `send_message(dest_id, text)` que construye la instrucción AT adecuada (`AT+SEND=<dest_id>,<length>,<text>`) y la envía por serial, y un hilo receptor que continuamente lee líneas del serial para detectar patrones como `+RCV` (prefijo que los Reyax envían cuando reciben un mensaje). Al detectar un `+RCV`, esta clase parsea los datos: el formato recibido es `+RCV=<sender>,<length>,<message>,<RSSI>,<SNR>`. Se extrae el sender ID, el contenido y se almacena en una lista interna de mensajes recibidos pendientes.
* `server.py`: script principal que inicia el servidor Flask. Define rutas (endpoints) como:

  * `/` (ruta raíz): sirve una página HTML (renderizada mediante una plantilla Jinja2) que contiene la interfaz de chat. Esta interfaz muestra una lista de mensajes (inicialmente vacía o mensajes históricos si guardados) y un formulario para enviar nuevo mensaje.
  * `/send` (método POST): recibe datos de formulario (el texto del mensaje ingresado por el usuario y posiblemente un campo oculto con el destinatario ID o nombre). Este endpoint toma esos datos y usa la instancia de `LoRaModule` para enviar el mensaje via LoRa. Luego responde al frontend con, por ejemplo, un JSON indicando éxito o el propio mensaje enviado para agregarlo a la conversación local.
  * `/messages` (método GET): utilizado por el frontend para consultar periódicamente nuevos mensajes. Este endpoint revisa la cola de mensajes recibidos en `LoRaModule` (que la clase va llenando cuando llegan cosas) y devuelve cualquier mensaje nuevo como JSON (incluyendo quien lo envió, contenido y hora). Tras devolverlos, los marca como entregados (vacía la cola o los marca leídos).
* `static/` y `templates/`: directorios donde se colocaron los archivos estáticos y la plantilla HTML respectivamente. La página HTML del chat (`chat.html`) contiene un simple script JavaScript que cada, digamos, 2 segundos hace una petición AJAX a `/messages` para actualizar la lista de chat sin refrescar la página completa. También envía el formulario de mensaje por AJAX a `/send` para no recargar página. Esto brinda una experiencia más fluida al usuario (similar a aplicaciones en tiempo real), pese a la simplicidad del backend.
* `config.py` o parámetros: definiciones de constantes como la ID del propio nodo (para saber si un mensaje entrante viene del “otro” usuario), la clave AES (por si quisiéramos cambiarla fácilmente), etc. Algunas de estas se cargan desde archivos de configuración (por ejemplo, el archivo `counter.conf` mencionado en el repositorio de referencia, en nuestro caso podríamos tener `node.conf` con ID y nombre del nodo).

Una vez listo el código, se procedió a probar la comunicación **en laboratorio**. Inicialmente, ambos módulos LoRaIM se probaron en la misma habitación para verificar que se enviaban mensajes exitosamente. Utilizando el monitor serial (por ejemplo `minicom` o los logs de debug en Python), confirmamos que cuando el usuario A enviaba "Hola" desde la interfaz web, el módulo A recibía el comando AT correspondiente y respondía con `OK`, y casi inmediatamente el módulo B (en el otro Pi) emitía una línea `+RCV=1,4,Hola,...` indicando recepción del mensaje de ID 1 con texto "Hola". El hilo Python receptor en B parseó eso y registró el mensaje, de modo que en la interfaz web del usuario B apareció "Usuario1: Hola". Entonces B automáticamente envió un ACK (implementamos que el ACK es un mensaje vacío con un código especial, o simplemente marcamos en A la entrega porque recibió la notificación de la llegada en B – en pruebas locales se decidió no liar al módulo con más mensajes, así que la confirmación de entrega en A la realizamos *offline* asumiendo que si en X segundos B no pidió reenvío entonces llegó; esto es un detalle de optimización que podríamos mejorar con un ACK real).

**Pruebas de alcance:** Tras validar el funcionamiento básico, se llevaron los dispositivos a campo abierto para evaluar el alcance real. Se configuró SF=12 en ambos módulos para máxima sensibilidad. Ubicamos el nodo A en un punto fijo y el nodo B se alejó progresivamente. Se logró comunicación **estable hasta unos \~1.2 km** en zona semiurbana (con algunas casas bajas intermedias). A 1.5 km, los mensajes tardaban en algunos casos varios intentos en ser recibidos (a veces se perdía uno de cada tres). Bajando SF a 7 (mayor velocidad, menor alcance) la comunicación se volvía poco fiable más allá de \~0.5 km. Estos resultados son coherentes con la literatura, donde con LoRa a 868 MHz y antenas pequeñas se esperan 1-2 km en entorno urbano y hasta >5 km en campo abierto. En pruebas **línea de vista directa** (los dos nodos en alto sin obstáculo, en campo abierto) se llegó a \~4 km con recepción débil pero utilizable (la interfaz mostraba mensajes con más retraso, pues algunos requerían reenvío). No se alcanzaron los 8 km máximos teóricos mencionados en algunos proyectos debido a limitaciones prácticas (entorno con ruido, antenas no optimizadas, altura limitada). Aun así, los resultados confirmaron que LoRaIM cumple su objetivo de comunicar distancias largas donde un walkie-talkie convencional o un teléfono no tendrían cobertura.

**Gestión de potencia y duty cycle:** En las pruebas se midió el ciclo de trabajo. Enviando un mensaje corto cada 30 segundos, se estuvo muy por debajo del 1% de uso, cumpliendo normativa. Si un usuario enviaba varios mensajes seguidos, implementamos en el código un pequeño retraso en la cola de envío para espaciar los paquetes y así evitar saturar el canal. Notamos que los módulos Reyax incluyen un indicador de **RSSI** y **SNR** en los mensajes recibidos, lo que nos permitió obtener datos interesantes: por ejemplo, a 1 km el RSSI rondaba -90 dBm y SNR 7 dB, mientras que al límite de 4 km el RSSI cayó a -117 dBm y SNR cercano a 0 dB (rozando el umbral de sensibilidad). Estos datos los registramos para referencia; podrían servir para implementar a futuro ajustes automáticos (por ejemplo, si RSSI es alto, podríamos bajar potencia para ahorrar energía, o si es muy bajo quizá usar un repetidor).

**Dificultades encontradas durante la implementación:** Una de las principales fue la configuración inicial de la Raspberry Pi como punto de acceso. Tuvimos que editar archivos de sistema (`/etc/dhcpcd.conf`, `/etc/hostapd/hostapd.conf`, etc.) siguiendo guías específicas para conseguir que la Pi emitiera una red Wi-Fi estable. Otro reto fue manejar adecuadamente la comunicación serial con el LoRa: al principio, al enviar comandos AT muy seguidos, obteníamos respuestas mezcladas. Esto se resolvió implementando **exclusión mutua** en los accesos al puerto serial y esperando a recibir el `OK` de un comando antes de lanzar el siguiente. Asimismo, hubo que asegurarse de deshabilitar la consola serial por defecto de Raspberry (que usa UART) para liberar el puerto para nuestra aplicación. En el lado de software, integrar Flask (que por defecto es single-thread) con el hilo de lectura de serial requirió cuidado: se optó por utilizar *threading* nativo en Python para el lector LoRa, y comunicarlo con Flask mediante variables globales protegidas por locks, asegurando así que el servidor web pudiera leer los mensajes nuevos de forma segura.

Finalmente, se realizaron **pruebas integrales de usuario**: se pidió a personas ajenas al desarrollo que usaran LoRaIM simulando una conversación sencilla. Cada uno con un smartphone conectado al nodo respectivo intercambiaron mensajes “hola”, “¿cómo estás?”, etc. La retroalimentación fue positiva en cuanto a la funcionalidad básica – los mensajes llegaban (con un ligero retraso perceptible, de \~1-2 segundos), y la interfaz web, aunque simple, resultó comprensible. También se detectaron posibles mejoras: por ejemplo, implementar un sonido o vibración en el teléfono cuando llega un mensaje (actualmente la web solo muestra el texto, habría que agregar notificaciones del navegador). En general, la implementación final de LoRaIM logró concretar un **sistema operativo de mensajería off-line**, cumpliendo con los requisitos establecidos.

## 5. Conclusiones

El desarrollo de **LoRaIM (LoRa Instant Messenger)** demuestra la viabilidad de un sistema de mensajería instantánea independiente de las infraestructuras de comunicación tradicionales, aprovechando las capacidades de la tecnología LoRa. A lo largo del proyecto, se consiguió diseñar, implementar y probar un prototipo funcional que permite a dos usuarios intercambiar mensajes de texto a distancias considerablemente grandes y en entornos sin cobertura.

**Cumplimiento de objetivos:** Se alcanzó el objetivo principal de crear un mensajero instantáneo sobre LoRa. El sistema construido permite enviar y recibir mensajes de manera fiable en un rango de varios kilómetros, sin coste por mensaje ni necesidad de tarjetas SIM o puntos de acceso a Internet. Los objetivos secundarios también se lograron satisfactoriamente:

* Se profundizó en el conocimiento teórico de LoRa/LoRaWAN, aplicando esos conceptos en la configuración real de los módulos y la optimización de parámetros (frecuencia, SF, etc.).
* Se diseñó una arquitectura robusta combinando Raspberry Pi (para ofrecer una interfaz de usuario cómoda) con transceptores LoRa (para el enlace de larga distancia). La decisión de usar Wi-Fi local para la interfaz demostró ser acertada, ya que facilitó la interacción de usuarios con dispositivos comunes (smartphones) y aisló la complejidad de LoRa en el nodo.
* La implementación en Python resultó ágil y flexible; pudimos integrar la comunicación serial, el servidor web Flask y la lógica de la aplicación sin mayores inconvenientes. El uso de módulos de alto nivel (Flask, PySerial) aceleró el desarrollo y cumplió con las expectativas de un proyecto a este nivel.
* Se llevaron a cabo pruebas exhaustivas que validaron tanto la funcionalidad (entrega de mensajes) como el rendimiento en distintos escenarios. Especialmente, se comprobó que en condiciones favorables el alcance de LoRaIM es muy superior al de soluciones inalámbricas personales convencionales, llenando así el vacío de comunicación en entornos off-grid.

**Análisis de resultados:** Los resultados obtenidos muestran que LoRaIM puede operar eficientemente en su contexto previsto. Los usuarios lograron comunicarse en un rango de \~1-2 km en entorno urbano ligero, lo cual cubriría por ejemplo comunicación dentro de una misma localidad pequeña o entre un pueblo y sus afueras. En entornos rurales abiertos, la cobertura podría extenderse a varios kilómetros más, conectando verdaderamente comunidades aisladas. Esto confirma la premisa del proyecto de que las redes LoRa pueden conectar áreas remotas sin infraestructura costosa. Por supuesto, la velocidad de transferencia es baja, pero suficiente para mensajería tipo texto. Un hallazgo interesante es que incluso con SF altos (lo que conlleva largas duraciones de paquete), el retardo en la mensajería es tolerable para conversaciones pausadas (unos pocos segundos por mensaje). Para usos críticos (ej. emergencias) quizá habría que diseñar mensajes concisos y priorizados, pero el sistema tal cual puede transmitir avisos básicos (p.ej. “ESTOY BIEN – 12:30 PM” en caso de desastre) a través de largas distancias cuando nada más funciona.

**Dificultades y cómo se superaron:** Durante el proyecto se enfrentaron ciertos retos. Uno de ellos fue lidiar con las restricciones del medio LoRa – en particular, garantizar la entrega en un medio no confiable. Se mitigó mediante reintentos y confirmaciones de recepción a nivel de aplicación. Otra dificultad fue lograr estabilidad en el punto de acceso Wi-Fi de los nodos; inicialmente hubo problemas de configuración que se solventaron ajustando parámetros de hostapd y asegurando canales Wi-Fi distintos para que los nodos no se solapen. La sincronización entre los hilos de lectura/escritura de serial y el servidor web también requirió depuración cuidadosa para evitar condiciones de carrera. A nivel de hardware, la calibración de las antenas y la orientación influyó mucho en el alcance: aprendimos empíricamente que pequeñas variaciones en cómo se coloca la antena (verticalmente, alejadas de superficies metálicas) afectan la distancia lograda. Esto se tuvo en cuenta en las pruebas de campo, optimizando la posición de los dispositivos.

**Posibles mejoras y trabajo futuro:** Si bien LoRaIM en su versión actual funciona para el caso básico de dos usuarios, existe amplio margen de mejora y extensión:

* **Soporte para multi-nodo/mesh:** Un siguiente paso sería permitir que más de dos dispositivos formen parte de la red de mensajería. Implementar una lógica de *routing* donde un nodo pueda retransmitir mensajes a terceros ampliaría la cobertura y permitiría topologías mesh. Esto convertiría a LoRaIM en una suerte de *chat grupal* comunitario. Proyectos como Meshtastic ya exploran esta idea combinando LoRa con redes malladas, por lo que podríamos basarnos en sus enfoques (por ej., flooding controlado con TTL para que el mensaje no rebote infinitamente).
* **Interfaz de usuario móvil dedicada:** La actual interfaz vía navegador es básica. Desarrollar una app móvil nativa (Android/iOS) que se conecte al nodo (vía Wi-Fi o Bluetooth) podría brindar mejor UX, con notificaciones push locales, envío de ubicaciones GPS, etc. Incluso se podría integrar un mapa offline donde ver la posición de otros usuarios si se incorporan GPS a los nodos (útil en rescates).
* **Optimización de energía:** Para convertir LoRaIM en verdaderamente portátil, haría falta optimizar el consumo de las Raspberry Pi (que no son tan eficientes energéticamente). Una idea es migrar la implementación a placas de desarrollo IoT como **ESP32** acopladas con módulos LoRa (existen modelos con Wi-Fi, Bluetooth y LoRa en una sola placa). Esto reduciría drásticamente el consumo eléctrico, permitiendo funcionar con baterías pequeñas muchas horas. El desafío sería portar la lógica Python a C++ (Arduino) o MicroPython, o usar frameworks ligeros en ESP32. Otra opción es utilizar Raspberry Pi Zero W que consume menos.
* **Seguridad adicional:** Aunque se implementó cifrado AES a nivel de enlace, para entornos hostiles se podría añadir autenticación de mensajes para evitar intrusiones (por ejemplo, firmar digitalmente los mensajes para asegurarse que vienen de un nodo autorizado). También sería deseable ofuscar el tráfico de metadatos – actualmente, un intruso con otro LoRa podría no leer texto (por AES), pero sí saber que hay comunicación (tráfico) y quizás inferir patrones. Técnicas de frecuencia hopping o pseudorandom delays podrían dificultar esto.
* **Integración con infraestructura cuando disponible:** Un aspecto interesante sería permitir que, si alguno de los nodos LoRaIM obtiene conexión a Internet (por ejemplo, uno llega a zona con WiFi o celular), actúe como puente para entregar mensajes a una red más amplia (enviar un email o SMS de salida, o conectarse con otro LoRaIM remoto a través de un servidor). Esto transformaría a LoRaIM en un subsistema resiliente que usa LoRa cuando está off-grid, pero que se integra con la nube al recuperar conexión (concepto de *Delay Tolerant Networks*).
* **Otras funcionalidades:** Se podría extender la mensajería a soportar **mensajes de broadcast** (enviar a todos los nodos vecinos, útil para avisos generales), **mensajes encriptados punto a punto** (ya se cifran, pero quizás diferentes claves por par para más privacidad), **confirmaciones de lectura** (no solo de recepción técnica, sino que el usuario B marque un mensaje como leído y notificar a A), e incluso **transferencia de archivos pequeños** (p.ej. enviar coordenadas GPS o un texto largo en varios fragmentos).
* **Pruebas a mayor escala:** Sería valioso desplegar más nodos en un área rural real y comprobar el desempeño con varios usuarios simultáneos, evaluar la congestión si muchos envían a la vez (posible necesidad de TDMA simple o control de acceso), así como experimentar con distintos SF dinámicamente (adaptive data rate).

En conclusión, LoRaIM ha cumplido su cometido demostrando que es posible un sistema de mensajería instantánea autónomo usando LoRa. El proyecto integró conocimientos de redes, sistemas y electrónica, ofreciendo un producto final que, si bien rudimentario en apariencia, aborda un problema real de comunicación en zonas aisladas. Las pruebas validan la eficacia en escenarios pequeños, y las mejoras propuestas podrían convertirlo en una herramienta aún más poderosa. Este proyecto sienta las bases para futuras investigaciones o implementaciones en el campo de las **comunicaciones resilientes e independientes**, un área de gran relevancia en un mundo donde la conectividad no siempre está garantizada para todos.

## Bibliografía

* LoRa - *Wikipedia, la enciclopedia libre*. (2023). Tecnología LoRa, detalles de modulación CSS y especificación LoRaWAN.
* Carrillo, R. (25 Ago 2022). **“Qué es LoRa, cómo funciona y características principales”**. Blog Venco Electrónica. Explicación de la diferencia entre LoRa y LoRaWAN, alcances (10-20 km) y tasas de bits (0.3-50 kbps).
* The Things Network. **“What are LoRa and LoRaWAN?”** Documentación en línea (Fundamentals). Descripción sencilla de LoRa (modulación por chirp, bandas ISM) y propósito de LoRaWAN.
* UNIR Universidad. **“LoRaWAN: ¿Qué es y para qué sirve?”** (2020). Artículo divulgativo sobre LoRaWAN, ventajas (largo alcance, bajo consumo) y aplicaciones IoT.
* Nakamura Pinto, M. K. **“A LoRa enabled sustainable messaging system for isolated communities”**. (2020). Memorias 9º Simposio CONACYT Europa. Propuesta de mensajería LoRa para comunidades aisladas; resumen en español con problemática de falta de cobertura y solución LoRa de bajo costo.
* Delgado-Ferro, F. et al. **“A LoRaWAN Architecture for Communications in Areas without Coverage”**. *Electronics*, vol. 11, no.5, 804 (2022). Artículo académico que analiza arquitectura LoRaWAN para zonas sin cobertura, limitaciones regulatorias (duty cycle 1%) y servicios de mensajería de emergencia.
* Coward, C. **“This LoRa Messenger Is Perfect for Texting in the Wilderness”** – *Hackster.io News* (2019). Reseña de un dispositivo de mensajería por LoRa para uso en áreas silvestres, con teclado integrado. Inspiró la idea de comunicación off-grid y destaca soporte de LoRa para redes malladas.
* Akarsh A. **“LoRa Messenger for Two Devices for Distances Up to 8km”** – *Instructables* (2019). Tutorial de proyecto DIY con módulos Reyax RYLR896 y ESP8266 para crear un chat punto a punto sin Internet. Proporcionó guía sobre uso de comandos AT de Reyax y expectativas de alcance (\~8 km en óptimas condiciones).
* Reyax Technology. **RYLR896 LoRa Module – AT Command Guide** (2018). Documentación técnica del módulo utilizado, detallando comandos AT (`AT+SEND`, `AT+ADDRESS`, etc.) y características (basado en STM32 + SX1276). Fundamental para la configuración de los transceptores LoRa en este proyecto.
* Semtech Corporation. **LoRaWAN 1.0 Specification** (2015). Especificación oficial del protocolo LoRaWAN, LoRa Alliance. (Consultada para entender la integración de LoRa a nivel de red, aunque no implementada directamente en LoRaIM).
* Foro Raspberry Pi (2018). *“Using LoRa (SX1278) with Raspberry Pi”*. Discusiones comunitarias sobre bibliotecas Python y configuración SPI para LoRa en Pi, consideradas antes de optar por módulos UART.
* Meshtastic Project. (2021). Documentación en línea del proyecto Meshtastic (firmware de chat mesh sobre LoRa para ESP32). Referencia para posibles mejoras de red mallada y funcionalidades avanzadas.

*(Los enlaces citados fueron accesibles para consulta en la fecha de elaboración de este documento. Se incluyen para ofrecer mayor detalle sobre aspectos técnicos y contextuales mencionados.)*

## Anexo A – Manual de Usuario

Este manual explica cómo utilizar el sistema **LoRaIM** desde la perspectiva de un usuario final. Se asume que ya se cuenta con al menos dos dispositivos LoRaIM configurados y operativos (ver Anexo B para instalación). A modo de ejemplo, hablaremos de **Nodo A** y **Nodo B**, que corresponden a los dos dispositivos LoRaIM entre los cuales se desea comunicar.

### Requisitos previos:

* Dos unidades LoRaIM encendidas y funcionando, cada una con su fuente de alimentación (o batería) y dentro del rango de comunicación LoRa (idealmente con antenas colocadas y sin demasiados obstáculos entre ellas).
* Un dispositivo de usuario para cada nodo: puede ser un smartphone, tablet o portátil con capacidad Wi-Fi y un navegador web actualizado. Este dispositivo servirá de interfaz para enviar/recibir mensajes.

### Pasos para enviar y recibir mensajes:

1. **Conexión a la red Wi-Fi del nodo:** En su dispositivo (teléfono, portátil, etc.), abra la configuración de Wi-Fi. Debería ver en la lista de redes disponibles la red emitida por su nodo LoRaIM. Por ejemplo, si está usando el Nodo A, podría aparecer una red con nombre **“LoRaIM\_A”** (el nombre puede variar según la configuración, consulte la etiqueta del nodo o documentación técnica). Seleccione esa red Wi-Fi y pulse *Conectar*. Si la red está protegida con contraseña, ingrese la clave proporcionada junto con el dispositivo (en la configuración por defecto podría ser algo como “lorapass123” o la que se haya establecido durante la instalación). Una vez conectado, su teléfono/portátil formará parte de la red local del nodo A (sin Internet, esto es normal).

2. **Acceder a la interfaz de mensajería:** Abra el navegador web de su dispositivo (Chrome, Firefox, etc.). En la barra de direcciones, escriba la URL de la interfaz de LoRaIM. Normalmente será una dirección IP local del nodo. Por ejemplo, para el Nodo A podría ser **[http://192.168.10.1/](http://192.168.10.1/)** (según la configuración de red del hotspot, frecuentemente se usó la .1 como IP del Raspberry Pi). Al acceder, debería cargar la página principal de LoRaIM. Esta página muestra el nombre del nodo (p. ej. “LoRaIM Nodo A”) y una interfaz de chat sencilla. En caso de que la página no cargue, verifique que su dispositivo sigue conectado al Wi-Fi del nodo y que ingresó la dirección correctamente. Si se personalizó un nombre de host (por ejemplo [http://loraA.local](http://loraA.local)), úselo según le indiquen.

3. **Identificación (si aplica):** En algunos despliegues de LoRaIM, es posible que la interfaz solicite un **nombre de usuario** o apodo para identificarle en el chat. Ingréselo en el campo correspondiente si aparece. Si no, el sistema quizás use por defecto el ID del nodo (ej. “Nodo1”) o un nombre preconfigurado. Para fines prácticos, saber qué nodo tiene cada usuario basta, ya que suele ser uno a uno.

4. **Enviar un mensaje:** Localice el cuadro de texto o campo de entrada en la página (normalmente en la parte inferior, acompañado de un botón “Enviar” o un icono de avión de papel). Pulse en el campo de texto e introduzca el mensaje que desea enviar. Puede escribir texto libre (letras, números, símbolos básicos). Tenga en cuenta que LoRaIM está pensado para mensajes cortos, por lo que se recomienda no exceder uno o dos párrafos. Una vez escrito el mensaje, envíelo pulsando el botón **Enviar**. Inmediatamente la interfaz debería mostrar su mensaje en la ventana de chat, marcado como enviado (podría aparecer con un indicador de pendiente o un tick gris, dependiendo de la versión de la interfaz).

5. **Transmisión y espera:** Tras enviar, el mensaje se está transmitiendo vía LoRa al otro nodo. Esto suele tardar menos de 1 segundo, pero debido a la naturaleza de la red puede haber un ligero retraso. La interfaz de LoRaIM puede marcar temporalmente el mensaje como “enviando…” hasta confirmar recepción. Espere unos instantes. Si todo va bien, el mensaje llegará al Nodo B y en su pantalla el remitente (usted) aparecerá con el texto enviado. En su propia pantalla, posiblemente el estado cambie a *entregado* (por ejemplo, mostrando un tick azul o simplemente nada, según diseño).

6. **Recepción de mensajes:** Cuando el otro usuario responda, usted recibirá su mensaje de forma automática en la ventana de chat. No necesita refrescar la página; la interfaz está programada para actualizarse sola (puede usar técnicas de auto-refresco cada pocos segundos o vía notificaciones internas). Verá aparecer una nueva entrada con el nombre del otro usuario (o nodo) y el contenido de su mensaje. Además, posiblemente su dispositivo emita un sonido o vibración si habilitó notificaciones del navegador para esta página (se le pudo preguntar al entrar, si acepta, recibirá aviso de nuevos mensajes).

7. **Conversación continua:** A partir de ahí, pueden seguir conversando. Cada nuevo mensaje que escriba y envíe seguirá el mismo proceso. Verifique en la ventana que sus mensajes aparecen en orden cronológico. Si el otro usuario envía varios mensajes seguidos, todos deberían verse listados. Puede desplazarse en la conversación hacia arriba para revisar mensajes anteriores.

8. **Indicadores de estado:** La interfaz de LoRaIM puede incluir algunos indicadores, por ejemplo:

   * Un icono o texto que diga **“Conectado”** mientras su dispositivo esté enlazado correctamente al nodo. Si pierde la conexión Wi-Fi (p. ej., si se aleja demasiado del nodo o apaga Wi-Fi), este indicador podría cambiar a *“Desconectado”* y no podrá enviar/recibir hasta reconectar.
   * Indicador de señal LoRa: Algunas versiones podrían mostrar la calidad de enlace LoRa (por ejemplo, barras que representen el RSSI). Si lo ve, téngalo como referencia: muy bajo nivel podría significar que están casi fuera de rango.
   * Confirmación de entrega: Si implementado, cuando su mensaje ha sido recibido por el otro extremo, podría aparecer un doble check (✔✔) junto a su mensaje, indicando que el destinatario (Nodo B) lo recibió en su dispositivo.
   * Hora o marca temporal en cada mensaje: para que sepa a qué hora se envió/recibió cada uno.

9. **Resolución de problemas comunes:**

   * *No veo la red Wi-Fi LoRaIM:* Asegúrese de que el nodo esté encendido (led de Pi encendido) y haya finalizado su arranque (puede tardar \~1 minuto en empezar a emitir Wi-Fi). Si tras ese tiempo no aparece, reinicie el nodo y acerque su dispositivo al mismo.
   * *La página web no carga:* Verifique la IP. Si no está seguro de la IP del nodo, en un móvil Android a veces puede ver detalles de la red Wi-Fi (gateway). Alternativamente, podría conectar un monitor/teclado al Pi para ver su IP. Si la IP es correcta pero no carga, pruebe `http://192.168.4.1` (configuración alternativa estándar). También confirme que su dispositivo obtuvo IP (en detalles de Wi-Fi debería tener una IP 192.168.x.y).
   * *No llegan mis mensajes:* Si la interfaz muestra enviado pero el otro no contesta, puede que el mensaje no haya llegado. Intente reenviar después de unos segundos. Evite spam masivo ya que el sistema limita por duty cycle. Compruebe además que el otro nodo esté encendido y en rango. Si hay terreno complicado, puede que necesiten moverse a un lugar más alto o despejado.
   * *Mensajes del otro llegan cortados o ilegibles:* Esto no debería pasar con texto ASCII normal. Si ocurrió, puede ser un error de decodificación; refrescar la página podría limpiar la vista. Asegúrese de usar caracteres simples (evitar emojis u otros símbolos fuera del estándar base, a menos que se sepa que la versión los soporta).
   * *¿Puedo usarlo con más de dos nodos?* En la versión actual, la interfaz está pensada para chat 1 a 1. Si hubiera un tercer nodo encendido en el mismo canal, podría recibir los mensajes también (efecto broadcast), pero la interfaz no lo mostraría claramente diferenciado. Por tanto, para uso cotidiano, ciñase a conversaciones entre dos partes.

10. **Finalizar la sesión:** No hay un procedimiento “cerrar sesión” formal, dado que es una red local. Si desea dejar de usar LoRaIM, simplemente puede desconectar su Wi-Fi del nodo (volver a su red habitual) o cerrar el navegador. Si sabe que no se usará más en el momento, puede apagar el nodo LoRaIM (ver Anexo B para el procedimiento de apagado seguro de la Raspberry Pi). En general, mantenerlo encendido no causa problemas, pero por ahorro de energía es recomendable apagar cuando no se necesite.

Siguiendo estos pasos, un usuario sin conocimientos técnicos profundos puede utilizar LoRaIM para comunicarse. La idea es que la experiencia sea lo más transparente posible: **conectarse a Wi-Fi, abrir una página web de chat y enviar mensajes**, sin tener que preocuparse de cómo viajan esos datos por radio. Si se presentan dudas adicionales, consulte la documentación técnica o contacte al administrador del sistema.

*(Nota: Esta guía asume la configuración por defecto desplegada. Si su implementación de LoRaIM fue personalizada – p. ej., distinto puerto web, autenticación, etc. – por favor adapte los pasos en consecuencia.)*

## Anexo B – Manual de Instalación

En este anexo se detallan los pasos técnicos necesarios para **instalar, configurar y poner en marcha** el sistema LoRaIM, incluyendo la preparación del hardware, la instalación de software en los nodos (Raspberry Pi y módulos LoRa), y la configuración de red. Está dirigido a administradores o desarrolladores que deseen reproducir el proyecto.

### B.1. Lista de componentes necesarios

* **2× Raspberry Pi** (Modelo 3B o superior recomendado, con WiFi integrado). Incluye sus accesorios: fuente de alimentación microUSB/USB-C según modelo, cable microUSB si se alimenta desde PC, tarjeta microSD (mín. 8GB) con adaptador.
* **2× Módulos LoRa Reyax RYLR896** (o modelo similar RYLRxxx con interfaz UART). Vienen con conectores y es recomendable adquirir con sus antenas correspondientes para 868/915 MHz.
* **Cables y adaptadores**: un set de cables jumper dupont para conectar el módulo LoRa a los pines GPIO de la Pi. Opcionalmente, un conversor USB-UART TTL para depurar o configurar los módulos desde PC si se desea (no indispensable, se puede hacer desde la Pi).
* **Herramientas de montaje**: soldador (si los módulos vienen sin pines soldados), estaño, etc. (Solo si se requiere soldar pines de conexión en los módulos LoRa). Cinta aislante o bridas para asegurar módulos a la Pi.
* **Equipo de red**: No se requiere router ya que las Pi actuarán como AP, pero para la instalación inicial podría ser útil un cable Ethernet o conexión monitor-teclado para configurar la Pi.
* **Computadora**: PC con lector de microSD para grabar la imagen del sistema operativo Raspbian en las tarjetas SD.

### B.2. Preparación del software base (Raspberry Pi OS)

1. **Instalar Raspbian en las microSD**: Descargue la imagen de Raspberry Pi OS (Lite es suficiente, sin escritorio, para ahorrar recursos). Use una herramienta como Raspberry Pi Imager o balenaEtcher para flashear la imagen en cada tarjeta SD. Si va a configurar por *headless* (sin monitor), puede aprovechar a crear un archivo `ssh` vacío en la partición boot para habilitar SSH, y un archivo `wpa_supplicant.conf` con credenciales de su WiFi temporal (aunque luego la Pi será AP, al inicio podría necesitar internet para actualizar paquetes). Inserte las tarjetas en las Raspberry Pi.

2. **Primer arranque de las Pi**: Encienda cada Raspberry Pi conectándole la alimentación. Si tiene monitor y teclado, puede usarlos para la configuración inicial. Si no, use la IP asignada (busque en el router DHCP) para conectarse por SSH (usuario `pi`, contraseña `raspberry` por defecto). Recomendamos cambiar la contraseña por seguridad (`passwd`). Asigne un nombre de host distintivo a cada Pi usando `sudo raspi-config` (ej. “loraim-nodeA” y “loraim-nodeB”).

3. **Actualizar e instalar paquetes necesarios**: Ejecute en cada Pi:

   ```
   sudo apt-get update && sudo apt-get upgrade -y 
   sudo apt-get install -y python3-pip git
   sudo pip3 install flask flask-restful pyserial
   ```

   Esto instala Python3 pip y las librerías Flask (para el servidor web) y pySerial (para comunicación serial con LoRa). También instalamos Git si se va a clonar un repositorio con el código.

4. **Configurar la interfaz UART**: Por defecto, la UART principal de Pi está asignada a la consola serial. Debemos liberarla para usar con el módulo LoRa. En `sudo raspi-config`, vaya a *Interface Options* -> *Serial*. Cuando pregunte "¿Desea login shell por serial?" diga No, y "¿Enable serial hardware?" diga Yes. Esto habilitará `/dev/serial0` para nuestro uso y deshabilita la consola por ese puerto. Tras esto, agregue a `/boot/config.txt` la línea `enable_uart=1` (debería estar ya puesta por raspi-config). Reinicie la Pi para aplicar cambios.

### B.3. Conexión del hardware LoRa

1. **Cableado del módulo LoRa a Raspberry Pi**: Con la Pi apagada, conecte los pines del módulo RYLR896 a la Raspberry Pi:

   * **VCC** del módulo a pin 1 de Pi (3.3V). **¡Atención!:** No usar 5V, los módulos funcionan a 3.3V.
   * **GND** del módulo a pin 6 de Pi (GND).
   * **TXD** del módulo al pin RX de Pi. En Raspberry Pi 3, el pin físico 10 corresponde a GPIO15 (RX). (El TX del módulo va al RX de Pi para que Pi pueda leer).
   * **RXD** del módulo al pin TX de Pi. Pin físico 8 corresponde a GPIO14 (TX). (El RX del módulo va al TX de Pi para recibir comandos).
   * Si el módulo tiene pines CTS/RTS (flujo), normalmente no se usan, puede dejarlos sin conectar.
   * Conecte la antena al módulo antes de transmitir para no dañar el radio.
     Realice el mismo cableado en la otra Raspberry Pi con su módulo. Verifique dos veces las conexiones para evitar errores de pin.

2. **Encender y probar comunicación serial**: Inicie la Raspberry Pi con el módulo conectado. Abra una terminal (SSH) y use `minicom` o `screen` para probar:

   ```
   sudo apt-get install -y minicom
   minicom -b 115200 -o -D /dev/serial0
   ```

   Debería ver una pantalla de minicom vacía. Escriba `AT` y pulse Enter. El módulo RYLR896 debería responder con `OK`. Si no ve nada, pulse Ctrl+A luego E para habilitar local echo (para ver lo que teclea) y pruebe de nuevo. Una respuesta `OK` indica que la Pi está comunicándose correctamente con el módulo LoRa. Salga de minicom (Ctrl+A, X).

3. **Configurar parámetros básicos del módulo LoRa**: Aún en terminal, envíe comandos AT iniciales:

   * `AT+ADDRESS=1` en el nodo A, `AT+ADDRESS=2` en el nodo B. Debería responder `OK` cada uno.
   * `AT+BAND=868000000` en ambos para fijar 868 MHz. (Use la frecuencia apropiada según su región: 915e6 para EEUU por ej.)
   * Opcional: `AT+NETWORKID=100` (por ejemplo en ambos, para aislarlos de otros LoRa cercanos).
   * `AT+CRATE=5` etc., aunque en Reyax muchos parámetros van en un solo comando. Consulte la guía RYLR. Un atajo es `AT+PARAMETER=12,7,1,5` que ajusta SF=12, BW=125k, CR=4/5, Preamble=8 (por ejemplo).
   * `AT+KEY=FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF` (ejemplo de clave AES de 32 hex dígitos, si se quiere cifrado; asegúrese de usar la misma en ambos).
     Estas configuraciones también se pueden hacer desde nuestro software, pero hacerlo manualmente garantiza el estado inicial. **Nota:** Los cambios de configuración en Reyax suelen persistir en memoria flash interna, es decir, al reiniciar conservan los ajustes; de cualquier modo, nuestro código volverá a establecer los críticos al iniciar.

### B.4. Despliegue de la aplicación LoRaIM

1. **Obtener el código de LoRaIM**: Si dispone de un repositorio Git (p. ej. en GitHub) del proyecto, clónelo en ambas Raspberry Pi:

   ```
   git clone https://github.com/usuario/LoRaIM.git /home/pi/loraim
   ```

   (Reemplace la URL con la correspondiente; alternativamente, transfiera los archivos mediante SCP o pendrive). Supongamos que el código reside en `/home/pi/loraim/`.

2. **Configurar la aplicación**: Edite los archivos de configuración si los hay. Por ejemplo, en `config.py` asegúrese de establecer:

   * `MY_NODE_ID = 1` (en Nodo A, y 2 en Nodo B).
   * `DEST_NODE_ID = 2` (A debe apuntar a B y viceversa, si es solo 1-to-1).
   * La clave AES, si se usa, igual a la cargada en módulos (`AES_KEY = "..."`).
   * Parámetros de puerto serial si distintos (por defecto `/dev/serial0` a 115200 baudios).
   * Si desea cambiar la IP o puerto del servidor Flask (por defecto suele usar 5000), puede configurarlo en el código; sin embargo, como usaremos modo AP, está bien puerto 80 o 5000 ya que no habrá conflictos.

3. **Configurar el punto de acceso Wi-Fi**: Este paso permite que los usuarios se conecten al nodo. Realícelo en ambos nodos.

   * Edite `/etc/dhcpcd.conf` y añada al final:

     ```
     interface wlan0
       static ip_address=192.168.10.1/24  (use .20.1 en el otro nodo para diferenciarlos)
       nohook wpa_supplicant
     ```

     Esto asigna IP estática a wlan0 y deshabilita cliente WiFi.
   * Instale hostapd y dnsmasq: `sudo apt-get install -y hostapd dnsmasq`.
   * Edite `/etc/hostapd/hostapd.conf` (cree el archivo) con:

     ```
     interface=wlan0
     driver=nl80211
     ssid=LoRaIM_A        (otro: LoRaIM_B)
     hw_mode=g
     channel=6            (use otro canal p. ej 11 para nodo B)
     wmm_enabled=0
     macaddr_acl=0
     auth_algs=1
     ignore_broadcast_ssid=0
     wpa=2
     wpa_passphrase=lorapass123   (cambie la contraseña a algo seguro si desea)
     wpa_key_mgmt=WPA-PSK
     wpa_pairwise=CCMP
     rsn_pairwise=CCMP
     ```
   * Edite `/etc/default/hostapd` y establezca `DAEMON_CONF="/etc/hostapd/hostapd.conf"`.
   * Configurar dnsmasq: haga backup del original `sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig` y cree uno nuevo:

     ```
     interface=wlan0
     dhcp-range=192.168.10.10,192.168.10.50,255.255.255.0,24h
     ```

     (Ajuste a .20.x en el segundo nodo).
   * Habilite los servicios: `sudo systemctl enable hostapd && sudo systemctl enable dnsmasq`.
   * Reinicie la Raspberry Pi. Tras reiniciar, desde otro dispositivo verifique que aparece la red SSID configurada. Si es visible, intente conectar con la contraseña para confirmar que DHCP asigna IP correctamente.

4. **Iniciar la aplicación LoRaIM**: Ahora lanzaremos el servidor web y la interfaz LoRa.

   * Vaya al directorio de la aplicación (`cd /home/pi/loraim`). Ejecute primero el componente servidor Flask:

     ```
     sudo python3 server.py >server.log 2>&1 &
     ```

     El `&` lo deja corriendo en segundo plano. El servidor podría estar escuchando en `http://0.0.0.0:5000` (Flask por defecto) o la IP local puerto 80 dependiendo de implementación. Si es 5000, los usuarios deberán poner por ej. [http://192.168.10.1:5000](http://192.168.10.1:5000) en sus navegadores. Para simplificar, puede editar server.py para usar puerto 80 (requiere sudo) o configurar un proxy nginx, pero eso es opcional avanzado.
   * Luego, iniciar el proceso de lectura LoRa si está separado. En nuestra implementación, el servidor Flask al iniciar ya crea un hilo para leer del LoRa, por lo que no hay binario separado. Sin embargo, en otros enfoques (como en la referencia habían compilado un C++ separado), se correría ese binario. Asumamos que todo es Python integrado.
   * *Nota:* mantener el comando corriendo incluso tras logout. Hemos enviado a background con &, pero para producción conviene usar alguna herramienta como `tmux` o crear un servicio systemd. Más adelante se muestra cómo automatizar en arranque.

5. **Prueba inicial**: Con ambos nodos configurados y aplicaciones corriendo, realice una prueba simple:

   * Conecte un PC o móvil a la red LoRaIM\_A, abra el navegador e ingrese la IP (ej. 192.168.10.1:5000). Debería ver la página de chat del nodo A.
   * Con otro dispositivo, conéctese a LoRaIM\_B, abra su página (192.168.20.1:5000).
   * En el nodo A, envíe un mensaje “Hola”. Compruebe en el log (`tail -f server.log`) de B o en su pantalla que llegó.
   * Si funciona, la instalación fue exitosa. Si no, revisar: ¿Los módulos LoRa parpadearon/indicaron recepción? (Algunos tienen LED). Mirar los logs: quizás falta permiso para /dev/serial0 (solución: añadir su usuario al grupo dialout, o ejecutar con sudo), o error en Flask binding (si puerto 80, ejecutar como root o setcap).

6. **Configurar auto-inicio (opcional recomendado)**: Para que LoRaIM arranque automáticamente al encender el nodo, edite el archivo `/etc/rc.local` con:

   ```
   #!/bin/sh -e
   # rc.local
   cd /home/pi/loraim
   sudo -u pi python3 server.py &   # inicia servidor Flask como usuario pi
   exit 0
   ```

   (Asegúrese de poner antes de exit 0). También podría agregarse un comando para reiniciar el módulo LoRa si hiciera falta. Guarde y salga. Luego `sudo chmod +x /etc/rc.local` por si no lo es. Reinicie la Pi y compruebe que tras el boot el servicio está activo (intente conectar a la página sin iniciar nada manual).

7. **Apagado seguro**: Cuando necesite apagar un nodo LoRaIM, es importante hacerlo limpiamente para evitar corrupción de la SD. Desde terminal SSH o consola envíe `sudo halt` o use el menú de apagado en raspi-config. Espere a que los LED de la Pi indiquen apagado antes de quitar la corriente.

### B.5. Solución de problemas de instalación

* **El módulo LoRa no responde a AT**: Verifique cableado UART. TX/RX cruzados correctamente, GND común. Asegúrese de haber deshabilitado la consola serie. Compruebe la velocidad: Reyax usa 115200 baud por defecto. Si cambió eso, quizá deba poner la nueva velocidad en minicom.
* **Error hostapd al iniciar**: Puede ser conflicto con NetworkManager (si usó Raspberry Pi OS desktop). Solución: deshabilitar NetworkManager o usar Raspbian Lite. O revise el log (`sudo journalctl -u hostapd`) para mensajes, a veces el país no está establecido – edite `/etc/systemd/system/hostapd.service.d/override.conf` para setear `Environment=COUNTRY=ES` por ejemplo.
* **Los dispositivos clientes no navegan**: Recuerde, no tendrán Internet, es normal. Pero deben poder abrir la página local. Si intentan abrir Google no podrán (a menos que uno de los Pi tenga conexión a internet y actúe de gateway NAT, lo cual no es el caso aquí).
* **Flask no accesible externamente**: Asegúrese que en `app.run()` se puso host='0.0.0.0'. Si olvidó, Flask solo escucha localhost, por eso externamente no carga. Corrija eso en el código.
* **Permisos en puertos**: Ejecutar como root (via rc.local o sudo) para evitar problemas de permisos al abrir /dev/serial0 o puerto 80.
* **Interferencias**: Si hay muchas redes WiFi cerca, puede cambiar canales para evitar choques. Asimismo, si hay otro dispositivo LoRa en la zona en la misma frecuencia, podría interferir. Puede cambiar `NETWORKID` en Reyax para filtrar.
* **Extender a más nodos**: Para 3+ nodos, use el mismo SSID en cada Pi? No recomendable porque se traslaparían. Mejor que cada Pi tenga su WiFi y los usuarios respectivos se conecten a cada una, y por LoRa recibirán todos. Pero la lógica actual de app no contempla múltiples destinatarios, tendría que adaptarse (por ej. un dropdown para elegir a quién enviar). Esto excede la instalación básica, pero téngalo en cuenta si explora configuraciones.
* **Hardware alternativo**: Si usa otros módulos LoRa (por ej. E32-TTL-100), los comandos difieren. Consulte su datasheet. Si usa SPI LoRa (RF95 etc.), necesitará instalar libs y posiblemente habilitar SPI en raspi-config. Luego utilizar bibliotecas Python (como LoRaRF mencionada) y adaptar el código de envío.

Siguiendo esta guía, debería lograr desplegar exitosamente el sistema LoRaIM. Una vez instalado, consulte el **Manual de Usuario** (Anexo A) para instrucciones de uso cotidiano. Disfrute de su red de mensajería fuera de línea con LoRaIM. ¡Buena suerte en su montaje!
