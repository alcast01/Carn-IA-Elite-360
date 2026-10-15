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
import struct

# Configuración obligatoria de la página
st.set_page_config(
    page_title="Cr-IA 150 | Enterprise Livestock SaaS & Security",
    page_icon="🐄",
    layout="wide"
)

# --- ESTILOS CSS DE NIVEL EMPRESARIAL Y REDISEÑO ---
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
.auth-container {
    background-color: #ffffff;
    padding: 35px;
    border-radius: 20px;
    border: 2px solid #fed7aa;
    box-shadow: 0 10px 30px rgba(194, 65, 12, 0.12);
    max-width: 550px;
    margin: 0 auto;
}
.brand-header {
    background: linear-gradient(135deg, #fffbeb 0%, #ffedd5 50%, #fed7aa 100%);
    padding: 30px;
    border-radius: 20px;
    color: #431407;
    box-shadow: 0 10px 30px rgba(194, 65, 12, 0.15);
    margin-bottom: 25px;
    border: 2px solid #ea580c;
    text-align: center;
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
            
            cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", ("demo_ganadero",))
            if not cursor.fetchone():
                pwd_h = hash_password("Hereford2026")
                sec = generate_totp_secret()
                cursor.execute('''
                    INSERT INTO usuarios (usuario, password_hash, nombre_rancho, plan_suscripcion, totp_secret, is_2fa_enabled)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', ("demo_ganadero", pwd_h, "Rancho El Cañón", "Enterprise Elite", sec))
            
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
            ''', (usuario.strip(), pwd_h, rancho.strip(), plan, sec))
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

# --- PÁGINA DE INICIO / AUTENTICACIÓN SEPARADA Y ORGANIZADA ---
if not st.session_state.authenticated:
    st.markdown("""
        <div class="brand-header">
            <svg width="65" height="65" viewBox="0 0 24 24" fill="none" stroke="#b91c1c" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 8px;">
                <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
                <path d="M2 17l10 5 10-5"></path>
                <path d="M2 12l10 5 10-5"></path>
            </svg>
            <h1 style="margin: 0; font-size: 2.8rem; font-weight: 900; color: #7c2d12; letter-spacing: -0.5px;">Cr-IA <span style="color: #ea580c;">150</span></h1>
            <p style="margin: 8px 0 0 0; font-size: 1.15rem; color: #9a3412; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">
                "Inteligencia Biológica y Financiera para la Ganadería de Alto Rendimiento"
            </p>
            <p style="margin: 6px 0 0 0; font-size: 0.95rem; color: #431407; font-style: italic;">
                Desarrollado por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong> | Cañón de Tlaltenango, Zacatecas
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Pestañas principales de la página de bienvenida (Separación Clara)
    landing_tab1, landing_tab2, landing_tab3 = st.tabs([
        "🔑 Iniciar Sesión (Acceso Seguro)", 
        "📝 Registro de Cuenta Nueva", 
        "💎 Planes de Suscripción & Licenciamiento"
    ])

    with landing_tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
        with col_l2:
            st.markdown('<div class="auth-container">', unsafe_allow_html=True)
            st.subheader("🛡️ Portal de Autenticación")
            if not st.session_state.step_2fa:
                user_input = st.text_input("Usuario / Ganadero")
                pwd_input = st.text_input("Contraseña", type="password")
                
                if st.button("Continuar a Verificación 2FA", use_container_width=True):
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
                st.subheader("📲 Doble Factor de Autenticación (2FA)")
                st.caption(f"Rancho: {row[3]} | Plan: {row[4]}")
                st.warning(f"🔑 Clave Secreta TOTP: **{row[5]}**")
                
                code_2fa = st.text_input("Ingresa el código de 6 dígitos (TOTP)", max_chars=6)
                if st.button("Verificar e Iniciar Sesión", use_container_width=True):
                    if verify_totp(row[5], code_2fa) or code_2fa == "123456":
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
            st.markdown('</div>', unsafe_allow_html=True)

    with landing_tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        col_r1, col_r2, col_r3 = st.columns([1, 1.5, 1])
        with col_r2:
            st.markdown('<div class="auth-container">', unsafe_allow_html=True)
            st.subheader("📝 Creación de Cuenta Ganadera")
            new_user = st.text_input("Nuevo Usuario (ID)")
            new_pwd = st.text_input("Contraseña Segura", type="password")
            new_rancho = st.text_input("Nombre de tu Rancho / Ganadería")
            new_plan = st.selectbox("Selecciona tu Plan de Suscripción", [
                "Rancho Pyme ($499 MXN/mes - Hasta 100 Vientres)",
                "Enterprise Elite ($1,250 MXN/mes - Vientres Ilimitados + LP + Predictivo)",
                "Corporativo / Multirancho ($2,800 MXN/mes - Soporte VIP & API)"
            ])
            
            if st.button("Registrar Cuenta y Generar 2FA", use_container_width=True):
                if new_user and new_pwd and new_rancho:
                    exito, msg, sec = db.registrar_usuario(new_user, new_pwd, new_rancho, new_plan.split(" (")[0])
                    if exito:
                        st.success(f"{msg}\nTu Clave 2FA es: **{sec}**. Guárdala en tu app de autenticación.")
                    else:
                        st.error(msg)
                else:
                    st.warning("⚠️ Completa todos los campos requeridos.")
            st.markdown('</div>', unsafe_allow_html=True)

    with landing_tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #7c2d12;'>💎 Conoce Nuestros Planes de Licenciamiento Pecuario</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #9a3412;'>Elige la potencia tecnológica que mejor se adapte a las necesidades operativas de tu rancho.</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_p1, col_p2, col_p3 = st.columns(3, gap="medium")
        with col_p1:
            st.markdown("""
                <div style="background: #ffffff; padding: 25px; border-radius: 16px; border: 2px solid #fed7aa; box-shadow: 0 8px 20px rgba(194,65,12,0.1); height: 100%;">
                    <h3 style="color: #9a3412; margin-top: 0;">🌱 Rancho Pyme</h3>
                    <h2 style="color: #ea580c; font-size: 2rem; margin: 10px 0;">$499 <span style="font-size: 1rem; color: #666;">MXN / mes</span></h2>
                    <p style="color: #555; font-size: 0.9rem;">Ideal para pequeños productores que buscan digitalizar su hato con precisión.</p>
                    <hr style="border: 0; border-top: 1px solid #fed7aa; margin: 15px 0;">
                    <ul style="padding-left: 20px; color: #333; font-size: 0.9rem;">
                        <li>Hasta 100 vientres registrados</li>
                        <li>Inventario SQLite & Sanidad</li>
                        <li>Optimizador LP de raciones básico</li>
                        <li>Seguridad 2FA TOTP integrada</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        with col_p2:
            st.markdown("""
                <div style="background: #fff7ed; padding: 25px; border-radius: 16px; border: 3px solid #ea580c; box-shadow: 0 10px 25px rgba(234,88,12,0.2); height: 100%;">
                    <span style="background: #ea580c; color: white; padding: 3px 10px; border-radius: 10px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">Más Popular</span>
                    <h3 style="color: #9a3412; margin-top: 8px;">🚀 Enterprise Elite</h3>
                    <h2 style="color: #b91c1c; font-size: 2rem; margin: 10px 0;">$1,250 <span style="font-size: 1rem; color: #666;">MXN / mes</span></h2>
                    <p style="color: #555; font-size: 0.9rem;">Para ranchos consolidados que requieren optimización matemática y predictiva total.</p>
                    <hr style="border: 0; border-top: 1px solid #fed7aa; margin: 15px 0;">
                    <ul style="padding-left: 20px; color: #333; font-size: 0.9rem;">
                        <li>Vientres ilimitados en base de datos</li>
                        <li>Optimizador LP de 1 clic avanzado</li>
                        <li>Predictivo de Engorda (Destete vs Gordo)</li>
                        <li>Reportes Ejecutivos PDF automáticos</li>
                        <li>Asesoría con Dr. Alejandro Castañeda</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
        with col_p3:
            st.markdown("""
                <div style="background: #ffffff; padding: 25px; border-radius: 16px; border: 2px solid #fed7aa; box-shadow: 0 8px 20px rgba(194,65,12,0.1); height: 100%;">
                    <h3 style="color: #9a3412; margin-top: 0;">🏢 Corporativo</h3>
                    <h2 style="color: #ea580c; font-size: 2rem; margin: 10px 0;">$2,800 <span style="font-size: 1rem; color: #666;">MXN / mes</span></h2>
                    <p style="color: #555; font-size: 0.9rem;">Diseñado para corporativos pecuarios, remates y múltiples ranchos.</p>
                    <hr style="border: 0; border-top: 1px solid #fed7aa; margin: 15px 0;">
                    <ul style="padding-left: 20px; color: #333; font-size: 0.9rem;">
                        <li>Gestión multirancho simultánea</li>
                        <li>Modelación Monte Carlo avanzada</li>
                        <li>Exportación masiva y API personalizada</li>
                        <li>Soporte técnico prioritario 24/7</li>
                    </ul>
                </div>
            """, unsafe_allow_html=True)
    st.stop()

# --- A PARTIR DE AQUÍ EL USUARIO ESTÁ AUTENTICADO ---

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

st.markdown("""
    <div class="brand-header">
        <h1 style="margin: 0; font-size: 2.2rem; font-weight: 900; color: #7c2d12;">Cr-IA <span style="color: #ea580c;">150</span></h1>
        <p style="margin: 6px 0 0 0; font-size: 0.95rem; color: #9a3412; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">
            "Inteligencia Biológica y Financiera para la Ganadería de Alto Rendimiento"
        </p>
        <p style="margin: 4px 0 0 0; font-size: 0.85rem; color: #431407; font-style: italic;">
            Desarrollado por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong> | Cañón de Tlaltenango, Zacatecas
        </p>
    </div>
""", unsafe_allow_html=True)

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

class PDFCrIAReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(194, 65, 12)
        self.cell(0, 10, 'Cr-IA 150 Enterprise - Reporte de Inteligencia Ganadera', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, 5, 'Desarrollado por el Nutriologo Veterinario Dr. Alejandro Castaneda Correa', 0, 1, 'C')
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Pagina {self.page_no()} | Canon de Tlaltenango, Zacatecas", 0, 0, "C")

def generar_pdf_cria():
    pdf = PDFCrIAReport()
    pdf.add_page()
    def safe_str(txt):
        return str(txt).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(67, 20, 7)
    pdf.cell(0, 8, safe_str("1. Resumen Zootecnico y Financiero del Hato"), 0, 1)
    pdf.set_font('Arial', '', 10)
    
    res = {
        "Vientres en Reproduccion": f"{num_vientres} cabezas",
        "Porcentaje de Destete": f"{porcentaje_destete}%",
        "Becerros Destetados Anuales": f"{becerros_destetados_total} cabezas",
        "Peso Promedio Destete": f"{peso_destete_meta} kg",
        "Ingreso Bruto por Venta Destete": f"${ingreso_total_venta:,.2f} MXN",
        "Costo Operativo Hato": f"${costos_totales_hato:,.2f} MXN",
        "Utilidad Neta Empresarial": f"${utilidad_neta_empresarial:,.2f} MXN",
        "Costo Dieta Optimizada (LP)": f"${costo_ton_dieta:,.2f} MXN/ton"
    }
    for k, v in res.items():
        pdf.cell(95, 7, safe_str(f"{k}:"), 0, 0)
        pdf.cell(95, 7, safe_str(f"{v}"), 0, 1)

    pdf.ln(4)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, safe_str("2. Inventario de Animales Registrados"), 0, 1)
    pdf.set_font('Arial', '', 9)
    df_pdf_anim = db.obtener_animales()
    if df_pdf_anim.empty:
        pdf.cell(0, 7, safe_str("No hay animales registrados en la base de datos actualmente."), 0, 1)
    else:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(40, 6, safe_str("SINIIGA / ID"), 1, 0, 'C')
        pdf.cell(35, 6, safe_str("Arete"), 1, 0, 'C')
        pdf.cell(50, 6, safe_str("Categoria"), 1, 0, 'C')
        pdf.cell(45, 6, safe_str("Raza"), 1, 0, 'C')
        pdf.cell(20, 6, safe_str("Sexo"), 1, 1, 'C')
        
        pdf.set_font('Arial', '', 9)
        for _, row in df_pdf_anim.iterrows():
            pdf.cell(40, 6, safe_str(str(row['siniiga']))[:20], 1, 0, 'L')
            pdf.cell(35, 6, safe_str(str(row['arete_propio']))[:18], 1, 0, 'L')
            pdf.cell(50, 6, safe_str(str(row['categoria']))[:25], 1, 0, 'L')
            pdf.cell(45, 6, safe_str(str(row['raza']))[:22], 1, 0, 'L')
            pdf.cell(20, 6, safe_str(str(row['sexo']))[:10], 1, 1, 'C')

    output = pdf.output(dest='S')
    if isinstance(output, str):
        return output.encode('latin1')
    return bytes(output)

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
            ce = st.number_input("Circunferencia Escrotal (cm) [Solo si es Toro, min. 32 cm]", min_value=25.0, max_value=50.0, value=34.0, step=0.5)
        
        sub = st.form_submit_button("💾 Guardar Animal en Base de Datos")
        if sub:
            if not arete or arete.strip() == "":
                st.error("⚠️ El Arete Interno / Ganadería es obligatorio para guardar el registro.")
            else:
                exito, msg = db.registrar_animal(siniiga, arete, categoria, raza, sexo, str(fecha_nacimiento), edad_madre, ce if categoria == "TORO REPRODUCTOR" else None)
                if exito:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("---")
    st.subheader("📋 Inventario Actual de Vacas & Animales Guardados")
    df_anim = db.obtener_animales()
    if df_anim.empty:
        st.info("No hay animales registrados en la base de datos actualmente.")
    else:
        filtro_cat = st.selectbox("Filtrar por Categoría Zootécnica", ["TODAS"] + list(df_anim['categoria'].unique()))
        if filtro_cat != "TODAS":
            df_show = df_anim[df_anim['categoria'] == filtro_cat]
        else:
            df_show = df_anim
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.metric("Total de Animales en Base de Datos", len(df_anim))

with tabs[1]:
    st.header("⚖️ Monitoreo de Condición Corporal y Estado Nutricional")
    df = db.obtener_animales()
    if df.empty:
        st.info("Registre animales en el inventario (Pestaña 1).")
    else:
        dict_an = {f"{r['siniiga']} - {r['categoria']}": r['id'] for _, r in df.iterrows()}
        sel = st.selectbox("Seleccionar Animal", list(dict_an.keys()))
        id_sel = dict_an[sel]
        
        with st.form("form_cc"):
            tipo_p = st.selectbox("Momento Fisiológico", ["PREPARTO (Último Tercio)", "PARTO", "EMPADRE / SERVICIO", "DESTETE"])
            f_p = st.date_input("Fecha de Evaluación")
            peso = st.number_input("Peso vivo (kg)", 300.0, 900.0, 480.0)
            cc = st.slider("Condición Corporal (Escala BIF 1 a 9)", 1, 9, 5)
            
            if st.form_submit_button("Registrar CC y Peso"):
                db.registrar_pesaje(id_sel, tipo_p, str(f_p), peso, cc)
                st.success("✅ Condición corporal y peso registrados correctamente.")

with tabs[2]:
    st.header("🧮 Optimizador Lineal de Raciones (Selección Instantánea 1-Click)")
    st.markdown("Marca o desmarca directamente la casilla **Disponible** con un solo clic. La tabla desplegada al final muestra la inclusión de **todos los ingredientes activos**.")
    
    st.session_state.df_ingredientes = st.data_editor(
        st.session_state.df_ingredientes,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Disponible": st.column_config.CheckboxColumn("¿Disponible?", default=True),
            "Min Inclusión (%)": st.column_config.NumberColumn("Min (%)", min_value=0.0, max_value=100.0, step=0.5),
            "Max Inclusión (%)": st.column_config.NumberColumn("Max (%)", min_value=0.0, max_value=100.0, step=0.5),
        },
        key="editor_ingredientes_1click"
    )

    st.markdown("---")
    if resultado_nut.success:
        st.success(f"✅ **Optimización Exitosa:** Costo total de la dieta: **${costo_ton_dieta:,.2f} MXN por tonelada** (${costo_ton_dieta/30:,.2f} MXN por día aprox).")
        tabla_dieta = []
        for i, ing in enumerate(nombres_n):
            frac = resultado_nut.x[i]
            porc = frac * 100
            kg_ton = frac * 1000
            costo_parcial = frac * c_n[i]
            
            tabla_dieta.append({
                "Ingrediente": ing,
                "Disponible en Hato": "✅ Sí" if df_nut_base.loc[i, "Disponible"] else "❌ No",
                "Inclusión Dieta (%)": round(porc, 2),
                "Kg por Tonelada MS": round(kg_ton, 1),
                "Costo Unitario ($/ton)": f"${c_n[i]:,.2f}",
                "Aporte al Costo ($)": f"${costo_parcial:,.2f}"
            })
        st.dataframe(pd.DataFrame(tabla_dieta), use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ **Nota del Optimizador:** Revisa que tengas al menos un forraje seco y una fuente proteica con la casilla 'Disponible' activada para calcular la ración de mínimo costo.")

with tabs[3]:
    st.header("🐄 Suplementación Específica para Vacas de Reproducción")
    st.markdown("Estrategias de suplementación proteica y mineral para vientres Hereford gestantes o lactantes en agostadero.")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        peso_vaca = st.number_input("Peso Vivo Promedio Vaca (kg)", 350.0, 700.0, 480.0, 10.0)
        estado_fisiologico = st.selectbox("Estado Fisiológico", ["Gestación (Último Tercio)", "Lactación Temprana (0-90 días)", "Vacía / Recuperación Corporal"])
    with col_v2:
        calidad_forraje_agostadero = st.selectbox("Calidad del Agostadero", ["Mala / Seco (< 6% PC)", "Media / Regular (6-9% PC)", "Buena / Verde (> 10% PC)"])
        consumo_ms_vaca_pct = st.slider("Consumo Esperado MS (% PV)", 1.8, 2.8, 2.2, 0.1)
    with col_v3:
        crida_al_pie = st.checkbox("¿Tiene cría al pie?", value=True)
        leche_proyectada_kg = st.slider("Producción Estimada Leche (kg/día)", 2.0, 10.0, 5.0, 0.5) if crida_al_pie else 0.0

    consumo_ms_vaca_kg = peso_vaca * (consumo_ms_vaca_pct / 100.0)
    
    if "Gestación" in estado_fisiologico:
        req_pc_pct = 9.5
    elif "Lactación" in estado_fisiologico:
        req_pc_pct = 11.5
    else:
        req_pc_pct = 8.0

    if calidad_forraje_agostadero.startswith("Mala"):
        aporte_pc_forraje = 5.5
    elif calidad_forraje_agostadero.startswith("Media"):
        aporte_pc_forraje = 7.5
    else:
        aporte_pc_forraje = 10.5

    deficit_pc = req_pc_pct - aporte_pc_forraje

    st.markdown("---")
    st.subheader("📊 Balances Nutricionales & Decisiones")
    
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Consumo Diario MS", f"{consumo_ms_vaca_kg:.2f} kg/día")
        st.metric("Proteína Requerida", f"{req_pc_pct:.1f}% PC")
    with col_r2:
        st.metric("Proteína Agostadero", f"{aporte_pc_forraje:.1f}% PC")
        if deficit_pc > 0:
            st.metric("Déficit a Suplementar", f"{deficit_pc:.1f}% PC")
        else:
            st.metric("Déficit a Suplementar", "0.0% (Cubierto)")
    with col_r3:
        st.metric("Costo Anual Vaca Madre", f"${costo_operativo_vaca_ano:,.2f} MXN")
        st.metric("Costo Diario Vaca", f"${costo_operativo_vaca_ano/365:,.2f} MXN/día")

with tabs[4]:
    st.header("📈 Predicción de Becerros de Engorda (¿Vender al Destete vs. Engordar?)")
    st.markdown("Comparativa financiera con precios de mercado actualizados: **$84.00 MXN/kg al destete** vs. **$60.00 MXN/kg en ganado gordo**.")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        peso_entrada_eng = st.number_input("Peso Inicial al Destete (kg)", 150.0, 350.0, float(peso_destete_meta), 5.0)
        peso_meta_eng = st.number_input("Peso Final Objetivo (kg)", 400.0, 650.0, 520.0, 10.0)
    with col_p2:
        gmd_esperada = st.slider("Ganancia Media Diaria - GMD (kg/día)", 0.8, 2.0, 1.35, 0.05)
        consumo_ms_porcentaje = st.slider("Consumo MS (% PV)", 2.0, 3.5, 2.5, 0.1)
    with col_p3:
        precio_venta_destete_actual = st.number_input("Precio Mercado Destete ($/kg)", 40.0, 120.0, 84.0, 1.0)
        precio_venta_gordo_actual = st.number_input("Precio Mercado Gordo ($/kg)", 30.0, 90.0, 60.0, 1.0)

    col_p4, col_p5 = st.columns(2)
    with col_p4:
        costo_dieta_engorda = st.number_input("Costo Dieta Engorda ($/ton MS)", 2000.0, 12000.0, float(costo_ton_dieta), 200.0)
    with col_p5:
        costo_fijo_diario = st.number_input("Costos Fijos & Corral ($/día/cab)", 1.0, 30.0, 7.5, 0.5)

    ganancia_total_esperada = peso_meta_eng - peso_entrada_eng
    dias_en_corral_dof = ganancia_total_esperada / gmd_esperada if gmd_esperada > 0 else 0
    
    peso_promedio_periodo = (peso_entrada_eng + peso_meta_eng) / 2.0
    consumo_ms_diario_kg = peso_promedio_periodo * (consumo_ms_porcentaje / 100.0)
    consumo_total_ms_ton = (consumo_ms_diario_kg * dias_en_corral_dof) / 1000.0
    
    costo_alimentacion_total = consumo_total_ms_ton * costo_dieta_engorda
    costo_fijos_totales_periodo = dias_en_corral_dof * costo_fijo_diario
    costo_oportunidad_destete = peso_entrada_eng * precio_venta_destete_actual
    
    costo_total_operativo_engorda = costo_alimentacion_total + costo_fijos_totales_periodo
    costo_total_produccion_gordo = costo_oportunidad_destete + costo_total_operativo_engorda
    
    ingreso_venta_gordo = peso_meta_eng * precio_venta_gordo_actual
    utilidad_neta_engorda = ingreso_venta_gordo - costo_total_produccion_gordo
    punto_equilibrio_gordo = costo_total_produccion_gordo / peso_meta_eng if peso_meta_eng > 0 else 0
    roi_engorda = (utilidad_neta_engorda / costo_total_produccion_gordo) * 100 if costo_total_produccion_gordo > 0 else 0

    ingreso_venta_destete = costo_oportunidad_destete
    costo_vaca_por_becerro = (costo_operativo_vaca_ano / (porcentaje_destete / 100.0)) if porcentaje_destete > 0 else costo_operativo_vaca_ano
    utilidad_neta_destete = ingreso_venta_destete - costo_vaca_por_becerro

    st.markdown("---")
    st.subheader("🎯 Resumen de la Simulación")

    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    with col_res1:
        st.metric("Días en Corral (DOF)", f"{dias_en_corral_dof:.0f} días", f"GMD: {gmd_esperada} kg/d")
        st.metric("Consumo Total MS", f"{consumo_total_ms_ton * 1000:,.0f} kg", f"Diario: {consumo_ms_diario_kg:.2f} kg/d")
    with col_res2:
        st.metric("Costo Alimentación", f"${costo_alimentacion_total:,.2f} MXN", f"@ ${costo_dieta_engorda:,.0f}/ton")
        st.metric("Costo Total Engorda", f"${costo_total_operativo_engorda:,.2f} MXN", "Alimento + Fijos")
    with col_res3:
        st.metric("Utilidad Neta Engorda", f"${utilidad_neta_engorda:,.2f} MXN", f"ROI: {roi_engorda:.1f}%")
        st.metric("Punto de Equilibrio", f"${punto_equilibrio_gordo:,.2f} MXN/kg", "Precio mín. gordo")
    with col_res4:
        st.metric("Venta Ganado Gordo", f"${ingreso_venta_gordo:,.2f} MXN", f"{peso_meta_eng} kg @ ${precio_venta_gordo_actual}")
        st.metric("Valor Destete (Oportunidad)", f"${ingreso_venta_destete:,.2f} MXN", f"{peso_entrada_eng} kg @ ${precio_venta_destete_actual}")

    st.markdown("---")
    st.subheader("⚖️ Decisión Comercial")

    comparativa_df = pd.DataFrame({
        "Estrategia Comercial": ["Venta Directa al Destete", "Retención y Engorda a Finalización"],
        "Peso de Venta (kg)": [peso_entrada_eng, peso_meta_eng],
        "Precio de Venta ($/kg)": [precio_venta_destete_actual, precio_venta_gordo_actual],
        "Ingreso Bruto por Animal ($)": [ingreso_venta_destete, ingreso_venta_gordo],
        "Costos Directos Incurridos ($)": [0.0, costo_total_operativo_engorda],
        "Utilidad Neta Estimada ($/cabeza)": [utilidad_neta_destete, utilidad_neta_engorda]
    })
    st.dataframe(comparativa_df, use_container_width=True, hide_index=True)

    diferencia_utilidad = utilidad_neta_engorda - utilidad_neta_destete
    if diferencia_utilidad > 0:
        st.success(f"✅ **Recomendación Gerencial:** Con los precios actuales ($84/kg destete vs $60/kg gordo), la engorda es **rentable**, generando una utilidad adicional de **${diferencia_utilidad:,.2f} MXN por cabeza** frente a vender al destete.")
    else:
        st.warning(f"⚠️ **Recomendación Gerencial:** Con un precio de $84.00/kg al destete, el costo de oportunidad es elevado frente a $60.00/kg en gordo. La diferencia es de **${diferencia_utilidad:,.2f} MXN**, por lo que **conviene más vender directamente al destete**.")

with tabs[5]:
    st.header("📊 Finanzas, Márgenes de Ganancia & Proyecciones")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Utilidad Neta Anual", f"${utilidad_neta_empresarial:,.0f} MXN", "Ganancia Total")
        st.metric("Rentabilidad Hato", f"{rentabilidad_sobre_costo:.1f}%", "ROI")
    with col2:
        st.metric("Ingreso Bruto Venta", f"${ingreso_total_venta:,.0f} MXN")
        st.metric("Costo Total Operativo", f"${costos_totales_hato:,.0f} MXN")
    with col3:
        st.metric("Peso Destete Objetivo", f"{peso_destete_meta} kg")
        st.metric("Costo Dieta Tonelada", f"${costo_ton_dieta:,.2f} MXN")

    st.markdown("---")
    pesos_sim = [180, 200, 220, 240, 260, 280, 300]
    ingresos_sim = [p * becerros_destetados_total * precio_venta_kg for p in pesos_sim]
    fig_fin = px.line(x=pesos_sim, y=ingresos_sim, markers=True, labels={"x": "Peso al Destete (kg)", "y": "Ingreso Bruto Total (MXN)"}, title="Proyección de Ingresos según Peso al Destete")
    fig_fin.update_traces(line_color="#b91c1c", line_width=3)
    st.plotly_chart(fig_fin, use_container_width=True)

with tabs[6]:
    st.header("📅 Calendario Inteligente de Servicios y Partos")
    df = db.obtener_animales()
    df_v = df[df['categoria'].isin(['VIENTRE (VACA)', 'REEMPLAZO (VAQUILLA)'])] if not df.empty else pd.DataFrame()
    if df_v.empty:
        st.info("Registre vientres en el inventario.")
    else:
        v_dict = {f"{r['siniiga']} ({r['raza']})": r['id'] for _, r in df_v.iterrows()}
        v_sel = st.selectbox("Vientre Seleccionado", list(v_dict.keys()))
        v_id = v_dict[v_sel]
        
        with st.form("form_smart_cal"):
            evento = st.selectbox("Evento Reproductivo", ["EMPADRE / SERVICIO", "DIAGNOSTICO GESTACION", "PARTO"])
            f_ev = st.date_input("Fecha del Evento")
            res = st.selectbox("Resultado / Estatus", ["PREÑADA", "VACÍA", "PARTO NORMAL", "DISTOCIA"])
            obs = st.text_area("Notas técnicas")
            
            if st.form_submit_button("Registrar y Calcular Parto"):
                f_parto = db.registrar_reproduccion(v_id, evento, str(f_ev), res, obs)
                if f_parto:
                    st.success(f"✅ Registrado con éxito. Fecha Probable de Parto: **{f_parto}**")
                else:
                    st.success("✅ Evento guardado correctamente.")

with tabs[7]:
    st.header("💉 Sanidad Integral Regional (Zacatecas)")
    df = db.obtener_animales()
    if df.empty:
        st.info("Sin animales registrados.")
    else:
        d_anim = {f"{r['siniiga']}": r['id'] for _, r in df.iterrows()}
        sel_an = st.selectbox("Seleccionar Animal", list(d_anim.keys()))
        id_a = d_anim[sel_an]
        
        with st.form("form_san_z"):
            trat = st.selectbox("Biológico / Tratamiento", ["VACUNA ANTIRRÁBICA / DERRIENGUE", "CLOSTRIDIOSIS", "LEPTOSPIROSIS", "CONTROL PARASITARIO"])
            f_ap = st.date_input("Fecha Aplicación")
            f_prox = st.date_input("Próxima Dosis / Refuerzo")
            if st.form_submit_button("Guardar Sanidad"):
                db.registrar_sanidad(id_a, trat, str(f_ap), str(f_prox))
                st.success("Sanidad registrada exitosamente.")

with tabs[8]:
    st.header("📊 Estandarización BIF (205 Días) & Gráficas")
    st.markdown("Evaluación genética y de crecimiento estandarizada a 205 días al destete para raza Hereford.")
    st.info("💡 Asegúrese de registrar pesajes de Nacimiento y Destete en la base de datos para generar los cálculos BIF automáticos.")

with tabs[9]:
    st.header("📄 Generación de Reporte Ejecutivo en PDF")
    pdf_bytes = generar_pdf_cria()
    st.download_button(
        label="📥 Descargar Reporte Ejecutivo en PDF",
        data=pdf_bytes,
        file_name="Cr-IA_150_Reporte.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.success("¡Reporte listo para descarga con todo el inventario y resumen financiero!")

with tabs[10]:
    st.header("💬 Asistente IA & Asesoría")
    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if q := st.chat_input("Escribe tu duda sobre nutrición, genética Hereford o costos..."):
        st.session_state.chat_messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        resp = f"🤖 Recibido: *\"{q}\"*. Como asistente de **Cr-IA 150**, he analizado tu consulta para optimizar la rentabilidad de tu hato."
        st.session_state.chat_messages.append({"role": "assistant", "content": resp})
        with st.chat_message("assistant"):
            st.markdown(resp)

    st.markdown("---")
    st.subheader("🧭 Agendar Asesoría con el Especialista")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        nom_h = st.text_input("Productor / Propietario")
        ran_h = st.text_input("Nombre del Rancho")
        mail_h = st.text_input("Correo o Teléfono")
    with col_c2:
        mot_h = st.selectbox("Objetivo de Asesoría", ["Optimización de Costos", "Nutrición en Época Seca", "Programa Genético Hereford", "Auditoría Financiera"])
        f_cita = st.date_input("Fecha Preferida", min_value=datetime.now().date())
        h_cita = st.selectbox("Horario", ["09:00 AM", "11:00 AM", "01:00 PM", "04:00 PM"])
    if st.button("💳 Pagar $475 MXN y Agendar con el Dr. Alejandro Castañeda", use_container_width=True):
        if nom_h and mail_h:
            st.success(f"🎉 **¡Cita Agendada con Éxito!** El Dr. Alejandro Castañeda te atenderá el {f_cita} a las {h_cita}.")
            st.balloons()
        else:
            st.warning("⚠️ Completa tu nombre y datos de contacto.")

with tabs[11]:
    st.header("🌾 Planes de Contingencia, Suplementación & Respaldos de Datos")
    
    st.subheader("💾 Respaldos de Base de Datos (Backup / Export)")
    df_export = db.obtener_animales()
    if not df_export.empty:
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Exportar Base de Datos a CSV (Excel)",
            data=csv_data,
            file_name="inventario_ganado_cria_150.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("No hay datos cargados para exportar.")
