import os, time, json, hashlib, logging, feedparser, yaml
from threading import Thread, Event
from paho.mqtt import client as mqtt
from openai import OpenAI, APIError

log = logging.getLogger("alert_ai")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    log.warning("No OPENAI_API_KEY provided – IA disabled!")

FEEDS_YAML     = os.getenv("FEEDS_FILE", "/app/feeds.yaml")
INTERVAL       = int(os.getenv("FEED_INTERVAL", 300))   # seg
TOPIC_OUT      = os.getenv("ALERT_TOPIC_OUT", "alert/out")
TOPIC_IN       = os.getenv("ALERT_TOPIC_IN",  "alert/in")
MQTT_HOST      = os.getenv("MQTT_HOST",      "mosquitto")
MQTT_PORT      = int(os.getenv("MQTT_PORT",  1883))

client = mqtt.Client()
client.connect(MQTT_HOST, MQTT_PORT)
client.loop_start()

if OPENAI_API_KEY:
    openai = OpenAI()
    PROMPT = ("Eres un clasificador de emergencias para España. "
              "Devuelve SOLO 'ALERTA' si el texto describe un riesgo "
              "grave o inminente. Si no, devuelve 'OK'. Texto:\n\n\"{txt}\"")

def gpt_is_alert(txt: str) -> bool:
    try:
        rsp = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":PROMPT.format(txt=txt[:4000])}],
            max_tokens=1, temperature=0.0)
        return rsp.choices[0].message.content.strip().upper() == "ALERTA"
    except APIError as e:
        log.error("OpenAI error %s", e)
        return False

def load_feeds():
    try:
        with open(FEEDS_YAML) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        log.warning("Feeds file not found: %s", FEEDS_YAML)
        return []

# ── hilo que fusiona fuentes externas ─────────────────────────────────
def feed_worker(stop: Event):
    seen = set()
    feeds = load_feeds()
    while not stop.is_set():
        start = time.time()
        for feed in feeds:
            d = feedparser.parse(feed["url"])
            for e in d.entries:
                uid = hashlib.sha1((feed["name"]+e.get("id",e.link)).encode()).hexdigest()
                if uid in seen:
                    continue
                seen.add(uid)
                title = e.get("title","")
                summary = e.get("summary","")
                text = f"{title}\n{summary}"
                if OPENAI_API_KEY and gpt_is_alert(text):
                    payload = json.dumps({"src": feed["name"],
                                          "title": title,
                                          "link":  e.link,
                                          "ts":    e.get("published","")})
                    client.publish(TOPIC_OUT, payload)
                    log.info("⚠ IA publicó alerta: %s", title)
        # dormir hasta INTERVAL
        delay = INTERVAL - (time.time() - start)
        if delay > 0:
            stop.wait(delay)

# ── MQTT puente para alertas LoRa (alert/in) ──────────────────────────
def mqtt_bridge():
    def cb(_c,_u,msg):
        client.publish(TOPIC_OUT, msg.payload)
    client.subscribe(TOPIC_IN)
    client.message_callback_add(TOPIC_IN, cb)

# ── función pública para FastAPI startup/shutdown ─────────────────────
stop_evt = Event()
thread   = None
def start():
    mqtt_bridge()
    global thread
    thread = Thread(target=feed_worker, args=(stop_evt,), daemon=True)
    thread.start()
    log.info("alert_ai started.")

def stop():
    stop_evt.set()
    if thread:
        thread.join(5)
    client.loop_stop()
