import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from scipy.optimize import linprog
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA 150 & NutriON 360 ULTRA | Hereford Elite SaaS",
    page_icon="🐄",
    layout="wide"
)

# --- ESTILOS CSS AVANZADOS & CLAROS (UI/UX PROFESIONAL) ---
st.markdown("""
    <style>
    html, body, [class*="css"], .stMarkdown, .stText, .stSelectbox, .stSlider, .stNumberInput, div, span, p, label, .stRadio {
        font-family: 'Calibri', sans-serif !important;
        color: #1e293b !important;
    }
    .main {
        background-color: #fffaf8;
    }
    /* TARJETAS DE MÉTRICAS */
    .stMetric {
        background: #ffffff;
        padding: 12px 14px !important;
        border-radius: 14px;
        box-shadow: 0 4px 20px -3px rgba(194, 65, 12, 0.1);
        border: 1px solid #fed7aa;
        border-left: 5px solid #ea580c;
        margin-bottom: 10px !important;
    }
    .stMetric label {
        font-size: 0.75rem !important;
        color: #9a3412 !important;
        font-weight: 700 !important;
        text-transform: uppercase;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
        color: #431407 !important;
        font-weight: 800 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #431407 !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CREDENCIALES Y AUTENTICACIÓN ---
USUARIO_PRINCIPAL = "alejandro_c"
PASSWORD_PRINCIPAL = "Tlaltenango2026*"

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    st.title("🔒 Cr-IA 150 & NutriON 360 - Acceso Seguro Restringido")
    st.subheader("Sistema Ganadero Elite | Cañón de Tlaltenango, Zacatecas")
    
    with st.form("form_login"):
        user_input = st.text_input("Usuario Principal", value="alejandro_c")
        pass_input = st.text_input("Contraseña", type="password", value="Tlaltenango2026*")
        btn_login = st.form_submit_button("Iniciar Sesión Segura")
        
        if btn_login:
            if user_input == USUARIO_PRINCIPAL and pass_input == PASSWORD_PRINCIPAL:
                st.session_state['autenticado'] = True
                st.success("✅ Acceso autorizado. Cargando plataforma...")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")
    st.stop()

# --- CLASE DE BASE DE DATOS Y GESTIÓN ---
class CrIA150NutriON:
    def __init__(self, db_name="cria_nutrion_elite.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._crear_tablas()

    def _crear_tablas(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS animales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siniiga TEXT UNIQUE,
                arete_propio TEXT,
                categoria TEXT,
                raza TEXT,
                sexo TEXT,
                fecha_nacimiento TEXT,
                edad_madre_anos REAL,
                circunferencia_escrotal REAL DEFAULT NULL
            )
        ''')
        self.cursor.execute('''
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
        self.cursor.execute('''
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
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sanidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER,
                tipo_tratamiento TEXT,
                fecha_aplicacion TEXT,
                proxima_dosis TEXT,
                FOREIGN KEY (animal_id) REFERENCES animales (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS costos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER,
                concepto TEXT,
                monto_mxn REAL,
                fecha TEXT,
                FOREIGN KEY (animal_id) REFERENCES animales (id)
            )
        ''')
        self.conn.commit()

    def registrar_animal(self, siniiga, arete, categoria, raza, sexo, fecha_nac, edad_madre, ce):
        try:
            self.cursor.execute('''
                INSERT INTO animales (siniiga, arete_propio, categoria, raza, sexo, fecha_nacimiento, edad_madre_anos, circunferencia_escrotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (siniiga, arete, categoria, raza, sexo.upper(), fecha_nac, edad_madre, ce))
            self.conn.commit()
            return True, "Registro guardado con éxito."
        except sqlite3.IntegrityError:
            return False, f"El SINIIGA {siniiga} ya se encuentra registrado."

    def registrar_pesaje(self, animal_id, tipo, fecha, peso, cc):
        self.cursor.execute('''
            INSERT INTO pesajes (animal_id, tipo_pesaje, fecha_pesaje, peso_kg, condicion_corporal)
            VALUES (?, ?, ?, ?, ?)
        ''', (animal_id, tipo.upper(), fecha, peso, cc))
        self.conn.commit()

    def registrar_reproduccion(self, animal_id, tipo_evento, fecha, resultado, obs):
        f_parto_est = None
        if tipo_evento == "EMPADRE / SERVICIO":
            f_dt = datetime.strptime(fecha, "%Y-%m-%d")
            f_dt_parto = f_dt + timedelta(days=283)
            f_parto_est = f_dt_parto.strftime("%Y-%m-%d")

        self.cursor.execute('''
            INSERT INTO reproduccion (animal_id, tipo_evento, fecha_evento, fecha_probable_parto, resultado, observaciones)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (animal_id, tipo_evento, fecha, f_parto_est, resultado, obs))
        self.conn.commit()
        return f_parto_est

    def registrar_sanidad(self, animal_id, tratamiento, fecha, prox):
        self.cursor.execute('''
            INSERT INTO sanidad (animal_id, tipo_tratamiento, fecha_aplicacion, proxima_dosis)
            VALUES (?, ?, ?, ?)
        ''', (animal_id, tratamiento, fecha, prox))
        self.conn.commit()

    def registrar_costo(self, animal_id, concepto, monto, fecha):
        self.cursor.execute('''
            INSERT INTO costos (animal_id, concepto, monto_mxn, fecha)
            VALUES (?, ?, ?, ?)
        ''', (animal_id, concepto, monto, fecha))
        self.conn.commit()

    def obtener_animales(self):
        return pd.read_sql("SELECT * FROM animales", self.conn)

    def obtener_reproduccion(self):
        return pd.read_sql("SELECT r.*, a.siniiga FROM reproduccion r JOIN animales a ON r.animal_id = a.id", self.conn)

    def obtener_costos(self):
        return pd.read_sql("SELECT c.*, a.siniiga FROM costos c JOIN animales a ON c.animal_id = a.id", self.conn)

db = CrIA150NutriON()

# --- INICIALIZACIÓN DE INGREDIENTES PARA OPTIMIZACIÓN LINEAL (NUTTION 360) ---
if "df_ingredientes_nutrion" not in st.session_state:
    st.session_state.df_ingredientes_nutrion = pd.DataFrame({
        "Nombre del Ingrediente": [
            "Ensilado de maiz", "Heno de zacate Buffel / Pasto nativo", "Harina de soya", 
            "Grano de maiz molido", "Pasta de canola", "Melaza de caña", 
            "Sal mineralizada 12% P", "Urea ganadera", "Núcleo Becerro Engorda", "Grasa sobrepaso"
        ],
        "Categoria": ["Forraje Húmedo", "Forraje Seco", "Suplemento Proteico", "Grano Energético", "Suplemento Proteico", "Subproducto Energético", "Suplemento Mineral", "Fuente No Proteica", "Suplemento Mineral", "Suplemento Energético"],
        "Disponible": [True, True, True, True, True, True, True, True, True, True],
        "Precio Estimado (MXN/ton)": [1100.0, 3200.0, 12500.0, 5800.0, 8500.0, 4800.0, 11000.0, 14000.0, 24000.0, 34000.0],
        "Proteina Cruda (PC % MS)": [8.0, 8.5, 48.0, 8.5, 38.0, 4.8, 0.0, 281.0, 0.0, 1.0],
        "Energia Neta Ganancia (ENg Mcal/kg)": [0.95, 0.82, 1.45, 1.52, 1.38, 1.30, 0.0, 0.0, 0.0, 2.10],
        "FND (% MS)":
