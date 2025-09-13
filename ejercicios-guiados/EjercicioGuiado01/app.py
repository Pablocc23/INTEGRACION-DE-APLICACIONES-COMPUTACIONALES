# Genera un código en Python que reciba un texto y clasique si correspon a Iaas, Paas, Saas o Faas usando reglas básicas.

#PASO 1: Instalar scikit-learn
# Asegúrate de tener instalado scikit-learn para el procesamiento de texto y la clasificación.
# Puedes instalarlo usando pip. Si no tienes pip instalado, primero instálalo.

# Abre tu terminal y ejecuta este comando:

# en bash
# pip install scikit-learn

# Si usas Python desde Microsoft Store (como parece), y te da problemas, intenta con:

# En bash

# python -m pip install scikit-learn


"""
Clasificador simple de modelos de servicio en la nube (IaaS / PaaS / SaaS / FaaS)
- Regla primero (regex con español e inglés)
- ML de respaldo (TF-IDF + LogisticRegression)
- Interfaz por argparse:
    * --texto "..."         -> clasifica una sola cadena
    * --interactivo         -> modo interactivo (escribe 'salir' para terminar)
Uso de ejemplo:
    python clasificador_cloud.py --texto "Despliego funciones serverless que reaccionan a eventos"
    python clasificador_cloud.py --interactivo
"""

import re
import sys
import argparse
import unicodedata

# === Opcional: scikit-learn para respaldo con ML ===
# Si no está instalado, el clasificador seguirá funcionando solo con reglas.
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False
    TfidfVectorizer = None
    LogisticRegression = None


# ---------- Utilidades ----------
def normalize(text: str) -> str:
    """Minúsculas + quita acentos/diacríticos para robustecer las regex."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


# ---------- Reglas (Regex) ----------
# IaaS
PAT_IAAS = re.compile(
    r'\b('
    r'infrastructure as a service|infraestructura como servicio|iaas|'
    r'vm|virtual (machine|machines|server|servers)|maquinas? virtuales?|'
    r'provision(?:ing)?|load balancer|balanceador(?:es)? de carga|'
    r'firewalls?|network(?:ing)?|redes?|'
    r'block storage|almacenamiento de bloques?|'
    r'object storage|almacenamiento de objetos?|'
    r'bare metal|data ?center|centro(?:s)? de datos?'
    r')\b',
    flags=re.IGNORECASE
)

# PaaS
PAT_PAAS = re.compile(
    r'\b('
    r'platform as a service|plataforma como servicio|paas|'
    r'runtime environment|entorno de ejecucion|'
    r'application framework|framework de aplicacion|'
    r'managed database|base de datos gestionada|'
    r'development platform|plataforma de desarrollo|'
    r'middleware|'
    r'container orchestration|orquestacion de contenedores|'
    r'deployment tools?|herramientas? de despliegue'
    r')\b',
    flags=re.IGNORECASE
)

# SaaS
PAT_SAAS = re.compile(
    r'\b('
    r'software as a service|software como servicio|saas|'
    r'crm|email service|servicio de correo|'
    r'office suite|suite de oficina|'
    r'web app|aplicacion web|'
    r'cloud software|software en la nube|'
    r'hosted application|aplicacion alojada|'
    r'collaboration tools?|herramientas? de colaboracion|'
    r'streaming platform|plataforma de streaming'
    r')\b',
    flags=re.IGNORECASE
)

# FaaS
PAT_FAAS = re.compile(
    r'\b('
    r'function as a service|funciones? como servicio|faas|'
    r'serverless|sin servidor|'
    r'event[- ]driven|impulsado por eventos?|'
    r'function deployment|despliegue de funciones?|'
    r'lambda function|funciones? lambda|'
    r'triggered by event|activad[ao]s? por eventos?|'
    r'short[- ]lived code|codigo de corta duracion'
    r')\b',
    flags=re.IGNORECASE
)

def is_iaas(text_norm: str) -> bool:
    return PAT_IAAS.search(text_norm) is not None

def is_paas(text_norm: str) -> bool:
    return PAT_PAAS.search(text_norm) is not None

def is_saas(text_norm: str) -> bool:
    return PAT_SAAS.search(text_norm) is not None

def is_faas(text_norm: str) -> bool:
    return PAT_FAAS.search(text_norm) is not None


# ---------- Entrenamiento de respaldo (ML) ----------
training_texts = [
    "Provision virtual machines and manage networking",  # IaaS
    "Setup storage and firewalls using infrastructure",  # IaaS
    "Use runtime environment to deploy applications",    # PaaS
    "Develop apps on a managed platform",                # PaaS
    "Access CRM and email via cloud software",           # SaaS
    "Our web app is hosted online",                      # SaaS
    "Run serverless functions triggered by events",      # FaaS
    "Execute short-lived code in response to triggers",  # FaaS
    # Español
    "Desplegar maquinas virtuales y configurar redes",   # IaaS
    "Plataforma de desarrollo con base de datos gestionada",  # PaaS
    "Usar una aplicacion web de CRM en la nube",         # SaaS
    "Funciones sin servidor activadas por eventos",      # FaaS
]
training_labels = [
    "IaaS", "IaaS",
    "PaaS", "PaaS",
    "SaaS", "SaaS",
    "FaaS", "FaaS",
    "IaaS", "PaaS", "SaaS", "FaaS"
]

if SKLEARN_OK:
    vectorizer = TfidfVectorizer(lowercase=True)
    X_train = vectorizer.fit_transform(training_texts)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, training_labels)
else:
    vectorizer = None
    model = None


# ---------- Clasificación combinada ----------
def classify_service(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return "Invalid input"

    text_norm = normalize(text)

    # 1) Reglas (prioridad)
    if is_iaas(text_norm):
        return "IaaS (by regex)"
    if is_paas(text_norm):
        return "PaaS (by regex)"
    if is_saas(text_norm):
        return "SaaS (by regex)"
    if is_faas(text_norm):
        return "FaaS (by regex)"

    # 2) Respaldo ML
    if SKLEARN_OK and vectorizer is not None and model is not None:
        X_input = vectorizer.transform([text])
        pred = model.predict(X_input)[0]
        proba = model.predict_proba(X_input)[0]
        labels = model.classes_
        pairs = sorted(zip(labels, proba), key=lambda x: x[1], reverse=True)[:2]
        top_str = ", ".join(f"{lbl}: {p:.2f}" for lbl, p in pairs)
        return f"{pred} (by AI, top: {top_str})"

    # 3) Sin ML disponible
    return "Unknown (no regex match; ML unavailable)"


# ---------- Main con argparse ----------
def main():
    parser = argparse.ArgumentParser(
        description="Clasificador de servicios en la nube: IaaS / PaaS / SaaS / FaaS"
    )
    parser.add_argument(
        "--texto", type=str,
        help='Texto para clasificar directamente. Ej: --texto "Despliego funciones serverless"'
    )
    parser.add_argument(
        "--interactivo", action="store_true",
        help="Iniciar modo interactivo (escribe 'salir' para terminar)"
    )
    args = parser.parse_args()

    # 1) Interactivo explícito, o sin args y hay TTY -> interactivo
    if args.interactivo or (not args.texto and sys.stdin.isatty()):
        print("=== Clasificador de IaaS / PaaS / SaaS / FaaS ===")
        while True:
            try:
                text = input("\nEscribe un párrafo para clasificar (o escribe 'salir' para terminar):\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\nPrograma terminado.")
                break

            if text.strip().lower() == 'salir':
                print("Programa terminado.")
                break

            result = classify_service(text)
            print(f"\nClasificación: {result}")
        return

    # 2) --texto
    if args.texto:
        result = classify_service(args.texto)
        print(f"\nClasificación: {result}")
        return

    # 3) Si viene texto por stdin (pipe)
    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            result = classify_service(text)
            print(f"\nClasificación: {result}")
            return

    # 4) Nada que hacer
    print("⚠️ Proporciona --texto \"...\" o usa --interactivo para iniciar el modo interactivo.")


if __name__ == "__main__":
    main()