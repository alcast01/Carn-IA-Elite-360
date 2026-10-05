import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA 150 | Sistema de Vaca-Cría Avanzado",
    page_icon="🐂",
    layout="wide"
)

# --- CLASE DE GESTIÓN Y LÓGICA CIENTÍFICA DE DATOS ---
class CrIA150Avangard:
    def __init__(self, db_name="cria_150_cientifica.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._crear_tablas()

    def _crear_tablas(self):
        # Animales / Vientres, Toros y Crías
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS animales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siniiga TEXT UNIQUE,
                arete_propio TEXT,
                categoria TEXT, -- 'VIENTRE (VACA)', 'REEMPLAZO (VAQUILLA)', 'CRIA', 'TORO REPRODUCTOR'
                raza TEXT,
                sexo TEXT,
                fecha_nacimiento TEXT,
                edad_madre_anos REAL,
                circunferencia_escrotal REAL DEFAULT NULL -- Específico para toros
            )
        ''')
        # Pesajes y Condición Corporal detallada (Escala 1-9 BIF)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pesajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER,
                tipo_pesaje TEXT, -- 'NACIMIENTO', 'DESTETE', 'PREPARTO', 'EMPADRE'
                fecha_pesaje TEXT,
                peso_kg REAL,
                condicion_corporal INTEGER, -- Escala 1 a 9 (Objetivo parto: 5-6)
                FOREIGN KEY (animal_id) REFERENCES animales (id)
            )
        ''')
        # Reproducción y Anestro Postparto
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reproduccion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER,
                tipo_evento TEXT, -- 'EMPADRE / SERVICIO', 'DIAGNOSTICO GESTACION', 'PARTO'
                fecha_evento TEXT,
                resultado TEXT, -- 'PREÑADA', 'VACÍA', 'PARTO NORMAL', 'DISTOCIA'
                observaciones TEXT,
                FOREIGN KEY (animal_id) REFERENCES animales (id)
            )
        ''')
        # Sanidad Regional (Derriengue, Clostridios, etc.)
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
        self.conn.commit()

    def registrar_animal(self, siniiga, arete, categoria, raza, sexo, fecha_nac, edad_madre, ce):
        try:
            self.cursor.execute('''
                INSERT INTO animales (siniiga, arete_propio, categoria, raza, sexo, fecha_nacimiento, edad_madre_anos, circunferencia_escrotal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (siniiga, arete, categoria, raza, sexo.upper(), fecha_nac, edad_madre, ce))
            self.conn.commit()
            return True, "Registro científico guardado con éxito en Cr-IA 150."
        except sqlite3.IntegrityError:
            return False, f"El SINIIGA {siniiga} ya se encuentra registrado."

    def registrar_pesaje(self, animal_id, tipo, fecha, peso, cc):
        self.cursor.execute('''
            INSERT INTO pesajes (animal_id, tipo_pesaje, fecha_pesaje, peso_kg, condicion_corporal)
            VALUES (?, ?, ?, ?, ?)
        ''', (animal_id, tipo.upper(), fecha, peso, cc))
        self.conn.commit()

    def registrar_reproduccion(self, animal_id, tipo_evento, fecha, resultado, obs):
        self.cursor.execute('''
            INSERT INTO reproduccion (animal_id, tipo_evento, fecha_evento, resultado, observaciones)
            VALUES (?, ?, ?, ?, ?)
        ''', (animal_id, tipo_evento, fecha, resultado, obs))
        self.conn.commit()

    def registrar_sanidad(self, animal_id, tratamiento, fecha, prox):
        self.cursor.execute('''
            INSERT INTO sanidad (animal_id, tipo_tratamiento, fecha_aplicacion, proxima_dosis)
            VALUES (?, ?, ?, ?, ?)
        ''', (animal_id, tratamiento, fecha, prox))
        self.conn.commit()

    def obtener_animales(self):
        return pd.read_sql("SELECT * FROM animales", self.conn)

    def evaluar_destete_bif(self, animal_id):
        self.cursor.execute("SELECT sexo, fecha_nacimiento, edad_madre_anos FROM animales WHERE id = ?", (animal_id,))
        animal = self.cursor.fetchone()
        if not animal:
            return None

        sexo, fecha_nac_str, edad_madre = animal
        fecha_nac = datetime.strptime(fecha_nac_str, "%Y-%m-%d")

        self.cursor.execute("SELECT tipo_pesaje, fecha_pesaje, peso_kg FROM pesajes WHERE animal_id = ?", (animal_id,))
        pesajes = self.cursor.fetchall()
        
        peso_nacer, peso_destete, dias_edad = None, None, None
        for tipo, fecha_p_str, peso in pesajes:
            if tipo == 'NACIMIENTO':
                peso_nacer = peso
            elif tipo == 'DESTETE':
                peso_destete = peso
                fecha_p = datetime.strptime(fecha_p_str, "%Y-%m-%d")
                dias_edad = (fecha_p - fecha_nac).days

        if not peso_nacer or not peso_destete or not dias_edad or dias_edad <= 0:
            return None

        gdp = (peso_destete - peso_nacer) / dias_edad
        pa_205_base = (gdp * 205) + peso_nacer
        
        # Factores de corrección BIF por sexo y edad de madre
        factor_sexo = 1.05 if sexo == 'HEMBRA' else 1.00
        if edad_madre < 3.0:
            factor_madre = 1.10
        elif edad_madre > 10.0:
            factor_madre = 1.05
        else:
            factor_madre = 1.00

        peso_ajustado_final = pa_205_base * factor_sexo * factor_madre

        return {
            "dias": dias_edad,
            "gdp": round(gdp, 3),
            "peso_205": round(peso_ajustado_final, 2)
        }

db = CrIA150Avangard()

# --- INTERFAZ DE USUARIO ---
st.title("🐂 Cr-IA 150")
st.subheader("Plataforma Zootécnica Basada en Evidencia | Cañón de Tlaltenango, Zac.")

menu = [
    "Inventario y Altas", 
    "Control de Condición Corporal (CC 1-9)", 
    "Gestión Reproductiva y Anestro", 
    "Sanidad Integral Regional",
    "Evaluación BIF (205 Días)",
    "Protocolo de Parto y Alimentación Nocturna"
]
choice = st.sidebar.selectbox("Módulos Científicos Hato", menu)

if choice == "Inventario y Altas":
    st.header("📝 Alta de Reproductor / Vientre / Cría")
    with st.form("form_alta_avanzada"):
        col1, col2 = st.columns(2)
        with col1:
            siniiga = st.text_input("SINIIGA Oficial")
            arete = st.text_input("Arete Interno / Ganadería")
            categoria = st.selectbox("Categoría Zootécnica", ["VIENTRE (VACA)", "REEMPLAZO (VAQUILLA)", "CRIA", "TORO REPRODUCTOR"])
            raza = st.text_input("Composición Racial (ej. 3/4 Simmental 1/4 Brahman)")
        with col2:
            sexo = st.selectbox("Sexo", ["MACHO", "HEMBRA"])
            fecha_nacimiento = st.date_input("Fecha de Nacimiento")
            edad_madre = st.number_input("Edad de la Madre al Parto (Años)", 1.5, 15.0, 4.0, 0.5)
            ce = st.number_input("Circunferencia Escrotal (cm) [Solo si es Toro, min. 32 cm]", 25.0, 50.0, 34.0, help="Indicador de fertilidad propia y precocidad sexual en hijas.")
        
        sub = st.form_submit_button("Registrar en Base Científica")
        if sub:
            if siniiga:
                exito, msg = db.registrar_animal(siniiga, arete, categoria, raza, sexo, str(fecha_nacimiento), edad_madre, ce if categoria == "TORO REPRODUCTOR" else None)
                if exito: st.success(msg)
                else: st.warning(msg)
            else:
                st.error("El SINIIGA es obligatorio.")

elif choice == "Control de Condición Corporal (CC 1-9)":
    st.header("⚖️ Monitoreo de Condición Corporal y Estado Nutricional")
    st.markdown("La investigación en rumiantes demuestra que la CC al parto es el factor determinante absoluto del intervalo entre partos.")
    
    df = db.obtener_animales()
    if df.empty:
        st.info("Registre animales en el inventario.")
    else:
        dict_an = {f"{r['siniiga']} - {r['categoria']}": r['id'] for _, r in df.iterrows()}
        sel = st.selectbox("Seleccionar Animal", list(dict_an.keys()))
        id_sel = dict_an[sel]
        
        with st.form("form_cc"):
            tipo_p = st.selectbox("Momento Fisiológico de Evaluación", ["PREPARTO (Último Tercio)", "PARTO", "EMPADRE / SERVICIO", "DESTETE"])
            f_p = st.date_input("Fecha de Evaluación")
            peso = st.number_input("Peso vivo (kg)", 300.0, 900.0, 480.0)
            cc = st.slider("Condición Corporal (Escala BIF 1 a 9)", 1, 9, 5, help="1=Esquelética, 5-6=Óptima al parto, 9=Obesa.")
            
            sub_cc = st.form_submit_button("Registrar CC y Peso")
            if sub_cc:
                db.registrar_pesaje(id_sel, tipo_p, str(f_p), peso, cc)
                if cc < 5:
                    st.warning("⚠️ **Alerta Nutricional:** CC inferior al óptimo (5-6). Riesgo elevado de anestro prolongado postparto. Se requiere suplementación energética-proteica inmediata.")
                else:
                    st.success("✅ Condición corporal dentro de parámetros óptimos de eficiencia.")

elif choice == "Gestión Reproductiva y Anestro":
    st.header("🔄 Seguimiento Reproductivo y Eficiencia del Hato")
    df = db.obtener_animales()
    df_v = df[df['categoria'].isin(['VIENTRE (VACA)', 'REEMPLAZO (VAQUILLA)'])]
    
    if df_v.empty:
        st.info("No hay vientres registrados.")
    else:
        v_dict = {f"{r['siniiga']} ({r['raza']})": r['id'] for _, r in df_v.iterrows()}
        v_sel = st.selectbox("Vientre Seleccionado", list(v_dict.keys()))
        v_id = v_dict[v_sel]
        
        with st.form("form_repro_av"):
            evento = st.selectbox("Evento
