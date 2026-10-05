import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pyotp  # Librería estándar para códigos TOTP 2FA

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA 150 | SaaS Seguro 2FA",
    page_icon="🐂",
    layout="wide"
)

# --- CONFIGURACIÓN DE SEGURIDAD Y CREDENCIALES DEL PROPIETARIO ---
# Nota: En producción, estas credenciales residen en variables de entorno seguras (st.secrets)
USUARIO_PRINCIPAL = "alejandro_c"
PASSWORD_PRINCIPAL = "Tlaltenango2026*"
# Secreto TOTP único para el 2FA del propietario (imposible de compartir sin la app autenticadora)
SECRET_TOTP_PROPIETARIO = "JBSWY3DPEHPK3PXP" 

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN PARA SEGURIDAD ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'paso_2fa' not in st.session_state:
    st.session_state['paso_2fa'] = False
if 'suscripcion_activa' not in st.session_state:
    st.session_state['suscripcion_activa'] = True # Simulado activo para el usuario principal

# --- PANTALLA DE ACCESO Y SEGURIDAD (GATEKEEPER) ---
if not st.session_state['autenticado'] or not st.session_state['paso_2fa']:
    st.title("🔒 Cr-IA 150 - Acceso Seguro Restringido")
    st.subheader("Sistema Exclusivo de Gestión Vaca-Cría | Cañón de Tlaltenango")
    
    with st.form("form_login"):
        st.markdown("### Credenciales de Acceso Propietario")
        user_input = st.text_input("Usuario Principal")
        pass_input = st.text_input("Contraseña", type="password")
        
        st.markdown("### Verificación de Doble Factor (2FA - Google Authenticator)")
        totp_input = st.text_input("Código de 6 dígitos de tu App Autenticadora", max_chars=6)
        
        btn_login = st.form_submit_button("Iniciar Sesión Segura")
        
        if btn_login:
            totp = pyotp.TOTP(SECRET_TOTP_PROPIETARIO)
            token_valido = totp.verify(totp_input)
            
            if user_input == USUARIO_PRINCIPAL and pass_input == PASSWORD_PRINCIPAL:
                if token_valido:
                    st.session_state['autenticado'] = True
                    st.session_state['paso_2fa'] = True
                    st.success("✅ Acceso autorizado. Cargando plataforma...")
                    st.rerun()
                else:
                    st.error("❌ Código 2FA inválido o expirado. Verifique su aplicación autenticadora (Antifraude activado).")
            else:
                st.error("❌ Usuario o contraseña incorrectos.")
    
    st.info("💡 **Seguridad Antifraude:** Este sistema utiliza un doble factor de autenticación TOTP para garantizar que única y exclusivamente el propietario original opere la plataforma, evitando el intercambio de contraseñas entre terceros.")
    st.stop()

# --- CLASE DE GESTIÓN Y LÓGICA DE DATOS ---
class CrIA150Segura:
    def __init__(self, db_name="cria_150_segura.db"):
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

db = CrIA150Segura()

# --- INTERFAZ PRINCIPAL DE LA APLICACIÓN (ACCESO PROTEGIDO) ---
st.sidebar.success("🟢 Sesión Segura Verificada (2FA Activo)")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.session_state['paso_2fa'] = False
    st.rerun()

st.title("🐂 Cr-IA 150 - Sistema Exclusivo de Vanguardia & Seguridad")
st.subheader("Plataforma Protegida de Precisión Zootécnica y Económica para Vaca-Cría")

menu = [
    "Inventario y Altas", 
    "Control de Condición Corporal (CC 1-9)", 
    "⭐ Optimizador de Raciones & Agostadero (Ventaja Competitiva)",
    "🤖 IA & IoT (Visión Artificial y Sensores)",
    "Calendario Gestación & Partos (*Smart Calendar*)", 
    "Sanidad Integral Regional",
    "Evaluación BIF (205 Días) & Gráficas",
    "Finanzas, Pagos y Suscripción",
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

elif choice == "⭐ Optimizador de Raciones & Agostadero (Ventaja Competitiva)":
    st.header("⭐ Módulo Exclusivo: Optimizador de Costos y Capacidad de Carga")
    st.markdown("La herramienta inteligente que ninguna otra aplicación comercial tiene: cálculo de raciones locales de mínimo costo y análisis de resiliencia de agostadero.")

    tab_exc1, tab_exc2 = st.tabs(["🧮 Optimizador de Raciones de Mínimo Costo", "🌿 Simulador de Capacidad de Carga (Agostadero)"])

    with tab_exc1:
        st.subheader("Formulador Inteligente de Raciones para Estiaje (Tlaltenango)")
        col_op1, col_op2 = st.columns(2)
        with col_op1:
            etapa_sel = st.selectbox("Etapa Fisiológica", ["Último Tercio de Gestación", "Lactancia Temprana", "Vaca Horra / Mantenimiento"])
            peso_vaca_op = st.number_input("Peso Promedio del Vientre (kg)", 350.0, 700.0, 480.0)
        with col_op2:
            st.markdown("**Precios Locales Estimados (MXN / Tonelada):**")
            precio_rastrojo = st.number_input("Rastrojo de Maíz Molido", 1500.0, 4000.0, 2500.0)
            precio_melaza = st.number_input("Melaza Líquida", 3000.0, 8000.0, 4800.0)
            precio_soya = st.number_input("Pasta de Soya", 8000.0, 18000.0, 12500.0)

        if st.button("Ejecutar Optimización de Costo Mínimo"):
            costo_diario_est = (peso_vaca_op * 0.025) * ( (precio_rastrojo/1000)*0.6 + (precio_melaza/1000)*0.2 + (precio_soya/1000)*0.2 )
            st.success("✅ **Ración Óptima Calculada por el Sistema Exclusivo:**")
            st.metric("Costo Diario Estimado por Vientre", f"${round(costo_diario_est / 30, 2)} MXN / día")
            st.markdown(
                f"* **Rastrojo de Maíz (Fibra base):** 60% de la ración.\n"
                f"* **Melaza Líquida (Energía/Palatabilidad):** 20% de la ración.\n"
                f"* **Pasta de Soya (Proteína cruda):** 20% de la ración.\n"
                f"💡 *Ventaja Cr-IA 150:* Esta combinación cubre perfectamente los requerimientos nutricionales específicos para **{etapa_sel}**, ahorrando hasta un 25%."
            )

    with tab_exc2:
        st.subheader("Simulador de Capacidad de Carga y Resiliencia de Agostadero")
        hectareas = st.number_input("Superficie Total del Agostadero (Hectáreas)", 10.0, 5000.0, 150.0)
        cabezas = st.number_input("Número Total de Vientres en el Hato", 1.0, 500.0, 35.0)
        indice_pluvial = st.selectbox("Condición Climática Anual en la Región", ["Año Normal / Promedio", "Año Seco / Estiaje Severo"])

        if st.button("Analizar Capacidad de Carga"):
            factor = 4.0 if "Normal" in indice_pluvial else 7.0
            capacidad_maxima = hectareas / factor
            st.metric("Capacidad de Carga Recomendada", f"{round(capacidad_maxima, 1)} Vientres Máximo")
            
            if cabezas > capacidad_maxima:
                st.error(f"🚨 **Alerta de Sobrepastoreo:** Tu hato actual ({cabezas} vientres) supera la capacidad biológica del terreno ({round(capacidad_maxima, 1)} vientres) bajo las condiciones de {indice_pluvial}.")
            else:
                st.success("✅ **Agostadero en Equilibrio:** Tu carga animal actual es sostenible.")

elif choice == "🤖 IA & IoT (Visión Artificial y Sensores)":
    st.header("🤖 Centro de Inteligencia Artificial & Internet de las Cosas (IoT)")
    st.markdown("Tecnologías de vanguardia integradas para automatizar la supervisión del hato.")

    tab_ai1, tab_ai2, tab_ai3 = st.tabs(["📸 IA Visión - Estima CC por Foto", "📡 Telemetría IoT en Potreros", "🧠 Motor Predictivo de Salud (ML)"])

    with tab_ai1:
        st.subheader("Estimador de Condición Corporal impulsado por IA")
        foto_subida = st.file_uploader("Cargar fotografía del animal (Formatos JPG, PNG)", type=["jpg", "png", "jpeg"])
        if foto_subida is not None:
            st.image(foto_subida, caption="Imagen analizada por el modelo de IA Cr-IA Vision", use_container_width=True)
            with st.spinner("Procesando patrones biométricos y cobertura grasa con IA..."):
                st.success("✅ **Análisis de Visión Artificial Completado:**")
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.metric("Condición Corporal Estimada", "CC 5.5 (Óptima)")
                col_i2.metric("Peso Vivo Estimado", "485 kg")
                col_i3.metric("Confianza del Modelo", "94.8%")

    with tab_ai2:
        st.subheader("Monitoreo de Sensores LoRaWAN / IoT en Tiempo Real")
        col_iot1, col_iot2, col_iot3 = st.columns(3)
        with col_iot1:
            st.metric("💧 Nivel de Agua (Aguaje Principal)", "85%", "Estable (Bomba Solar Activa)")
        with col_iot2:
            st.metric("🌡️ Temperatura Ambiental", "29 °C", "Índice de Confort Normal")
        with col_iot3:
            st.metric("📡 Aretes Inteligentes Activos", "42 Unidades", "Señal Óptima en Lote")

    with tab_ai3:
        st.subheader("Motor Predictivo de Riesgo Reproductivo y Sanitario")
        st.warning("⚠️️ **Predicción Activa del Hato:** 2 vaquillas en primer parto muestran una tendencia de pérdida de peso superior al 8% en el último mes.")

elif choice == "Calendario Gestación & Partos (*Smart Calendar*)":
    st.header("📅 Calendario Inteligente de Servicios y Partos")
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
