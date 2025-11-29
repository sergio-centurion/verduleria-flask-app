import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "inventario.db"

def init_database():
    # Eliminar base de datos existente (para reiniciar de cero)
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("🗑️ Base de datos anterior eliminada.")
        except PermissionError:
            print("⚠️ Error: Cierra la base de datos o el servidor antes de reiniciar.")
            return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
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
            email TEXT,
            FOREIGN KEY (rol_id) REFERENCES roles (id)
        )
    ''')
    
    # Tabla de productos (CON IMAGEN)
    cur.execute('''
        CREATE TABLE productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            categoria TEXT,
            imagen_url TEXT,  -- <--- CAMPO NUEVO PARA FOTOS
            vendedor_id INTEGER,
            activo BOOLEAN DEFAULT 1,
            FOREIGN KEY (vendedor_id) REFERENCES usuarios (id)
        )
    ''')

    # Tablas necesarias para el sistema de ventas (que están en tu app.py)
    cur.execute('''
        CREATE TABLE ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            total REAL,
            fecha DATETIME,
            estado TEXT,
            numero_pedido TEXT,
            tipo_tarjeta TEXT,
            ultimos_4 TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE venta_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            producto_id INTEGER,
            cantidad INTEGER,
            precio_unitario REAL,
            FOREIGN KEY(venta_id) REFERENCES ventas(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE metodos_pago (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            tipo_tarjeta TEXT,
            ultimos_4 TEXT,
            predeterminado BOOLEAN DEFAULT 0
        )
    ''')

    cur.execute('''
        CREATE TABLE cambios_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            vendedor_id INTEGER,
            stock_anterior INTEGER,
            stock_nuevo INTEGER,
            precio_anterior REAL,
            precio_nuevo REAL,
            porcentaje_cambio REAL,
            motivo TEXT,
            estado TEXT, -- 'pendiente', 'autorizado', 'rechazado'
            fecha_solicitud DATETIME,
            fecha_autorizacion DATETIME,
            autorizado_por INTEGER
        )
    ''')
    
    # Insertar roles
    roles = ['dueno', 'vendedor', 'cliente']
    for rol in roles:
        cur.execute("INSERT INTO roles (nombre) VALUES (?)", (rol,))
    
    # Insertar usuarios de prueba
    usuarios = [
        ('admin', generate_password_hash('admin'), 1),    # dueño
        ('vendedor', generate_password_hash('vendedor'), 2), # vendedor  
        ('cliente', generate_password_hash('cliente'), 3),   # cliente
    ]
    
    for username, password, rol_id in usuarios:
        cur.execute(
            "INSERT INTO usuarios (username, password, rol_id) VALUES (?, ?, ?)",
            (username, password, rol_id)
        )
    
    # Insertar productos de ejemplo CON FOTOS REALES
    # Formato: (Nombre, Descripcion, Precio, Stock, Categoria, URL_FOTO, VendedorID)
    productos = [
        ('Manzanas', 'Manzanas rojas frescas y jugosas', 2.50, 100, 'Frutas', 
         'https://images.pexels.com/photos/102104/pexels-photo-102104.jpeg?auto=compress&cs=tinysrgb&w=400', 2),
         
        ('Plátanos', 'Plátanos maduros ricos en potasio', 1.80, 50, 'Frutas', 
         'https://images.pexels.com/photos/2872755/pexels-photo-2872755.jpeg?auto=compress&cs=tinysrgb&w=400', 2),
         
        ('Naranjas', 'Naranjas ideales para jugo', 3.00, 75, 'Frutas', 
         'https://images.pexels.com/photos/327098/pexels-photo-327098.jpeg?auto=compress&cs=tinysrgb&w=400', 2),
         
        ('Lechuga', 'Lechuga mantecosa fresca de huerta', 1.50, 30, 'Verduras', 
         'https://images.pexels.com/photos/1199562/pexels-photo-1199562.jpeg?auto=compress&cs=tinysrgb&w=400', 2),
         
        ('Tomates', 'Tomates orgánicos perita', 2.20, 40, 'Verduras', 
         'https://images.pexels.com/photos/533280/pexels-photo-533280.jpeg?auto=compress&cs=tinysrgb&w=400', 2),
         
        ('Papas', 'Papas negras lavadas bolsa 1kg', 1.00, 200, 'Verduras', 
         'https://images.pexels.com/photos/144248/potatoes-vegetables-erdfrucht-bio-144248.jpeg?auto=compress&cs=tinysrgb&w=400', 2),
    ]
    
    for nombre, descripcion, precio, stock, categoria, imagen_url, vendedor_id in productos:
        cur.execute(
            "INSERT INTO productos (nombre, descripcion, precio, stock, categoria, imagen_url, vendedor_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nombre, descripcion, precio, stock, categoria, imagen_url, vendedor_id)
        )
    
    conn.commit()
    conn.close()
    
    print("✅ Base de datos inicializada correctamente con FOTOS!")
    print("Usuarios de prueba creados:")
    print("  Dueño: admin / admin")
    print("  Vendedor: vendedor / vendedor") 
    print("  Cliente: cliente / cliente")

if __name__ == "__main__":
    init_database()