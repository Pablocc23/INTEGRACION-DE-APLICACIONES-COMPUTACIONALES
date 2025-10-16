# pgui_client.py
import json
import os
import threading
import time
import base64
import datetime as dt
from urllib.parse import urljoin, urlencode

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import requests

APP_TITLE = "Cliente GUI - Microservicio JWT"
LOCALSTORAGE_FILE = "localstorage.json"

DEFAULT_CONFIG = {
    "host": "http://127.0.0.1",
    "port": 5000,
    "endpoints": {
        "index": "/",
        "register": "/register",
        "login": "/login",
        "protected": "/protected",
        "refresh": "/refresh",
        "books": "/books"
    },
    "tokens": {
        "access_token": "",
        "refresh_token": ""
    }
}

# Colores del semáforo
COLOR_RED = "#d9534f"
COLOR_ORANGE = "#f0ad4e"
COLOR_GREEN = "#5cb85c"
COLOR_GREY = "#9e9e9e"

# ---------- Utilidades de almacenamiento ----------
class LocalStorage:
    def __init__(self, path=LOCALSTORAGE_FILE):
        self.path = path
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        # mezcla con defaults sin pisar lo ya guardado
        self.data = self._deep_merge(DEFAULT_CONFIG, self.data)

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Error guardando localstorage:", e)

    def _deep_merge(self, base, override):
        if isinstance(base, dict) and isinstance(override, dict):
            merged = dict(base)
            for k, v in override.items():
                merged[k] = self._deep_merge(base.get(k), v)
            return merged
        return override if override is not None else base


# ---------- Decodificar JWT (sin verificar firma, sólo lectura de payload) ----------
def decode_jwt(token: str):
    """
    Devuelve (header, payload) como dicts o (None, None) si falla.
    No verifica firma; solo parsea base64url para mostrar en el log.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None, None

        def b64json(x):
            x += "=" * (-len(x) % 4)
            return json.loads(base64.urlsafe_b64decode(x.encode()).decode())

        header = b64json(parts[0])
        payload = b64json(parts[1])
        return header, payload
    except Exception:
        return None, None


def ts_to_str(ts):
    """Convierte timestamp (segundos UNIX) a cadena local legible."""
    try:
        return dt.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


# ---------- Cliente HTTP ----------
class MicroserviceClient:
    def __init__(self, storage: LocalStorage, log_func, set_semaforo_state):
        self.storage = storage
        self.log = log_func
        self.set_semaforo_state = set_semaforo_state
        self.session = requests.Session()

    def base_url(self):
        host = self.storage.data["host"].rstrip("/")
        port = self.storage.data["port"]
        return f"{host}:{port}"

    def url_for(self, key):
        ep = self.storage.data["endpoints"].get(key, "/")
        return urljoin(self.base_url() + "/", ep.lstrip("/"))

    def _auth_headers(self, use_access=True):
        headers = {"Content-Type": "application/json"}
        if use_access:
            access = self.storage.data["tokens"].get("access_token")
            if access:
                headers["Authorization"] = f"Bearer {access}"
        return headers

    def _log_jwt(self, which="access_token"):
        tok = self.storage.data["tokens"].get(which, "")
        if not tok:
            self.log(f"[JWT] No hay {which} guardado.")
            return
        header, payload = decode_jwt(tok)
        self.log(f"[JWT] {which} (primeros 30 chars): {tok[:30]}...")
        if header:
            self.log(f"[JWT] header: {json.dumps(header, indent=2, ensure_ascii=False)}")
        if payload:
            pretty = dict(payload)
            # mostrar campos comunes legibles
            if "iat" in pretty:
                pretty["iat_readable"] = ts_to_str(pretty["iat"])
            if "exp" in pretty:
                pretty["exp_readable"] = ts_to_str(pretty["exp"])
            self.log(f"[JWT] payload: {json.dumps(pretty, indent=2, ensure_ascii=False)}")

    # ---------- Healthcheck (GET /) ----------
    def healthcheck(self):
        self.set_semaforo_state("orange")
        url = self.url_for("index")
        self.log(f"[HEALTH] Consultando {url}")
        try:
            r = self.session.get(url, timeout=5)
            self.log(f"[HEALTH] Respuesta {r.status_code}: {r.text}")
            if r.ok:
                self.set_semaforo_state("green")
                return True
            else:
                self.set_semaforo_state("red")
                return False
        except Exception as e:
            self.log(f"[HEALTH] Error: {e}")
            self.set_semaforo_state("red")
            return False

    # ---------- Register ----------
    def register(self, username, email, password):
        url = self.url_for("register")
        payload = {"username": username, "email": email, "password": password}
        self.log(f"[REGISTER] POST {url}")
        self.log(f"[REGISTER] body: {json.dumps(payload)}")
        try:
            r = self.session.post(url, json=payload, headers=self._auth_headers(False), timeout=10)
            self.log(f"[REGISTER] status={r.status_code} body={r.text}")
            if r.status_code == 201:
                messagebox.showinfo("Registro", "Usuario registrado con éxito.")
                return True
            else:
                messagebox.showwarning("Registro", f"Fallo registro: {r.status_code}\n{r.text}")
                return False
        except Exception as e:
            self.log(f"[REGISTER] Error: {e}")
            messagebox.showerror("Registro", str(e))
            return False

    # ---------- Login ----------
    def login(self, username, password):
        url = self.url_for("login")
        payload = {"username": username, "password": password}
        self.log(f"[LOGIN] POST {url}")
        self.log(f"[LOGIN] body: {json.dumps(payload)}")

        try:
            r = self.session.post(url, json=payload, headers=self._auth_headers(False), timeout=10)
            self.log(f"[LOGIN] status={r.status_code} body={r.text}")

            if r.ok:
                data = r.json()
                acc = data.get("access_token", "")
                ref = data.get("refresh_token", "")
                if not acc or not ref:
                    messagebox.showwarning("Login", "No se recibieron tokens.")
                    return False
                self.storage.data["tokens"]["access_token"] = acc
                self.storage.data["tokens"]["refresh_token"] = ref
                self.storage.save()
                self._log_jwt("access_token")
                self._log_jwt("refresh_token")
                messagebox.showinfo("Login", "Inicio de sesión exitoso.")
                return True
            else:
                messagebox.showwarning("Login", f"Fallo login: {r.status_code}\n{r.text}")
                return False
        except Exception as e:
            self.log(f"[LOGIN] Error: {e}")
            messagebox.showerror("Login", str(e))
            return False

    # ---------- Refresh token ----------
    def refresh_access_token(self):
        url = self.url_for("refresh")
        headers = {"Content-Type": "application/json"}
        # El refresh va en Authorization: Bearer <refresh>
        refresh = self.storage.data["tokens"].get("refresh_token", "")
        if not refresh:
            self.log("[REFRESH] No hay refresh token guardado.")
            return False
        headers["Authorization"] = f"Bearer {refresh}"
        self.log(f"[REFRESH] POST {url} con refresh Bearer (oculto)")
        try:
            r = self.session.post(url, headers=headers, timeout=10)
            self.log(f"[REFRESH] status={r.status_code} body={r.text}")
            if r.ok:
                data = r.json()
                acc = data.get("access_token", "")
                if acc:
                    self.storage.data["tokens"]["access_token"] = acc
                    self.storage.save()
                    self._log_jwt("access_token")
                    return True
            return False
        except Exception as e:
            self.log(f"[REFRESH] Error: {e}")
            return False

    # ---------- GET /protected con auto-refresh ----------
    def get_protected(self):
        url = self.url_for("protected")
        self.log(f"[PROTECTED] GET {url}")
        try:
            r = self.session.get(url, headers=self._auth_headers(True), timeout=10)
            self.log(f"[PROTECTED] status={r.status_code} body={r.text}")

            if r.status_code == 401:
                # intento de refresh
                self.log("[PROTECTED] 401: intentando refresh de access token…")
                if self.refresh_access_token():
                    self.log("[PROTECTED] Reintentando con nuevo access token…")
                    r2 = self.session.get(url, headers=self._auth_headers(True), timeout=10)
                    self.log(f"[PROTECTED] status={r2.status_code} body={r2.text}")
                    return r2
                else:
                    self.log("[PROTECTED] Refresh falló.")
            return r
        except Exception as e:
            self.log(f"[PROTECTED] Error: {e}")
            return None

    # ---------- GET /books (opcionalmente ?q=) con auto-refresh ----------
    def get_books(self, q=""):
        base = self.url_for("books")
        url = base
        if q:
            url = f"{base}?{urlencode({'q': q})}"

        self.log(f"[BOOKS] GET {url}")
        try:
            r = self.session.get(url, headers=self._auth_headers(True), timeout=15)
            self.log(f"[BOOKS] status={r.status_code} body_len={len(r.text)}")

            if r.status_code == 401:
                self.log("[BOOKS] 401: intentando refresh de access token…")
                if self.refresh_access_token():
                    self.log("[BOOKS] Reintentando con nuevo access token…")
                    r2 = self.session.get(url, headers=self._auth_headers(True), timeout=15)
                    self.log(f"[BOOKS] status={r2.status_code} body_len={len(r2.text)}")
                    return r2
                else:
                    self.log("[BOOKS] Refresh falló.")
            return r
        except Exception as e:
            self.log(f"[BOOKS] Error: {e}")
            return None


# ---------- GUI ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x720")

        self.storage = LocalStorage()
        self.client = MicroserviceClient(
            storage=self.storage,
            log_func=self.append_log,
            set_semaforo_state=self.set_semaforo
        )

        self._build_ui()
        self._start_health_loop()

    # UI Layout
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Barra superior: configuración + semáforo + acciones rápidas
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)
        top.columnconfigure(10, weight=1)

        ttk.Label(top, text="Host:").grid(row=0, column=0, sticky="w")
        self.var_host = tk.StringVar(value=self.storage.data["host"])
        ttk.Entry(top, textvariable=self.var_host, width=22).grid(row=0, column=1, padx=5)

        ttk.Label(top, text="Puerto:").grid(row=0, column=2, sticky="w")
        self.var_port = tk.IntVar(value=self.storage.data["port"])
        ttk.Entry(top, textvariable=self.var_port, width=8).grid(row=0, column=3, padx=5)

        ttk.Button(top, text="Guardar configuración", command=self.save_config).grid(row=0, column=4, padx=10)

        # Semáforo
        self.semaforo_canvas = tk.Canvas(top, width=72, height=26, highlightthickness=0)
        self.semaforo_canvas.grid(row=0, column=5, padx=10)
        self.semaforo_lights = [
            self.semaforo_canvas.create_oval(2, 2, 24, 24, fill=COLOR_GREY, outline=""),
            self.semaforo_canvas.create_oval(26, 2, 48, 24, fill=COLOR_GREY, outline=""),
            self.semaforo_canvas.create_oval(50, 2, 72, 24, fill=COLOR_GREY, outline=""),
        ]
        # Leyenda semáforo
        ttk.Label(top, text="Rojo: caída | Naranja: comprobando | Verde: OK").grid(row=0, column=6, sticky="w", padx=10)

        ttk.Button(top, text="Checar /Health", command=lambda: self.run_thread(self.client.healthcheck)).grid(row=0, column=7, padx=10)

        # Tabs principales
        nb = ttk.Notebook(self)
        nb.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Tab Autenticación
        tab_auth = ttk.Frame(nb)
        nb.add(tab_auth, text="Autenticación")

        # Login
        login_frame = ttk.LabelFrame(tab_auth, text="Login")
        login_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ttk.Label(login_frame, text="Usuario:").grid(row=0, column=0, sticky="w")
        self.var_login_user = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.var_login_user, width=24).grid(row=0, column=1, padx=5)
        ttk.Label(login_frame, text="Contraseña:").grid(row=1, column=0, sticky="w")
        self.var_login_pass = tk.StringVar()
        ttk.Entry(login_frame, textvariable=self.var_login_pass, show="•", width=24).grid(row=1, column=1, padx=5)
        ttk.Button(login_frame, text="Iniciar sesión", command=self.do_login).grid(row=2, column=0, columnspan=2, pady=8)

        # Registro
        reg_frame = ttk.LabelFrame(tab_auth, text="Registro")
        reg_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ttk.Label(reg_frame, text="Usuario:").grid(row=0, column=0, sticky="w")
        self.var_reg_user = tk.StringVar()
        ttk.Entry(reg_frame, textvariable=self.var_reg_user, width=24).grid(row=0, column=1, padx=5)
        ttk.Label(reg_frame, text="Email:").grid(row=1, column=0, sticky="w")
        self.var_reg_email = tk.StringVar()
        ttk.Entry(reg_frame, textvariable=self.var_reg_email, width=24).grid(row=1, column=1, padx=5)
        ttk.Label(reg_frame, text="Contraseña:").grid(row=2, column=0, sticky="w")
        self.var_reg_pass = tk.StringVar()
        ttk.Entry(reg_frame, textvariable=self.var_reg_pass, show="•", width=24).grid(row=2, column=1, padx=5)
        ttk.Button(reg_frame, text="Registrar", command=self.do_register).grid(row=3, column=0, columnspan=2, pady=8)

        # Tab Acciones protegidas
        tab_actions = ttk.Frame(nb)
        nb.add(tab_actions, text="Acciones protegidas")

        act_left = ttk.LabelFrame(tab_actions, text="/protected")
        act_left.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ttk.Button(act_left, text="GET /protected", command=self.call_protected).grid(row=0, column=0, padx=5, pady=5, sticky="w")

        act_right = ttk.LabelFrame(tab_actions, text="/books")
        act_right.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ttk.Label(act_right, text="Buscar (q):").grid(row=0, column=0, sticky="w")
        self.var_q = tk.StringVar()
        ttk.Entry(act_right, textvariable=self.var_q, width=28).grid(row=0, column=1, padx=5)
        ttk.Button(act_right, text="GET /books", command=self.call_books).grid(row=0, column=2, padx=5)

        # Tabla de resultados de /books
        cols = ("isbn", "book_id", "title", "author", "publisher", "year", "genre", "price", "stock", "format")
        self.books_tree = ttk.Treeview(tab_actions, columns=cols, show="headings", height=14)
        for c in cols:
            self.books_tree.heading(c, text=c)
            self.books_tree.column(c, width=110, anchor="w")
        self.books_tree.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))

        tab_actions.rowconfigure(1, weight=1)
        tab_actions.columnconfigure(0, weight=1)
        tab_actions.columnconfigure(1, weight=1)

        # Tab Tokens
        tab_tokens = ttk.Frame(nb)
        nb.add(tab_tokens, text="Tokens y configuración")
        # Ver tokens
        token_box = ttk.LabelFrame(tab_tokens, text="Tokens")
        token_box.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ttk.Button(token_box, text="Mostrar info Access Token", command=lambda: self.client._log_jwt("access_token")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Button(token_box, text="Mostrar info Refresh Token", command=lambda: self.client._log_jwt("refresh_token")).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(token_box, text="Hacer Refresh ahora", command=lambda: self.run_thread(self._do_refresh_now)).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        # Editar endpoints
        ep_box = ttk.LabelFrame(tab_tokens, text="Endpoints")
        ep_box.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self._endpoint_vars = {}
        row = 0
        for key in ["index", "register", "login", "protected", "refresh", "books"]:
            ttk.Label(ep_box, text=key).grid(row=row, column=0, sticky="w")
            var = tk.StringVar(value=self.storage.data["endpoints"][key])
            self._endpoint_vars[key] = var
            ttk.Entry(ep_box, textvariable=var, width=40).grid(row=row, column=1, padx=5, pady=2, sticky="w")
            row += 1
        ttk.Button(ep_box, text="Guardar endpoints", command=self.save_endpoints).grid(row=row, column=0, columnspan=2, pady=6)

        # Log (siempre visible)
        log_frame = ttk.LabelFrame(self, text="Log del microservicio / cliente")
        log_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.rowconfigure(2, weight=1)

        self.log_text = ScrolledText(log_frame, height=10, wrap="word", state="disabled", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)

        # Línea inicial
        self.append_log("Aplicación iniciada. Config cargada de localstorage.json")
        self.append_log(f"Base URL: {self.client.base_url()}")
        self.append_log(f"Endpoints: {json.dumps(self.storage.data['endpoints'], ensure_ascii=False)}")

    # ---------- Acciones GUI ----------
    def save_config(self):
        self.storage.data["host"] = self.var_host.get().strip()
        try:
            self.storage.data["port"] = int(self.var_port.get())
        except Exception:
            messagebox.showwarning("Config", "Puerto inválido")
            return
        self.storage.save()
        self.append_log("[CONFIG] Host/puerto guardados.")
        self.append_log(f"[CONFIG] Base URL: {self.client.base_url()}")

    def save_endpoints(self):
        for k, var in self._endpoint_vars.items():
            self.storage.data["endpoints"][k] = var.get().strip()
        self.storage.save()
        self.append_log("[CONFIG] Endpoints guardados:")
        self.append_log(json.dumps(self.storage.data["endpoints"], indent=2, ensure_ascii=False))

    def do_register(self):
        username = self.var_reg_user.get().strip()
        email = self.var_reg_email.get().strip()
        password = self.var_reg_pass.get().strip()
        if not username or not email or not password:
            messagebox.showwarning("Registro", "Llena usuario, email y contraseña.")
            return
        self.run_thread(self.client.register, username, email, password)

    def do_login(self):
        user = self.var_login_user.get().strip()
        pwd = self.var_login_pass.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Login", "Llena usuario y contraseña.")
            return
        self.run_thread(self.client.login, user, pwd)

    def call_protected(self):
        def _call():
            r = self.client.get_protected()
            if r is None:
                return
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text}
            self.append_log(f"[PROTECTED] Resultado parseado: {json.dumps(data, ensure_ascii=False)}")
        self.run_thread(_call)

    def call_books(self):
        q = self.var_q.get().strip()
        def _call():
            r = self.client.get_books(q=q)
            if r is None:
                return
            try:
                data = r.json()
            except Exception:
                self.append_log(f"[BOOKS] No JSON válido:\n{r.text[:1000]}")
                return
            # limpiar tabla
            for i in self.books_tree.get_children():
                self.books_tree.delete(i)
            if isinstance(data, list):
                for row in data:
                    vals = tuple(row.get(col, "") for col in self.books_tree["columns"])
                    self.books_tree.insert("", "end", values=vals)
            self.append_log(f"[BOOKS] Filas cargadas: {len(data) if isinstance(data, list) else 'N/A'}")
        self.run_thread(_call)

    def _do_refresh_now(self):
        ok = self.client.refresh_access_token()
        if ok:
            messagebox.showinfo("Refresh", "Access token renovado.")
        else:
            messagebox.showwarning("Refresh", "No se pudo renovar access token.")

    # ---------- Semáforo ----------
    def set_semaforo(self, state: str):
        # state: "red", "orange", "green"
        colors = {
            "red":   (COLOR_RED, COLOR_GREY, COLOR_GREY),
            "orange":(COLOR_GREY, COLOR_ORANGE, COLOR_GREY),
            "green": (COLOR_GREY, COLOR_GREY, COLOR_GREEN),
        }.get(state, (COLOR_GREY, COLOR_GREY, COLOR_GREY))

        for item, color in zip(self.semaforo_lights, colors):
            self.semaforo_canvas.itemconfig(item, fill=color)

    def _health_loop(self):
        self.client.healthcheck()
        # reprogramar
        self.after(10000, self._health_loop)  # cada 10s

    def _start_health_loop(self):
        self.after(500, self._health_loop)

    # ---------- Logs ----------
    def append_log(self, text):
        now = dt.datetime.now().strftime("%H:%M:%S")
        line = f"[{now}] {text}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ---------- Helpers ----------
    def run_thread(self, fn, *args, **kwargs):
        def runner():
            # estado naranja durante operación
            prev = None
            try:
                prev = "orange"
                self.set_semaforo(prev)
                return fn(*args, **kwargs)
            finally:
                # no forzamos verde: dejamos que healthloop lo ponga;
                # si quieres, puedes devolver a gris aquí.
                pass
        t = threading.Thread(target=runner, daemon=True)
        t.start()


if __name__ == "__main__":
    App().mainloop()
