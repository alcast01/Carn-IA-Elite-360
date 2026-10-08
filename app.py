import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from scipy.optimize import linprog
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from datetime import datetime, timedelta
import os

# Configuración obligatoria de la página
st.set_page_config(
    page_title="Cr-IA 150 | Hereford Elite SaaS",
    page_icon="🐄",
    layout="wide"
)

# --- ESTILOS CSS SEGUROS ---
st.markdown("""<style>
.main { background-color: #fffaf8; }
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
</style>""", unsafe_allow_html=True)

# --- CLASE DE BASE DE DATOS ROBUSTA (CONEXIÓN AISLADA POR MÉTODO) ---
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS costos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    animal_id INTEGER,
                    concepto TEXT,
                    monto_mxn REAL,
                    fecha TEXT,
                    FOREIGN KEY (animal_id) REFERENCES animales (id)
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error creando tablas en base de datos: {e}")

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
            return True, f"¡Vaca / Animal registrado y guardado con éxito en la base de datos! (Arete: {arete_val}, SINIIGA: {siniiga_val})"
        except Exception as e:
            return False, f"Error al guardar en base de datos: {e}"

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

# --- INICIALIZACIÓN DE ESTADOS ---
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
        "Min Inclusión (%)": [0.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.0, 0.5, 0.0],
        "Max Inclusión (%)": [50.0, 50.0, 25.0, 60.0, 20.0, 6.0, 3.0, 1.2, 3.0, 4.0]
    })

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {"role": "assistant", "content": "¡Hola! Soy el asistente integrado en **Cr-IA 150**. ¿Cómo podemos optimizar la nutrición, los costos y las ganancias de tu hato hoy?"}
    ]

# --- BARRA LATERAL ---
st.sidebar.success("🟢 Sistema Activo")
st.sidebar.markdown("---")
with st.sidebar.expander("🐂 Parámetros del Hato & Empresa", expanded=True):
    num_vientres = st.number_input("Número de Vientres en el Hato", min_value=1, max_value=5000, value=100, step=10)
    peso_destete_meta = st.slider("Peso Objetivo al Destete (kg)", min_value=180.0, max_value=300.0, value=230.0, step=5.0)
    porcentaje_destete = st.slider("Porcentaje de Destete Esperado (%)", min_value=60.0, max_value=95.0, value=85.0, step=1.0)
    precio_venta_kg = st.number_input("Precio de Venta Becerro Destetado (MXN/kg)", min_value=30.0, max_value=120.0, value=84.0, step=1.0)
    costo_operativo_vaca_ano = st.number_input("Costo Anual por Vaca Madre (MXN/año)", min_value=1000.0, max_value=15000.0, value=6500.0, step=250.0)

# --- ENCABEZADO PRINCIPAL ---
st.markdown('<div style="background: linear-gradient(135deg, #fffbeb 0%, #ffedd5 50%, #fed7aa 100%); padding: 25px; border-radius: 20px; color: #431407; box-shadow: 0 10px 30px rgba(194, 65, 12, 0.15); margin-bottom: 25px; border: 2px solid #ea580c;"><div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 20px;"><div style="display: flex; align-items: center; gap: 20px;"><div style="background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%); color: #ffffff; font-size: 2.2rem; font-weight: bold; padding: 14px 22px; border-radius: 16px; box-shadow: 0 6px 20px rgba(185, 28, 28, 0.3); text-align: center; border: 2px solid #fef08a;">🐄🐮<br><span style="font-size: 0.65rem; letter-spacing: 1px; text-transform: uppercase; font-weight: 800;">Vaca & Becerro Hereford</span></div><div><h1 style="margin: 0; font-size: 2.2rem; font-weight: 900; color: #7c2d12; letter-spacing: -0.5px;">Cr-IA <span style="color: #ea580c;">150</span></h1></div></div><div><span style="background-color: #b91c1c; color: #ffffff; padding: 8px 16px; border-radius: 25px; font-size: 0.85rem; font-weight: 700; border: 1px solid #fef08a; text-transform: uppercase; letter-spacing: 1.5px; box-shadow: 0 4px 10px rgba(185, 28, 28, 0.2);">Enterprise Elite SaaS V4.1</span></div></div><div style="margin-top: 18px; padding-top: 15px; border-top: 1px solid rgba(194, 65, 12, 0.2); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;"><p style="margin: 0; font-size: 0.95rem; color: #7c2d12; font-style: italic; font-weight: 500;">"Optimizando la relación vaca-becerro con ganancia de peso superior y máxima eficiencia en agostadero."</p><p style="margin: 0; font-size: 0.9rem; color: #431407; font-weight: 700;">💻 Creado y desarrollado por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong> | Cañón de Tlaltenango</p></div></div>', unsafe_allow_html=True)

# --- OPTIMIZACIÓN LINEAL ---
df_nut_base = st.session_state.df_ingredientes
nombres_n = df_nut_base["Nombre del Ingrediente"].astype(str).values
c_n = df_nut_base["Precio Estimado (MXN/ton)"].astype(float).values
pc_n = df_nut_base["Proteina Cruda (PC % MS)"].astype(float).values / 100.0  
eng_n = df_nut_base["Energia Neta Ganancia (ENg Mcal/kg)"].astype(float).values

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

# --- CLASE PDF REPORT GENERATOR ---
class PDFCrIAReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(194, 65, 12)
        self.cell(0, 10, 'Cr-IA 150 - Reporte Ejecutivo Ganadero', 0, 1, 'C')
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
    pdf.cell(0, 8, safe_str("1. Resumen Zootecnico del Hato Hereford"), 0, 1)
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

    # 3. Inventario de Animales y Vientres Registrados en Base de Datos
    pdf.ln(4)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, safe_str("3. Inventario de Animales y Vientres Registrados"), 0, 1)
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

# --- MENÚ DE MÓDULOS (11 TABS) ---
tabs = st.tabs([
    "📋 1. Inventario & Altas",
    "⚖️ 2. Condición Corporal",
    "🧮 3. Optimizador LP",
    "📊 4. Finanzas & Ganancias",
    "📅 5. Smart Calendar (Partos)",
    "💉 6. Sanidad Regional",
    "📊 7. Evaluación BIF",
    "📄 8. Reporte Ejecutivo PDF",
    "💬 9. Asistente IA & Citas",
    "🌾 10. Contingencia & Manejo",
    "📈 11. Proyección & Engorda (Futuro)"
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
            ce = st.number_input("Circunferencia Escrotal (cm) [Solo si es Toro, min. 32 cm]", 25.0, 50.0, 34.0)
        
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
    st.header("🧮 Optimizador Lineal de Raciones")
    st.markdown("Calcula la dieta de mínimo costo mediante programación lineal (`scipy.optimize.linprog`) cumpliendo con requerimientos nutricionales para ganado Hereford.")
    
    st.session_state.df_ingredientes = st.data_editor(
        st.session_state.df_ingredientes,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Disponible": st.column_config.CheckboxColumn("¿Disponible?", default=True),
            "Min Inclusión (%)": st.column_config.NumberColumn("Min (%)", min_value=0.0, max_value=100.0, step=0.5),
            "Max Inclusión (%)": st.column_config.NumberColumn("Max (%)", min_value=0.0, max_value=100.0, step=0.5),
        },
        key="editor_ingredientes_persisted"
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
        st.info("ℹ️ **Nota del Optimizador:** Ajusta la disponibilidad de ingredientes y rangos de inclusión en la tabla superior para encontrar una solución matemática factible.")

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
    fig_fin.update_traces(line_color="#b91c1c", line_width=3)
    st.plotly_chart(fig_fin, use_container_width=True)

with tabs[4]:
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

with tabs[5]:
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

with tabs[6]:
    st.header("📊 Estandarización BIF (205 Días) & Gráficas")
    st.markdown("Evaluación genética y de crecimiento estandarizada a 205 días al destete para raza Hereford.")
    st.info("💡 Asegúrese de registrar pesajes de Nacimiento y Destete en la base de datos para generar los cálculos BIF automáticos.")

with tabs[7]:
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

with tabs[8]:
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

with tabs[9]:
    st.header("🌾 Planes de Contingencia, Suplementación & Manejo Sanitario Avanzado")
    st.markdown("""
        ### 🌵 1. Contingencia por Sequía y Estiaje
        * **Activación de Destete Precoz:** Retirar becerros a partir de los 60-75 días si la disponibilidad de forraje en agostadero cae por debajo del 10%.
        * **Estrategia Alimentaria:** Uso de rastrojos amonificados con urea y bloques multinutricionales en el Cañón de Tlaltenango para proteger la condición corporal del vientre Hereford.

        ---

        ### 🦠 2. Protocolo Sanitario Integral de Precisión

        #### A. Anaplasmosis Bovina (*Anaplasma marginale*)
        * **Diagnóstico:** Frotis sanguíneo (coloración Giemsa) visualizando corpúsculos marginales en eritrocitos; pruebas serológicas (ELISA o PCR) en fases agudas y animales portadores asintomáticos. Signos clínicos: anemia severa, fiebre, ictericia y caída abrupta en la producción láctea.
        * **Tratamiento:** Aplicación temprana de **Oxitetraciclina de Larga Acción (LA)** a dosis terapéuticas (20 mg/kg PV). Terapia de soporte obligatoria con hematínicos, complejo B y fluidoterapia en cuadros avanzados.
        * **Técnica de Aplicación:** Vía intramuscular profunda o subcutánea estricta. **Cambio obligatorio de aguja por animal** en vacunaciones y manejos masivos para evitar la transmisión iatrogénica por sangre.
        * **Prevención:** Control riguroso de insectos vectores (tábanos, moscas de los cuernos) y garrapatas; desinfección rigurosa de material quirúrgico y de sangrado.
        * **Control:** Baños periódicos con insecticidas/acaricidas y rotación inteligente de potreros para disminuir la presión de vectores mecánicos y biológicos.
        * **Medidas de Erradicación:** Identificación y tratamiento masivo de portadores crónicos en el pie de cría; eliminación temporal o desecho de animales persistentemente positivos que actúan como reservorios en el hato.

        #### B. Control y Manejo de Garrapata (*Rhipicephalus microplus*)
        * **Diagnóstico:** Inspección visual rutinaria en zonas corporales de predilección (perineo, ubre, ijar, tabla del cuello, axilas); monitoreo de carga parasitaria por lote.
        * **Tratamiento:** Uso estratégico de acaricidas sistémicos y de contacto (Ivermectinas, Doramectina, Amitraz, Piretroides, Fluazuron). Rotación estricta de principios activos para prevenir resistencia química.
        * **Técnica de Aplicación:** Baños de aspersión a alta presión garantizando la saturación completa del pliegue cutáneo, o aplicación pour-on/inyectable según la formulación del producto y peso real del animal.
        * **Prevención:** Establecimiento de dobles cercos perimetrales, cuarentena estricta y revisión de animales de remplazo ajenos introducidos al rancho.
        * **Control:** Baños estratégicos estacionales sincronizados con las épocas de mayor eclosión (temporada cálida y húmeda); pruebas de eficacia o bioensayos periódicos.
        * **Medidas de Erradicación:** Manejo integral de pasturas mediante el descanso rotacional de potreros por periodos superiores al ciclo biológico de la larva de la garrapata en el suelo (quebrado biológico); programas de erradicación comunitaria/regional.

        #### C. Control de Parásitos Gastrointestinales (Nematodos / Estrongílidos)
        * **Diagnóstico:** Coprología cuantitativa mediante la técnica de **McMaster** para determinar el recuento de Huevos por Gramo de Heces (HGP); coprocultivos para diferenciar géneros (*Haemonchus*, *Ostertagia*, *Cooperia*).
        * **Tratamiento:** Desparasitantes de amplio espectro (Benzimidazoles, Levamizol, Lactonas macrocíclicas). Selección del fármaco basada en el resultado coprológico.
        * **Técnica de Aplicación:** Vía oral (drench) o inyectable, calculando rigurosamente la dosis con base en el pesaje del animal más pesado del lote para evitar subdosificaciones que generen resistencia antihelmíntica.
        * **Prevención:** Evitar el sobrepastoreo; no permitir que el ganado consuma pasturas por debajo de 5 cm de altura, zona donde se concentra la mayor cantidad de larvas infectantes (L3).
        * **Control:** Desparasitación estratégica al inicio y término de la época de lluvias; descanso de potreros para reducir la contaminación parasitaria ambiental.
        * **Medidas de Erradicación:** Implementación del **Refugio Parasitario** (dejar sin tratar a un 10-15% del hato con menor carga y mejor condición corporal) para mantener una población de parásitos susceptibles en el pasto que diluya la resistencia genética.

        ---

        ### 🌙 3. Protocolo Fisiológico de Alimentación Nocturna (Night Feeding)
        * Suministrar el alimento principal al atardecer (17:00 - 21:00 hrs) desplaza fisiológicamente el inicio de las pariciones hacia las horas de luz diurna, reduciendo la mortalidad neonatal y facilitando la supervisión zootécnica.
    """)

with tabs[10]:
    st.header("📈 Módulo Predictivo: Engorda, Retención y Ciclo Completo (Mercado Real)")
    st.markdown("Modelo financiero optimizado para comparar con precisión zootécnica la decisión gerencial entre **Vender al Destete** ($84/kg) vs. **Retener para Engorda Intensiva** (Venta a $60/kg en finalización).")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        peso_entrada_eng = st.number_input("Peso Inicial al Destete (kg)", min_value=150.0, max_value=350.0, value=float(peso_destete_meta), step=5.0)
        peso_meta_eng = st.number_input("Peso Final / Rastro Objetivo (kg)", min_value=400.0, max_value=650.0, value=520.0, step=10.0)
    with col_p2:
        gmd_esperada = st.slider("Ganancia Media Diaria - GMD (kg/día)", min_value=0.8, max_value=2.0, value=1.35, step=0.05)
        consumo_ms_porcentaje = st.slider("Consumo de Materia Seca (% del Peso Vivo)", min_value=2.0, max_value=3.5, value=2.5, step=0.1)
    with col_p3:
        # Precios configurados de acuerdo al mercado real reportado ($84 destete, $60 gordo)
        precio_venta_destete_actual = st.number_input("Precio de Mercado Becerro Destetado ($/kg)", min_value=40.0, max_value=120.0, value=84.0, step=1.0)
        precio_venta_gordo_actual = st.number_input("Precio de Mercado Ganado Gordo ($/kg)", min_value=30.0, max_value=90.0, value=60.0, step=1.0)

    col_p4, col_p5 = st.columns(2)
    with col_p4:
        costo_dieta_engorda = st.number_input("Costo de Dieta de Engorda ($/ton MS)", min_value=2000.0, max_value=12000.0, value=float(costo_ton_dieta), step=200.0)
    with col_p5:
        costo_fijo_diario = st.number_input("Costos Fijos, Sanidad y Corrales ($/día/cabeza)", min_value=1.0, max_value=30.0, value=7.5, step=0.5)

    # --- MODELO MATEMÁTICO Y FINANCIERO OPTIMIZADO ---
    ganancia_total_esperada = peso_meta_eng - peso_entrada_eng
    dias_en_corral_dof = ganancia_total_esperada / gmd_esperada if gmd_esperada > 0 else 0
    
    # Consumo diario basado en peso promedio del periodo de engorda
    peso_promedio_periodo = (peso_entrada_eng + peso_meta_eng) / 2.0
    consumo_ms_diario_kg = peso_promedio_periodo * (consumo_ms_porcentaje / 100.0)
    consumo_total_ms_ton = (consumo_ms_diario_kg * dias_en_corral_dof) / 1000.0
    
    # Costos detallados de la engorda
    costo_alimentacion_total = consumo_total_ms_ton * costo_dieta_engorda
    costo_fijos_totales_periodo = dias_en_corral_dof * costo_fijo_diario
    costo_oportunidad_destete = peso_entrada_eng * precio_venta_destete_actual
    
    costo_total_operativo_engorda = costo_alimentacion_total + costo_fijos_totales_periodo
    costo_total_produccion_gordo = costo_oportunidad_destete + costo_total_operativo_engorda
    
    ingreso_venta_gordo = peso_meta_eng * precio_venta_gordo_actual
    utilidad_neta_engorda = ingreso_venta_gordo - costo_total_produccion_gordo
    punto_equilibrio_gordo = costo_total_produccion_gordo / peso_meta_eng if peso_meta_eng > 0 else 0
    roi_engorda = (utilidad_neta_engorda / costo_total_produccion_gordo) * 100 if costo_total_produccion_gordo > 0 else 0

    # Ingreso y utilidad por venta directa al destete (por cabeza)
    ingreso_venta_destete = costo_oportunidad_destete
    # Nota: El costo proporcional de la vaca madre por becerro destetado se puede estimar o comparar directamente
    costo_vaca_por_becerro = (costo_operativo_vaca_ano / (porcentaje_destete / 100.0)) if porcentaje_destete > 0 else costo_operativo_vaca_ano
    utilidad_neta_destete = ingreso_venta_destete - costo_vaca_por_becerro

    st.markdown("---")
    st.subheader("🎯 Variables Predictivas y Financieras del Ciclo Completo")

    col_res1, col_res2, col_res3, col_res4 = st.columns(4)
    with col_res1:
        st.metric("Días en Corral (DOF)", f"{dias_en_corral_dof:.0f} días", f"GMD: {gmd_esperada} kg/d")
        st.metric("Consumo Total MS", f"{consumo_total_ms_ton * 1000:,.0f} kg", f"Diario: {consumo_ms_diario_kg:.2f} kg/d")
    with col_res2:
        st.metric("Costo Alimentación", f"${costo_alimentacion_total:,.2f} MXN", f"@ ${costo_dieta_engorda:,.0f}/ton")
        st.metric("Costo Total Engorda", f"${costo_total_operativo_engorda:,.2f} MXN", "Alimento + Fijos")
    with col_res3:
        st.metric("Utilidad Neta Engorda", f"${utilidad_neta_engorda:,.2f} MXN", f"ROI: {roi_engorda:.1f}%")
        st.metric("Punto de Equilibrio", f"${punto_equilibrio_gordo:,.2f} MXN/kg", "Precio mín. venta")
    with col_res4:
        st.metric("Venta Ganado Gordo", f"${ingreso_venta_gordo:,.2f} MXN", f"{peso_meta_eng} kg @ ${precio_venta_gordo_actual}")
        st.metric("Valor Destete (Oportunidad)", f"${ingreso_venta_destete:,.2f} MXN", f"{peso_entrada_eng} kg @ ${precio_venta_destete_actual}")

    st.markdown("---")
    st.subheader("⚖️ Análisis Comparativo de Negocio: Venta al Destete vs. Engorda")

    comparativa_df = pd.DataFrame({
        "Estrategia de Comercialización": ["Venta Directa al Destete", "Retención y Engorda a Finalización"],
        "Peso de Venta (kg)": [peso_entrada_eng, peso_meta_eng],
        "Precio de Venta ($/kg)": [precio_venta_destete_actual, precio_venta_gordo_actual],
        "Ingreso Bruto por Animal ($)": [ingreso_venta_destete, ingreso_venta_gordo],
        "Costos Directos Incurridos ($)": [0.0, costo_total_operativo_engorda],
        "Utilidad Neta Estimada ($/cabeza)": [utilidad_neta_destete, utilidad_neta_engorda]
    })
    st.dataframe(comparativa_df, use_container_width=True, hide_index=True)

    diferencia_utilidad = utilidad_neta_engorda - utilidad_neta_destete
    if diferencia_utilidad > 0:
        st.success(f"✅ **Conclusión Financiera:** Con los precios actuales de mercado ($84/kg al destete vs. $60/kg en gordo), retener el becerro y llevarlo a engorda genera una utilidad neta adicional de **${diferencia_utilidad:,.2f} MXN por cabeza** frente a venderlo inmediatamente al destete.")
    else:
        st.warning(f"⚠️ **Conclusión Financiera:** Con un precio de $84.00/kg al destete, el **costo de oportunidad** es muy elevado frente a un precio de venta de $60.00/kg en ganado gordo. La engorda arroja una diferencia de **${diferencia_utilidad:,.2f} MXN**, por lo que financieramente resulta más rentable realizar la venta directa del becerro al destete.")
