#!/usr/bin/env fish
# publish_random.fish – envía palabras aleatorias a test/topic

# ─── Configura aquí tus parámetros MQTT ────────────────────────────────
set broker  192.168.1.40
set port    1883
set topic   test/topic
set interval 10        # segundos entre mensajes

# ─── Generador sencillo de palabras aleatorias ─────────────────────────
function random_word
    # 1.  Si el diccionario estándar existe, usa una palabra real
    if test -r /usr/share/dict/words
        cat /usr/share/dict/words | shuf -n 1 | string trim
    else
        # 2.  Fallback: cadena alfanumérica de 6 letras
        set chars (string split '' abcdefghijklmnopqrstuvwxyz)
        set word ''
        for i in (seq 6)
            set word $word$chars[(random 1 (count $chars))]
        end
        echo $word
    end
end

# ─── Bucle infinito de publicación ────────────────────────────────────
while true
    set msg (random_word)
    echo "⮕  Publicando \"$msg\""
    mosquitto_pub -h $broker -p $port -t $topic -m $msg
    sleep $interval
end

