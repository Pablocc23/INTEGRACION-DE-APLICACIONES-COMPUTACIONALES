import time
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import redis
import requests
import xml.etree.ElementTree as ET
from flask_cors import CORS
from passlib.hash import sha256_crypt
import jwt

# ===========================
# CONFIGURACIÓN
# ===========================
LIBROS_HOST = "http://34.45.141.126:5001"  # microservicio Libros

app = Flask(__name__)
CORS(app)

# MariaDB: autenticación JWT
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'libros_user'
app.config['MYSQL_PASSWORD'] = '666'
app.config['MYSQL_DB'] = 'autenticacion_jwt'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# JWT
SECRET_KEY = "super_secret_jwt_key"
ALGORITHM = "HS256"
ACCESS_EXPIRES_MIN = 5
REFRESH_EXPIRES_MIN = 30

# Logger simple
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ===========================
# FUNCIONES JWT
# ===========================
def create_token(username, expires_minutes):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(minutes=expires_minutes),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None

# ===========================
# MARIA DB
# ===========================
def mariadb_insert_user(username, email, password_hash):
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO usuarios (username, email, password_hash)
        VALUES (%s, %s, %s)
    """, (username, email, password_hash))
    mysql.connection.commit()
    cur.close()

def mariadb_get_user(username):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    return row

# ===========================
# REDIS
# ===========================
def redis_set_user(username, data):
    r.hset(f"user:{username}", mapping=data)

def redis_get_user(username):
    return r.hgetall(f"user:{username}") or None

# ===========================
# ROOT
# ===========================
@app.route("/")
def root():
    return jsonify({
        "ok": True,
        "message": "Gateway: JWT + Redis + MariaDB + Libros con imágenes",
        "endpoints": {
            "/register": "Crear usuario",
            "/login": "Iniciar sesión",
            "/refresh": "Nuevo token",
            "/books": "Consulta libros del microservicio Libros"
        }
    })

# ===========================
# REGISTRO
# ===========================
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"ok": False, "error": "Faltan campos"}), 400

    # evitar duplicados
    if mariadb_get_user(username):
        return jsonify({"ok": False, "error": "Usuario ya existe"}), 409

    pwd_hash = sha256_crypt.hash(password)

    # guardar en MariaDB
    mariadb_insert_user(username, email, pwd_hash)

    # guardar en Redis
    redis_set_user(username, {
        "username": username,
        "email": email,
        "password_hash": pwd_hash
    })

    return jsonify({"ok": True, "message": "Usuario creado"}), 201

# ===========================
# LOGIN
# ===========================
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    user = redis_get_user(username) or mariadb_get_user(username)
    if not user:
        return jsonify({"ok": False, "error": "Usuario no existe"}), 404

    pwd_hash = user.get("password_hash")
    if not pwd_hash or not sha256_crypt.verify(password, pwd_hash):
        return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401

    access = create_token(username, ACCESS_EXPIRES_MIN)
    refresh = create_token(username, REFRESH_EXPIRES_MIN)

    return jsonify({
        "ok": True,
        "access_token": access,
        "refresh_token": refresh
    })

# ===========================
# REFRESH
# ===========================
@app.route("/refresh", methods=["POST"])
def refresh():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Token requerido"}), 401

    token = auth.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload:
        return jsonify({"ok": False, "error": "Refresh inválido"}), 401

    new_access = create_token(payload["sub"], ACCESS_EXPIRES_MIN)
    return jsonify({"ok": True, "access_token": new_access})

# ===========================
# PARSEAR XML DE LIBROS (CON IMÁGENES)
# ===========================
def libros_xml_to_json(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []

    for book in root.findall("book"):

        row = {
            "book_id": book.findtext("book_id", ""),
            "isbn": book.findtext("isbn", ""),
            "title": book.findtext("title", ""),
            "author": book.findtext("author", ""),
            "publisher": book.findtext("publisher", ""),
            "year": book.findtext("year", ""),
            "genre": book.findtext("genre", ""),
            "price": book.findtext("price", ""),
            "stock": book.findtext("stock", ""),
            "format": book.findtext("format", "")
        }

        # -------- NUEVO: procesar imágenes --------
        images = []
        images_parent = book.find("images")

        if images_parent is not None:
            for img in images_parent.findall("image"):
                images.append({
                    "image_id": img.findtext("image_id", ""),
                    "url": img.findtext("image_url", ""),
                    "is_primary": img.findtext("is_primary", "0") == "1",
                    "sort_order": img.findtext("sort_order", "0")
                })

        row["images"] = images
        # ------------------------------------------

        out.append(row)

    return out

# ===========================
# ENDPOINT /books (JWT requerido)
# ===========================
@app.route("/books", methods=["GET"])
def books():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Token requerido"}), 401

    token = auth.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return jsonify({"ok": False, "error": "Token inválido"}), 401

    # pasar parámetro q al microservicio
    q = request.args.get("q", "")
    url = f"{LIBROS_HOST}/api/books"
    if q:
        url += f"?q={requests.utils.quote(q)}"

    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "No se pudo contactar microservicio Libros",
            "detail": str(e)
        }), 502

    try:
        books = libros_xml_to_json(resp.content)
    except:
        return jsonify({"ok": False, "error": "XML inválido"}), 500

    return jsonify({"ok": True, "books": books})

# ===========================
# MAIN
# ===========================
if __name__ == "__main__":
    log.info("Servidor Flask corriendo en http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
