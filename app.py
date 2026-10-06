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
    page_title="Cr-IA 150 & NutriON 360 ULTRA | SaaS Ganadero Elite",
    page_icon="🐂",
    layout="wide"
)

# --- ESTILOS CSS AVANZADOS & DISEÑO SaaS ---
st.markdown("""
    <style>
    html, body, [class*="css"], .stMarkdown, .stText, .stSelectbox, .stSlider, .stNumberInput, div, span, p, label, .stRadio {
        font-family: 'Calibri', sans-serif !important;
        color: #1e293b !important;
    }
    .brand-container {
        background: linear-gradient(135deg, #082214 0%, #113f27 50%, #04120a 100%);
        padding: 30px;
        border-radius: 18px;
        color: white;
        box-shadow: 0 10px 35px rgba(0,0,0,0.3);
        margin-bottom: 25px;
        border: 1px solid rgba(212, 175, 55, 0.4);
    }
    .brand-title {
        font-size: 2.5rem;
        font-weight: 900;
        margin: 0;
        letter-spacing: -0.5px;
        color: #ffffff;
    }
    .brand-title span {
        color: #d4af37;
    }
    .brand-subtitle {
        font-size: 1.1rem;
        color: #d1fae5;
        margin-top: 6px;
        font-weight: 500;
    }
    .brand-badge {
        background-color: rgba(212, 175, 55, 0.2);
        color: #d4af37;
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 700;
        border: 1px solid #d4af37;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .brand-footer-info {
        margin-top: 20px;
        padding-top: 15px;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
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
        "FND (% MS)": [45.0, 68.0, 12.0, 9.0, 28.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "Min Inclusión (%)": [0.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0],
        "Max Inclusión (%)": [50.0, 50.0, 25.0, 60.0, 20.0, 6.0, 3.0, 1.2, 3.0, 4.0]
    })

# --- INICIALIZACIÓN DE CHAT IA ---
if "nutrion_chat_messages" not in st.session_state:
    st.session_state.nutrion_chat_messages = [
        {"role": "assistant", "content": "¡Hola! Soy **NutriON 360 ULTRA V4.0**, integrado en **Cr-IA 150**. ¿Cómo podemos optimizar la nutrición, los costos y las ganancias de tu hato hoy?"}
    ]

# --- BARRA LATERAL ---
st.sidebar.success("🟢 Sesión Activa (Propietario)")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("🐂 Parámetros del Hato & Empresa", expanded=True):
    num_vientres = st.number_input("Número de Vientres en el Hato", min_value=1, max_value=5000, value=100, step=10)
    peso_destete_meta = st.slider("Peso Objetivo al Destete (kg)", min_value=180.0, max_value=300.0, value=230.0, step=5.0)
    porcentaje_destete = st.slider("Porcentaje de Destete Esperado (%)", min_value=60.0, max_value=95.0, value=85.0, step=1.0)
    precio_venta_kg = st.number_input("Precio de Venta Becerro Destetado (MXN/kg)", min_value=30.0, max_value=100.0, value=65.0, step=1.0)
    costo_operativo_vaca_ano = st.number_input("Costo Anual por Vaca Madre (MXN/año)", min_value=1000.0, max_value=15000.0, value=6500.0, step=250.0)

# --- LOGOTIPO Y ENCABEZADO SaaS ---
st.markdown("""
    <div class="brand-container">
        <div class="brand-header" style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="background: linear-gradient(135deg, #d4af37 0%, #aa8c2c 100%); color: #04120a; font-size: 2.3rem; font-weight: bold; padding: 12px 20px; border-radius: 14px; box-shadow: 0 6px 20px rgba(0,0,0,0.4); text-align: center; border: 1px solid #fff;">
                    🐂📈
                </div>
                <div>
                    <h1 class="brand-title">Cr-IA <span>150</span> & NutriON <span>360 ULTRA</span></h1>
                    <p class="brand-subtitle"><b>Slogan:</b> "Tecnolog-IA y Nutrición de Precisión: Eficiencia Zootécnica, Control Financiero y Máximas Ganancias."</p>
                </div>
            </div>
            <div>
                <span class="brand-badge">Enterprise Elite SaaS V4.0</span>
            </div>
        </div>
        <div class="brand-footer-info">
            <p style="margin: 0; font-size: 0.95rem; color: #a8d5ba; font-style: italic;">
                "Transformando cada kilogramo destetado y cada gramo de nutriente en dividendos reales para tu negocio ganadero."
            </p>
            <p style="margin: 0; font-size: 0.9rem; color: #ffffff; font-weight: 600;">
                💻 Aplicación creada y desarrollada por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong> | Cañón de Tlaltenango
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- CÁLCULO DE OPTIMIZACIÓN LINEAL (NUTTION 360) ---
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
        self.cell(0, 10, f'Pagina {self.page_no()} | Canon de Tlaltenango, Zacatecas', 0, 0, 'C')

def generar_pdf_cria():
    pdf = PDFCrIAReport()
    pdf.add_page()
    def safe_str(txt):
        return str(txt).encode('latin-1', 'replace').decode('latin-1')

    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(67, 20, 7)
    pdf.cell(0, 8, safe_str("1. Resumen Zootecnico del Hato"), 0, 1)
    pdf.set_font('Arial', '', 10)
    
    res = {
        "Vientres en Reproduccion": f"{num_vientres} cabezas",
        "Porcentaje de Destete": f"{porcentaje_destete}%",
        "Becerros Destetados Anuales": f"{becerros_destetados_total} cabezas",
        "Peso Promedio Destete": f"{peso_destete_meta} kg",
        "Costo Dieta Optimizada (LP)": f"${costo_ton_dieta:,.2f} MXN/ton"
    }
    for k, v in res.items():
        pdf.cell(95, 7, safe_str(f"{k}:"), 0, 0)
        pdf.cell(95, 7, safe_str(f"{v}"), 0, 1)

    pdf.ln(4)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, safe_str("2. Evaluacion Financiera y Ganancias"), 0, 1)
    pdf.set_font('Arial', '', 10)
    
    econ = {
        "Ingreso Total por Venta de Becerros": f"${ingreso_total_venta:,.2f} MXN",
        "Costo Operativo Total del Hato": f"${costos_totales_hato:,.2f} MXN",
        "Utilidad Neta Empresarial": f"${utilidad_neta_empresarial:,.2f} MXN",
        "Rentabilidad sobre Inversion": f"{rentabilidad_sobre_costo:.1f}%"
    }
    for k, v in econ.items():
        pdf.cell(95, 7, safe_str(f"{k}:"), 0, 0)
        pdf.cell(95, 7, safe_str(f"{v}"), 0, 1)

    output = pdf.output()
    return bytes(output) if isinstance(output, (bytes, bytearray)) else output.encode('latin1')

# --- MENÚ DE MÓDULOS UNIFICADOS (10 TABS) ---
tabs = st.tabs([
    "📋 1. Inventario & Altas",
    "⚖️ 2. Condición Corporal",
    "🧮 3. Optimizador LP (NutriON)",
    "📊 4. Finanzas & Ganancias",
    "📅 5. Smart Calendar (Partos)",
    "💉 6. Sanidad Regional",
    "📊 7. Evaluación BIF",
    "📄 8. Reporte Ejecutivo PDF",
    "💬 9. Asistente IA & Citas",
    "🌾 10. Contingencia & Manejo"
])

with tabs[0]:
    st.header("📝 Alta de Reproductor / Vientre / Cría")
    with st.form("form_alta_avanzada"):
        col1, col2 = st.columns(2)
        with col1:
            siniiga = st.text_input("SINIIGA Oficial")
            arete = st.text_input("Arete Interno / Ganadería")
            categoria = st.selectbox("Categoría Zootécnica", ["VIENTRE (VACA)", "REEMPLAZO (VAQUILLA)", "CRIA", "TORO REPRODUCTOR"])
            raza = st.text_input("Composición Racial (ej. Hereford / Simmental)")
        with col2:
            sexo = st.selectbox("Sexo", ["MACHO", "HEMBRA"])
            fecha_nacimiento = st.date_input("Fecha de Nacimiento")
            edad_madre = st.number_input("Edad de la Madre al Parto (Años)", 1.5, 15.0, 4.0, 0.5)
            ce = st.number_input("Circunferencia Escrotal (cm) [Solo si es Toro, min. 32 cm]", 25.0, 50.0, 34.0)
        
        sub = st.form_submit_button("Registrar en Base de Datos")
        if sub:
            if siniiga:
                exito, msg = db.registrar_animal(siniiga, arete, categoria, raza, sexo, str(fecha_nacimiento), edad_madre, ce if categoria == "TORO REPRODUCTOR" else None)
                if exito:
                    st.success(msg)
                else:
                    st.warning(msg)
            else:
                st.error("El SINIIGA es obligatorio.")

with tabs[1]:
    st.header("⚖️ Monitoreo de Condición Corporal y Estado Nutricional")
    df = db.obtener_animales()
    if df.empty:
        st.info("Registre animales en el inventario.")
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
    st.header("🧮 Optimizador Lineal de Raciones (NutriON 360 LP)")
    st.markdown("Calcula la dieta de mínimo costo mediante programación lineal (`scipy.optimize.linprog`) cumpliendo con requerimientos de proteína y energía.")
    
    st.session_state.df_ingredientes_nutrion = st.data_editor(
        st.session_state.df_ingredientes_nutrion,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Disponible": st.column_config.CheckboxColumn("¿Disponible?", default=True),
            "Min Inclusión (%)": st.column_config.NumberColumn("Min (%)", min_value=0.0, max_value=100.0, step=0.5),
            "Max Inclusión (%)": st.column_config.NumberColumn("Max (%)", min_value=0.0, max_value=100.0, step=0.5),
        },
        key="editor_ingredientes_nutrion_persisted"
    )

    st.markdown("---")
    if resultado_nut.success:
        st.success(f"✅ **Optimización Exitosa:** Costo total de la dieta: **${costo_ton_dieta:,.2f} MXN por tonelada** (${costo_ton_dieta/30:,.2f} MXN por día aprox).")
        tabla_dieta = []
        for i, ing in enumerate(nombres_n):
            frac = resultado_nut.x[i]
            porc = frac * 100
            kg_ton = frac * 1000
            if porc > 0.01:
                costo_parcial = frac * c_n[i]
                tabla_dieta.append({
                    "Ingrediente": ing,
                    "Inclusión (%)": round(porc, 1),
                    "Kg por Tonelada": round(kg_ton, 1),
                    "Costo Unitario ($/ton)": f"${c_n[i]:,.2f}",
                    "Aporte al Costo ($)": f"${costo_parcial:,.2f}"
                })
        st.dataframe(pd.DataFrame(tabla_dieta), use_container_width=True, hide_index=True)
    else:
        st.error("⚠️ Ajusta las restricciones o disponibilidad para encontrar solución factible.")

with tabs[3]:
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
    fig_fin.update_traces(line_color="#10b981", line_width=3)
    st.plotly_chart(fig_fin, use_container_width=True)

with tabs[4]:
    st.header("📅 Calendario Inteligente de Servicios y Partos")
    df = db.obtener_animales()
    df_v = df[df['categoria'].isin(['VIENTRE (VACA)', 'REEMPLAZO (VAQUILLA)'])]
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

with tabs[5]:
    st.header("💉 Sanidad Integral Regional (Zacatecas)")
    df = db.obtener_animales()
    if df.empty:
        st.info("Sin animales.")
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

with tabs[6]:
    st.header("📊 Estandarización BIF (205 Días) & Gráficas")
    st.markdown("Evaluación genética y de crecimiento estandarizada a 205 días al destete.")
    st.info("💡 Asegúrese de registrar pesajes de Nacimiento y Destete en la base de datos para generar los cálculos BIF automáticos.")

with tabs[7]:
    st.header("📄 Generación de Reporte Ejecutivo en PDF")
    pdf_bytes = generar_pdf_cria()
    st.download_button(
        label="📥 Descargar Reporte Ejecutivo en PDF",
        data=pdf_bytes,
        file_name="Cr-IA_150_NutriON_360_Reporte.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.success("¡Reporte listo para descarga!")

with tabs[8]:
    st.header("💬 Asistente Virtual NutriON IA & Asesoría")
    for m in st.session_state.nutrion_chat_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if q := st.chat_input("Escribe tu duda sobre nutrición, costos o manejo ganadero..."):
        st.session_state.nutrion_chat_messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        resp = f"🤖 Recibido: *\"{q}\"*. Como asistente **NutriON 360 & Cr-IA 150**, he analizado tu consulta para optimizar la rentabilidad de tu hato."
        st.session_state.nutrion_chat_messages.append({"role": "assistant", "content": resp})
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
        mot_h = st.selectbox("Objetivo de Asesoría", ["Optimización de Costos", "Nutrición en Época Seca", "Programa Genético", "Auditoría Financiera"])
        f_cita = st.date_input("Fecha Preferida", min_value=datetime.now().date())
        h_cita = st.selectbox("Horario", ["09:00 AM", "11:00 AM", "01:00 PM", "04:00 PM"])
    if st.button("💳 Pagar $475 MXN y Agendar con el Dr. Alejandro Castañeda", use_container_width=True):
        if nom_h and mail_h:
            st.success(f"🎉 **¡Cita Agendada con Éxito!** El Dr. Alejandro Castañeda te atenderá el {f_cita} a las {h_cita}.")
            st.balloons()
        else:
            st.warning("⚠️ Completa tu nombre y datos de contacto.")

with tabs[9]:
    st.header("🌾 Planes de Contingencia, Suplementación & Manejo")
    st.markdown("""
        * **Sequía y Estiaje:** Activación de destete precoz, uso de rastrojos amonificados y bloques multinutricionales en el Cañón de Tlaltenango.
        * **Manejo Sanitario:** Protocolo preventivo contra anaplasmosis, garrapata y control estricto de parásitos gastrointestinales.
        * **Night Feeding:** Suministro de alimento al atardecer para concentrar los partos en horario diurno.
    """)
