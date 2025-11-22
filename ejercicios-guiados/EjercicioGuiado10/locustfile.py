from locust import HttpUser, task, constant

# Configuración Base
TARGET_IP = "104.248.215.179"

class MicroserviceUser(HttpUser):
    """
    Clase abstracta: Locust NO intentará ejecutar esta clase directamente.
    Solo ejecutará las subclases de abajo.
    """
    abstract = True  # <--- ESTA LINEA ES LA SOLUCIÓN
    wait_time = constant(1) 

    @task
    def ping_root(self):
        # Si tu API requiere una ruta, cámbiala aquí (ej: "/api/health")
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Fallo con estado: {response.status_code}")

# --- Usuarios para cada puerto ---

class Service5000(MicroserviceUser):
    host = f"http://{TARGET_IP}:5000"

class Service5001(MicroserviceUser):
    host = f"http://{TARGET_IP}:5001"

class Service5002(MicroserviceUser):
    host = f"http://{TARGET_IP}:5002"

class Service5003(MicroserviceUser):
    host = f"http://{TARGET_IP}:5003"

class Service5004(MicroserviceUser):
    host = f"http://{TARGET_IP}:5004"

class Service5005(MicroserviceUser):
    host = f"http://{TARGET_IP}:5005"

class Service5006(MicroserviceUser):
    host = f"http://{TARGET_IP}:5006"