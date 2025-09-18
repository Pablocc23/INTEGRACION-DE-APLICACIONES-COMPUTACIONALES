<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <!-- Tu XML actual tiene raíz <library> y <isbn> como ELEMENTO -->
  <xsl:template match="/library">
    <html>
      <head>
        <meta charset="UTF-8"/>
        <title>Catálogo de libros</title>
        <link rel="stylesheet" href="estilo.css"/>

        <style>
          /* Header con buscador a la derecha */
          .page {
            max-width: 1200px; margin: 24px auto;
            padding: 0 20px;
          }
          .header {
            display:flex; align-items:center; justify-content:space-between;
            margin: 8px 0 20px;
          }
          .header h1 {
            margin:0; font-size: 2rem; color:#1b2a41;
          }
          .controls { display:flex; align-items:center; gap:.5rem; }
          .controls label { font-weight:600; color:#364b61; }
          #isbnFilter { padding:.6rem .9rem; font-size:1rem; min-width:280px; border-radius:10px; border:1px solid #d8e1ea; }

          /* Tarjetas y grilla (coincide con tu look) */
          .grid {
            display:grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap:20px;
          }
          .card {
            background:#fff; border:1px solid #e5ecf3; border-radius:18px;
            padding:18px 20px; box-shadow: 0 6px 20px rgba(15,30,50,.07);
          }
          .card.hidden{ display:none; }

          /* Encabezado de ISBN en gris, arriba */
          .isbn-head {
            color:#8da0b3; font-weight:600; letter-spacing:.04em;
            font-size:.90rem; margin-bottom:6px;
          }

          .title {
            font-weight:800; font-size:1.15rem; color:#1f2d3d; margin: 2px 0 8px;
          }
          .meta { color:#4b5d70; font-size:.98rem; margin:2px 0; }
          .pill {
            display:inline-block; background:#eef4ff; border:1px solid #dbe6ff;
            border-radius:999px; padding:3px 10px; font-size:.82rem; margin-right:8px;
          }
          .price { color:#1f7a3e; font-weight:800; }
          .stock-pill {
            display:inline-block; background:#eaf8f0; border:1px solid #cbeeda;
            color:#176a3a; border-radius:999px; padding:3px 10px; font-weight:700; font-size:.82rem;
            margin-right:8px;
          }

          /* Fondo suave como en la captura */
          body {
            background: radial-gradient(1200px 500px at 10% -10%, #eef5ff 0%, transparent 60%),
                        radial-gradient(900px 400px at 90% -10%, #f4fbff 0%, transparent 60%),
                        #f6f9fc;
          }
        </style>

        <script>
          <![CDATA[
          function filterByIsbn(){
            var input = document.getElementById('isbnFilter');
            if(!input) return;
            var raw = (input.value || '').toLowerCase();
            var query = raw.replace(/[^0-9a-z]/g,''); // normaliza (sin guiones/espacios)
            var cards = document.querySelectorAll('#books .card');
            for(var i=0;i<cards.length;i++){
              var c = cards[i];
              var isbnRaw = (c.getAttribute('data-isbn')||'').toLowerCase();
              var isbn = isbnRaw.replace(/[^0-9a-z]/g,'');
              if(!query || isbn.indexOf(query)!==-1){ c.classList.remove('hidden'); }
              else{ c.classList.add('hidden'); }
            }
          }
          window.onload = function(){ filterByIsbn(); };
          ]]>
        </script>
      </head>
      <body>
        <div class="page">
          <div class="header">
            <h1>Catálogo de libros</h1>
            <div class="controls">
              <label for="isbnFilter">Buscar ISBN:</label>
              <input id="isbnFilter" type="text" placeholder="Escribe el ISBN…" oninput="filterByIsbn()"/>
            </div>
          </div>

          <div id="books" class="grid">
            <xsl:for-each select="book">
              <div class="card">
                <!-- data-isbn para el filtro -->
                <xsl:attribute name="data-isbn"><xsl:value-of select="isbn"/></xsl:attribute>

                <!-- ISBN arriba en gris -->
                <div class="isbn-head">
                  <span>ISBN: </span><xsl:value-of select="isbn"/>
                </div>

                <!-- Título -->
                <div class="title"><xsl:value-of select="title"/></div>

                <!-- Autores (varios) y año -->
                <div class="meta">
                  Autor:
                  <xsl:for-each select="author">
                    <xsl:value-of select="."/>
                    <xsl:if test="position()!=last()">, </xsl:if>
                  </xsl:for-each>
                  &#160; Año: <xsl:value-of select="year"/>
                </div>

                <!-- Género (pill), Precio en verde, Stock pill y Formato -->
                <div class="meta">
                  <span class="pill"><xsl:value-of select="genre"/></span>
                  <span class="price">Precio: $<xsl:value-of select="price"/></span>
                </div>
                <div class="meta">
                  <span class="stock-pill">Stock: <xsl:value-of select="stock"/></span>
                  • <xsl:value-of select="format"/>
                </div>
              </div>
            </xsl:for-each>
          </div>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
