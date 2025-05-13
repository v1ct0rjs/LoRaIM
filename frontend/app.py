from flask import Flask, render_template, request, jsonify
import os, requests

app = Flask(__name__, static_folder="static", template_folder="templates")

# URL del backend FastAPI (dentro de la red Docker)
API_URL = os.getenv("API_URL", "http://fastapi:8000")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/messages")
def messages():
    limit = request.args.get("limit", 20)
    resp = requests.get(f"{API_URL}/messages/", params={"limit": limit})
    return jsonify(resp.json())

@app.route("/publish", methods=["POST"])
def publish():
    data = request.get_json()
    msg = data.get("message", "")
    resp = requests.post(f"{API_URL}/publish/", json={"message": msg})
    return jsonify(resp.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
