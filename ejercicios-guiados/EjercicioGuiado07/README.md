# 🧩 Proyecto Redis vs MariaDB + JWT + Microservicio de Libros (XML → JSON)

**Autor:** Pablo Celedón Cabriales  
**Materia:** Integración de Aplicaciones Computacionales  
**Sistema Operativo:** CentOS 9 (VM en Google Cloud)  
**Fecha:** 09 Octubre 2025  

---

## 📘 Descripción general

Este proyecto implementa **dos microservicios Flask interconectados** que comparan el rendimiento entre **Redis** y **MariaDB** durante operaciones de registro, login y consulta de usuarios.  
Además, integra un **microservicio externo de Libros** que devuelve información en formato XML y es consumido por la API principal, convirtiéndolo dinámicamente a JSON.

El sistema aplica **autenticación JWT (JSON Web Tokens)**, mide los **tiempos de respuesta de Redis vs MariaDB** y muestra los resultados en una interfaz web (`index.html`) desarrollada en HTML, CSS y JavaScript.

---

## 🧱 Arquitectura del sistema

```
        ┌──────────────────────────────┐
        │   FRONTEND (index.html)      │
        │   ────────────────────────   │
        │   app.js + style.css         │
        │   Llama endpoints Flask      │
        └─────────────┬────────────────┘
                      │
        ┌─────────────┴────────────────┐
        │  BACKEND Flask (app.py)      │
        │  Redis vs MariaDB + JWT      │
        │  Endpoints: /register, /login│
        │  /protected, /refresh, /user │
        │  /books (XML→JSON proxy)     │
        └─────────────┬────────────────┘
                      │
        ┌─────────────┴──────────────────────┐
        │ Microservicio Libros (main.py)     │
        │ MariaDB local (libros.sql)         │
        │ Devuelve XML en /api/books         │
        └────────────────────────────────────┘
```

---

## ⚙️ Instalación en CentOS 9

### 1️⃣ Instalación de dependencias del sistema

```bash
sudo dnf install python3-pip python3-devel gcc mariadb-server redis -y
sudo systemctl enable mariadb --now
sudo systemctl enable redis --now
```

Verifica que ambos servicios estén activos:
```bash
sudo systemctl status mariadb
sudo systemctl status redis
```

---

### 2️⃣ Creación de la base de datos MariaDB

#### A. Base de datos de autenticación (`jwt.sql`)
Ejecuta en el cliente MySQL:
```bash
mysql -u root -p
```

Y dentro:
```sql
CREATE DATABASE autenticacion_jwt;
CREATE USER 'libros_user'@'localhost' IDENTIFIED BY '666';
GRANT ALL PRIVILEGES ON autenticacion_jwt.* TO 'libros_user'@'localhost';
USE autenticacion_jwt;

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) UNIQUE,
  email VARCHAR(120),
  password_hash TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### B. Base de datos de Libros (`libros.sql`)
```sql
CREATE DATABASE Libros;
USE Libros;
CREATE USER 'libros_user'@'localhost' IDENTIFIED BY '666';
GRANT ALL PRIVILEGES ON Libros.* TO 'libros_user'@'localhost';
SOURCE libros.sql;
```

---

### 3️⃣ Instalación de dependencias de Python

Ejecuta en la raíz del proyecto:

```bash
pip install flask flask-mysqldb redis requests flask-cors passlib jwt mysqlclient
```

> 💡 Nota: si usas entornos virtuales:
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 🚀 Ejecución de los microservicios

### 🟩 1. Microservicio Libros (`main.py`)
Este servicio entrega los libros en formato **XML** desde MariaDB.

```bash
python3 main.py
```

Debería mostrar:
```
Running on http://0.0.0.0:5001
```

📡 Endpoint:  
`GET http://<IP>:5001/api/books`

Devuelve XML como:
```xml
<catalog>
  <book>
    <book_id>1</book_id>
    <title>Clean Code</title>
    <author>Robert C. Martin</author>
  </book>
</catalog>
```

---

### 🟦 2. API Redis vs MariaDB (`app.py`)
Este servicio gestiona usuarios, tokens y consulta los libros del microservicio anterior.

```bash
python3 app.py
```

📡 Endpoints principales:

| Endpoint | Método | Descripción |
|-----------|---------|-------------|
| `/register` | POST | Registra usuario en Redis y MariaDB |
| `/login` | POST | Genera tokens JWT |
| `/protected` | GET | Verifica JWT activo |
| `/refresh` | POST | Renueva token de acceso |
| `/user/<username>` | GET | Compara tiempos de consulta |
| `/books` | GET | Llama al microservicio XML y convierte a JSON |

---

### 🟨 3. Interfaz Web (`index.html`)

Ubica los archivos `index.html`, `style.css` y `app.js` en una carpeta pública (por ejemplo `/var/www/html/api/`), o ejecútalos localmente con:

```bash
python3 -m http.server 8080
```

Abre en el navegador:
```
http://<IP>:8080
```

La interfaz permite:
- Registrar y loguear usuarios.
- Mostrar tokens JWT.
- Ver resultados Redis vs MariaDB.
- Consultar los libros (XML → JSON).

---

## 🔍 Logs del servidor

Durante la ejecución del servidor Flask (`app.py`), se muestran métricas de comparación en consola:

```
✅ REGISTRO EXITOSO: Usuario: pablo
⏱️ Redis → 0.000234s | MariaDB → 0.002891s | Ratio → 12.35x

✅ LOGIN EXITOSO: pablo
⏱️ Redis → 0.000143s | MariaDB → 0.001978s | Ratio → 13.83x

📚 [Libros] GET http://34.71.199.168:5001/api/books (0.254s) → 50 resultados
```

---

## 📊 Resultados esperados

- Redis supera consistentemente a MariaDB en tiempos de lectura y escritura.  
- JWT asegura autenticación en endpoints protegidos.  
- El microservicio Libros entrega datos XML convertidos correctamente a JSON.  
- El `index.html` muestra la interacción completa desde el navegador.

---

## 🧩 Archivos incluidos

```
├── app.py              # Flask principal (Redis vs MariaDB + JWT + Libros)
├── main.py             # Microservicio Libros (XML)
├── jwt.sql             # Script DB autenticación
├── libros.sql          # Script DB libros
├── index.html          # Interfaz web
├── style.css           # Estilos visuales
├── app.js              # Lógica de interfaz
└── README.md           # Este documento
```

---

## 💡 Conclusiones

- **Redis** es más eficiente para accesos repetitivos, caching y operaciones rápidas.  
- **MariaDB** mantiene persistencia estructurada y relaciones más seguras a largo plazo.  
- La combinación de ambos ofrece balance entre velocidad y confiabilidad.  
- Los logs de Flask muestran claramente las métricas en tiempo real.
