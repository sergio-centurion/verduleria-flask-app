import sqlite3 
DB_PATH = "inventario.db" 
conn = sqlite3.connect(DB_PATH) 
conn.row_factory = sqlite3.Row 
print("=== USUARIOS EXISTENTES ===") 
users = conn.execute("SELECT * FROM usuarios").fetchall() 
for user in users: 
    print(f"ID: {user[0]}, Username: {user[1]}, Password: {user[2][:30]}..., Rol ID: {user[3]}") 
print("\n=== ROLES EXISTENTES ===") 
roles = conn.execute("SELECT * FROM roles").fetchall() 
for role in roles: 
    print(f"ID: {role[0]}, Nombre: {role[1]}") 
print("\n=== PRODUCTOS EXISTENTES ===") 
products = conn.execute("SELECT * FROM productos").fetchall() 
for prod in products: 
    print(f"ID: {prod[0]}, Nombre: {prod[1]}, Stock: {prod[4]}") 
conn.close() 
