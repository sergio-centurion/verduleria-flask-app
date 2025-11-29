# init_completo.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "inventario.db"

print("🚀 Creando base de datos COMPLETAMENTE NUEVA...")

# Asegurarse de que no existe
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ==================== CREAR TABLAS ====================
print("📋 Creando tablas...")

# Tabla de roles
cur.execute('''
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    )
''')

# Tabla de usuarios
cur.execute('''
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol_id INTEGER NOT NULL,
        FOREIGN KEY (rol_id) REFERENCES roles (id)
    )
''')

# Tabla de productos
cur.execute('''
    CREATE TABLE productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        categoria TEXT,
        vendedor_id INTEGER,
        activo BOOLEAN DEFAULT 1,
        FOREIGN KEY (vendedor_id) REFERENCES usuarios (id)
    )
''')

# Tabla de ventas
cur.execute('''
    CREATE TABLE ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        total REAL NOT NULL,
        tipo_tarjeta TEXT,
        ultimos_4 TEXT,
        fecha TEXT NOT NULL,
        estado TEXT DEFAULT 'completada',
        numero_pedido TEXT UNIQUE,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
''')

# Tabla de items de venta
cur.execute('''
    CREATE TABLE venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venta_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        precio_unitario REAL NOT NULL,
        FOREIGN KEY (venta_id) REFERENCES ventas (id),
        FOREIGN KEY (producto_id) REFERENCES productos (id)
    )
''')

# Tabla de métodos de pago
cur.execute('''
    CREATE TABLE metodos_pago (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        tipo_tarjeta TEXT NOT NULL,
        ultimos_4 TEXT NOT NULL,
        predeterminado BOOLEAN DEFAULT 0,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
''')

# Tabla de cambios de stock
cur.execute('''
    CREATE TABLE cambios_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        vendedor_id INTEGER NOT NULL,
        stock_anterior INTEGER NOT NULL,
        stock_nuevo INTEGER NOT NULL,
        precio_anterior REAL NOT NULL,
        precio_nuevo REAL NOT NULL,
        porcentaje_cambio REAL NOT NULL,
        motivo TEXT,
        estado TEXT DEFAULT 'pendiente',
        fecha_solicitud TEXT NOT NULL,
        fecha_autorizacion TEXT,
        autorizado_por INTEGER,
        FOREIGN KEY (producto_id) REFERENCES productos (id),
        FOREIGN KEY (vendedor_id) REFERENCES usuarios (id),
        FOREIGN KEY (autorizado_por) REFERENCES usuarios (id)
    )
''')

# ==================== INSERTAR DATOS ====================
print("👥 Insertando roles y usuarios...")

# Insertar roles
roles = ['dueno', 'vendedor', 'cliente']
for rol in roles:
    cur.execute("INSERT INTO roles (nombre) VALUES (?)", (rol,))

# Insertar usuarios CORRECTOS
usuarios = [
    ('admin', generate_password_hash('admin'), 1),      # dueño
    ('vendedor', generate_password_hash('vendedor'), 2), # vendedor
    ('cliente', generate_password_hash('cliente'), 3),   # cliente
]

for username, password, rol_id in usuarios:
    cur.execute(
        "INSERT INTO usuarios (username, password, rol_id) VALUES (?, ?, ?)",
        (username, password, rol_id)
    )

print("🍎 Insertando productos...")
# Insertar productos
productos = [
    ('Manzanas', 'Manzanas rojas frescas', 2.50, 100, 'Frutas', 2),
    ('Plátanos', 'Plátanos maduros', 1.80, 50, 'Frutas', 2),
    ('Naranjas', 'Naranjas jugosas', 3.00, 75, 'Frutas', 2),
    ('Lechuga', 'Lechuga fresca', 1.50, 30, 'Verduras', 2),
    ('Tomates', 'Tomates orgánicos', 2.20, 40, 'Verduras', 2),
]

for nombre, descripcion, precio, stock, categoria, vendedor_id in productos:
    cur.execute(
        "INSERT INTO productos (nombre, descripcion, precio, stock, categoria, vendedor_id) VALUES (?, ?, ?, ?, ?, ?)",
        (nombre, descripcion, precio, stock, categoria, vendedor_id)
    )

conn.commit()
conn.close()

print("✅ Base de datos creada EXITOSAMENTE!")
print("\n📋 USUARIOS DE PRUEBA:")
print("   👑 Dueño:    admin / admin")
print("   📊 Vendedor: vendedor / vendedor")
print("   🛒 Cliente:  cliente / cliente")
print("\n🎯 Ahora ejecuta: python app.py")