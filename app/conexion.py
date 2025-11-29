# conexion.py
import sqlite3
from pathlib import Path

DB_PATH = "inventario.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def crear_tablas():
    conn = get_connection()
    c = conn.cursor()

    # Roles con permisos como columnas (fácil de consultar)
    c.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL,
        descripcion TEXT,
        puede_vender INTEGER DEFAULT 0,
        puede_gestionar_stock INTEGER DEFAULT 0,
        puede_aprobar_cancelaciones INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Usuarios (login) -> referencia a roles
    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        rol_id INTEGER NOT NULL,
        activo INTEGER DEFAULT 1,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(rol_id) REFERENCES roles(id)
    )
    """)

    # Empleados (datos extra)
    c.execute("""
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER UNIQUE,
        nombre TEXT,
        apellido TEXT,
        dni TEXT,
        telefono TEXT,
        fecha_ingreso TEXT,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    # Productos
    c.execute("""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        precio REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        categoria TEXT,
        activo INTEGER DEFAULT 1,
        vendedor_id INTEGER,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(vendedor_id) REFERENCES usuarios(id)
    )
    """)

    # Ventas
    c.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        total REAL,
        tipo_tarjeta TEXT,
        ultimos_4 TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        estado TEXT DEFAULT 'completada',
        numero_pedido TEXT UNIQUE,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    # Items por venta
    c.execute("""
    CREATE TABLE IF NOT EXISTS venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        producto_id INTEGER,
        cantidad INTEGER,
        precio_unitario REAL,
        FOREIGN KEY(venta_id) REFERENCES ventas(id),
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)

    # Metodos de pago
    c.execute("""
    CREATE TABLE IF NOT EXISTS metodos_pago (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        tipo_tarjeta TEXT,
        ultimos_4 TEXT,
        predeterminado INTEGER DEFAULT 0,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    # Cancelaciones
    c.execute("""
    CREATE TABLE IF NOT EXISTS cancelaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER,
        usuario_id INTEGER,
        motivo TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP,
        fecha_respuesta TEXT,
        respuesta_por INTEGER,
        FOREIGN KEY(venta_id) REFERENCES ventas(id),
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(respuesta_por) REFERENCES usuarios(id)
    )
    """)

    # Solicitudes (altas/bajas propuestas por vendedores)
    c.execute("""
    CREATE TABLE IF NOT EXISTS solicitudes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        tipo TEXT,
        producto_id INTEGER,
        datos TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    )
    """)

    # Acciones admin (log)
    c.execute("""
    CREATE TABLE IF NOT EXISTS acciones_admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        accion TEXT,
        detalle TEXT,
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(admin_id) REFERENCES usuarios(id)
    )
    """)

    # Config global de la empresa
    c.execute("""
    CREATE TABLE IF NOT EXISTS config_empresa (
        id INTEGER PRIMARY KEY CHECK(id = 1),
        nombre TEXT,
        email_contacto TEXT,
        max_horas_cancelacion INTEGER DEFAULT 24,
        limite_stock_alerta INTEGER DEFAULT 10
    )
    """)
    
    # Cambios de stock (CORREGIDO - sin error de sintaxis)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cambios_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        vendedor_id INTEGER NOT NULL,
        stock_anterior INTEGER NOT NULL,
        stock_nuevo INTEGER NOT NULL,
        porcentaje_cambio REAL,
        estado TEXT DEFAULT 'pendiente',
        autorizado_por INTEGER,
        fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP,
        fecha_autorizacion TEXT,
        motivo TEXT,
        FOREIGN KEY(producto_id) REFERENCES productos(id),
        FOREIGN KEY(vendedor_id) REFERENCES usuarios(id),
        FOREIGN KEY(autorizado_por) REFERENCES usuarios(id)
    )
    """)

    conn.commit()
    conn.close()


# --- Helpers utiles ---
def obtener_usuario_por_username(username):
    conn = get_connection()
    u = conn.execute("SELECT u.*, r.nombre AS rol_nombre, r.puede_gestionar_stock, r.puede_vender, r.puede_aprobar_cancelaciones FROM usuarios u JOIN roles r ON u.rol_id = r.id WHERE username = ?", (username,)).fetchone()
    conn.close()
    return u

def obtener_rol_por_id(rol_id):
    conn = get_connection()
    r = conn.execute("SELECT * FROM roles WHERE id = ?", (rol_id,)).fetchone()
    conn.close()
    return r

def listar_productos_activos():
    conn = get_connection()
    p = conn.execute("SELECT * FROM productos WHERE activo=1").fetchall()
    conn.close()
    return p