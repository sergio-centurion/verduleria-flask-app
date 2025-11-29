# reset_db_correcto.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "inventario.db"

print("🔧 Reseteando base de datos CORRECTAMENTE...")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Limpiar TODAS las tablas completamente
cur.execute("DROP TABLE IF EXISTS usuarios")
cur.execute("DROP TABLE IF EXISTS roles")
cur.execute("DROP TABLE IF EXISTS productos")
cur.execute("DROP TABLE IF EXISTS ventas")
cur.execute("DROP TABLE IF EXISTS venta_items")
cur.execute("DROP TABLE IF EXISTS metodos_pago")
cur.execute("DROP TABLE IF EXISTS cambios_stock")

# Crear tabla de roles CORRECTA
cur.execute('''
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    )
''')

# Crear tabla de usuarios CORRECTA
cur.execute('''
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol_id INTEGER NOT NULL,
        FOREIGN KEY (rol_id) REFERENCES roles (id)
    )
''')

# Crear tabla de productos
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

# Crear tabla de ventas
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

# Crear tabla de items de venta
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

# Insertar roles
roles = ['dueno', 'vendedor', 'cliente']
for rol in roles:
    cur.execute("INSERT INTO roles (nombre) VALUES (?)", (rol,))

# Insertar usuarios CORRECTOS (rol_id = 1, 2, 3)
usuarios = [
    ('admin', generate_password_hash('admin'), 1),      # dueño - rol_id 1
    ('vendedor', generate_password_hash('vendedor'), 2), # vendedor - rol_id 2  
    ('cliente', generate_password_hash('cliente'), 3),   # cliente - rol_id 3
]

for username, password, rol_id in usuarios:
    cur.execute(
        "INSERT INTO usuarios (username, password, rol_id) VALUES (?, ?, ?)",
        (username, password, rol_id)
    )

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

print("✅ Base de datos recreada CORRECTAMENTE!")
print("📋 Usuarios disponibles:")
print("   👑 Dueño: admin / admin")
print("   📊 Vendedor: vendedor / vendedor") 
print("   🛒 Cliente: cliente / cliente")