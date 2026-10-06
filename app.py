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

# --- CLASE DE BASE DE DATOS SEGURA ---
class CrIA150NutriON:
    def __init__(self, db_name="cria_nutrion_elite.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._crear_tablas()

    def _crear_tablas(self):
        try:
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
        except Exception as e:
            st.error(f"Error al inicializar base de datos: {e}")

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

# --- INICIALIZACIÓN DE ESTADOS ---
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
        "FND (% MS)": [45.0, 68.0, 12.0, 9.0, 28.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "Min Inclusión (%)": [0.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0],
        "Max Inclusión (%)": [50.0, 50.0, 25.0, 60.0, 20.0, 6.0, 3.0, 1.2, 3.0, 4.0]
    })

if "nutrion_chat_messages" not in st.session_state:
    st.session_state.nutrion_chat_messages = [
        {"role": "assistant", "content": "¡Hola! Soy **NutriON 360 ULTRA V4.0**, integrado en **Cr-IA 150**. ¿Cómo podemos optimizar la nutrición, los costos y las ganancias de tu hato hoy?"}
    ]

# --- BARRA LATERAL ---
st.sidebar.success("🟢 Acceso Directo Propietario")
st.sidebar.markdown("---")
with st.sidebar.expander("🐂 Parámetros del Hato & Empresa", expanded=True):
    num_vientres = st.number_input("Número de Vientres en el Hato", min_value=1, max_value=5000, value=100, step=10)
    peso_destete_meta = st.slider("Peso Objetivo al Destete (kg)", min_value=180.0, max_value=300.0, value=230.0, step=5.0)
    porcentaje_destete = st.slider("Porcentaje de Destete Esperado (%)", min_value=60.0, max_value=95.0, value=85.0, step=1.0)
    precio_venta_kg = st.number_input("Precio de Venta Becerro Destetado (MXN/kg)", min_value=30.0, max_value=100.0, value=65.0, step=1.0)
    costo_operativo_vaca_ano = st.number_input("Costo Anual por Vaca Madre (MXN/año)", min_value=1000.0, max_value=15000.0, value=6500.0, step=250.0)

# --- LOGOTIPO Y ENCABEZADO CLARO (VACA HEREFORD CON BECERRO) ---
st.markdown("""
    <div style="background: linear-gradient(135deg, #fffbeb 0%, #ffedd5 50%, #fed7aa 100%); padding: 25px; border-radius: 20px; color: #431407; box-shadow: 0 10px 30px rgba(194, 65, 12, 0.15); margin-bottom: 25px; border: 2px solid #ea580c;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%); color: #ffffff; font-size: 2.2rem; font-weight: bold; padding: 14px 22px; border-radius: 16px; box-shadow: 0 6px 20px rgba(185, 28, 28, 0.3); text-align: center; border: 2px solid #fef08a;">
                    🐄🐮<br><span style="font-size: 0.65rem; letter-spacing: 1px; text-transform: uppercase; font-weight: 800;">Vaca & Becerro Hereford</span>
                </div>
                <div>
                    <h1 style="margin: 0; font-size: 2.2rem; font-weight: 900; color: #7c2d12; letter-spacing: -0.5px;">
                        Cr-IA <span style="color: #ea580c;">150</span> & NutriON <span style="color: #b91c1c;">360 ULTRA</span>
                    </h1>
                    <p style="margin: 6px 0 0 0; font-size: 1.05rem; color: #9a3412; font-weight: 600;">
                        <b>Slogan:</b> "Vaca Hereford y Becerro al Máximo Rendimiento: Genética, Nutrición y Finanzas Hiperrentables."
                    </p>
                </div>
            </div>
            <div>
                <span style="background-color: #b91c1c; color: #ffffff; padding: 8px 16px; border-radius: 25px; font-size: 0.85rem; font-weight: 700; border: 1px solid #fef08a; text-transform: uppercase; letter-spacing: 1.5px; box-shadow: 0 4px 10px rgba(185, 28, 28, 0.2);">
                    Enterprise Elite SaaS V4.0
                </span>
            </div>
        </div>
        <div style="margin-top: 18px; padding-top: 15px; border-top: 1px solid rgba(194, 65, 12, 0.2); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
            <p style="margin: 0; font-size: 0.95rem; color: #7c2d12; font-style: italic; font-weight: 500;">
                "Optimizando la relación vaca-becerro con ganancia de peso superior y máxima eficiencia en agostadero."
            </p>
            <p style="margin: 0; font-size: 0.9rem; color: #431407; font-weight: 700;">
                💻 Creado y desarrollado por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong> | Cañón de Tlaltenango
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- CÁLCULO DE OPTIMIZACIÓN LINEAL ---
df_nut_base = st.session_state.df_ingredientes_nutrion
try:
    nombres_n = df_nut_base["Nombre del Ingrediente"].astype(str).values
    c_n = df_nut_base["Precio Estimado (MXN/ton)"].astype(float).values
    pc_n = df_nut_base["Proteina Cruda (PC % MS)"].astype(float).values / 100.0  
    eng_n = df_nut_base["Energia Neta Ganancia (ENg Mcal/kg)"].astype(float).values
    disponibles_n = df_nut_base["Disponible"].astype(bool).values
except KeyError as err:
    st.error(f"Falta columna clave en ingredientes: {err}")
    st.stop()

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

A_ub_n = np.array([
    -pc_n,
    -eng_n
])
b_ub_n = np.array([
    -pc_min_req,
    -eng_min_req
])

resultado_nut = linprog(c_n, A_ub=A_ub_n, b_ub=b_ub_n, A_eq=A_eq_n, b_eq=b_eq_n, bounds=bounds_n, method='highs')

costo_ton_dieta = resultado_nut.fun if resultado_nut.success else 4800.0
becerros_destetados_total = int(num_vientres * (porcentaje_destete / 100.0))
ingreso_total_venta = becerros_destetados_total * peso_destete_meta * precio_venta_kg
costos_totales_hato = num_vientres * costo_operativo_vaca_ano
utilidad_neta_empresarial = ingreso_total_venta - costos_totales_hato
rentabilidad_sobre_costo = (utilidad_neta_empresarial / costos_totales_hato) * 100 if costos_totales_hato > 0 else 0.0

# --- CLASE PDF REPORT GENERATOR ---
class PDFCrIAReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(194, 65, 12)
        self.cell(0, 10, 'Cr-IA 150 & NutriON 360 ULTRA - Reporte Ejecutivo Ganadero', 0, 1, 'C')
        self.set_font('Arial', 'I', 9)
        self.cell(0, 5, 'Desarrollado por el Nutriologo Veterinario Dr. Alejandro Castaneda Correa', 0, 1, 'C')
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'
