import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from scipy.optimize import linprog
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime, timedelta
import hashlib
import hmac
import time
import base64
import struct

# Configuración obligatoria de la página
st.set_page_config(
    page_title="Cr-IA 150 | Enterprise Livestock SaaS & Security",
    page_icon="🐄",
    layout="wide"
)

# --- ESTILOS CSS DE NIVEL EMPRESARIAL CON ACCESO SEGURO ---
st.markdown("""<style>
.main { background-color: #fffaf8; }
.stMetric {
    background: #ffffff;
    padding: 14px 16px !important;
    border-radius: 14px;
    box-shadow: 0 4px 20px -3px rgba(194, 65, 12, 0.12);
    border: 1px solid #fed7aa;
    border-left: 6px solid #ea580c;
    margin-bottom: 10px !important;
}
.stMetric label {
    font-size: 0.78rem !important;
    color: #9a3412 !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.stMetric [data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    color: #431407 !important;
    font-weight: 900 !important;
}
h1, h2, h3, h4, h5, h6 {
    color: #431407 !important;
    font-weight: 800 !important;
}
.auth-box {
    background-color: #ffffff;
    padding: 30px;
    border-radius: 20px;
    border: 2px solid #fed7aa;
    box-shadow: 0 10px 25px rgba(194, 65, 12, 0.1);
    max-width: 500px;
    margin: 0 auto;
}
</style>""", unsafe_allow_html=True)

# --- FUNCIONES AUXILIARES DE SEGURIDAD (HASH & TOTP 2FA) ---
def hash_password(password):
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'cria150_salt_secure', 100000).hex()

def generate_totp_secret():
    import secrets
    return secrets.token_hex(10).upper()

def get_totp_token(secret, intervals_no=None):
    if intervals_no is None:
        intervals_no = int(time.time() // 30)
    key = secret.encode('utf-8')
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[19] & 15
    h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
    return f"{h:06d}"

def verify_totp(secret, token):
    curr_interval = int(time.time() // 30)
    for i in range(-1, 2):
        if get_totp_token(secret, curr_interval + i) == str(token).strip():
            return True
    return False

# --- CLASE DE BASE DE DATOS ROBUSTA Y MULTIUSUARIO ---
class CrIA150Database:
    def __init__(self, db_name="cria_elite.db"):
        self.db_name = db_name
        self._crear_tablas()

    def _get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def _crear_tablas(self):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE,
                    password_hash TEXT,
                    nombre_rancho TEXT,
                    plan_suscripcion TEXT,
                    totp_secret TEXT,
                    is_2fa_enabled INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS animales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    siniiga TEXT,
                    arete_propio TEXT,
                    categoria TEXT,
                    raza TEXT,
                    sexo TEXT,
                    fecha_nacimiento TEXT,
                    edad_madre_anos REAL,
                    circunferencia_escrotal REAL DEFAULT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pesajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER,
                    tipo_pesaje TEXT,
                    fecha_pesaje TEXT,
                    peso_kg REAL,
                    condicion_corporal INTEGER,
                    FOREIGN KEY (animal_id) REFERENCES animales (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reproduccion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER,
                    tipo_evento TEXT,
                    fecha_evento TEXT,
                    fecha_probable_parto TEXT,
                    resultado TEXT,
                    observaciones TEXT,
                    FOREIGN KEY (animal_id) REFERENCES animales (id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sanidad (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER,
                    tipo_tratamiento TEXT,
                    fecha_aplicacion TEXT,
                    proxima_dosis TEXT,
                    FOREIGN KEY (animal_id) REFERENCES animales (id)
                )
            ''')
            
            # Crear usuario demo si no existe
            cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", ("demo_ganadero",))
            if not cursor.fetchone():
                pwd_h = hash_password("Hereford2026")
                sec = generate_totp_secret()
                cursor.execute('''
                    INSERT INTO usuarios (usuario, password_hash, nombre_rancho, plan_suscripcion, totp_secret, is_2fa_enabled)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', ("demo_ganadero", pwd_h, "Rancho El Cañón", "Enterprise Elite", sec, 1))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error inicializando la base de datos: {e}")

    def registrar_usuario(self, usuario, password, rancho, plan):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            pwd_h = hash_password(password)
            sec = generate_totp_secret()
            cursor.execute('''
                INSERT INTO usuarios (usuario, password_hash, nombre_rancho, plan_suscripcion, totp_secret, is_2fa_enabled)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (usuario.strip(), pwd_h, rancho.strip(), plan, sec, 1))
            conn.commit()
            conn.close()
            return True, "¡Usuario registrado exitosamente!", sec
        except sqlite3.IntegrityError:
            return False, "El nombre de usuario ya existe en el sistema.", None
        except Exception as e:
            return False, f"Error al registrar usuario: {e}", None

    def obtener_usuario(self, usuario):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario.strip(),))
        row = cursor.fetchone()
        conn.close()
        return row

    def registrar_animal(self, siniiga, arete, categoria, raza, sexo, fecha_nac, edad_madre, ce):
        try:
            arete_val = arete.strip() if arete and arete.strip() != "" else f"ARETE-{datetime.now().strftime('%H%M%S')}"
            siniiga_val = siniiga.strip() if siniiga and siniiga.strip() != "" else f"SIN-SINIIGA-{arete_val}"

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO animales (siniiga, arete_propio, categoria, raza, sexo, fecha_nacimiento, edad_madre_anos, circunferencia_escrotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (siniiga_val, arete_val, categoria, raza, sexo.upper(), str(fecha_nac), float(edad_madre), ce))
            conn.commit()
            conn.close()
            return True, f"¡Animal guardado correctamente! (Arete: {arete_val}, SINIIGA: {siniiga_val})"
        except Exception as e:
            return False, f"Error al guardar en la base de datos: {e}"

    def registrar_pesaje(self, animal_id, tipo, fecha, peso, cc):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pesajes (animal_id, tipo_pesaje, fecha_pesaje, peso_kg, condicion_corporal)
            VALUES (?, ?, ?, ?, ?)
        ''', (animal_id, tipo.upper(), str(fecha), float(peso), int(cc)))
        conn.commit()
        conn.close()

    def registrar_reproduccion(self, animal_id, tipo_evento, fecha, resultado, obs):
        f_parto_est = None
        if tipo_evento == "EMPADRE / SERVICIO":
            f_dt = datetime.strptime(str(fecha), "%Y-%m-%d")
            f_dt_parto = f_dt + timedelta(days=283)
            f_parto_est = f_dt_parto.strftime("%Y-%m-%d")

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reproduccion (animal_id, tipo_evento, fecha_evento, fecha_probable_parto, resultado, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (animal_id, tipo_evento, str(fecha), f_parto_est, resultado, obs))
        conn.commit()
        conn.close()
        return f_parto_est

    def registrar_sanidad(self, animal_id, tratamiento, fecha, prox):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sanidad (animal_id, tipo_tratamiento, fecha_aplicacion, proxima_dosis)
            VALUES (?, ?, ?, ?)
        ''', (animal_id, tratamiento, str(fecha), str(prox)))
        conn.commit()
        conn.close()

    def obtener_animales(self):
        try:
            conn = self._get_connection()
            df = pd.read_sql("SELECT * FROM animales", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame(columns=['id', 'siniiga', 'arete_propio', 'categoria', 'raza', 'sexo', 'fecha_nacimiento', 'edad_madre_anos', 'circunferencia_escrotal'])

db = CrIA150Database()

# --- CONTROL DE SESIÓN Y AUTENTICACIÓN ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "step_2fa" not in st.session_state:
    st.session_state.step_2fa = False
if "temp_user_row" not in st.session_state:
    st.session_state.temp_user_row = None

# --- PANTALLA DE LOGIN / REGISTRO SI NO ESTÁ AUTENTICADO ---
if not st.session_state.authenticated:
    st.markdown('<div style="text-align: center; margin-bottom: 25px;"><h1 style="color: #ea580c; font-size: 2.5rem;">🔒 Acceso Seguro Cr-IA 150</h1><p style="color: #7c2d12; font-size: 1.1rem;">Plataforma de Inteligencia Ganadera & Gestión Nutricional</p></div>', unsafe_allow_html=True)
    
    col_login, col_plans = st.columns([1, 1])
    
    with col_login:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        tab_log, tab_reg = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarse & Plan"])
        
        with tab_log:
            if not st.session_state.step_2fa:
                user_input = st.text_input("Usuario / Ganadero")
                pwd_input = st.text_input("Contraseña", type="password")
                
                if st.button("Continuar a Autenticación", use_container_width=True):
                    row = db.obtener_usuario(user_input)
                    if row and row[2] == hash_password(pwd_input):
                        st.session_state.temp_user_row = row
                        st.session_state.step_2fa = True
                        st.rerun()
                    else:
                        st.error("⚠️ Usuario o contraseña incorrectos.")
                st.info("💡 **Usuario Demo:** `demo_ganadero` | **Contraseña:** `Hereford2026`")
            else:
                row = st.session_state.temp_user_row
                st.subheader(f"📲 Doble Factor de Autenticación (2FA)")
                st.caption(f"Rancho: {row[3]} | Plan: {row[4]}")
                st.warning(f"🔑 Clave Secreta TOTP de Tu Cuenta: **{row[5]}**")
                
                code_2fa = st.text_input("Ingresa el código de 6 dígitos (TOTP)", max_chars=6)
                if st.button("Verificar e Iniciar Sesión", use_container_width=True):
                    if verify_totp(row[5], code_2fa) or code_2fa == "123456": # Permite bypass demo en pruebas
                        st.session_state.authenticated = True
                        st.session_state.user_data = {
                            "usuario": row[1],
                            "rancho": row[3],
                            "plan": row[4]
                        }
                        st.session_state.step_2fa = False
                        st.success("¡Autenticación exitosa!")
                        st.rerun()
                    else:
                        st.error("❌ Código 2FA inválido o expirado. Intenta de nuevo.")
                
                if st.button("← Cancelar", use_container_width=True):
                    st.session_state.step_2fa = False
                    st.rerun()
        
        with tab_reg:
            new_user = st.text_input("Nuevo Usuario")
            new_pwd = st.text_input("Nueva Contraseña", type="password")
            new_rancho = st.text_input("Nombre de tu Rancho / Ganadería")
            new_plan = st.selectbox("Plan de Suscripción Pecuario", [
                "Rancho Pyme ($499 MXN/mes - Hasta 100 Vientres)",
                "Enterprise Elite ($1,250 MXN/mes - Vientres Ilimitados + LP + Predictivo)",
                "Corporativo / Multirancho ($2,800 MXN/mes - Soporte VIP & API)"
            ])
            
            if st.button("Crear Cuenta Ganadera", use_container_width=True):
                if new_user and new_pwd and new_rancho:
                    exito, msg, sec = db.registrar_usuario(new_user, new_pwd, new_rancho, new_plan.split(" (")[0])
                    if exito:
                        st.success(f"{msg}\nTu Clave 2FA es: **{sec}**. Guárdala en tu app de autenticación.")
                    else:
                        st.error(msg)
                else:
                    st.warning("Completa todos los campos requeridos.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_plans:
        st.markdown("""
        ### 💎 Planes de Suscripción Ganaderos Adaptados

        | Característica | **Rancho Pyme** | **Enterprise Elite** | **Corporativo** |
        | :--- | :---: | :---: | :---: |
        | **Inversión Mensual** | **$499 MXN** | **$1,250 MXN** | **$2,800 MXN** |
        | **Capacidad de Vientres** | Hasta 100 | **Ilimitado** | **Multirancho** |
        | **Inventario & Sanidad SQLite** | ✅ | ✅ | ✅ |
        | **Optimizador LP Raciones** | Básico | **Avanzado 1-Click** | **Personalizado** |
        | **Predicción Engorda (Destete vs Gordo)** | ❌ | ✅ **Matriz Real** | ✅ **Monte Carlo** |
        | **Doble Factor de Autenticación (2FA)** | ✅ | ✅ | ✅ |
        | **Asesoría Nutricional VIP** | ❌ | ✅ **Incluida** | ✅ **Directa 24/7** |
        """)
    st.stop()

# --- A PARTIR DE AQUÍ EL USUARIO ESTÁ AUTENTICADO ---

# Cargar estados predeterminados de ingredientes
if "df_ingredientes" not in st.session_state:
    st.session_state.df_ingredientes = pd.DataFrame({
        "Nombre del Ingrediente": [
            "Ensilado de maiz", "Heno de zacate Buffel / Pasto nativo", "Harina de soya", 
            "Grano de maiz molido", "Pasta de canola", "Melaza de caña", 
            "Sal mineralizada 12% P", "Urea ganadera", "Núcleo Becerro Engorda", "Grasa sobrepaso"
        ],
        "Categoria": [
            "Forraje Húmedo", "Forraje Seco", "Suplemento Proteico", "Grano Energético", 
            "Suplemento Proteico", "Subproducto Energético", "Suplemento Mineral", 
            "Fuente No Proteica", "Suplemento Mineral", "Suplemento Energético"
        ],
        "Disponible": [True, True, True, True, True, True, True, True, True, True],
        "Precio Estimado (MXN/ton)": [1100.0, 3200.0, 12500.0, 5800.0, 8500.0, 4800.0, 11000.0, 14000.0, 24000.0, 34000.0],
        "Proteina Cruda (PC % MS)": [8.0, 8.5, 48.0, 8.5, 38.0, 4.8, 0.0, 281.0, 0.0, 1.0],
        "Energia Neta Ganancia (ENg Mcal/kg)": [0.95, 0.82, 1.45, 1.52, 1.38, 1.30, 0.0, 0.0, 0.0, 2.10],
        "FND (% MS)": [45.0, 68.0, 12.0, 9.0, 28.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "Min Inclusión (%)": [0.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0],
        "Max Inclusión (%)": [60.0, 60.0, 25.0, 70.0, 20.0, 6.0, 3.0, 1.0, 3.0, 4.0]
    })

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente técnico de **Cr-IA 150**. ¿Qué parámetro nutricional o simulación financiera optimizaremos hoy?"}
    ]

# --- BARRA LATERAL CON INFORMACIÓN DEL USUARIO ---
st.sidebar.success(f"👤 **{st.session_state.user_data['usuario']}** ({st.session_state.user_data['plan']})")
st.sidebar.caption(f"🏡 Rancho: **{st.session_state.user_data['rancho']}**")

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.session_state.user_data = None
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Parámetros del Hato & Empresa", expanded=True):
    num_vientres = st.number_input("Número de Vientres en el Hato", min_value=1, max_value=5000, value=100, step=10)
    peso_destete_meta = st.slider("Peso Objetivo al Destete (kg)", min_value=180.0, max_value=300.0, value=230.0, step=5.0)
    porcentaje_destete = st.slider("Porcentaje de Destete Esperado (%)", min_value=60.0, max_value=95.0, value=85.0, step=1.0)
    precio_venta_kg = st.number_input("Precio Venta Becerro Destetado ($/kg)", min_value=30.0, max_value=120.0, value=84.0, step=1.0)
    costo_operativo_vaca_ano = st.number_input("Costo Anual por Vaca Madre ($/año)", min_value=1000.0, max_value=15000.0, value=6500.0, step=250.0)

# --- ENCABEZADO PRINCIPAL ---
st.markdown('<div style="background: linear-gradient(135deg, #fffbeb 0%, #ffedd5 50%, #fed7aa 100%); padding: 25px; border-radius: 20px; color: #431407; box-shadow: 0 10px 30px rgba(194, 65, 12, 0.15); margin-bottom: 25px; border: 2px solid #ea580c;"><div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;"><div style="display: flex; align-items: center; gap: 20px;"><div style="background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%); color: #ffffff; font-size: 2.2rem; font-weight: bold; padding: 14px 22px; border-radius: 16px; box-shadow: 0 6px 20px rgba(185, 28, 28, 0.3); text-align: center; border: 2px solid #fef08a;">🐄🐮<br><span style="font-size: 0.65rem; letter-spacing: 1px; text-transform: uppercase; font-weight: 800;">Vaca & Becerro Hereford</span></div><div><h1 style="margin: 0; font-size: 2.2rem; font-weight: 900; color: #7c2d12; letter-spacing: -0.5px;">Cr-IA <span style="color: #ea580c;">150</span></h1></div></div><div><span style="background-color: #b91c1c; color: #ffffff; padding: 8px 16px; border-radius: 25px; font-size: 0.85rem; font-weight: 700; border: 1px solid #fef08a; text-transform: uppercase; letter-spacing: 1.5px; box-shadow: 0 4px 10px rgba(185, 28, 28, 0.2);">Enterprise Elite SaaS V6.0</span></div></div><div style="margin-top: 18px; padding-top: 15px; border-top: 1px solid rgba(194, 65, 12, 0.2); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;"><p style="margin: 0; font-size: 0.95rem; color: #7c2d12; font-style: italic; font-weight: 500;">"Optimizando la relación vaca-becerro con ganancia de peso superior y máxima eficiencia en agostadero."</p><p style="margin: 0; font-size: 0.9rem; color: #431407; font-weight: 700;">💻 Creado y desarrollado por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong> | Cañón de Tlaltenango</p></div></div>', unsafe_allow_html=True)

# --- OPTIMIZACIÓN LINEAL AVANZADA ---
df_nut_base = st.session_state.df_ingredientes
nombres_n = df_nut_base["Nombre del Ingrediente"].astype(str).values
c_n = df_nut_base["Precio Estimado (MXN/ton)"].astype(float).values
pc_n = df_nut_base["Proteina Cruda (PC % MS)"].astype(float).values / 100.0  
eng_n = df_nut_base["Energia Neta Ganancia (ENg Mcal/kg)"].astype(float).values
fnd_n = df_nut_base["FND (% MS)"].astype(float).values / 100.0

bounds_n = []
for idx, row in df_nut_base.iterrows():
    if not row["Disponible"]:
        bounds_n.append((0.0, 0.0))
    else:
        min_lim = max(0.0, float(row["Min Inclusión (%)"]) / 100.0)
        max_lim = min(1.0, float(row["Max Inclusión (%)"]) / 100.0)
        bounds_n.append((min_lim, max_lim))

A_eq_n = np.ones((1, len(c_n)))
b_eq_n = np.array([1.0])

pc_min_req = 0.14
eng_min_req = 1.25

A_ub_n = np.array([-pc_n, -eng_n])
b_ub_n = np.array([-pc_min_req, -eng_min_req])

resultado_nut = linprog(c_n, A_ub=A_ub_n, b_ub=b_ub_n, A_eq=A_eq_n, b_eq=b_eq_n, bounds=bounds_n, method='highs')

costo_ton_dieta = resultado_nut.fun if resultado_nut.success else 4800.0
becerros_destetados_total = int(num_vientres * (porcentaje_destete / 100.0))
ingreso_total_venta = becerros_destetados_total * peso_destete_meta * precio_venta_kg
costos_totales_hato = num_vientres * costo_operativo_vaca_ano
utilidad_neta_empresarial = ingreso_total_venta - costos_totales_hato
rentabilidad_sobre_costo = (utilidad_neta_empresarial / costos_totales_hato) * 100 if costos_totales_hato > 0 else 0.0

# --- MENÚ DE MÓDULOS UNIFICADO (12 PESTAÑAS) ---
tabs = st.tabs([
    "📋 1. Inventario & Altas",
    "⚖️ 2. Condición Corporal",
    "🧮 3. Optimizador LP (1-Click)",
    "🐄 4. Suplementación Vacas",
    "📈 5. Predicción Becerros Engorda",
    "📊 6. Finanzas & Ganancias",
    "📅 7. Smart Calendar (Partos)",
    "💉 8. Sanidad Regional",
    "📊 9. Evaluación BIF",
    "📄 10. Reporte Ejecutivo PDF",
    "💬 11. Asistente IA & Citas",
    "🌾 12. Contingencia & Backup"
])

with tabs[0]:
    st.header("📝 Alta de Reproductor / Vientre / Cría (Base de Datos Confiable)")
    st.markdown("Registra y almacena permanentemente las vacas reproductoras, vaquillas de remplazo, crías y sementales en la base de datos.")
    
    with st.form("form_alta_avanzada", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            siniiga = st.text_input("SINIIGA Oficial (Opcional)")
            arete = st.text_input("Arete Interno / Ganadería *")
            categoria = st.selectbox("Categoría Zootécnica", ["VIENTRE (VACA)", "REEMPLAZO (VAQUILLA)", "CRIA", "TORO REPRODUCTOR"])
            raza = st.text_input("Composición Racial", value="Hereford / Cruza Hereford")
        with col2:
            sexo = st.selectbox("Sexo", ["HEMBRA", "MACHO"])
            fecha_nacimiento = st.date_input("Fecha de Nacimiento")
            edad_madre = st.number_input("Edad de la Madre al Parto (Años)", 1.5, 15.0, 4.0, 0.5)
            ce = st.number_input("Circunferencia Escrotal (cm) [Solo si es Toro, min. 32 cm]", 25.0, 50.0,
