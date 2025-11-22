import requests
from locust import HttpUser, task, constant, events
from locust.exception import StopUser

# === 1. CONFIGURACIÓN DE RED ===
TARGET_IP = "104.248.215.179"

# URL de Login: Basado en tu 'auth.py' y tu captura de pantalla (Puerto 5002)
AUTH_URL = f"http://{TARGET_IP}:5002/api/login"

# === 2. DATOS REALES (Extraídos de heartguard_backup.sql) ===
CREDENTIALS = {
    "login": "carlos.gómez@heartguard.com", # Usuario Doctor Real
    "password": "123" # Contraseña indicada por el usuario
}

# IDs extraídos del SQL Dump para evitar errores 404
TEST_DATA = {
    "patient_id": "7199cd3d-47ce-409f-89d5-9d01ca82fd08", # Paciente: David Ruiz Romero
    "appointment_id": "db61d072-67ef-4cad-b396-6f86d13187df", # Cita del 2025-10-28
    "history_id": "e94966ca-22d8-4af5-aa97-9c5b45630dae", # Historial de David
    "device_id": "c132e3d6-18fe-4ef9-9589-f60053446edc" # Dispositivo CardioWatch Pro
}

class AuthenticatedUser(HttpUser):
    """
    Clase base. Se encarga de obtener el Token JWT del puerto 5002
    antes de que arranque cualquier prueba de los otros microservicios.
    """
    abstract = True
    token = None
    
    def on_start(self):
        try:
            # Intentamos loguearnos
            response = requests.post(AUTH_URL, json=CREDENTIALS, timeout=5)
            
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                # print(f"🔑 Login OK para {self.__class__.__name__}") 
            else:
                print(f"💀 Error Login ({response.status_code}) en {AUTH_URL}: {response.text}")
                # Si falla el login, detenemos este usuario para no ensuciar las gráficas
                raise StopUser()
                
        except Exception as e:
            print(f"🔥 Error de conexión al Auth: {e}")
            raise StopUser()

    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

# === 3. ESCENARIOS DE PRUEBA (Microservicios) ===

class ServiceAppointments(AuthenticatedUser):
    # Basado en appointments.py -> corre en 5003 o 5001 según despliegue
    # Ajustar puerto aquí si es necesario. Asumo 5001 según tu chat anterior.
    host = f"http://{TARGET_IP}:5001" 
    wait_time = constant(1)

    @task
    def get_appointment_detail(self):
        if self.token:
            self.client.get(
                f"/api/appointments/{TEST_DATA['appointment_id']}", 
                headers=self.get_headers(),
                name="GET /api/appointments/{id}"
            )

class ServiceMedicalHistory(AuthenticatedUser):
    # Basado en medical_history.py -> Puerto 5004
    host = f"http://{TARGET_IP}:5004"
    wait_time = constant(1)

    @task
    def get_patient_history(self):
        if self.token:
            # Endpoint extraído de medical_history.py línea 337
            self.client.get(
                f"/api/medical-history?patient_id={TEST_DATA['patient_id']}", 
                headers=self.get_headers(),
                name="GET /api/medical-history"
            )

class ServicePatients(AuthenticatedUser):
    # Basado en patients.py -> Puerto 5002/5005 (Probablemente 5005)
    host = f"http://{TARGET_IP}:5005"
    wait_time = constant(1)

    @task
    def get_patient_profile(self):
        if self.token:
            # Endpoint extraído de patients.py línea 272
            self.client.get(
                f"/api/patients/{TEST_DATA['patient_id']}", 
                headers=self.get_headers(),
                name="GET /api/patients/{id}"
            )

class ServiceVitals(AuthenticatedUser):
    # Basado en vital_monitoring.py -> Puerto 5006
    host = f"http://{TARGET_IP}:5006"
    wait_time = constant(1)

    @task
    def get_vital_signs(self):
        if self.token:
            # Endpoint extraído de vital_monitoring.py línea 239
            # Requiere patient_id y range_hours
            params = {
                "patient_id": TEST_DATA['patient_id'],
                "range_hours": 24
            }
            self.client.get(
                "/api/vitals", 
                params=params,
                headers=self.get_headers(),
                name="GET /api/vitals"
            )