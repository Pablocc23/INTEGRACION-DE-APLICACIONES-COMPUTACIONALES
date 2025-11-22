import requests
from concurrent.futures import ThreadPoolExecutor
import re

TARGET_IP = "104.248.215.179"
# Rango de puertos donde sueles levantar servicios (ajusta si usas otros)
PORTS_TO_SCAN = range(5000, 5010) 

def get_service_name(port):
    base_url = f"http://{TARGET_IP}:{port}"
    try:
        # 1. Intentamos leer el título del Swagger (Documentación)
        # Tus archivos usan flasgger, así que la doc está en /api/docs/
        response = requests.get(f"{base_url}/api/docs/", timeout=2)
        
        if response.status_code == 200:
            # Buscamos el texto dentro de <title>...</title>
            match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if match:
                clean_title = match.group(1).replace(" - Swagger UI", "").strip()
                return f"✅ Puerto {port}: DETECTADO -> '{clean_title}'"
            return f"⚠️ Puerto {port}: Activo (Swagger accesible pero sin título)"
            
        # 2. Si no hay Swagger, probamos si responde algo en la raíz
        elif response.status_code == 404:
             return f"⚠️ Puerto {port}: Activo (Servicio funcionando, pero sin /api/docs)"
        else:
             return f"⚠️ Puerto {port}: Responde código {response.status_code}"

    except requests.exceptions.ConnectionError:
        return None # Puerto cerrado, lo ignoramos

print(f"🕵️  Escaneando nombres de servicios en {TARGET_IP}...\n")

with ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(get_service_name, PORTS_TO_SCAN)
    
    found_any = False
    for res in results:
        if res:
            print(res)
            found_any = True
            
    if not found_any:
        print("❌ No se encontraron servicios activos en el rango 5000-5010.")