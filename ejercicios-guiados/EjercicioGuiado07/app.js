// ===== Config =====
const DEFAULT_CFG = {
  ip: "127.0.0.1",
  port: "5000",
  endpoints: {
    register: "/register",
    login: "/login",
    refresh: "/refresh",
    profile: "/protected",
    books: "/books" // o "/libros/books" según tu servidor
  }
};

function loadCfg() {
  try {
    const raw = localStorage.getItem("cfg");
    if (!raw) return structuredClone(DEFAULT_CFG);
    const cfg = JSON.parse(raw);
    return { ...structuredClone(DEFAULT_CFG), ...cfg, endpoints: { ...DEFAULT_CFG.endpoints, ...(cfg.endpoints||{}) } };
  } catch {
    return structuredClone(DEFAULT_CFG);
  }
}

function saveCfg(cfg) {
  localStorage.setItem("cfg", JSON.stringify(cfg));
}

function apiUrl(path) {
  const cfg = loadCfg();
  const host = cfg.port ? `http://${cfg.ip}:${cfg.port}` : `http://${cfg.ip}`;
  return `${host}${path}`;
}

function bearer() {
  const t = localStorage.getItem("accessToken");
  return t ? { "Authorization": `Bearer ${t}` } : {};
}

function log(msg, data) {
  const box = document.getElementById("logBox");
  const time = new Date().toLocaleTimeString();
  const line = `[${time}] ${msg}${data !== undefined ? " " + JSON.stringify(data) : ""}\n`;
  box.textContent += line;
  box.scrollTop = box.scrollHeight;
  console.log(msg, data ?? "");
}

async function http(method, path, body = undefined, auth = false) {
  const url = apiUrl(path);
  const headers = { "Content-Type": "application/json", ...(auth ? bearer() : {}) };
  log(`→ ${method} ${url}`, body ?? "");
  const res = await fetch(url, {
    method, headers, mode: "cors",
    body: body ? JSON.stringify(body) : undefined,
  });
  let payload = null;
  try { payload = await res.json(); } catch { payload = await res.text(); }
  log(`← ${res.status} ${method} ${url}`, payload);
  if (!res.ok) throw { status: res.status, payload };
  return payload;
}

// ===== UI Helpers =====
function setApiStatus(text, ok) {
  const el = document.getElementById("apiStatus");
  el.textContent = text;
  el.style.borderColor = ok ? "#22c55e" : "#ef4444";
  el.style.color = ok ? "#d1fae5" : "#fecaca";
}

// ===== Usuario: Consultar /user/<username> =====
document.getElementById("userForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("userQuery").value.trim();
  if (!username) return alert("Debes ingresar un username");
  const { ip, port } = loadCfg();
  const url = `http://${ip}:${port}/user/${username}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    log(`GET /user/${username}`, data);
    document.getElementById("userResult").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    document.getElementById("userResult").textContent = "Error consultando usuario.";
    log("Error /user/<username>", err);
  }
});


function updateTokensUI() {
  const access = localStorage.getItem("accessToken") || "";
  const refresh = localStorage.getItem("refreshToken") || "";
  document.getElementById("accessTokenBox").value = access;
  document.getElementById("refreshTokenBox").value = refresh;

  const decoded = {};
  try {
    if (access) {
      const [, p] = access.split(".");
      const json = JSON.parse(atob(p.replace(/-/g, "+").replace(/_/g, "/")));
      decoded.access = json;
    }
    if (refresh) {
      const [, p] = refresh.split(".");
      const json = JSON.parse(atob(p.replace(/-/g, "+").replace(/_/g, "/")));
      decoded.refresh = json;
    }
  } catch { /* ignore */ }
  document.getElementById("jwtDecoded").textContent = JSON.stringify(decoded, null, 2);
}

// ===== Tabs =====
document.querySelectorAll(".tabs button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.dataset.tab;
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.getElementById(id).classList.add("active");
  });
});

// ===== Config Dialog =====
const cfgDialog = document.getElementById("configDialog");
document.getElementById("openConfigBtn").addEventListener("click", () => {
  const cfg = loadCfg();
  document.getElementById("cfgIp").value = cfg.ip;
  document.getElementById("cfgPort").value = cfg.port;
  document.getElementById("cfgRegister").value = cfg.endpoints.register;
  document.getElementById("cfgLogin").value = cfg.endpoints.login;
  document.getElementById("cfgRefresh").value = cfg.endpoints.refresh;
  document.getElementById("cfgProfile").value = cfg.endpoints.profile;
  document.getElementById("cfgBooks").value = cfg.endpoints.books;
  cfgDialog.showModal();
});

document.getElementById("saveConfigBtn").addEventListener("click", (e) => {
  e.preventDefault();
  const newCfg = {
    ip: document.getElementById("cfgIp").value.trim(),
    port: document.getElementById("cfgPort").value.trim(),
    endpoints: {
      register: document.getElementById("cfgRegister").value.trim(),
      login: document.getElementById("cfgLogin").value.trim(),
      refresh: document.getElementById("cfgRefresh").value.trim(),
      profile: document.getElementById("cfgProfile").value.trim(),
      books: document.getElementById("cfgBooks").value.trim()
    }
  };
  saveCfg(newCfg);
  cfgDialog.close();
  log("Config guardada", newCfg);
  probeApi();
});

// ===== Auth: Register/Login/Refresh/Profile =====
document.getElementById("registerForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const body = {
    username: document.getElementById("regUsername").value,
    email: document.getElementById("regEmail").value,
    password: document.getElementById("regPassword").value
  };
  const { endpoints } = loadCfg();
  try {
    const r = await http("POST", endpoints.register, body);
    alert("Registrado: " + JSON.stringify(r));
  } catch(err) {
    alert("Error registro: " + JSON.stringify(err.payload));
  }
});

document.getElementById("loginForm").addEventListener("submit", async (e)=>{
  e.preventDefault();
  const body = {
    username: document.getElementById("logUsername").value,
    password: document.getElementById("logPassword").value
  };
  const { endpoints } = loadCfg();
  try {
    const r = await http("POST", endpoints.login, body);
    localStorage.setItem("accessToken", r.access_token);
    localStorage.setItem("refreshToken", r.refresh_token);
    updateTokensUI();
    alert("Login OK");
  } catch(err) {
    alert("Error login: " + JSON.stringify(err.payload));
  }
});

document.getElementById("btnRefresh").addEventListener("click", async ()=>{
  const { endpoints } = loadCfg();
  try {
    const r = await http("POST", endpoints.refresh, undefined, /*auth*/true);
    localStorage.setItem("accessToken", r.access_token);
    updateTokensUI();
    alert("Access token renovado");
  } catch(err) {
    alert("Error refresh: " + JSON.stringify(err.payload));
  }
});

document.getElementById("btnProfile").addEventListener("click", async ()=>{
  const { endpoints } = loadCfg();
  try {
    const r = await http("GET", endpoints.profile, undefined, /*auth*/true);
    alert("Protected OK: " + JSON.stringify(r));
  } catch(err) {
    if (err.status === 401) alert("401: Access token expirado. Usa Refresh.");
    else alert("Error protected: " + JSON.stringify(err.payload));
  }
});

document.getElementById("btnClearTokens").addEventListener("click", ()=>{
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  updateTokensUI();
  alert("Tokens eliminados");
});

// ===== Libros: Listar =====
document.getElementById("btnListBooks").addEventListener("click", async ()=>{
  const { endpoints } = loadCfg();
  const query = (document.getElementById("searchText").value || "").trim();
  let path = endpoints.books;
  if (query) {
    const esc = encodeURIComponent(query);
    // si tu endpoint soporta query ?q=...
    path = `${path}?q=${esc}`;
  }
  try {
    const data = await http("GET", path, undefined, /*auth*/true);
    renderBooks(Array.isArray(data) ? data : (data.books || []));
  } catch(err) {
    alert("Error obteniendo libros: " + JSON.stringify(err.payload));
  }
});

function renderBooks(rows) {
  const tb = document.getElementById("booksTbody");
  tb.innerHTML = "";
  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#999;">Sin resultados</td></tr>`;
    return;
  }
  for (const b of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${b.book_id ?? ""}</td>
      <td>${b.title ?? ""}</td>
      <td>${b.author ?? b.author_name ?? ""}</td>
      <td>${b.publisher ?? ""}</td>
      <td>${b.year ?? ""}</td>
      <td>${b.genre ?? b.genre_name ?? ""}</td>
      <td>${b.format ?? b.format_name ?? ""}</td>
    `;
    tb.appendChild(tr);
  }
}

// ===== Logs =====
document.getElementById("btnClearLogs").addEventListener("click", ()=>{
  document.getElementById("logBox").textContent = "";
});

// ===== Probe API on load =====
async function probeApi() {
  const { endpoints } = loadCfg();
  try {
    await http("GET", endpoints.profile, undefined, /*auth*/true);
    setApiStatus("API: OK (con token)", true);
  } catch {
    // si falla protected, probamos GET / (pública)
    try {
      await http("GET", "/", undefined, false);
      setApiStatus("API: OK (pública)", true);
    } catch {
      setApiStatus("API: no accesible", false);
    }
  }
}

updateTokensUI();
probeApi();
