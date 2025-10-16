import time
import logging
from math import isfinite

from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import redis
from werkzeug.security import generate_password_hash, check_password_hash

# -----------------------
# Configuración de Flask
# -----------------------
app = Flask(__name__)

# MariaDB (según tus datos)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'libros_user'
app.config['MYSQL_PASSWORD'] = '666'
app.config['MYSQL_DB'] = 'autenticacion_jwt'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# Redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Logging claro en consola
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
log = logging.getLogger('app')

# -----------------------
# Utilidades de tiempo
# -----------------------
def time_it(fn, *args, **kwargs):
    """Ejecuta fn(*args, **kwargs) y devuelve (resultado, duracion_en_segundos)."""
    t0 = time.time()
    res = fn(*args, **kwargs)
    t1 = time.time()
    return res, (t1 - t0)

def ratio_slower(numerator, denominator):
    """Retorna cuántas veces (numerator) es más lento que (denominator)."""
    if denominator <= 0 or not isfinite(denominator):
        return None
    return numerator / denominator

# -----------------------
# Operaciones MariaDB
# -----------------------
def mariadb_insert_user(username, email, password_hash):
    cur = mysql.connection.cursor()
    cur.execute(
        """
        INSERT INTO usuarios (username, email, password_hash)
        VALUES (%s, %s, %s)
        """,
        (username, email, password_hash)
    )
    mysql.connection.commit()
    cur.close()

def mariadb_get_user_by_username(username):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT id, username, email, password_hash, created_at FROM usuarios WHERE username=%s",
        (username,)
    )
    row = cur.fetchone()
    cur.close()
    return row

# -----------------------
# Operaciones Redis (HASH)
#   Key: user:{username}
#   Campos: id (opcional, cuando exista), username, email, password_hash, created_at
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
# Rutas
# -----------------------

@app.route("/")
def root():
    return jsonify({
        "ok": True,
        "endpoints": {
            "POST /register": {"username": "str", "email": "str", "password": "str"},
            "POST /login": {"username": "str", "password": "str"},
            "GET  /user/<username>": "Lee usuario de Redis y MariaDB con tiempos",
        },
        "dbs": {
            "mariadb": {
                "host": app.config['MYSQL_HOST'],
                "user": app.config['MYSQL_USER'],
                "db": app.config['MYSQL_DB']
            },
            "redis": {"host": "localhost", "port": 6379, "db": 0}
        }
    })

@app.route("/register", methods=["POST"])
def register():
    """
    Registra usuario en Redis (hash) y MariaDB, midiendo tiempos.
    Body JSON: { "username": "...", "email": "...", "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"ok": False, "error": "username, email y password son requeridos"}), 400

    # Pre-chequeo: ¿existe ya en MariaDB?
    existing_mdb, t_mdb_read = time_it(mariadb_get_user_by_username, username)
    log.info(f"[MariaDB] READ (pre-check) user='{username}' -> {t_mdb_read:.6f}s")
    if existing_mdb:
        return jsonify({"ok": False, "error": "username ya existe en MariaDB", "t_mariadb_read": t_mdb_read}), 409

    # Hash seguro
    pwd_hash = generate_password_hash(password)

    # Insert Redis
    redis_payload = {
        "username": username,
        "email": email,
        "password_hash": pwd_hash,
        # created_at la aprenderemos de MariaDB cuando lo insertemos, aquí puede ir vacío o timestamp app
    }
    _, t_redis_write = time_it(redis_set_user_hash, username, redis_payload)
    log.info(f"[Redis] HSET user='{username}' -> {t_redis_write:.6f}s")

    # Insert MariaDB
    try:
        _, t_mdb_write = time_it(mariadb_insert_user, username, email, pwd_hash)
        log.info(f"[MariaDB] INSERT user='{username}' -> {t_mdb_write:.6f}s")
    except Exception as e:
        log.exception("[MariaDB] Error INSERT; revertir Redis para consistencia suave")
        # Intento de limpieza en Redis si falla MariaDB (consistencia eventual)
        r.delete(redis_user_key(username))
        return jsonify({"ok": False, "error": f"MariaDB INSERT falló: {e}"}), 500

    # Recuperamos el registro “fuente de verdad” de MariaDB para completar created_at e id y reflejar en Redis:
    mdb_row, t_mdb_read2 = time_it(mariadb_get_user_by_username, username)
    log.info(f"[MariaDB] READ (post-insert) user='{username}' -> {t_mdb_read2:.6f}s")

    if mdb_row:
        # Refrescamos Redis con id y created_at reales
        redis_refresh = {
            "id": str(mdb_row["id"]),
            "username": mdb_row["username"],
            "email": mdb_row["email"],
            "password_hash": mdb_row["password_hash"],
            "created_at": str(mdb_row["created_at"]),
        }
        _, t_redis_write2 = time_it(redis_set_user_hash, username, redis_refresh)
        log.info(f"[Redis] HSET (refresh) user='{username}' -> {t_redis_write2:.6f}s")
    else:
        t_redis_write2 = 0.0

    # Comparaciones
    slower_write = ratio_slower(t_mdb_write, t_redis_write) if t_redis_write else None
    slower_read = ratio_slower(t_mdb_read2, t_redis_write2) if t_redis_write2 else None

    return jsonify({
        "ok": True,
        "message": "Usuario registrado en Redis y MariaDB",
        "timings_seconds": {
            "redis_write": t_redis_write,
            "mariadb_write": t_mdb_write,
            "mariadb_read_after_insert": t_mdb_read2,
            "redis_write_refresh": t_redis_write2
        },
        "comparisons": {
            "mariadb_write_vs_redis_write": (f"{slower_write:.2f}x más lento" if slower_write else None),
            "mariadb_read_vs_redis_write_refresh": (f"{slower_read:.2f}x más lento" if slower_read else None)
        }
    }), 201

@app.route("/login", methods=["POST"])
def login():
    """
    Solicita username y password,
    intenta leer de Redis y compara con MariaDB, midiendo tiempos de lectura.
    Body JSON: { "username": "...", "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"ok": False, "error": "username y password son requeridos"}), 400

    # 1) Intento Redis (HASH)
    redis_user, t_r_read = time_it(redis_get_user_hash, username)
    log.info(f"[Redis] HGETALL user='{username}' -> {t_r_read:.6f}s")

    auth_ok = False
    from_source = None
    details = {}

    if redis_user and "password_hash" in redis_user:
        auth_ok = check_password_hash(redis_user["password_hash"], password)
        from_source = "redis"
        details["redis_user"] = {k: v for k, v in redis_user.items() if k != "password_hash"}

    # 2) Si Redis falla (cache miss o auth fallida), consultamos MariaDB
    mdb_user, t_mdb_read = time_it(mariadb_get_user_by_username, username)
    log.info(f"[MariaDB] READ user='{username}' -> {t_mdb_read:.6f}s")

    if mdb_user and not auth_ok:
        auth_ok = check_password_hash(mdb_user["password_hash"], password)
        if auth_ok and not redis_user:
            # Calentamos cache si no existía
            cache_payload = {
                "id": str(mdb_user["id"]),
                "username": mdb_user["username"],
                "email": mdb_user["email"],
                "password_hash": mdb_user["password_hash"],
                "created_at": str(mdb_user["created_at"]),
            }
            _, t_r_write = time_it(redis_set_user_hash, username, cache_payload)
            log.info(f"[Redis] HSET (warm-cache) user='{username}' -> {t_r_write:.6f}s")
        from_source = from_source or "mariadb"
        details["mariadb_user"] = {k: str(v) for k, v in mdb_user.items() if k != "password_hash"}

    # Comparación de lecturas
    slower_read = ratio_slower(t_mdb_read, t_r_read) if t_r_read else None

    return jsonify({
        "ok": auth_ok,
        "authenticated_from": from_source,
        "timings_seconds": {
            "redis_read": t_r_read,
            "mariadb_read": t_mdb_read
        },
        "comparison": {
            "mariadb_read_vs_redis_read": (f"{slower_read:.2f}x más lento" if slower_read else None)
        },
        "details": details if auth_ok else {"error": "Credenciales inválidas"}
    }), (200 if auth_ok else 401)

@app.route("/user/<username>", methods=["GET"])
def get_user(username):
    """
    Lee el usuario de ambos sistemas y devuelve los tiempos.
    """
    redis_user, t_r_read = time_it(redis_get_user_hash, username)
    log.info(f"[Redis] HGETALL user='{username}' -> {t_r_read:.6f}s")

    mdb_user, t_mdb_read = time_it(mariadb_get_user_by_username, username)
    log.info(f"[MariaDB] READ user='{username}' -> {t_mdb_read:.6f}s")

    slower_read = ratio_slower(t_mdb_read, t_r_read) if t_r_read else None

    return jsonify({
        "ok": True,
        "timings_seconds": {
            "redis_read": t_r_read,
            "mariadb_read": t_mdb_read
        },
        "comparison": {
            "mariadb_read_vs_redis_read": (f"{slower_read:.2f}x más lento" if slower_read else None)
        },
        "redis_user": {k: v for k, v in (redis_user or {}).items() if k != "password_hash"} if redis_user else None,
        "mariadb_user": {k: str(v) for k, v in (mdb_user or {}).items() if k != "password_hash"} if mdb_user else None
    })
# -----------------------
# Main
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

