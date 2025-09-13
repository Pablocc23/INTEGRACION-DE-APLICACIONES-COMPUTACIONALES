from flask import Flask, request, Response
import MySQLdb
import xml.etree.ElementTree as ET

app = Flask(__name__)

# Conexión a la BD
def get_db_connection():
    return MySQLdb.connect(
        host="localhost",
        user="libros_user",
        passwd="666",
        db="Libros",
        charset="utf8"
    )

# Función auxiliar para construir XML
def build_books_xml(rows):
    root = ET.Element("catalog")
    for row in rows:
        book_el = ET.SubElement(root, "book")
        ET.SubElement(book_el, "isbn").text = str(row["isbn"])
        ET.SubElement(book_el, "title").text = row["title"]
        ET.SubElement(book_el, "author").text = row["author"]
        ET.SubElement(book_el, "year").text = str(row["year"])
        ET.SubElement(book_el, "genre").text = row["genre"]
        ET.SubElement(book_el, "price").text = str(row["price"])
        ET.SubElement(book_el, "stock").text = str(row["stock"])
        ET.SubElement(book_el, "format").text = row["format"]
    return root

def xml_response(root):
    xml_str = ET.tostring(root, encoding="utf-8")
    return Response(xml_str, mimetype="application/xml")

# ------------------------------
# ENDPOINTS
# ------------------------------

# /api/books ← ver todos los libros
@app.route("/api/books", methods=["GET"])
def get_books():
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT b.isbn, b.title, 
               CONCAT(a.first_name, ' ', a.last_name) AS author,
               b.year, g.name AS genre, b.price, b.stock, f.name AS format
        FROM Books b
        JOIN Authors a ON b.author_id = a.author_id
        JOIN Genres g ON b.genre_id = g.genre_id
        JOIN Formats f ON b.format_id = f.format_id
    """)
    rows = cursor.fetchall()
    conn.close()

    root = build_books_xml(rows)
    return xml_response(root)

# /api/books/<ISBN> ← buscar por ISBN
@app.route("/api/books/<isbn>", methods=["GET"])
def get_book_by_isbn(isbn):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT b.isbn, b.title, 
               CONCAT(a.first_name, ' ', a.last_name) AS author,
               b.year, g.name AS genre, b.price, b.stock, f.name AS format
        FROM Books b
        JOIN Authors a ON b.author_id = a.author_id
        JOIN Genres g ON b.genre_id = g.genre_id
        JOIN Formats f ON b.format_id = f.format_id
        WHERE b.isbn = %s
    """, (isbn,))
    rows = cursor.fetchall()
    conn.close()

    root = build_books_xml(rows)
    return xml_response(root)

# /api/books/formats/<format_id> ← buscar por formato
@app.route("/api/books/formats/<int:format_id>", methods=["GET"])
def get_books_by_format(format_id):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT b.isbn, b.title, 
               CONCAT(a.first_name, ' ', a.last_name) AS author,
               b.year, g.name AS genre, b.price, b.stock, f.name AS format
        FROM Books b
        JOIN Authors a ON b.author_id = a.author_id
        JOIN Genres g ON b.genre_id = g.genre_id
        JOIN Formats f ON b.format_id = f.format_id
        WHERE b.format_id = %s
    """, (format_id,))
    rows = cursor.fetchall()
    conn.close()

    root = build_books_xml(rows)
    return xml_response(root)

# /api/books/author/<author_id> ← buscar por autor
@app.route("/api/books/author/<int:author_id>", methods=["GET"])
def get_books_by_author(author_id):
    conn = get_db_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT b.isbn, b.title, 
               CONCAT(a.first_name, ' ', a.last_name) AS author,
               b.year, g.name AS genre, b.price, b.stock, f.name AS format
        FROM Books b
        JOIN Authors a ON b.author_id = a.author_id
        JOIN Genres g ON b.genre_id = g.genre_id
        JOIN Formats f ON b.format_id = f.format_id
        WHERE b.author_id = %s
    """, (author_id,))
    rows = cursor.fetchall()
    conn.close()

    root = build_books_xml(rows)
    return xml_response(root)

# ------------------------------
# MAIN
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)

