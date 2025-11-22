import requests
from locust import HttpUser, task, between
from locust.exception import StopUser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# === 1. CONFIGURACIÓN ===
TARGET_IP = "104.248.215.179"
LOGIN_URL = f"http://{TARGET_IP}:5002/api/login"

CREDENTIALS = {
    "login": "carlos.gómez@heartguard.com",
    "password": "123"
}

TEST_DATA = {
    "patient_id": "7199cd3d-47ce-409f-89d5-9d01ca82fd08",
    "appointment_id": "db61d072-67ef-4cad-b396-6f86d13187df"
}

class OmniDoctor(HttpUser):
    # Espera entre 2 y 5 segundos entre acciones (Ritmo moderado/sostenible)
    wait_time = between(2, 5)
    
    # Definimos el host base para evitar errores de Locust
    host = f"http://{TARGET_IP}:5002"
    token = None

    def on_start(self):
        # Configuración para larga duración: Evitar mantener sockets abiertos innecesariamente
        self.client.keep_alive = False
        adapter = HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1))
        self.client.mount("http://", adapter)

        try:
            res = requests.post(LOGIN_URL, json=CREDENTIALS, headers={"Connection": "close"}, timeout=10)
            if res.status_code == 200:
                self.token = res.json().get("access_token")
            else:
                print(f"❌ Falló Login Inicial: {res.status_code}")
                raise StopUser()
        except Exception as e:
            print(f"🔥 Error Conexión: {e}")
            raise StopUser()

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Connection": "close" # Vital para pruebas largas en servidores dev
        }

    # === TAREAS PONDERADAS (Mix de uso real) ===
    
    # Peso 3: Consultar signos vitales es lo más común (Monitoreo)
    @task(3)
    def check_vitals(self):
        try:
            self.client.get(f"http://{TARGET_IP}:5006/api/vitals", 
                           params={"patient_id": TEST_DATA['patient_id'], "range_hours": 24},
                           headers=self.get_headers(), name="VITALES: Monitor 24h")
        except: pass

    # Peso 1: Consultar cita
    @task(1)
    def check_appointment(self):
        try:
            self.client.get(f"http://{TARGET_IP}:5001/api/appointments/{TEST_DATA['appointment_id']}", 
                           headers=self.get_headers(), name="CITAS: Detalle")
        except: pass

    # Peso 1: Consultar historial
    @task(1)
    def check_history(self):
        try:
            self.client.get(f"http://{TARGET_IP}:5004/api/medical-history?patient_id={TEST_DATA['patient_id']}", 
                           headers=self.get_headers(), name="HISTORIAL: Lista")
        except: pass