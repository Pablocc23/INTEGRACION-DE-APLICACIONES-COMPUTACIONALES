from locust import HttpUser, task, between
import random

# ==========================
# CONFIGURACIÓN
# ==========================
MICROSERVICE_IP = "http://136.112.28.160:5000"   # <--- HOST DEL MICROSERVICIO


class JWTUser(HttpUser):
    wait_time = between(1, 3)   # Simula usuarios reales
    token = None                # Access Token
    refresh_token = None        # Refresh Token

    def on_start(self):
        """
        Al iniciar cada usuario virtual:
        - hace login
        - obtiene tokens
        """
        self.login()

    def login(self):
        payload = {
            "username": "pablo",
            "password": "pablo123"   # tu contraseña correcta
        }

        with self.client.post("/login", json=payload, catch_response=True) as res:
            if res.status_code == 200:
                data = res.json()
                self.token = data["access_token"]
                self.refresh_token = data["refresh_token"]
                res.success()
            else:
                res.failure("❌ Error en login")

    # ==========================
    #         ENDPOINTS
    # ==========================

    @task(2)
    def test_index(self):
        self.client.get("/")

    @task(1)
    def test_register_get(self):
        self.client.get("/register")

    @task(1)
    def test_login_get(self):
        self.client.get("/login")

    @task(3)
    def test_protected(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/protected", headers=headers)

    @task(3)
    def test_books(self):
        if not self.token:
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get("/books?q=python", headers=headers)

    @task(2)
    def test_refresh(self):
        if not self.refresh_token:
            return
        headers = {"Authorization": f"Bearer {self.refresh_token}"}
        self.client.post("/refresh", headers=headers)

    @task(1)
    def test_register_post(self):
        """
        Genera usuario aleatorio para evitar repetidos
        """
        n = random.randint(10000, 99999)
        payload = {
            "username": f"user{n}",
            "email": f"test{n}@mail.com",
            "password": "123456"
        }
        self.client.post("/register", json=payload)
