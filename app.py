import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA 150 | Sistema Integral Vaca-Cría",
    page_icon="🐂",
    layout="wide"
)

# --- CLASE DE GESTIÓN Y LÓGICA DE DATOS ---
class CrIA150Integral:
    def __init__(self, db_name="cria_150_integral.db"):
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

db = CrIA150Integral()

# --- INTERFAZ DE USUARIO ---
st.title("🐂 Cr-IA 150 - Sistema Integral Vaca-Cría")
st.subheader("Plataforma Inteligente, Económica y de Contingencia Ganadera")

menu = [
    "Inventario y Altas", 
    "Control de Condición Corporal (CC 1-9)", 
    "Calendario Gestación & Partos (*Smart Calendar*)", 
    "Sanidad Integral Regional",
    "Evaluación BIF (205 Días) & Gráficas",
    "Finanzas y Proyección de Mercado",
    "Suplementación y Crecimiento (Vaca-Becerro)",
    "Plan de Contingencia (Sequía & Enfermedades)",
    "Protocolo de Parto y Alimentación Nocturna"
]
choice = st.sidebar.selectbox("Módulos del Sistema", menu)

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
            ce = st.number_input("Circunferencia Escrotal (cm) [Solo si es Toro, min. 32 cm]", 25.0, 50.0, 34.0)
        
        sub = st.form_submit_button("Registrar en Base de Datos")
        if sub:
            if siniiga:
                exito, msg = db.registrar_animal(siniiga, arete, categoria, raza, sexo, str(fecha_nacimiento), edad_madre, ce if categoria == "TORO REPRODUCTOR" else None)
                if exito: st.success(msg)
                else: st.warning(msg)
            else:
                st.error("El SINIIGA es obligatorio.")

elif choice == "Control de Condición Corporal (CC 1-9)":
    st.header("⚖️ Monitoreo de Condición Corporal y Estado Nutricional")
    st.markdown("La CC al parto es el factor determinante absoluto del intervalo entre partos en agostadero.")
    
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
            cc = st.slider("Condición Corporal (Escala BIF 1 a 9)", 1, 9, 5)
            
            sub_cc = st.form_submit_button("Registrar CC y Peso")
            if sub_cc:
                db.registrar_pesaje(id_sel, tipo_p, str(f_p), peso, cc)
                if cc < 5:
                    st.warning("⚠️ Alerta Nutricional: CC inferior al óptimo (5-6). Riesgo elevado de anestro prolongado postparto.")
                else:
                    st.success("✅ Condición corporal dentro de parámetros óptimos.")

elif choice == "Calendario Gestación & Partos (*Smart Calendar*)":
    st.header("📅 Calendario Inteligente de Servicios y Partos")
    st.markdown("Cálculo automático de la fecha probable de parto (gestación bovina promedio de **283 días**) a partir del servicio.")
    
    df = db.obtener_animales()
    df_v = df[df['categoria'].isin(['VIENTRE (VACA)', 'REEMPLAZO (VAQUILLA)'])]
    
    if df_v.empty:
        st.info("No hay vientres registrados para empadre.")
    else:
        v_dict = {f"{r['siniiga']} ({r['raza']})": r['id'] for _, r in df_v.iterrows()}
        v_sel = st.selectbox("Vientre Seleccionado", list(v_dict.keys()))
        v_id = v_dict[v_sel]
        
        with st.form("form_smart_cal"):
            evento = st.selectbox("Evento Reproductivo", ["EMPADRE / SERVICIO", "DIAGNOSTICO GESTACION", "PARTO"])
            f_ev = st.date_input("Fecha del Evento")
            res = st.selectbox("Resultado / Estatus", ["PREÑADA", "VACÍA", "PARTO NORMAL", "DISTOCIA"])
            obs = st.text_area("Notas técnicas (ej. Toro semental, protocolo IATF)")
            
            sub_r = st.form_submit_button("Registrar y Calcular Fecha de Parto")
            if sub_r:
                f_parto = db.registrar_reproduccion(v_id, evento, str(f_ev), res, obs)
                if f_parto:
                    st.success(f"✅ Servicio registrado con éxito. **Fecha Probable de Parto estimada: {f_parto}** (programada a 283 días).")
                else:
                    st.success("✅ Evento reproductivo guardado correctamente.")

    st.divider()
    st.subheader("📋 Historial de Gestaciones Activas")
    df_repro = db.obtener_reproduccion()
    if not df_repro.empty:
        st.dataframe(df_repro[['siniiga', 'tipo_evento', 'fecha_evento', 'fecha_probable_parto', 'resultado', 'observaciones']], use_container_width=True)
    else:
        st.info("Sin registros reproductivos aún.")

elif choice == "Sanidad Integral Regional":
    st.header("💉 Calendario Zoosanitario (Zacatecas)")
    df = db.obtener_animales()
    if df.empty:
        st.info("Sin animales.")
    else:
        d_anim = {f"{r['siniiga']}": r['id'] for _, r in df.iterrows()}
        sel_an = st.selectbox("Seleccionar Animal o Lote", list(d_anim.keys()))
        id_a = d_anim[sel_an]
        
        with st.form("form_san_z"):
            trat = st.selectbox("Biológico / Tratamiento", [
                "VACUNA ANTIRRÁBICA / DERRIENGUE",
                "CLOSTRIDIOSIS (Pierna Negra)",
                "LEPTOSPIROSIS / IBR / BVD",
                "CONTROL PARASITARIO"
            ])
            f_ap = st.date_input("Fecha de Aplicación")
            f_prox = st.date_input("Próxima Dosis / Refuerzo Anual")
            
            if st.form_submit_button("Guardar Sanidad"):
                db.registrar_sanidad(id_a, trat, str(f_ap), str(f_prox))
                st.success("Sanidad registrada exitosamente.")

elif choice == "Evaluación BIF (205 Días) & Gráficas":
    st.header("📊 Estandarización BIF y Análisis Gráfico del Hato")
    df = db.obtener_animales()
    if df.empty:
        st.info("No hay datos suficientes.")
    else:
        res_list = []
        for _, r in df.iterrows():
            eval_res = db.evaluar_destete_bif(r['id'])
            if eval_res:
                res_list.append({
                    "SINIIGA": r['siniiga'],
                    "Sexo": r['sexo'],
                    "Edad Madre (años)": r['edad_madre_anos'],
                    "Días a Destete": eval_res['dias'],
                    "GDP (kg/día)": eval_res['gdp'],
                    "Peso Ajustado 205 Días (kg)": eval_res['peso_205']
                })
        if len(res_list) > 0:
            df_final = pd.DataFrame(res_list)
            st.metric("Promedio de Peso Ajustado al Destete (Hato)", f"{round(df_final['Peso Ajustado 205 Días (kg)'].mean(), 2)} kg")
            st.dataframe(df_final, use_container_width=True)
            
            st.subheader("📈 Gráfica de Distribución de Pesos al Destete (BIF 205)")
            st.bar_chart(df_final.set_index("SINIIGA")["Peso Ajustado 205 Días (kg)"])
        else:
            st.info("Registre pesajes de Nacimiento y Destete en los animales para calcular los ajustes BIF y generar gráficas.")

elif choice == "Finanzas y Proyección de Mercado":
    st.header("💰 Economía, Costos y Proyección de Ingresos por Vientre")
    st.markdown("Evalúa la rentabilidad del hato integrando costos operativos reales y el precio de mercado del ternero al destete.")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        precio_venta_kg = st.number_input("Precio Esperado de Venta en Mercado (MXN por kg de ternero)", min_value=30.0, max_value=120.0, value=68.0)
    
    st.divider()
    df = db.obtener_animales()
    if df.empty:
        st.info("Registre animales y costos para ver proyecciones financieras.")
    else:
        d_anim = {f"{r['siniiga']} - {r['categoria']}": r['id'] for _, r in df.iterrows()}
        id_sel_fin = st.selectbox("Seleccionar Animal / Vaca para Registrar Costo Operativo", list(d_anim.keys()))
        animal_id_f = d_anim[id_sel_fin]
        
        with st.form("form_costos"):
            concepto = st.selectbox("Concepto de Gasto", [
                "Suplementación Estacional (Melaza/Rastrojo/Proteína)", 
                "Vacunación y Sanidad", 
                "Manejo / Mano de Obra / Aretes SINIIGA", 
                "Servicios Veterinarios / IATF"
            ])
            monto = st.number_input("Monto en Pesos (MXN)", min_value=1.0, max_value=50000.0, value=500.0)
            fecha_g = st.date_input("Fecha del Gasto")
            
            if st.form_submit_button("Registrar Gasto en Hato"):
                db.registrar_costo(animal_id_f, concepto, monto, str(fecha_g))
                st.success(f"Gasto de ${monto} MXN registrado correctamente.")

    st.divider()
    st.subheader("📊 Análisis Financiero Consolidado del Hato")
    df_costos = db.obtener_costos()
    if not df_costos.empty:
        total_gastos = df_costos['monto_mxn'].sum()
        col1, col2 = st.columns(2)
        col1.metric("Gasto Total Acumulado en el Hato", f"${total_gastos:,.2f} MXN")
        col2.metric("Total de Registros de Costos", len(df_costos))
        st.dataframe(df_costos[['siniiga', 'concepto', 'monto_mxn', 'fecha']], use_container_width=True)
    else:
        st.info("Sin costos registrados todavía.")

elif choice == "Suplementación y Crecimiento (Vaca-Becerro)":
    st.header("🌾 Suplementación, Manejo Nutricional y Crecimiento Acelerado")
    st.markdown("Estrategias de nutrición de precisión para maximizar el desarrollo del becerro al pie y proteger el estatus metabólico del vientre.")

    tab_n1, tab_n2, tab_n3 = st.tabs(["🚀 Creep Feeding (Crecimiento de Becerros)", "🐄 Nutrición de la Vaca en Lactancia", "🌽 Estrategia Regional (Cañón de Tlaltenango)"])

    with tab_n1:
        st.subheader("Técnica de *Creep Feeding* (Alimentación Restringida al Becerro)")
        st.markdown(
            "El *Creep Feeding* consiste en instalar comederos protegidos donde solo los becerros (a partir de los 60 días de edad) tienen acceso al alimento concentrado, evitando que la madre consuma la ración.\n\n"
            "* **Ventajas Científicas:**\n"
            "  * Incrementa de 20 a 35 kg extra el peso al destete sin afectar el desarrollo ruminal.\n"
            "  * Mejora la conversión alimenticia (la eficiencia es máxima a temprana edad, requiriendo menos alimento por kilo ganado).\n"
            "  * Facilita la transición post-destete al acostumbrar el rumen del becerro al grano y concentrados.\n"
            "* **Formulación Sugerida (16-18% Proteína Cruda):** Grano de maíz molido/rolado (65%), pasta de soya o canola (25%), melaza líquida como palatabilizante (5%) y sales minerales con fósforo (5%)."
        )

    with tab_n2:
        st.subheader("Manejo Nutricional del Vientre (Lactancia Temprana)")
        st.markdown(
            "Los primeros 90 días postparto representan el pico de lactancia y el momento de mayor demanda energética y proteica para la vaca.\n\n"
            "* **Riesgo Fisiológico:** Si la vaca pierde demasiada condición corporal (CC < 4.5) durante esta etapa, el reinicio de la actividad ovárica se bloquea (anestro prolongado), destruyendo la meta de un becerro por año.\n"
            "* **Acción Nutricional:** Asegurar aportes de proteína degradable en rumen (PDR) cuando el agostadero esté seco, permitiendo que la flora ruminal digiera eficientemente la fibra de baja calidad."
        )

    with tab_n3:
        st.subheader("Aprovechamiento de Subproductos Regionales")
        st.markdown(
            "En el Cañón de Tlaltenango, la estacionalidad exige optimizar los recursos locales durante el estiaje:\n\n"
            "* **Rastrojo de Maíz / Sorgo Tratado:** Mejorar su digestibilidad mediante amonificación o complementación con melaza y fuentes de nitrógeno no proteico (urea).\n"
            "* **Bloques Multinutricionales:** Colocación estratégica en potreros para estimular el consumo de forrajes fibrosos secos y aportar minerales esenciales (Fósforo, Calcio y Magnesio)."
        )

elif choice == "Plan de Contingencia (Sequía & Enfermedades)":
    st.header("🚨 Plan de Emergencia, Sanidad Crítica y Contingencia Ganadera")
    st.markdown("Protocolos zootécnicos y tratamientos recomendados ante desafíos sanitarios severos y sequía extrema.")

    tab1, tab2, tab3, tab4 = st.tabs(["🌵 Sequía / Estiaje", "🦠 Anaplasmosis", "🕷️ Control de Garrapata", "🪱 Gusano Barrenador"])

    with tab1:
        st.subheader("Plan de Respuesta ante Sequía Extrema")
        st.markdown(
            "1. **Destete Precoz / Anticipado:** Si el forraje del agostadero cae por debajo del 10% de disponibilidad útil, destetar terneros a los 60-90 días de edad. Esto reduce la demanda energética de la vaca en lactancia en un 35-40%, protegiendo su condición corporal para el siguiente empadre.\n"
            "2. **Desecho Estratégico:** Venta inmediata de vientres improductivos, vacías diagnosticadas por tacto, vacas con problemas dentales o temperamento agresivo.\n"
            "3. **Banco de Alimentos Regional:** Activación de raciones de sobrevivencia basadas en rastrojos amonificados o tratados con urea + melaza."
        )

    with tab2:
        st.subheader("Protocolo y Tratamiento: Anaplasmosis Bovina")
        st.markdown(
            "**Enfermedad hemotrópica transmitida por garrapatas, tábanos y fómites contaminados.**\n\n"
            "* **Signos Clínicos:** Anemia severa, ictericia (mucosas pálidas/amarillentas), fiebre alta inicial, debilidad extrema y caída súbita en la producción láctea.\n"
            "* **Tratamiento Clínico:** Aplicación de **Oxitetraciclina de larga acción (LA)** a dosis terapéutica (20 mg/kg PV) según criterio médico. En casos avanzados con anemia severa, se requiere terapia de soporte con complejos vitamínicos (Vitamina B12/Hierro) y protectores hepáticos."
        )

    with tab3:
        st.subheader("Protocolo y Tratamiento: Control de Garrapata")
        st.markdown(
            "**Ectoparásito vector de hemoparásitos y causante de pérdidas en ganancia de peso.**\n\n"
            "* **Estrategia de Tratamiento:** Baños de aspersión o inmersión con garrapaticidas específicos (combinación de piretroides, amidinas o lactonas macrocíclicas según el grado de resistencia local).\n"
            "* **Manejo de Potreros:** Implementación de periodos de descanso en potreros para cortar el ciclo biológico de la garrapata en el agostadero."
        )

    with tab4:
        st.subheader("Protocolo y Tratamiento: Gusano Barrenador (*Cochliomyia hominivorax*)")
        st.markdown(
            "**Alerta Sanitaria Crítica:** Infestación por larvas de mosca que se alimentan de tejido vivo en cualquier herida abierta.\n\n"
            "* **Inspección Obligatoria Diaria:** Revisión rigurosa de ombligos en terneros recién nacidos, heridas por marcas, castraciones y descornes.\n"
            "* **Tratamiento Curativo:** Limpieza profunda de la herida, aplicación tópica de **larvicidas curativos en spray o pasta** a base de organosfosforados, extracción manual cuidadosa de larvas con pinzas (nunca aplastar dentro de la herida) y aplicación de tratamiento de soporte antibiótico/cicatrizante."
        )

    st.divider()
    st.error("🚨 **AVISO DE ASESORÍA CLÍNICA VETERINARIA:** En caso de emergencia, brotes atípicos, alta morbilidad o dudas sobre dosificación de tratamientos, **contactar de inmediato a su veterinario Alejandro Castañeda Correa para asesoría y guía clínica especializada.**")

elif choice == "Protocolo de Parto y Alimentación Nocturna":
    st.header("🌙 Estrategia Fisiológica de Alimentación Nocturna (Night Feeding)")
    st.markdown(
        "**Fundamento Científico:** Investigaciones en fisiología bovina demuestran que ofrecer la ración completa o el suplemento alimenticio "
        "de mayor peso **al atardecer / noche (17:00 a 21:00 hrs)** desplaza los picos de contracción uterina y el inicio del trabajo de parto "
        "hacia las **horas diurnas (luz del día)**.\n\n"
        "*Beneficios comprobados:*\n"
        "* Reducción drástica de la mortalidad neonatal por atención oportuna de distocias.\n"
        "* Menor estrés para el personal de rancho durante la época de pariciones en el Cañón de Tlaltenango."
    )
    
    with st.form("form_night_feed"):
        fecha_inicio_par = st.date_input("Fecha Estimada de Inicio de Parición")
        horas_sumi = st.selectbox("Horario Programado de Suplementación Nocturna", ["17:00 Horas", "18:30 Horas", "20:00 Horas"])
        obs_nf = st.text_area("Notas sobre ingredientes (ej. rastrojo de maíz tratado + melaza/urea)")
        
        if st.form_submit_button("Activar Protocolo de Parto Diurno"):
            st.success(f"✅ Protocolo configurado con éxito. El suministro nocturno a las {horas_sumi} iniciará la sincronización metabólica.")
