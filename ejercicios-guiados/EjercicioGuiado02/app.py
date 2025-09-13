from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

# URL del API de Ollama dentro de Docker
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://ollama:11434/api")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")
        model = data.get("model", "deepseek-coder")  # default

        if not user_message:
            return jsonify({"error": "Mensaje vacío"}), 400

        ollama_request = {
            "model": model,
            "messages": [{"role": "user", "content": user_message}],
            "stream": False
        }

        resp = requests.post(
            f"{OLLAMA_API_URL}/chat",
            json=ollama_request,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        if resp.status_code == 200:
            ollama_response = resp.json()
            assistant_message = ollama_response.get("message", {}).get("content", "")
            return jsonify({"response": assistant_message})
        else:
            return jsonify({
                "error": f"Error en la API de Ollama ({resp.status_code})",
                "details": resp.text
            }), 500

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "No se puede conectar con Ollama"}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Timeout en la respuesta de Ollama"}), 408
    except Exception as e:
        return jsonify({"error": f"Error interno: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
