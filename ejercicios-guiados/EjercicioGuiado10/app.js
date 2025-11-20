// ================================================================
//  CONFIGURACIÓN (CARGA GUARDADA EN LOCALSTORAGE)
// ================================================================
let config = {
    ip: "",
    port: "",
    register: "/register",
    login: "/login",
    refresh: "/refresh",
    profile: "/protected",
    books: "/books"
};

function loadConfig() {
    const saved = localStorage.getItem("clientConfig");
    if (saved) config = JSON.parse(saved);
}

loadConfig();

// Gateway JWT (app.py)
function apiBase() {
    return `http://${config.ip}:${config.port}`;
}

// Microservicio Libros + Imágenes (main.py, puerto fijo 5001)
function librosBase() {
    return `http://${config.ip}:5001`;
}

// ================================================================
//  LOGGING
// ================================================================
function log(msg) {
    const box = document.getElementById("logBox");
    box.textContent += msg + "\n";
    box.scrollTop = box.scrollHeight;
}

// ================================================================
//  TOKEN HANDLING
// ================================================================
let accessToken = "";
let refreshToken = "";

function setTokens(access, refresh) {
    accessToken = access;
    refreshToken = refresh;
    document.getElementById("accessTokenBox").value = access || "";
    document.getElementById("refreshTokenBox").value = refresh || "";
}

function authHeaders() {
    return { "Authorization": "Bearer " + accessToken };
}

// ================================================================
//  EVENTOS TAB
// ================================================================
document.querySelectorAll(".tabs button").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tabs button").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));

        btn.classList.add("active");
        document.getElementById(btn.dataset.tab).classList.add("active");
    });
});

// ================================================================
//  CONFIG POPUP
// ================================================================
document.getElementById("openConfigBtn").addEventListener("click", () => {
    document.getElementById("cfgIp").value = config.ip;
    document.getElementById("cfgPort").value = config.port;
    document.getElementById("cfgRegister").value = config.register;
    document.getElementById("cfgLogin").value = config.login;
    document.getElementById("cfgRefresh").value = config.refresh;
    document.getElementById("cfgProfile").value = config.profile;
    document.getElementById("cfgBooks").value = config.books;

    document.getElementById("configDialog").showModal();
});

document.getElementById("saveConfigBtn").addEventListener("click", () => {
    config.ip = document.getElementById("cfgIp").value.trim();
    config.port = document.getElementById("cfgPort").value.trim();
    config.register = document.getElementById("cfgRegister").value.trim();
    config.login = document.getElementById("cfgLogin").value.trim();
    config.refresh = document.getElementById("cfgRefresh").value.trim();
    config.profile = document.getElementById("cfgProfile").value.trim();
    config.books = document.getElementById("cfgBooks").value.trim();

    localStorage.setItem("clientConfig", JSON.stringify(config));
    log("Configuración guardada.");
});

// ================================================================
//  REGISTRO
// ================================================================
document.getElementById("registerForm").addEventListener("submit", async e => {
    e.preventDefault();

    const body = {
        username: document.getElementById("regUsername").value.trim(),
        email: document.getElementById("regEmail").value.trim(),
        password: document.getElementById("regPassword").value
    };

    try {
        const res = await fetch(apiBase() + config.register, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });

        const data = await res.json();
        log("Registro → " + JSON.stringify(data));

    } catch (err) {
        log("Error registro: " + err);
    }
});

// ================================================================
//  LOGIN
// ================================================================
document.getElementById("loginForm").addEventListener("submit", async e => {
    e.preventDefault();

    const body = {
        username: document.getElementById("logUsername").value.trim(),
        password: document.getElementById("logPassword").value
    };

    try {
        const res = await fetch(apiBase() + config.login, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(body)
        });

        const data = await res.json();
        if (data.ok) {
            setTokens(data.access_token, data.refresh_token);
            log("Login correcto");
        } else {
            log("Login fallido");
        }
    } catch (err) {
        log("Error login: " + err);
    }
});

// ================================================================
//  PROFILE PROTECTED
// ================================================================
document.getElementById("btnProfile").addEventListener("click", async () => {
    try {
        const res = await fetch(apiBase() + config.profile, {
            headers: authHeaders()
        });
        const data = await res.json();
        log("Perfil → " + JSON.stringify(data));
    } catch (err) {
        log("Error protected: " + err);
    }
});

// ================================================================
//  REFRESH TOKEN
// ================================================================
document.getElementById("btnRefresh").addEventListener("click", async () => {
    try {
        const res = await fetch(apiBase() + config.refresh, {
            method: "POST",
            headers: authHeaders()
        });
        const data = await res.json();
        if (data.ok) {
            accessToken = data.access_token;
            document.getElementById("accessTokenBox").value = accessToken;
            log("Access token actualizado");
        }
    } catch (err) {
        log("Error refresh: " + err);
    }
});

// ================================================================
//  CLEAR TOKENS
// ================================================================
document.getElementById("btnClearTokens").addEventListener("click", () => {
    setTokens("", "");
    log("Tokens borrados.");
});

// =====================================================================
//  LISTAR LIBROS
// =====================================================================
let lastBooks = [];

document.getElementById("btnListBooks").addEventListener("click", loadBooks);

async function loadBooks() {
    const q = document.getElementById("searchText").value.trim();
    let url = apiBase() + config.books;
    if (q) url += "?q=" + encodeURIComponent(q);

    try {
        const res = await fetch(url, { headers: authHeaders() });
        const data = await res.json();
        const books = data.books || [];
        lastBooks = books;
        renderBooks(books);
    } catch (err) {
        log("Error obteniendo libros → " + err);
    }
}

function renderBooks(books) {
    const tbody = document.getElementById("booksTbody");
    tbody.innerHTML = "";

    if (!books.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td colspan="5" style="text-align:center;">No hay libros</td>
        `;
        tbody.appendChild(tr);
        return;
    }

    books.forEach(b => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${b.book_id || ""}</td>
            <td>${b.title}</td>
            <td>${b.author}</td>
            <td>${b.year}</td>
            <td>
                <button class="btn small" onclick="openImagesPanel(${b.book_id}, '${(b.title || "").replace(/'/g, "")}')">
                    Ver imágenes
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// =====================================================================
//  PANEL DE IMÁGENES
// =====================================================================
async function openImagesPanel(book_id, title) {
    document.getElementById("panelBookTitle").innerText = title;
    document.getElementById("imagesPanel").style.display = "block";
    window.currentBook = book_id;
    loadBookImages(book_id);
}

// =====================================================================
//  CARGAR IMÁGENES EXISTENTES (vía gateway /books)
// =====================================================================
async function loadBookImages(book_id) {
    const q = document.getElementById("searchText").value.trim();
    let url = apiBase() + config.books;
    if (q) url += "?q=" + encodeURIComponent(q);

    try {
        const res = await fetch(url, { headers: authHeaders() });
        const data = await res.json();
        const books = data.books || [];

        const book = books.find(b => Number(b.book_id) === Number(book_id));
        if (!book) {
            log("Libro no encontrado al cargar imágenes");
            return;
        }

        renderBookImages(book.images || []);

    } catch (err) {
        log("Error imágenes libro: " + err);
    }
}

// =====================================================================
//  RENDER IMÁGENES
// =====================================================================
function renderBookImages(images) {
    const container = document.getElementById("bookImages");
    container.innerHTML = "";

    if (!images.length) {
        container.innerHTML = "<p>No hay imágenes para este libro.</p>";
        return;
    }

    images.forEach(imgObj => {
        const div = document.createElement("div");
        div.className = "imgBox";
        div.innerHTML = `
            <img src="${imgObj.url || imgObj.image_url}" />
            <button class="btn danger small" onclick="deleteImage(${imgObj.image_id})">
                Borrar
            </button>
        `;
        container.appendChild(div);
    });
}

// =====================================================================
//  SUBIR IMÁGENES (directo al microservicio main.py)
// =====================================================================
document.getElementById("fileImages").addEventListener("change", showPreview);

function showPreview(e) {
    const container = document.getElementById("previewContainer");
    container.innerHTML = "";

    [...e.target.files].forEach(file => {
        const img = document.createElement("img");
        img.src = URL.createObjectURL(file);
        container.appendChild(img);
    });
}

document.getElementById("btnUploadImages").addEventListener("click", uploadImages);

async function uploadImages() {
    if (!window.currentBook) return;

    const files = document.getElementById("fileImages").files;
    if (files.length === 0) return log("No seleccionaste imágenes");

    const form = new FormData();
    [...files].forEach(f => form.append("images", f)); // nombre de campo correcto

    const url = `${librosBase()}/api/books/${window.currentBook}/images`;

    try {
        const res = await fetch(url, {
            method: "POST",
            body: form
        });

        const text = await res.text();
        log("Upload XML: " + text);

        await loadBookImages(window.currentBook);
        document.getElementById("previewContainer").innerHTML = "";

    } catch (err) {
        log("Error al subir imágenes: " + err);
    }
}

// =====================================================================
//  BORRAR IMAGEN (directo al microservicio main.py)
// =====================================================================
async function deleteImage(imageId) {
    if (!window.currentBook) return;

    const url = `${librosBase()}/api/books/${window.currentBook}/images/${imageId}`;

    try {
        const res = await fetch(url, {
            method: "DELETE"
        });

        const text = await res.text();
        log("DELETE XML → " + text);

        await loadBookImages(window.currentBook);
    } catch (err) {
        log("Error borrar imagen: " + err);
    }
}

// ================================================================
//  CLEAR LOGS
// ================================================================
document.getElementById("btnClearLogs").addEventListener("click", () => {
    document.getElementById("logBox").textContent = "";
});
