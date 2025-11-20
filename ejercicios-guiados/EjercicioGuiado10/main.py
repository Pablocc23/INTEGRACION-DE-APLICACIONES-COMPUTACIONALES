from flask import Flask, Response, request
from flask_cors import CORS
import MySQLdb
import xml.etree.ElementTree as ET
from google.cloud import storage
from werkzeug.utils import secure_filename
import os


# Swagger
from flasgger import Swagger, swag_from

# -------------------------------------------------------
# APP + SWAGGER
# -------------------------------------------------------
app = Flask(__name__)
CORS(app)  # permitir CORS para el cliente web
Swagger(app)

# -------------------------------------------------------
# CONFIGURACIÓN GCS + LIMITES
# -------------------------------------------------------
GCS_BUCKET = "pablocc23-i"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pablocomputer23/Microservices/buckets/libros/pablocc23-i-key.json"

ALLOWED_EXT = {"png", "jpg", "jpeg"}
MAX_MB = 5 * 1024 * 1024     # 5MB
MAX_IMAGES_PER_BOOK = 5

gcs_client = storage.Client()
bucket = gcs_client.bucket(GCS_BUCKET)

# -------------------------------------------------------
# CONEXIÓN A LA BASE DE DATOS
# -------------------------------------------------------
def get_db_connection():
    return MySQLdb.connect(
        host="localhost",
        user="libros_user",
        passwd="666",
        db="Libros",
        charset="utf8"
    )

# -------------------------------------------------------
# UTILIDADES XML
# -------------------------------------------------------
def xml_error(msg, code=400):
    root = ET.Element("error")
    root.text = msg
    return Response(ET.tostring(root), mimetype="application/xml", status=code)


def xml_response(root):
    xml_str = ET.tostring(root, encoding="utf-8")
    return Response(xml_str, mimetype="application/xml")


# -------------------------------------------------------
# XML PARA LIBROS
# -------------------------------------------------------
def build_books_xml(rows):
    root = ET.Element("catalog")

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    for row in rows:
        book_el = ET.SubElement(root, "book")

        ET.SubElement(book_el, "book_id").text = str(row["book_id"])
        ET.SubElement(book_el, "title").text = row["title"] or ""
        ET.SubElement(book_el, "author").text = row["author_name"] or ""
        ET.SubElement(book_el, "publisher").text = row["publisher"] or ""
        ET.SubElement(book_el, "year").text = str(row["year"] or "")
        ET.SubElement(book_el, "genre").text = row["genre_name"] or ""
        ET.SubElement(book_el, "format").text = row["format_name"] or ""

        cursor.execute("""
            SELECT image_id, image_url, is_primary, sort_order
            FROM Images
            WHERE book_id=%s
            ORDER BY sort_order ASC
        """, (row["book_id"],))

        imgs = cursor.fetchall()
        images_el = ET.SubElement(book_el, "images")

        for img in imgs:
            img_el = ET.SubElement(images_el, "image")
            ET.SubElement(img_el, "image_id").text = str(img["image_id"])
            ET.SubElement(img_el, "image_url").text = img["image_url"]
            ET.SubElement(img_el, "is_primary").text = str(img["is_primary"])
            ET.SubElement(img_el, "sort_order").text = str(img["sort_order"])

    conn.close()
    return root


# -------------------------------------------------------
# GET /api/books
# -------------------------------------------------------
@swag_from({
  "summary": "Lista todos los libros en XML",
  "description": "Incluye las imágenes asociadas a cada libro.",
  "parameters": [
    {
      "name": "q",
      "in": "query",
      "schema": {"type": "string"},
      "description": "Buscar por título o autor"
    }
  ],
  "responses": {
    "200": {"description": "XML con todos los libros"}
  }
})
@app.route("/api/books", methods=["GET"])
def get_books():
    q = (request.args.get("q") or "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    sql = """
        SELECT b.book_id, b.title, b.publisher, b.year,
               CONCAT(a.first_name,' ',a.last_name) AS author_name,
               g.name AS genre_name, f.name AS format_name
        FROM Books b
        LEFT JOIN Authors a ON b.author_id = a.author_id
        LEFT JOIN Genres  g ON b.genre_id  = g.genre_id
        LEFT JOIN Formats f ON b.format_id = f.format_id
    """
    params = ()

    if q:
        sql += " WHERE b.title LIKE %s OR a.first_name LIKE %s OR a.last_name LIKE %s"
        like = f"%{q}%"
        params = (like, like, like)

    sql += " ORDER BY b.book_id LIMIT 200"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    root = build_books_xml(rows)
    return xml_response(root)


# -------------------------------------------------------
# POST /api/books/<book_id>/images
# -------------------------------------------------------
@swag_from({
  "summary": "Subir varias imágenes al libro",
  "description": "Carga 1–5 imágenes (JPG/PNG) a Google Cloud Storage.",
  "parameters": [
    {"name": "book_id", "in": "path", "required": True, "schema": {"type": "integer"}}
  ],
  "requestBody": {
    "required": True,
    "content": {
      "multipart/form-data": {
        "schema": {
          "type": "object",
          "properties": {
            "images": {
              "type": "array",
              "items": {"type": "string", "format": "binary"}
            }
          }
        }
      }
    }
  },
  "responses": {
    "200": {"description": "Imágenes subidas correctamente"},
    "400": {"description": "Error de validación"}
  }
})
@app.route("/api/books/<int:book_id>/images", methods=["POST"])
def upload_images(book_id):

    if "images" not in request.files:
        return xml_error("No se enviaron imágenes", 400)

    files = request.files.getlist("images")

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("SELECT COUNT(*) AS n FROM Images WHERE book_id=%s", (book_id,))
    existing = cursor.fetchone()["n"]

    if existing + len(files) > MAX_IMAGES_PER_BOOK:
        return xml_error("Máximo 5 imágenes por libro", 400)

    uploaded_urls = []

    for f in files:

        ext = f.filename.rsplit(".", 1)[1].lower()
        if ext not in ALLOWED_EXT:
            return xml_error("Formato inválido (solo PNG/JPG/JPEG)", 400)

        if len(f.read()) > MAX_MB:
            return xml_error("Archivo supera 5MB", 400)
        f.seek(0)

        safe_name = secure_filename(f.filename)
        blob_name = f"libros/{book_id}_{safe_name}"
        blob = bucket.blob(blob_name)

        blob.upload_from_file(f.stream, content_type=f.mimetype)

        url = f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_name}"

        cursor.execute("""
            INSERT INTO Images(book_id, image_url, is_primary, sort_order)
            VALUES(%s, %s, %s, %s)
        """, (book_id, url, 0, existing + len(uploaded_urls) + 1))

        uploaded_urls.append(url)

    conn.commit()
    cursor.close()
    conn.close()

    root = ET.Element("upload_result")
    ET.SubElement(root, "book_id").text = str(book_id)

    imgs = ET.SubElement(root, "uploaded_images")
    for u in uploaded_urls:
        ET.SubElement(imgs, "image_url").text = u

    return xml_response(root)


# -------------------------------------------------------
# DELETE /api/books/<book_id>/images/<image_id>
# -------------------------------------------------------
@swag_from({
  "summary": "Eliminar una imagen específica",
  "description": "Borra la imagen del bucket GCS y de la base de datos.",
  "parameters": [
    {"name": "book_id", "in": "path", "required": True, "schema": {"type": "integer"}},
    {"name": "image_id", "in": "path", "required": True, "schema": {"type": "integer"}}
  ],
  "responses": {
    "200": {"description": "Imagen eliminada"},
    "404": {"description": "No existe"}
  }
})
@app.route("/api/books/<int:book_id>/images/<int:image_id>", methods=["DELETE"])
def delete_image(book_id, image_id):

    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
        SELECT image_url FROM Images WHERE image_id=%s AND book_id=%s
    """, (image_id, book_id))
    img = cursor.fetchone()

    if not img:
        return xml_error("La imagen no existe", 404)

    url = img["image_url"]
    blob_name = url.split(f"https://storage.googleapis.com/{GCS_BUCKET}/")[1]

    try:
        bucket.blob(blob_name).delete()
    except:
        pass

    cursor.execute("DELETE FROM Images WHERE image_id=%s", (image_id,))
    conn.commit()

    root = ET.Element("delete_result")
    ET.SubElement(root, "deleted_image_id").text = str(image_id)

    return xml_response(root)


# -------------------------------------------------------
# PUT /api/books/<book_id>/images
# -------------------------------------------------------
@swag_from({
  "summary": "Actualizar orden e imagen principal",
  "description": "Recibe XML con image_id, sort_order y is_primary.",
  "parameters": [
    {"name": "book_id", "in": "path", "required": True, "schema": {"type": "integer"}}
  ],
  "requestBody": {
    "required": True,
    "content": {
      "application/xml": {"schema": {"type": "string"}}
    }
  },
  "responses": {
    "200": {"description": "Actualizado correctamente"}
  }
})
@app.route("/api/books/<int:book_id>/images", methods=["PUT"])
def update_images(book_id):

    try:
        xml_data = ET.fromstring(request.data)
    except:
        return xml_error("XML inválido", 400)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE Images SET is_primary=0 WHERE book_id=%s", (book_id,))

    for img in xml_data.findall("image"):
        image_id   = img.findtext("image_id")
        sort_order = img.findtext("sort_order")
        is_primary = img.findtext("is_primary")

        cursor.execute("""
            UPDATE Images
            SET sort_order=%s, is_primary=%s
            WHERE image_id=%s AND book_id=%s
        """, (sort_order, is_primary, image_id, book_id))

    conn.commit()
    cursor.close()
    conn.close()

    root = ET.Element("update_result")
    ET.SubElement(root, "book_id").text = str(book_id)
    ET.SubElement(root, "status").text = "updated"

    return xml_response(root)


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    print("🔥 Microservicio Libros + Imágenes corriendo en http://0.0.0.0:5001")
    print("📘 Documentación Swagger en: http://localhost:5001/apidocs")
    app.run(debug=True, port=5001)
