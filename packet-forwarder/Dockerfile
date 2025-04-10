FROM balenalib/raspberrypi3-debian:latest

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    git build-essential cmake wiringpi python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Clonar o copiar el código del forwarder (suponiendo un repo)
WORKDIR /usr/src/app
RUN git clone https://github.com/alguien/mi-forwarder-lora.git
WORKDIR /usr/src/app/mi-forwarder-lora

# Compilar (varía según tu forwarder)
RUN make

# Exponer la entrada a logs, etc. (no siempre es necesario)
# EXPOSE 1700/udp

# Comando de arranque:
# Usar las variables de entorno para configurar IP, puertos, etc.
CMD ["./single_chan_pkt_fwd"]
