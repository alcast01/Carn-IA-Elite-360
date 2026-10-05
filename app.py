import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA Elite 360 | Cañón de Tlaltenango",
    page_icon="🐄",
    layout="wide"
)

# --- CLASE DE GESTIÓN Y LÓGICA DE DATOS ---
class GanaderiaTlaltenangoApp:
    def __init__(self, db_name="tlaltenango_elite_carne.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._crear_tablas()

    def _crear_tablas(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS animales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                siniiga TEXT UNIQUE,
                sexo TEXT,
                fecha_nacimiento TEXT,
                edad_madre_anos REAL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pesajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                animal_id INTEGER,
                tipo_pesaje TEXT,
                fecha_pesaje TEXT,
                peso_kg REAL,
                FOREIGN KEY (animal_id) REFERENCES animales (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS nutricion_registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_nombre TEXT,
                etapa_fisiologica TEXT,
                peso_promedio REAL,
                condicion_estacional TEXT,
                suplemento_recomendado TEXT,
                fecha TEXT
            )
        ''')
        self.conn.commit()

    def registrar_animal(self, siniiga, sexo, fecha_nacimiento, edad_madre_anos):
        try:
            self.cursor.execute('''
                INSERT INTO animales (siniiga, sexo, fecha_nacimiento, edad_madre_anos)
                VALUES (?, ?, ?, ?)
            ''', (siniiga, sexo.upper(), fecha_nacimiento, edad_madre_anos))
            self.conn.commit()
            return True, "Animal registrado exitosamente."
        except sqlite3.IntegrityError:
            return False, f"El SINIIGA {siniiga} ya se encuentra registrado."

    def registrar_pesaje(self, animal_id, tipo_pesaje, fecha_pesaje, peso_kg):
        self.cursor.execute('''
            INSERT INTO pesajes (animal_id, tipo_pesaje, fecha_pesaje, peso_kg)
            VALUES (?, ?, ?, ?)
        ''', (animal_id, tipo_pesaje.upper(), fecha_pesaje, peso_kg))
        self.conn.commit()

    def obtener_animales(self):
        return pd.read_sql("SELECT * FROM animales", self.conn)

    def guardar_registro_nutricion(self, lote, etapa, peso, estacion, suplemento):
        self.cursor.execute('''
            INSERT INTO nutricion_registros (lote_nombre, etapa_fisiologica, peso_promedio, condicion_estacional, suplemento_recomendado, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (lote, etapa, peso, estacion, suplemento, str(datetime.now().date())))
        self.conn.commit()

    def calcular_evaluacion_destete(self, animal_id):
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
        factor_sexo = 1.05 if sexo == 'HEMBRA' else 1.00
        
        if edad_madre < 3.0:
            factor_madre = 1.10
        elif edad_madre > 10.0:
            factor_madre = 1.05
        else:
            factor_madre = 1.00

        peso_ajustado_final = pa_205_base * factor_sexo * factor_madre

        return {
            "dias_al_destete": dias_edad,
            "gdp_kg_dia": round(gdp, 3),
            "peso_ajustado_205": round(peso_ajustado_final, 2)
        }

# Inicializar Base de Datos
db = GanaderiaTlaltenangoApp()

# --- INTERFAZ DE USUARIO (STREAMLIT) ---
st.title("🐄 Cr-IA Elite 360")
st.subheader("Gestión Integral de Ganado de Carne - Cañón de Tlaltenango, Zacatecas")

menu = [
    "Registrar Animal", 
    "Capturar Pesajes", 
    "Evaluación Individual", 
    "Evaluación y Clasificación de Lotes",
    "Nutrición y Raciones Regionales"
]
choice = st.sidebar.selectbox("Navegación del Hato", menu)

if choice == "Registrar Animal":
    st.header("📝 Registro de Nueva Cría / Pie de Cría")
    with st.form("form_animal"):
        siniiga = st.text_input("Número SINIIGA o Identificador Oficial")
        sexo = st.selectbox("Sexo", ["MACHO", "HEMBRA"])
        fecha_nacimiento = st.date_input("Fecha de Nacimiento")
        edad_madre = st.number_input("Edad de la Madre al Parto (Años)", min_value=1.5, max_value=15.0, value=4.0, step=0.5)
        
        submitted = st.form_submit_button("Guardar Animal")
        if submitted:
            if siniiga:
                exito, mensaje = db.registrar_animal(siniiga, sexo, str(fecha_nacimiento), edad_madre)
                if exito:
                    st.success(mensaje)
                else:
                    st.warning(mensaje)
            else:
                st.error("Por favor ingrese un SINIIGA válido.")

elif choice == "Capturar Pesajes":
    st.header("⚖️ Registro en Báscula")
    df_animales = db.obtener_animales()
    
    if df_animales.empty:
        st.info("Primero debe registrar animales en el sistema.")
    else:
        animal_dict = {f"{row['siniiga']} ({row['sexo']})": row['id'] for _, row in df_animales.iterrows()}
        animal_seleccionado = st.selectbox("Seleccione el Animal", list(animal_dict.keys()))
        animal_id = animal_dict[animal_seleccionado]
        
        with st.form("form_pesaje"):
            tipo_pesaje = st.selectbox("Tipo de Pesaje", ["NACIMIENTO", "DESTETE"])
            fecha_pesaje = st.date_input("Fecha del Pesaje")
            peso_kg = st.number_input("Peso en Kilogramos (kg)", min_value=10.0, max_value=800.0, value=40.0)
            
            submitted_p = st.form_submit_button("Registrar Báscula")
            if submitted_p:
                db.registrar_pesaje(animal_id, tipo_pesaje, str(fecha_pesaje), peso_kg)
                st.success(f"Pesaje de {tipo_pesaje} guardado correctamente ({peso_kg} kg).")

elif choice == "Evaluación Individual":
    st.header("📊 Evaluación Zootécnica Individual")
    df_animales = db.obtener_animales()
    
    if df_animales.empty:
        st.info("No hay animales registrados.")
    else:
        animal_dict = {f"{row['siniiga']} ({row['sexo']})": row['id'] for _, row in df_animales.iterrows()}
        animal_seleccionado = st.selectbox("Seleccione animal para evaluar", list(animal_dict.keys()))
        animal_id = animal_dict[animal_seleccionado]
        
        if st.button("Calcular Índices Productivos"):
            res = db.calcular_evaluacion_destete(animal_id)
            if res:
                col1, col2, col3 = st.columns(3)
                col1.metric("Días al Destete", f"{res['dias_al_destete']} días")
                col2.metric("Ganancia Diaria (GDP)", f"{res['gdp_kg_dia']} kg/día")
                col3.metric("Peso Ajustado 205 Días", f"{res['peso_ajustado_205']} kg")
            else:
                st.warning("Faltan datos de pesaje (Nacimiento y/o Destete) para este animal.")

elif choice == "Evaluación y Clasificación de Lotes":
    st.header("🏆 Evaluación Global del Hato y Clasificación por Índice")
    df_animales = db.obtener_animales()
    
    if df_animales.empty:
        st.info("No hay suficientes datos en el hato para realizar una evaluación global.")
    else:
        resultados_lote = []
        for _, row in df_animales.iterrows():
            res = db.calcular_evaluacion_destete(row['id'])
            if res:
                resultados_lote.append({
                    "SINIIGA": row['siniiga'],
                    "Sexo": row['sexo'],
                    "Edad Madre (años)": row['edad_madre_anos'],
                    "Días Destete": res['dias_al_destete'],
                    "GDP (kg/día)": res['gdp_kg_dia'],
                    "Peso Ajustado 205 kg": res['peso_ajustado_205']
                })
        
        if len(resultados_lote) > 0:
            df_lote = pd.DataFrame(resultados_lote)
            media_lote = df_lote["Peso Ajustado 205 kg"].mean()
            desviacion_lote = df_lote["Peso Ajustado 205 kg"].std() if len(df_lote) > 1 else 0

            def clasificar_animal(peso):
                if pd.isna(desviacion_lote) or desviacion_lote == 0:
                    return "Promedio"
                if peso >= (media_lote + 0.5 * desviacion_lote):
                    return "⭐ Superior (Reemplazo / Destacado)"
                elif peso <= (media_lote - 0.5 * desviacion_lote):
                    return "⚠️ Inferior (Revisar Vientre)"
                else:
                    return "✔️ Promedio del Hato"

            df_lote["Clasificación Genética"] = df_lote["Peso Ajustado 205 kg"].apply(clasificar_animal)
            st.metric("Promedio del Peso Ajustado del Hato", f"{round(media_lote, 2)} kg")
            st.dataframe(df_lote, use_container_width=True)
        else:
            st.info("Ningún animal cuenta con los registros completos de Nacimiento y Destete.")

elif choice == "Nutrición y Raciones Regionales":
    st.header("🌾 Módulo Nutricional Estratégico (Cañón de Tlaltenango)")
    st.markdown("Simulación de requerimientos de Consumo de Materia Seca (CMS) y formulación de suplementación basada en **recursos locales** (agostadero y esquilmos agrícolas).")

    with st.form("form_nutricion"):
        lote_nombre = st.text_input("Nombre del Lote de Ganado", value="Vacas Vientre - Agostadero Principal")
        etapa = st.selectbox("Etapa Fisiológica", [
            "Gestación Avanzada (Último Tercio)", 
            "Lactancia Temprana (0 - 90 días postparto)", 
            "Mantenimiento / Vaca Horra", 
            "Vaquillas de Reemplazo en Crecimiento"
        ])
        peso_promedio = st.number_input("Peso Vivo Promedio del Lote (kg)", min_value=300.0, max_value=700.0, value=450.0)
        estacion = st.selectbox("Condición Estacional Actual", ["Estiaje / Secas (Agostadero seco + Rastrojo)", "Lluvias / Temporal (Pastizal verde abundante)"])
        
        submitted_nut = st.form_submit_button("Simular Requerimientos y Dieta")

    if submitted_nut:
        # Cálculo estimado de Consumo de Materia Seca (CMS) como porcentaje del peso vivo según etapa
        if "Lactancia" in etapa:
            porcentaje_cms = 0.026  # 2.6% del PV
        elif "Gestación Avanzada" in etapa:
            porcentaje_cms = 0.022  # 2.2% del PV
        elif "Crecimiento" in etapa:
            porcentaje_cms = 0.025  # 2.5% del PV
        else:
            porcentaje_cms = 0.020  # 2.0% del PV

        cms_total = peso_promedio * porcentaje_cms

        st.success("Simulación Nutricional Generada Correctamente")
        
        col1, col2 = st.columns(2)
        col1.metric("Consumo de Materia Seca (CMS) Esperado", f"{round(cms_total, 2)} kg/día")
        col2.metric("Consumo como % del Peso Vivo", f"{porcentaje_cms * 100}%")

        st.subheader("📋 Recomendación de Suplementación Local")
        
        if "Estiaje" in estacion:
            suplemento = "Base de Rastrojo de Maíz ad libitum + 1.5 a 2.0 kg/día de suplemento energético-proteico (Melaza + Grano local / Pasta) y Bloque Mineral con Fósforo."
            st.warning("⚠️ **Condición de Estiaje detectada:** El agostadero local tiene baja proteína (< 6%). Es crítico aportar nitrógeno no proteico o proteína verdadera para mantener la actividad celulolítica de la panza y evitar caídas en la condición corporal.")
        else:
            suplemento = "Pastoreo exclusivo en agostadero verde de temporal + Mezcla de Sales Minerales con micro minerales."
            st.info("✔️ **Época de Lluvias detectada:** El pastizal nativo cubre los requerimientos de mantenimiento y gestación media. Solo asegurar libre acceso a minerales completos.")

        st.markdown(f"**Dieta Sugerida para el Lote:** {suplemento}")
        
        # Guardar en base de datos local
        db.guardar_registro_nutricion(lote_nombre, etapa, peso_promedio, estacion, suplemento)
