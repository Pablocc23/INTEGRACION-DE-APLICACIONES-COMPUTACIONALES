from flask import Flask, Response, request
import MySQLdb
import xml.etree.ElementTree as ET

app = Flask(__name__)

def get_db_connection():
    return MySQLdb.connect(
        host="localhost",
        user="libros_user",
        passwd="666",
        db="Libros",
        charset="utf8"
    )

def build_books_xml(rows):
    root = ET.Element("catalog")
    for row in rows:
        book_el = ET.SubElement(root, "book")
        ET.SubElement(book_el, "book_id").text   = str(row["book_id"])
        ET.SubElement(book_el, "title").text     = row["title"] or ""
        ET.SubElement(book_el, "author").text    = row["author_name"] or ""
        ET.SubElement(book_el, "publisher").text = row["publisher"] or ""
        ET.SubElement(book_el, "year").text      = str(row["year"] or "")
        ET.SubElement(book_el, "genre").text     = row["genre_name"] or ""
        ET.SubElement(book_el, "format").text    = row["format_name"] or ""
    return root

def xml_response(root):
    xml_str = ET.tostring(root, encoding="utf-8")
    return Response(xml_str, mimetype="application/xml")

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

if __name__ == "__main__":
    app.run(debug=True, port=5001)
