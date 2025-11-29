from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import sqlite3
import random
import time
import json
from datetime import datetime, timedelta
from functools import wraps 
from flask import abort 
from io import BytesIO
from xhtml2pdf import pisa

# ========================================================
# CONFIGURACIÓN INICIAL
# ========================================================
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CLAVE_MAESTRA_HIPER_SECRETA_UTN_2025_FINAL")
app.config['WTF_CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = "CSRF_KEY_SEGURA_Y_FUERTE"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)

csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "⚠️ Debes iniciar sesión para ver esta página."
login_manager.login_message_category = "warning"

DB_PATH = "inventario.db"

# ========================================================
#  UTILIDADES Y HELPERS
# ========================================================

def is_development():
    try:
        if os.environ.get('FLASK_ENV') == 'development': return True
        from flask import has_request_context
        if has_request_context():
            return '127.0.0.1' in request.host_url or 'localhost' in request.host_url
        return True
    except: return False

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def obtener_stock_actual(producto_id):
    conn = get_db_connection()
    try: pid = int(producto_id)
    except: return 0
    prod = conn.execute("SELECT stock FROM productos WHERE id=? AND activo=1", (pid,)).fetchone()
    conn.close()
    return prod["stock"] if prod else 0

# ========================================================
#  MODELO DE USUARIO
# ========================================================

class Usuario(UserMixin):
    def __init__(self, id, username, rol):
        self.id = id
        self.username = username
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    u = conn.execute("SELECT u.*, r.nombre as rol_nombre FROM usuarios u JOIN roles r ON u.rol_id = r.id WHERE u.id=?", (user_id,)).fetchone()
    conn.close()
    if u: return Usuario(u["id"], u["username"], u["rol_nombre"])
    return None

def rol_requerido(roles_permitidos):
    if not isinstance(roles_permitidos, list): roles_permitidos = [roles_permitidos]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated: return login_manager.unauthorized()
            if current_user.rol not in roles_permitidos:
                flash("⛔ Acceso denegado: No tienes permisos.", "danger")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_helpers():
    return dict(obtener_stock_actual=obtener_stock_actual, is_development=is_development)

# ========================================================
#  RUTAS DE AUTENTICACIÓN
# ========================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db_connection()
        user_data = conn.execute("SELECT u.*, r.nombre as rol_nombre FROM usuarios u JOIN roles r ON u.rol_id = r.id WHERE u.username=?", (username,)).fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data["password"], password):
            user_obj = Usuario(user_data["id"], user_data["username"], user_data["rol_nombre"])
            login_user(user_obj)
            flash(f"👋 Bienvenido de nuevo, {user_obj.username}", "success")
            if user_obj.rol == "dueno": return redirect(url_for("panel_dueno"))
            elif user_obj.rol == "vendedor": return redirect(url_for("vendedor_view"))
            return redirect(url_for("index"))
        else:
            flash("❌ Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("👋 ¡Hasta luego!", "info")
    return redirect(url_for("index"))

# ========================================================
#  RUTAS PÚBLICAS Y API STOCK
# ========================================================

@app.route("/")
def index():
    conn = get_db_connection()
    # AGREGAMOS: AND stock > 0
    productos = conn.execute("SELECT * FROM productos WHERE activo=1 AND stock > 0 ORDER BY nombre ASC").fetchall()
    conn.close()
    return render_template("index.html", productos=productos)

@app.route("/api/stock/<int:producto_id>")
def api_stock(producto_id):
    return jsonify({"stock": obtener_stock_actual(producto_id)})

@app.route("/api/sugerir_producto")
@login_required
@rol_requerido("vendedor")
def sugerir_producto():
    try:
        from api_helper import buscar_producto_openfoodfacts
        query = request.args.get('q', '').strip()
        if len(query) < 3: return jsonify([])
        resultados = buscar_producto_openfoodfacts(query)
        return jsonify(resultados)
    except: return jsonify([])

@app.route('/api/debug/rutas')
def api_debug_rutas():
    if not is_development(): return abort(403)
    return jsonify([str(p) for p in app.url_map.iter_rules()])

# ========================================================
#  API CARRITO (GUEST CHECKOUT HABILITADO)
# ========================================================

@app.route('/api/carrito', methods=['GET'])
def api_obtener_carrito():
    try:
        carrito = session.get('carrito', {})
        total_items = sum(i['cantidad'] for i in carrito.values())
        total_precio = sum(i['cantidad'] * i['precio'] for i in carrito.values())
        user_status = current_user.username if current_user.is_authenticated else "Invitado"
        return jsonify({'success': True, 'carrito': carrito, 'total_items': total_items, 'total_precio': total_precio, 'user': user_status})
    except Exception as e: return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/carrito/agregar', methods=['POST'])
def api_agregar_carrito():
    try:
        data = request.get_json()
        pid = data.get('producto_id')
        cant = int(data.get('cantidad', 1))
        
        conn = get_db_connection()
        prod = conn.execute("SELECT * FROM productos WHERE id=? AND activo=1", (pid,)).fetchone()
        conn.close()
        
        if not prod: return jsonify({'success': False, 'error': 'Producto no existe'}), 404
        if prod['stock'] < cant: return jsonify({'success': False, 'error': 'Stock insuficiente'}), 400
        
        carrito = session.get('carrito', {})
        key = str(pid)
        
        if key in carrito:
            nueva = carrito[key]['cantidad'] + cant
            if nueva > prod['stock']: return jsonify({'success': False, 'error': 'Stock máximo alcanzado'}), 400
            carrito[key]['cantidad'] = nueva
        else:
            carrito[key] = {'nombre': prod['nombre'], 'precio': float(prod['precio']), 'cantidad': cant}
            
        session['carrito'] = carrito
        session.modified = True
        
        return jsonify({
            'success': True, 
            'total_items': sum(i['cantidad'] for i in carrito.values()),
            'stock_actual': prod['stock'] - cant,
            'mensaje': f"Agregaste {prod['nombre']}"
        })
    except Exception as e: return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/carrito/actualizar', methods=['POST'])
def api_actualizar_carrito():
    try:
        data = request.get_json()
        pid = str(data.get('producto_id'))
        cant = int(data.get('cantidad', 1))
        carrito = session.get('carrito', {})
        
        if pid in carrito:
            if cant <= 0: del carrito[pid]
            else:
                stock = obtener_stock_actual(int(pid))
                if cant > stock: return jsonify({'success': False, 'error': 'Stock insuficiente'}), 400
                carrito[pid]['cantidad'] = cant
            session['carrito'] = carrito
            session.modified = True
            return jsonify({'success': True, 'total_items': sum(i['cantidad'] for i in carrito.values())})
        return jsonify({'success': False, 'error': 'No encontrado'}), 404
    except Exception as e: return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/carrito/eliminar/<int:producto_id>', methods=['DELETE'])
def api_eliminar_item(producto_id):
    carrito = session.get('carrito', {})
    if str(producto_id) in carrito:
        del carrito[str(producto_id)]
        session['carrito'] = carrito
        session.modified = True
        return jsonify({'success': True, 'total_items': sum(i['cantidad'] for i in carrito.values())})
    return jsonify({'success': False, 'error': 'No encontrado'}), 404

@app.route('/api/carrito/limpiar', methods=['POST'])
def api_limpiar_carrito():
    session['carrito'] = {}
    session.modified = True
    return jsonify({'success': True, 'total_items': 0})

@app.route('/api/carrito/debug', methods=['GET'])
def api_carrito_debug():
    """Ruta para debug del JS"""
    carrito = session.get('carrito', {})
    return jsonify({
        'success': True,
        'carrito': carrito,
        'user': current_user.username if current_user.is_authenticated else None,
        'is_authenticated': current_user.is_authenticated
    })

# ========================================================
#  RUTAS DE CARRITO HTML (Sin Login)
# ========================================================

@app.route("/carrito")
def ver_carrito():
    carrito = session.get("carrito", {})
    carrito_validado = {}
    for pid, item in carrito.items():
        try:
            stock = obtener_stock_actual(int(pid))
            if stock > 0:
                if item['cantidad'] > stock: item['cantidad'] = stock
                carrito_validado[pid] = item
        except: pass
    session["carrito"] = carrito_validado
    return render_template("ver_carrito.html", carrito=carrito_validado)

@app.route("/actualizar_cantidad_carrito", methods=["POST"])
def actualizar_cantidad_carrito():
    pid = request.form.get("producto_id")
    accion = request.form.get("accion")
    carrito = session.get("carrito", {})
    if pid in carrito:
        if accion == "incrementar":
            if carrito[pid]["cantidad"] < obtener_stock_actual(int(pid)): carrito[pid]["cantidad"] += 1
            else: flash("Stock máximo.", "warning")
        elif accion == "decrementar":
            if carrito[pid]["cantidad"] > 1: carrito[pid]["cantidad"] -= 1
            else: del carrito[pid]
        session["carrito"] = carrito
        session.modified = True
    return redirect(url_for("ver_carrito"))

@app.route("/eliminar_del_carrito/<int:producto_id>", methods=["POST"])
def eliminar_del_carrito(producto_id):
    carrito = session.get("carrito", {})
    if str(producto_id) in carrito:
        del carrito[str(producto_id)]
        session["carrito"] = carrito
        session.modified = True
        flash("Producto eliminado.", "info")
    return redirect(url_for("ver_carrito"))

@app.route("/vaciar_carrito", methods=["POST"])
def vaciar_carrito():
    session["carrito"] = {}
    session.modified = True
    flash("Carrito vaciado", "info")
    return redirect(url_for("ver_carrito"))

@app.route("/agregar_al_carrito/<int:producto_id>", methods=["POST"])
def agregar_al_carrito_html(producto_id):
    try: cantidad = int(request.form.get("cantidad", 1))
    except: cantidad = 1
    stock = obtener_stock_actual(producto_id)
    if cantidad > stock:
        flash("Stock insuficiente", "warning")
        return redirect(url_for("index"))
    conn = get_db_connection()
    prod = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    conn.close()
    carrito = session.get("carrito", {})
    key = str(producto_id)
    if key in carrito: carrito[key]["cantidad"] += cantidad
    else: carrito[key] = {"nombre": prod["nombre"], "precio": float(prod["precio"]), "cantidad": cantidad}
    session["carrito"] = carrito
    session.modified = True
    flash(f"Agregado: {prod['nombre']}", "success")
    return redirect(url_for("index"))

# ========================================================
#  CHECKOUT Y PAGOS (CON LOGIN OBLIGATORIO)
# ========================================================

@app.route("/finalizar_compra")
@login_required
@rol_requerido("cliente")
def finalizar_compra():
    carrito = session.get("carrito", {})
    if not carrito: return redirect(url_for("index"))
    conn = get_db_connection()
    items_checkout = []
    subtotal = 0
    for pid, item in carrito.items():
        p = conn.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
        if p and p['stock'] >= item['cantidad']:
            st = item['cantidad'] * float(p['precio'])
            items_checkout.append({'id': pid, 'nombre': p['nombre'], 'precio': p['precio'], 'cantidad': item['cantidad'], 'subtotal': st})
            subtotal += st
    metodo = conn.execute("SELECT * FROM metodos_pago WHERE usuario_id=? AND predeterminado=1", (current_user.id,)).fetchone()
    conn.close()
    return render_template("checkout.html", carrito=items_checkout, total=subtotal, metodo_guardado=metodo)

@app.route("/confirmar_compra", methods=["POST"])
@login_required
@rol_requerido("cliente")
def confirmar_compra():
    carrito = session.get("carrito", {})
    if not carrito: return redirect(url_for("index"))
    total = sum(int(item["cantidad"]) * float(item["precio"]) for item in carrito.values())
    metodo_pago = request.form.get("metodo_pago", "tarjeta")
    return render_template("confirmar_compra.html", carrito=carrito, total=total, metodo_pago=metodo_pago)

@app.route("/procesar_pago", methods=["POST"])
@login_required
@rol_requerido("cliente")
def procesar_pago():
    time.sleep(3) # Espera 3 seg
    carrito = session.get("carrito", {})
    if not carrito: return redirect(url_for("index"))
    
    total = sum(i['cantidad'] * i['precio'] for i in carrito.values())
    nro_pedido = f"VDL-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}"
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO ventas (usuario_id, total, fecha, estado, numero_pedido) VALUES (?, ?, ?, ?, ?)",
                    (current_user.id, total, datetime.now(), "completada", nro_pedido))
        venta_id = cur.lastrowid
        for pid, item in carrito.items():
            cur.execute("INSERT INTO venta_items (venta_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)",
                        (venta_id, pid, item['cantidad'], item['precio']))
            cur.execute("UPDATE productos SET stock = stock - ? WHERE id=?", (item['cantidad'], pid))
        conn.commit()
        session['carrito'] = {}
        session.modified = True
        flash("¡Pago exitoso!", "success")
        return redirect(url_for("comprobante_pago", numero_pedido=nro_pedido))
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for("finalizar_compra"))
    finally: conn.close()

# ========================================================
#  PDF Y COMPROBANTES
# ========================================================

@app.route("/comprobante/<numero_pedido>")
@login_required
@rol_requerido("cliente")
def comprobante_pago(numero_pedido):
    conn = get_db_connection()
    venta = conn.execute("SELECT * FROM ventas WHERE numero_pedido=? AND usuario_id=?", (numero_pedido, current_user.id)).fetchone()
    if not venta: return redirect(url_for("mis_compras"))
    items = conn.execute("SELECT p.nombre, vi.cantidad, vi.precio_unitario FROM venta_items vi JOIN productos p ON vi.producto_id=p.id WHERE vi.venta_id=?", (venta['id'],)).fetchall()
    conn.close()
    return render_template("comprobante_pago.html", venta=venta, items=items, fecha=datetime.now())

@app.route("/descargar_comprobante/<numero_pedido>")
@login_required
@rol_requerido("cliente")
def descargar_comprobante(numero_pedido):
    conn = get_db_connection()
    venta = conn.execute("SELECT * FROM ventas WHERE numero_pedido=? AND usuario_id=?", (numero_pedido, current_user.id)).fetchone()
    if not venta: return redirect(url_for("mis_compras"))
    items = conn.execute("SELECT p.nombre, vi.cantidad, vi.precio_unitario FROM venta_items vi JOIN productos p ON vi.producto_id=p.id WHERE vi.venta_id=?", (venta['id'],)).fetchall()
    conn.close()
    html = render_template("comprobante_pago.html", venta=venta, items=items, fecha=datetime.now(), es_pdf=True)
    pdf = BytesIO()
    pisa.CreatePDF(html, dest=pdf)
    pdf.seek(0)
    return send_file(pdf, as_attachment=True, download_name=f"Comprobante_{numero_pedido}.pdf", mimetype='application/pdf')

@app.route("/mis_compras")
@login_required
@rol_requerido("cliente")
def mis_compras():
    conn = get_db_connection()
    ventas = conn.execute("SELECT * FROM ventas WHERE usuario_id=? ORDER BY fecha DESC", (current_user.id,)).fetchall()
    data = []
    for v in ventas:
        items = conn.execute("SELECT p.nombre, vi.cantidad, vi.precio_unitario FROM venta_items vi JOIN productos p ON vi.producto_id=p.id WHERE vi.venta_id=?", (v['id'],)).fetchall()
        data.append({"venta": v, "items": items})
    conn.close()
    return render_template("mis_compras.html", compras=data)

@app.route("/cancelar_compra_rapida/<numero_pedido>", methods=["POST"])
@login_required
@rol_requerido("cliente")
def cancelar_compra_rapida(numero_pedido):
    conn = get_db_connection()
    venta = conn.execute("SELECT * FROM ventas WHERE numero_pedido=? AND usuario_id=?", (numero_pedido, current_user.id)).fetchone()
    if not venta: return redirect(url_for("mis_compras"))
    try: f = datetime.strptime(venta['fecha'], '%Y-%m-%d %H:%M:%S.%f')
    except: f = datetime.strptime(venta['fecha'], '%Y-%m-%d %H:%M:%S')
    if (datetime.now() - f).total_seconds() > 600:
        flash("Tiempo expirado.", "warning")
        return redirect(url_for("mis_compras"))
    items = conn.execute("SELECT producto_id, cantidad FROM venta_items WHERE venta_id=?", (venta['id'],)).fetchall()
    for i in items:
        conn.execute("UPDATE productos SET stock = stock + ? WHERE id=?", (i['cantidad'], i['producto_id']))
    conn.execute("UPDATE ventas SET estado='cancelada' WHERE id=?", (venta['id'],))
    conn.commit()
    conn.close()
    flash("Cancelado con éxito.", "success")
    return redirect(url_for("mis_compras"))

# ========================================================
#  DUEÑO Y VENDEDOR
# ========================================================

@app.route("/vendedor")
@login_required
@rol_requerido("vendedor")
def vendedor_view():
    conn = get_db_connection()
    prods = conn.execute("SELECT * FROM productos WHERE vendedor_id=? AND activo=1", (current_user.id,)).fetchall()
    bajo = conn.execute("SELECT * FROM productos WHERE vendedor_id=? AND stock < 10 AND activo=1", (current_user.id,)).fetchall()
    pend = conn.execute("SELECT cs.*, p.nombre FROM cambios_stock cs JOIN productos p ON cs.producto_id = p.id WHERE cs.estado='pendiente' AND cs.vendedor_id=?", (current_user.id,)).fetchall()
    conn.close()
    return render_template("vendedor.html", productos=prods, productos_bajo=bajo, cambios_pendientes=pend)

@app.route("/agregar_producto", methods=["GET", "POST"])
@login_required
@rol_requerido("vendedor")
def agregar_producto():
    if request.method == "POST":
        nombre = request.form["nombre"]
        descripcion = request.form.get("descripcion", "")
        try:
            precio = float(request.form["precio"])
            stock = int(request.form["stock"])
        except:
            flash("Precio o stock inválidos", "danger")
            return redirect(url_for("agregar_producto"))
        categoria = request.form.get("categoria", "")
        imagen_url = request.form.get("imagen_url", "")
        
        # Imagen por defecto si está vacía
        if not imagen_url:
            if categoria == 'Frutas': imagen_url = "https://images.pexels.com/photos/1132047/pexels-photo-1132047.jpeg?auto=compress&cs=tinysrgb&w=400"
            elif categoria == 'Verduras': imagen_url = "https://images.pexels.com/photos/533360/pexels-photo-533360.jpeg?auto=compress&cs=tinysrgb&w=400"

        conn = get_db_connection()
        conn.execute("INSERT INTO productos (nombre, descripcion, precio, stock, categoria, vendedor_id, imagen_url, activo) VALUES (?,?,?,?,?,?,?,1)",
                     (nombre, descripcion, precio, stock, categoria, current_user.id, imagen_url))
        conn.commit()
        conn.close()
        flash("Producto agregado", "success")
        return redirect(url_for("vendedor_view"))
    return render_template("agregar_producto.html")

@app.route("/solicitar_cambio_producto/<int:producto_id>", methods=["GET", "POST"])
@login_required
@rol_requerido("vendedor")
def solicitar_cambio_producto(producto_id):
    conn = get_db_connection()
    p = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    if request.method == "POST":
        n_st = int(request.form.get("stock"))
        n_pr = float(request.form.get("precio"))
        pct = ((n_st - p["stock"]) / p["stock"] * 100) if p["stock"] > 0 else 100
        conn.execute("INSERT INTO cambios_stock (producto_id, vendedor_id, stock_anterior, stock_nuevo, precio_anterior, precio_nuevo, porcentaje_cambio, motivo, estado, fecha_solicitud) VALUES (?,?,?,?,?,?,?,?,'pendiente', datetime('now'))",
                     (producto_id, current_user.id, p["stock"], n_st, p["precio"], n_pr, pct, request.form.get("motivo","")))
        conn.commit()
        flash("Solicitud enviada", "success")
        return redirect(url_for('vendedor_view'))
    conn.close()
    return render_template("solicitar_cambio.html", producto=p)

@app.route("/solicitar_baja_producto/<int:producto_id>", methods=["POST"])
@login_required
@rol_requerido("vendedor")
def solicitar_baja_producto(producto_id):
    conn = get_db_connection()
    p = conn.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    conn.execute("INSERT INTO cambios_stock (producto_id, vendedor_id, stock_anterior, stock_nuevo, precio_anterior, precio_nuevo, porcentaje_cambio, motivo, estado, fecha_solicitud) VALUES (?,?,?,?,?,?,?,?,'pendiente', datetime('now'))",
                 (producto_id, current_user.id, p["stock"], 0, p["precio"], p["precio"], -100, "Baja"))
    conn.commit()
    flash("Baja solicitada", "success")
    return redirect(url_for("vendedor_view"))

@app.route("/panel_dueno")
@login_required
@rol_requerido("dueno")
def panel_dueno():
    conn = get_db_connection()
    stats = conn.execute("SELECT COUNT(*) as total_ventas, COALESCE(SUM(total), 0) as total_ingresos FROM ventas WHERE estado='completada'").fetchone()
    pend = conn.execute("SELECT cs.*, p.nombre, u.username as vendedor FROM cambios_stock cs JOIN productos p ON cs.producto_id=p.id JOIN usuarios u ON cs.vendedor_id=u.id WHERE cs.estado='pendiente' ORDER BY cs.fecha_solicitud DESC").fetchall()
    top = conn.execute("SELECT p.nombre, SUM(vi.cantidad) as total FROM venta_items vi JOIN productos p ON vi.producto_id=p.id JOIN ventas v ON vi.venta_id=v.id WHERE v.estado='completada' GROUP BY p.id ORDER BY total DESC LIMIT 5").fetchall()
    aut = conn.execute("SELECT cs.*, p.nombre, u1.username as vendedor FROM cambios_stock cs JOIN productos p ON cs.producto_id=p.id JOIN usuarios u1 ON cs.vendedor_id=u1.id WHERE cs.estado='autorizado' ORDER BY cs.fecha_autorizacion DESC LIMIT 10").fetchall()
    conn.close()
    return render_template("panel_dueno.html", stats=stats, cambios_pendientes=pend, top_productos=top, cambios_autorizados=aut)

@app.route("/autorizar_cambio_stock/<int:cambio_id>", methods=["POST"])
@login_required
@rol_requerido("dueno")
def autorizar_cambio_stock(cambio_id):
    conn = get_db_connection()
    c = conn.execute("SELECT * FROM cambios_stock WHERE id=?", (cambio_id,)).fetchone()
    
    if c:
        # SI ES UNA BAJA (Stock nuevo es 0 y el motivo dice Baja), LO DESACTIVAMOS
        if c['stock_nuevo'] == 0 and "Baja" in c['motivo']:
            conn.execute("UPDATE productos SET stock=0, activo=0 WHERE id=?", (c['producto_id'],))
            flash("Producto dado de baja y ocultado de la tienda.", "success")
        else:
            # SI ES UN CAMBIO DE PRECIO/STOCK NORMAL
            conn.execute("UPDATE productos SET stock=?, precio=? WHERE id=?", 
                         (c['stock_nuevo'], c['precio_nuevo'], c['producto_id']))
            flash("Cambio de stock/precio autorizado.", "success")

        # Marcar la solicitud como autorizada
        conn.execute("UPDATE cambios_stock SET estado='autorizado', autorizado_por=?, fecha_autorizacion=datetime('now') WHERE id=?", 
                     (current_user.id, cambio_id))
        
        conn.commit()
    
    conn.close()
    return redirect(url_for("panel_dueno"))

@app.route("/rechazar_cambio_stock/<int:cambio_id>", methods=["POST"])
@login_required
@rol_requerido("dueno")
def rechazar_cambio_stock(cambio_id):
    conn = get_db_connection()
    conn.execute("UPDATE cambios_stock SET estado='rechazado', fecha_autorizacion=datetime('now') WHERE id=?", (cambio_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("panel_dueno"))


@app.route("/solicitudes_pendientes")
@login_required
@rol_requerido("dueno")
def solicitudes_pendientes():
    conn = get_db_connection()
    solicitudes = conn.execute("""
        SELECT cs.*, p.nombre as producto_nombre, u.username as vendedor
        FROM cambios_stock cs 
        JOIN productos p ON cs.producto_id = p.id
        JOIN usuarios u ON cs.vendedor_id = u.id
        WHERE cs.estado = 'pendiente'
        ORDER BY cs.fecha_solicitud DESC
    """).fetchall()
    conn.close()
    return render_template("solicitudes_cambio.html", cambios=solicitudes)

# ========================================================
#  INICIO
# ========================================================

@app.route('/debug')
def debug_page(): return "Debug OK"

if __name__ == "__main__":
    app.run(debug=True, port=5000)
