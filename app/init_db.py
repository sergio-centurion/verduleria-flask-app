# init_db_mejorado.py
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "inventario.db"

def init_database():
    # Eliminar base de datos existente (para desarrollo)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
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
    
    # Insertar roles
    roles = ['dueno', 'vendedor', 'cliente']
    for rol in roles:
        cur.execute("INSERT INTO roles (nombre) VALUES (?)", (rol,))
    
    # Insertar usuarios de prueba (CONTRASEÑAS MÁS SIMPLES PARA PRUEBA)
    usuarios = [
        ('admin', generate_password_hash('admin'), 1),  # dueño
        ('vendedor', generate_password_hash('vendedor'), 2),  # vendedor  
        ('cliente', generate_password_hash('cliente'), 3),  # cliente
    ]
    
    for username, password, rol_id in usuarios:
        cur.execute(
            "INSERT INTO usuarios (username, password, rol_id) VALUES (?, ?, ?)",
            (username, password, rol_id)
        )
    
    # Insertar productos de ejemplo asignados al vendedor (id=2)
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
    
    print("✅ Base de datos inicializada correctamente!")
    print("Usuarios de prueba creados:")
    print("  Dueño: admin / admin")
    print("  Vendedor: vendedor / vendedor") 
    print("  Cliente: cliente / cliente")
    print("\nNOTA: Estas son contraseñas simples solo para pruebas")

if __name__ == "__main__":
    init_database()