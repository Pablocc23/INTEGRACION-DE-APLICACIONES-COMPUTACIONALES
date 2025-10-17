import time
import logging
from math import isfinite
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import redis
import requests
import xml.etree.ElementTree as ET
from flask_cors import CORS
from passlib.hash import sha256_crypt
import jwt

# -----------------------
# CONFIGURACIÓN
# -----------------------
LIBROS_HOST = "http://34.71.199.168:5001"

app = Flask(__name__)
CORS(app)

# Config MariaDB
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'libros_user'
app.config['MYSQL_PASSWORD'] = '666'
app.config['MYSQL_DB'] = 'autenticacion_jwt'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# Config Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Config JWT
SECRET_KEY = "super_secret_jwt_key"
ALGORITHM = "HS256"
ACCESS_EXPIRES_MIN = 5
REFRESH_EXPIRES_MIN = 30

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('app')

# -----------------------
# FUNCIONES UTILITARIAS
# -----------------------
def time_it(fn, *args, **kwargs):
    t0 = time.time()
    res = fn(*args, **kwargs)
    t1 = time.time()
    return res, (t1 - t0)

def ratio_slower(numerator, denominator):
    if denominator <= 0 or not isfinite(denominator):
        return None
    return numerator / denominator

# JWT helpers
def create_token(username, expires_in):
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(minutes=expires_in),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# -----------------------
# OPERACIONES MARIADB
# -----------------------
def mariadb_insert_user(username, email, password_hash):
    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s)",
        (username, email, password_hash)
    )
    mysql.connection.commit()
    cur.close()

def mariadb_get_user_by_username(username):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, username, email, password_hash, created_at FROM usuarios WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    return row

# -----------------------
# OPERACIONES REDIS
# -----------------------
def redis_user_key(username):
    return f"user:{username}"

def redis_set_user_hash(username, data: dict):
    key = redis_user_key(username)
    r.hset(key, mapping=data)

def redis_get_user_hash(username):
    key = redis_user_key(username)
    data = r.hgetall(key)
    return data if data else None

# -----------------------
# ENDPOINTS
# -----------------------
@app.route("/")
def root():
    return jsonify({
        "ok": True,
        "message": "API Redis vs MariaDB + JWT + Libros",
        "endpoints": {
            "/register": "Registra usuario en Redis y MariaDB",
            "/login": "Inicia sesión y genera tokens JWT",
            "/protected": "Requiere Access Token JWT",
            "/refresh": "Genera nuevo Access Token usando Refresh",
            "/user/<username>": "Consulta usuario y tiempos",
            "/books": "Convierte XML del microservicio Libros a JSON"
        }
    })

# -----------------------
# REGISTRO
# -----------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"ok": False, "error": "Faltan campos"}), 400

    existing_mdb, t_check = time_it(mariadb_get_user_by_username, username)
    if existing_mdb:
        return jsonify({"ok": False, "error": "Usuario ya existe"}), 409

    pwd_hash = sha256_crypt.hash(password)
    redis_data = {"username": username, "email": email, "password_hash": pwd_hash}

    _, t_redis_insert = time_it(redis_set_user_hash, username, redis_data)
    _, t_mdb_insert = time_it(mariadb_insert_user, username, email, pwd_hash)
    mdb_row, _ = time_it(mariadb_get_user_by_username, username)

    _, t_redis_update = time_it(redis_set_user_hash, username, {
        "id": str(mdb_row["id"]),
        "username": mdb_row["username"],
        "email": mdb_row["email"],
        "password_hash": mdb_row["password_hash"],
        "created_at": str(mdb_row["created_at"])
    })

    slower_insert = ratio_slower(t_mdb_insert, t_redis_insert)
    log.info(f"🧩 [REGISTER] Redis={t_redis_insert:.6f}s | MariaDB={t_mdb_insert:.6f}s | "
             f"MariaDB fue {slower_insert:.2f}x más lento que Redis")

    print("\033[92m✅ REGISTRO EXITOSO:\033[0m Usuario:", username)
    print(f"⏱️  Redis → {t_redis_insert:.6f}s | MariaDB → {t_mdb_insert:.6f}s "
          f"| Ratio → {slower_insert:.2f}x\n")

    return jsonify({
        "ok": True,
        "message": f"Usuario {username} registrado correctamente",
        "timings": {"redis_insert": t_redis_insert, "mariadb_insert": t_mdb_insert},
        "comparison": f"MariaDB fue {slower_insert:.2f}x más lento que Redis"
    }), 201



# -----------------------
# LOGIN + TOKENS JWT
# -----------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "error": "Faltan credenciales"}), 400

    redis_user, t_r_read = time_it(redis_get_user_hash, username)
    mdb_user, t_mdb_read = time_it(mariadb_get_user_by_username, username)
    slower_read = ratio_slower(t_mdb_read, t_r_read)

    hash_to_check = redis_user.get("password_hash") if redis_user else None
    if not hash_to_check and mdb_user:
        hash_to_check = mdb_user.get("password_hash")

    auth_ok = False
    if hash_to_check:
        try:
            auth_ok = sha256_crypt.verify(password, hash_to_check)
        except Exception as e:
            log.error(f"Error verificando hash para usuario '{username}': {e}")

    if not auth_ok:
        log.warning(f"🚫 LOGIN FALLIDO user='{username}' | Redis={t_r_read:.6f}s | MariaDB={t_mdb_read:.6f}s")
        print("\033[91m❌ LOGIN INVALIDO:\033[0m Usuario:", username)
        return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401

    access_token = create_token(username, ACCESS_EXPIRES_MIN)
    refresh_token = create_token(username, REFRESH_EXPIRES_MIN)

    log.info(f"🔑 [LOGIN] Redis={t_r_read:.6f}s | MariaDB={t_mdb_read:.6f}s | "
             f"MariaDB fue {slower_read:.2f}x más lento que Redis")
    print("\033[96m✅ LOGIN EXITOSO:\033[0m", username)
    print(f"⏱️  Redis → {t_r_read:.6f}s | MariaDB → {t_mdb_read:.6f}s "
          f"| Ratio → {slower_read:.2f}x\n")

    return jsonify({
        "ok": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "comparison": f"MariaDB fue {slower_read:.2f}x más lento que Redis"
    })

# -----------------------
# ENDPOINTS JWT
# -----------------------
@app.route("/protected", methods=["GET"])
def protected():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Token requerido"}), 401
    token = auth.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return jsonify({"ok": False, "error": "Token inválido o expirado"}), 401
    return jsonify({"ok": True, "message": f"Bienvenido {payload['sub']}", "payload": payload})

@app.route("/refresh", methods=["POST"])
def refresh():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Token requerido"}), 401
    token = auth.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return jsonify({"ok": False, "error": "Refresh token inválido o expirado"}), 401
    new_access = create_token(payload["sub"], ACCESS_EXPIRES_MIN)
    return jsonify({"ok": True, "access_token": new_access})

# -----------------------
# USUARIO / LIBROS
# -----------------------
@app.route("/user/<username>", methods=["GET"])
def get_user(username):
    redis_user, t_r = time_it(redis_get_user_hash, username)
    mdb_user, t_m = time_it(mariadb_get_user_by_username, username)
    slower = ratio_slower(t_m, t_r)

    log.info(f"📊 [USER] {username} → Redis={t_r:.6f}s | MariaDB={t_m:.6f}s | "
             f"MariaDB fue {slower:.2f}x más lento que Redis")

    print("\033[93m🔍 CONSULTA USER:\033[0m", username)
    print(f"⏱️  Redis → {t_r:.6f}s | MariaDB → {t_m:.6f}s | Ratio → {slower:.2f}x\n")

    return jsonify({
        "ok": True,
        "comparison": f"MariaDB fue {slower:.2f}x más lento que Redis",
        "redis_user": redis_user,
        "mariadb_user": mdb_user
    })


# -----------------------
# LIBROS XML → JSON (versión Redis vs MariaDB con JWT)
# -----------------------
def libros_xml_to_json(xml_bytes):
    """Convierte XML del microservicio Libros en una lista JSON."""
    root = ET.fromstring(xml_bytes)
    out = []
    for book_el in root.findall("book"):
        row = {
            "isbn":   (book_el.findtext("isbn") or ""),
            "title":  (book_el.findtext("title") or ""),
            "author": (book_el.findtext("author") or ""),
            "publisher": (book_el.findtext("publisher") or ""),
            "year":   (book_el.findtext("year") or ""),
            "genre":  (book_el.findtext("genre") or ""),
            "price":  (book_el.findtext("price") or ""),
            "stock":  (book_el.findtext("stock") or ""),
            "format": (book_el.findtext("format") or "")
        }
        out.append(row)
    return out


@app.route("/books", methods=["GET"])
def books_proxy():
    """Proxy al microservicio Libros con protección JWT y métricas."""
    # --- Autenticación JWT manual ---
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"ok": False, "error": "Token requerido"}), 401

    token = auth.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload:
        return jsonify({"ok": False, "error": "Token inválido o expirado"}), 401

    # --- Construcción de URL con parámetro ?q= ---
    q = request.args.get("q", "").strip()
    url = f"{LIBROS_HOST}/api/books"
    if q:
        url += f"?q={requests.utils.quote(q)}"

    # --- Llamada al microservicio ---
    t0 = time.time()
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
    except Exception as e:
        log.error(f"❌ [Libros] Error al conectar con {url} → {e}")
        return jsonify({
            "ok": False,
            "error": "No se pudo contactar el microservicio Libros",
            "detail": str(e)
        }), 502
    t1 = time.time()

    # --- Parseo del XML ---
    try:
        rows = libros_xml_to_json(r.content)
    except Exception as e:
        log.error(f"❌ [Libros] Error parseando XML → {e}")
        return jsonify({
            "ok": False,
            "error": "No se pudo parsear XML de Libros",
            "detail": str(e)
        }), 500

    # --- Métricas y logs visuales ---
    duration = t1 - t0
    log.info(f"📚 [Libros] GET {url} ({duration:.3f}s) → {len(rows)} resultados")
    print("\033[94m📖 LIBROS:\033[0m", f"{len(rows)} libros | Tiempo {duration:.3f}s\n")

    return jsonify({
        "ok": True,
        "timing": duration,
        "books": rows
    }), 200


# -----------------------
# LOG GLOBAL DE PETICIONES
# -----------------------
@app.before_request
def log_request():
    """Log simple antes de cada petición HTTP (para depuración)."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {request.remote_addr} → {request.method} {request.path}")


# -----------------------
# MAIN
# -----------------------
if __name__ == "__main__":
    log.info("Servidor Flask ejecutándose en http://0.0.0.0:5000")
    log.info("Conectando Redis, MariaDB y Libros XML→JSON...")
    app.run(host="0.0.0.0", port=5000, debug=True)
