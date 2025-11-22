import csv
import jwt  # Necesario para leer el rol dentro del token
import requests
from locust import HttpUser, task, constant
from locust.exception import StopUser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# === 1. CONFIGURACIÓN ===
TARGET_IP = "104.248.215.179"
LOGIN_URL = f"http://{TARGET_IP}:5002/api/login"

# ID del Rol Doctor (Copiado de tu appointments.py)
DOCTOR_ROLE_ID = '0a0fdb28-314a-4b24-94e2-d30c6fb4b041'

# Paciente de prueba para que lo vean los doctores
TEST_PATIENT_ID = "7199cd3d-47ce-409f-89d5-9d01ca82fd08"

# Cargar Usuarios
USER_CREDENTIALS = []
try:
    with open("users.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                USER_CREDENTIALS.append({"login": row[0].strip(), "password": row[1].strip()})
except:
    print("Error cargando users.csv")
    exit(1)

class SmartUser(HttpUser):
    host = f"http://{TARGET_IP}:5002"
    wait_time = constant(2)
    token = None
    role_id = None
    email = None

    def on_start(self):
        # Estrategia CSV rotativa
        import random
        user_data = random.choice(USER_CREDENTIALS)
        self.email = user_data['login']
        
        # Configuración de conexión
        self.client.keep_alive = False
        adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5))
        self.client.mount("http://", adapter)

        try:
            res = requests.post(LOGIN_URL, json=user_data, headers={"Connection": "close"}, timeout=5)
            if res.status_code == 200:
                self.token = res.json().get("access_token")
                # --- INTELIGENCIA: DECODIFICAR TOKEN ---
                # Leemos el payload del JWT para saber qué rol tiene este usuario
                decoded = jwt.decode(self.token, options={"verify_signature": False})
                self.role_id = decoded.get('role_id')
                # print(f"✅ Login: {self.email} (Rol: {self.role_id})")
            else:
                print(f"⚠️ Login Falló para {self.email}: {res.status_code}")
                raise StopUser()
        except Exception as e:
            print(f"🔥 Error Login: {e}")
            raise StopUser()

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Connection": "close"
        }

    @task
    def smart_action(self):
        if not self.token: return

        # === COMPORTAMIENTO SEGÚN ROL ===
        
        if self.role_id == DOCTOR_ROLE_ID:
            # SI SOY DOCTOR: Puedo ver los signos vitales de David Ruiz
            # (Tu API permite a doctores ver a cualquier paciente)
            try:
                self.client.get(
                    f"http://{TARGET_IP}:5006/api/vitals", 
                    params={"patient_id": TEST_PATIENT_ID, "range_hours": 24},
                    headers=self.get_headers(), 
                    name="DOCTOR: Ver Vitales Paciente"
                )
            except: pass
            
        else:
            # SI SOY PACIENTE: Solo puedo ver MI PROPIA historia.
            # Tu endpoint 'medical_history' es inteligente: si no mandas ID,
            # busca el tuyo propio. ¡Usemos eso!
            try:
                self.client.get(
                    f"http://{TARGET_IP}:5004/api/medical-history", 
                    headers=self.get_headers(), 
                    name="PACIENTE: Ver Mi Historial"
                )
            except: pass