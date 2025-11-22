# ------------------------------------------
# Microservicio Flask - GCS + MariaDB (.env) + Swagger
# Descripción: Subida, listado y eliminación de imágenes en Google Cloud Storage
# Autor: Pablo Celedón Cabriales
# ------------------------------------------

from flask import Flask, request, jsonify, Response
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from google.cloud import storage
from functools import wraps
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import datetime
import os
import uuid

# -----------------------------
# Cargar variables del archivo .env
# -----------------------------
load_dotenv()

# -----------------------------
# Configuración Flask y DB
# -----------------------------
app = Flask(__name__)

from flasgger import Swagger, swag_from

app.config['SWAGGER'] = {
    'title': 'API de Imágenes GCS',
    'uiversion': 3,
    'specs_route': '/api/docs/'

}
swagger = Swagger(app)


app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST")
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB")
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

# -----------------------------
# Configuración GCS
# -----------------------------
GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_PUBLIC = os.getenv("GCS_PUBLIC", "0") == "1"
API_TOKEN = os.getenv("API_TOKEN")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

gcs_client = storage.Client()
bucket = gcs_client.bucket(GCS_BUCKET)

# -----------------------------
# Configuración general
# -----------------------------
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_SIZE = 16 * 1024 * 1024  # 16 MB

# -----------------------------
# Funciones auxiliares
# -----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def wants_json():
    return request.args.get("format", "").lower() == "json"


def make_error(msg, code):
    if wants_json():
        return jsonify({"status": "error", "message": msg}), code
    root = ET.Element("response")
    ET.SubElement(root, "status").text = "error"
    ET.SubElement(root, "message").text = msg
    return Response(ET.tostring(root), status=code, mimetype="application/xml")


def make_ok(payload):
    if wants_json():
        return jsonify({"status": "ok", **payload})
    root = ET.Element("response")
    ET.SubElement(root, "status").text = "ok"
    for k, v in payload.items():
        if isinstance(v, list):
            list_el = ET.SubElement(root, k)
            for item in v:
                item_el = ET.SubElement(list_el, "item")
                for subk, subv in item.items():
                    ET.SubElement(item_el, subk).text = str(subv)
        else:
            ET.SubElement(root, k).text = str(v)
    return Response(ET.tostring(root), mimetype="application/xml")


def object_signed_url(blob_name, mime):
    blob = bucket.blob(blob_name)
    return blob.generate_signed_url(
        expiration=datetime.timedelta(hours=1),
        version="v4",
        method="GET",
        response_type=mime
    )


def object_public_url(blob_name):
    return f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_name}"


def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return make_error("Token ausente o inválido", 401)
        token = header.replace("Bearer ", "").strip()
        if token != API_TOKEN:
            return make_error("Token incorrecto", 403)
        return f(*args, **kwargs)
    return wrapper


@swag_from({
    'tags': ['Imágenes'],
    'summary': 'Subir una imagen al bucket GCS',
    'description': 'Sube una imagen (png, jpg, jpeg, gif) y almacena sus metadatos.',
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Token Bearer. Ej: Bearer udem'
        },
        {
            'name': 'image',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'Archivo de imagen a subir'
        },
        {
            'name': 'format',
            'in': 'query',
            'type': 'string',
            'enum': ['json'],
            'required': False,
            'description': 'Si se envía format=json, la respuesta será en JSON'
        }
    ],
    'responses': {
        200: {
            'description': 'Imagen subida correctamente',
            'examples': {
                'application/json': {
                    'status': 'ok',
                    'filename': 'abc123_foto.jpg',
                    'mime_type': 'image/jpeg',
                    'size_bytes': 12345,
                    'storage_url': 'https://storage.googleapis.com/bucket/abc123_foto.jpg'
                }
            }
        },
        401: {'description': 'Token ausente o inválido'},
        403: {'description': 'Token incorrecto'},
        415: {'description': 'Formato no permitido'}
    }
})



# -----------------------------
# Rutas principales
# -----------------------------
@app.route("/upload", methods=["POST"])
@require_token
def upload_image():
    if "image" not in request.files:
        return make_error("No se encontró 'image' en la solicitud", 400)
    file = request.files["image"]
    if file.filename == "":
        return make_error("Archivo vacío", 400)
    if not allowed_file(file.filename):
        return make_error("Formato no permitido", 415)

    filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    mime = file.mimetype

    blob = bucket.blob(unique_name)
    blob.upload_from_file(file.stream, content_type=mime)

    # Generar URL
    if GCS_PUBLIC:
        url = object_public_url(unique_name)
    else:
        url = object_signed_url(unique_name, mime)

    # Insertar metadatos en la BD
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO image (filename, mime_type, size_bytes, storage_url)
        VALUES (%s, %s, %s, %s)
    """, (unique_name, mime, file.content_length or 0, url))
    mysql.connection.commit()
    cursor.close()

    return make_ok({
        "filename": unique_name,
        "mime_type": mime,
        "size_bytes": file.content_length or 0,
        "storage_url": url
    })


@swag_from({
    'tags': ['Imágenes'],
    'summary': 'Listar imágenes almacenadas',
    'description': 'Devuelve la lista de imágenes con URL, fecha, tamaño y MIME.',
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Token Bearer. Ej: Bearer udem'
        },
        {
            'name': 'format',
            'in': 'query',
            'type': 'string',
            'enum': ['json'],
            'required': False,
            'description': 'Formato JSON si se especifica format=json'
        }
    ],
    'responses': {
        200: {
            'description': 'Listado de imágenes',
            'examples': {
                'application/json': {
                    'status': 'ok',
                    'images': [
                        {
                            'filename': 'a123_foto.jpg',
                            'mime_type': 'image/jpeg',
                            'size_bytes': 20483,
                            'uploaded_at': '2025-11-12 14:33:00',
                            'storage_url': 'https://...'
                        }
                    ]
                }
            }
        },
        401: {'description': 'Token ausente o inválido'},
        403: {'description': 'Token incorrecto'},
    }
})


@app.route("/images", methods=["GET"])
@require_token
def list_images():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT filename, mime_type, size_bytes, uploaded_at, storage_url FROM image ORDER BY uploaded_at DESC")
    data = cursor.fetchall()
    cursor.close()
    return make_ok({"images": data})


@swag_from({
    'tags': ['Imágenes'],
    'summary': 'Eliminar una imagen del bucket y base de datos',
    'description': 'Elimina la imagen en GCS y su registro en MariaDB.',
    'parameters': [
        {
            'name': 'filename',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': 'Nombre del archivo a eliminar'
        },
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Token Bearer. Ej: Bearer udem'
        },
        {
            'name': 'format',
            'in': 'query',
            'type': 'string',
            'enum': ['json'],
            'required': False,
            'description': 'Formato JSON si se especifica format=json'
        }
    ],
    'responses': {
        200: {
            'description': 'Eliminada correctamente',
            'examples': {
                'application/json': {
                    'status': 'ok',
                    'message': 'Imagen eliminada correctamente',
                    'filename': 'abc123_foto.jpg'
                }
            }
        },
        404: {'description': 'Imagen no encontrada'},
        401: {'description': 'Token ausente o inválido'},
        403: {'description': 'Token incorrecto'}
    }
})


@app.route("/delete/<filename>", methods=["DELETE"])
@require_token
def delete_image(filename):
    # 1) Verificar si existe en la base de datos
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, filename FROM image WHERE filename = %s", (filename,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        return make_error("La imagen no existe en la base de datos", 404)

    # 2) Eliminar el archivo del bucket
    blob = bucket.blob(filename)

    try:
        blob.delete()
    except Exception as e:
        cursor.close()
        return make_error(f"No se pudo eliminar el archivo del bucket: {str(e)}", 500)

    # 3) Eliminar el registro en MariaDB
    cursor.execute("DELETE FROM image WHERE filename = %s", (filename,))
    mysql.connection.commit()
    cursor.close()

    # 4) Respuesta final
    return make_ok({
        "message": "Imagen eliminada correctamente",
        "filename": filename
    })


@app.route("/", methods=["GET"])
def root():
    return make_ok({
        "message": "Microservicio Flask GCS funcionando correctamente",
        "routes": ["/upload (POST)", "/images (GET)"],
        "auth": "Authorization: Bearer <token>",
        "format": "XML por defecto, JSON con ?format=json"
    })


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

