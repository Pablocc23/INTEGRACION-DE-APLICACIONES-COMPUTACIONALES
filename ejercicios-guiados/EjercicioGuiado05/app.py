from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from passlib.hash import sha256_crypt
from datetime import datetime, timedelta

from flask_cors import CORS

import requests
import xml.etree.ElementTree as ET
from flask import Response

LIBROS_HOST = "http://34.71.199.168:5001"


app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

# Configuración MariaDB
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '666'
app.config['MYSQL_DB'] = 'autenticacion_jwt'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Configuración JWT
app.config['JWT_SECRET_KEY'] = '666'  
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=7)

mysql = MySQL(app)
jwt = JWTManager(app)


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "msg": "Microservicio Flask con JWT funcionando 🚀",
        "endpoints": ["/register (POST)", "/login (POST)", "/protected (GET con token)", "/refresh (POST con refresh token)"]
    }), 200

@app.route('/register', methods=['GET'])
def register_info():
    return jsonify({"msg": "Usa POST con JSON para registrar un usuario"}), 200

@app.route('/login', methods=['GET'])
def login_info():
    return jsonify({"msg": "Usa POST con JSON para iniciar sesión"}), 200


# Registro de usuario
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = sha256_crypt.hash(data.get('password'))

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO usuarios (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password))
    mysql.connection.commit()
    cur.close()

    return jsonify({"msg": "Usuario registrado con éxito"}), 201


# Login (genera tokens)
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE username = %s", [username])
    user = cur.fetchone()
    cur.close()

    if user and sha256_crypt.verify(password, user['password_hash']):
        access_token = create_access_token(identity=str(user['id']))
        refresh_token = create_refresh_token(identity=str(user['id']))


        # Guardar tokens en BD
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                    (user['id'], access_token, datetime.utcnow() + timedelta(minutes=15)))
        cur.execute("INSERT INTO refresh_tokens (user_id, refresh_token, expires_at) VALUES (%s, %s, %s)",
                    (user['id'], refresh_token, datetime.utcnow() + timedelta(days=7)))
        mysql.connection.commit()
        cur.close()

        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    else:
        return jsonify({"msg": "Credenciales inválidas"}), 401


# Ruta protegida
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"msg": f"Acceso autorizado. Usuario ID: {current_user}"}), 200


# Refrescar token
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200


def libros_xml_to_json(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for book_el in root.findall("book"):
        row = {
            "isbn":   (book_el.findtext("isbn") or ""),
            "title":  (book_el.findtext("title") or ""),
            "author": (book_el.findtext("author") or ""),
            "year":   (book_el.findtext("year") or ""),
            "genre":  (book_el.findtext("genre") or ""),
            "price":  (book_el.findtext("price") or ""),
            "stock":  (book_el.findtext("stock") or ""),
            "format": (book_el.findtext("format") or "")
        }
        out.append(row)
    return out

@app.route('/books', methods=['GET'])
@jwt_required()  # <- protegido con JWT
def books_proxy():
    # Soporta búsqueda ?q=
    q = request.args.get("q", "").strip()
    url = f"{LIBROS_HOST}/api/books"
    if q:
        url += f"?q={requests.utils.quote(q)}"  # solo si luego implementas filtro en libros

    try:
        r = requests.get(url, timeout=5)
    except Exception as e:
        return jsonify({"error":"no se pudo contactar el microservicio de Libros", "detail": str(e)}), 502

    if r.status_code != 200:
        return jsonify({"error": "Libros devolvió error", "status": r.status_code}), 502

    # Convierte el XML de Libros a JSON para el cliente
    try:
        rows = libros_xml_to_json(r.content)
    except Exception as e:
        return jsonify({"error":"no se pudo parsear XML de Libros", "detail": str(e)}), 500

    return jsonify(rows), 200

@app.before_request
def log_request():
    print(f"[{datetime.utcnow()}] {request.method} {request.path}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

