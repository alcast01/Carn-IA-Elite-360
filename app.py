import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pyotp  # Librería estándar para códigos TOTP 2FA

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA 150 | SaaS Elite Vaca-Becerro",
    page_icon="🐂",
    layout="wide"
)

# --- ESTILOS CSS AVANZADOS & LOGO DE VANGUARDIA (MARKETING & UX B2B) ---
st.markdown("""
    <style>
    .brand-container {
        background: linear-gradient(135deg, #082214 0%, #113f27 50%, #04120a 100%);
        padding: 30px;
        border-radius: 18px;
        color: white;
        box-shadow: 0 10px 35px rgba(0,0,0,0.3);
        margin-bottom: 25px;
        border: 1px solid rgba(212, 175, 55, 0.4);
    }
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 20px;
    }
    .brand-title {
        font-size: 2.5rem;
        font-weight: 900;
        margin: 0;
        letter-spacing: -0.5px;
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
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

# --- CONFIGURACIÓN DE SEGURIDAD Y CREDENCIALES DEL PROPIETARIO ---
USUARIO_PRINCIPAL = "alejandro_c"
PASSWORD_PRINCIPAL = "Tlaltenango2026*"
SECRET_TOTP_PROPIETARIO = "JBSWY3DPEHPK3PXP" 

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN PARA SEGURIDAD ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'paso_2fa' not in st.session_state:
    st.session_state['paso_2fa'] = False
if 'suscripcion_activa' not in st.session_state:
    st.session_state['suscripcion_activa'] = True

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
                    st.error("❌ Código 2FA inválido o expirado. Verifique su aplicación autenticadora.")
            else:
                st.error("❌ Usuario o contraseña incorrectos.")
    
    st.info("💡 **Seguridad Antifraude:** Este sistema utiliza un doble factor de autenticación TOTP para garantizar que única y exclusivamente el propietario original opere la plataforma.")
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

# --- LOGOTIPO DE VANGUARDIA, SLOGAN EMPRESARIAL Y CRÉDITOS ---
st.markdown("""
    <div class="brand-container">
        <div class="brand-header">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="background: linear-gradient(135deg, #d4af37 0%, #aa8c2c 100%); color: #04120a; font-size: 2.3rem; font-weight: bold; padding: 12px 20px; border-radius: 14px; box-shadow: 0 6px 20px rgba(0,0,0,0.4); text-align: center; border: 1px solid #fff;">
                    🐂📈
                </div>
                <div>
                    <h1 class="brand-title">Cr-IA <span>150</span></h1>
                    <p class="brand-subtitle"><b>Slogan:</b> "De la Ganadería Tradicional a la Empresa Hiperrentable: Eficiencia Zootécnica, Control Financiero y Máximas Ganancias."</p>
                </div>
            </div>
            <div>
                <span class="brand-badge">Enterprise Elite SaaS</span>
            </div>
        </div>
        <div class="brand-footer-info">
            <p style="margin: 0; font-size: 0.95rem; color: #a8d5ba; font-style: italic;">
                "Transformando cada kilogramo destetado y cada recurso optimizado en dividendos reales para tu negocio ganadero."
            </p>
            <p style="margin: 0; font-size: 0.9rem; color: #ffffff; font-weight: 600;">
                💻 Aplicación creada y desarrollada por el Nutriólogo Veterinario <strong>Dr. Alejandro Castañeda Correa</strong>
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)

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
            arete = st.text_input("Areimport streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import pyotp  # Librería estándar para códigos TOTP 2FA

# Configuración de la página
st.set_page_config(
    page_title="Cr-IA 150 | SaaS Elite Vaca-Becerro",
    page_icon="🐂",
    layout="wide"
)

# --- ESTILOS CSS AVANZADOS & LOGO DE VANGUARDIA (MARKETING & UX B2B) ---
st.markdown("""
    <style>
    .brand-container {
        background: linear-gradient(135deg, #082214 0%, #113f27 50%, #04120a 100%);
        padding: 30px;
        border-radius: 18px;
        color: white;
        box-shadow: 0 10px 35px rgba(0,0,0,0.3);
        margin-bottom: 25px;
        border: 1px solid rgba(212, 175, 55, 0.4);
    }
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 20px;
    }
    .brand-title {
        font-size: 2.5rem;
        font-weight: 900;
        margin: 0;
        letter-spacing: -0.5px;
        color: #ffffff;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .brand-title span {
        color: #d4af37; /* Acento Dorado Elite */
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

# --- CONFIGURACIÓN DE SEGURIDAD Y CREDENCIALES DEL PROPIETARIO ---
USUARIO_PRINCIPAL = "alejandro_c"
PASSWORD_PRINCIPAL = "Tlaltenango2026*"
SECRET_TOTP_PROPIETARIO = "JBSWY3DPEHPK3PXP" 

# --- INICIALIZACIÓN DE ESTADO DE SESIÓN PARA SEGURIDAD ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'paso_2fa' not in st.session_state:
    st.session_state['paso_2fa'] = False
if 'suscripcion_activa' not in st.session_state:
    st.session_state['suscripcion_activa'] = True

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
                    st.error("❌ Código 2FA inválido o expirado. Verifique su aplicación autenticadora.")
            else:
                st.error("❌ Usuario o contraseña incorrectos.")
    
    st.info("💡 **Seguridad Antifraude:** Este sistema utiliza un doble factor de autenticación TOTP para garantizar que única y exclusivamente el propietario original opere la plataforma.")
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

# --- LOGOTIPO DE VANGUARDIA, SLOGAN EMPRESARIAL Y CRÉDITOS ---
st.markdown("""
    <div class="brand-container">
        <div class="brand-header">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="background: linear-gradient(135deg, #d4af37 0%, #aa8c2c 100%); color: #04120a; font-size: 2.3rem; font-weight: bold; padding: 12px 20px; border-radius: 14px; box-shadow: 0 6px 20px rgba(0,0,0,0.4); text-align: center; border: 1px solid #fff;">
                    🐂📈
                </div>
                <div>
                    <h1 class="brand-title">Cr-IA <span>150</span></h1>
                    <p class="brand-subtitle"><b>Slogan:</b> "De la Ganadería Tradicional a la Empresa Hiperrentable: Eficiencia Zootécnica, Control Financiero y Máximas Ganancias."</p>
                </div>
            </div>
            <div>
                <span class="brand-badge">Enterprise Elite SaaS</span>
            </div>
        </div>
        <div class="brand-footer-info">
            <p style="margin: 0; font-size: 0.95rem; color: #a8d5ba; font-style: italic;">
                "Transformando cada kilogramo dest
