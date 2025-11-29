console.log('✅ carrito.js cargado - Modo E-commerce (Carrito Anónimo Habilitado)');

if (typeof window.CarritoManager === 'undefined') {
    
    class CarritoManager {
        constructor() {
            console.log('🛒 Inicializando CarritoManager...');
            this.csrfToken = this.getCSRFToken();
            this.usuarioAutenticado = false;
            this.carritoCargado = false;
            this.totalItems = 0;
            
            this.initEventListeners();
            
            // Verificamos sesión pero NO bloqueamos si no hay usuario
            this.verificarAutenticacion().then(() => {
                console.log('✅ Inicialización completa');
                console.log('👤 Estado usuario:', this.usuarioAutenticado ? 'Registrado' : 'Invitado (Anónimo)');
            });
        }

        getCSRFToken() {
            let token = '';
            const selectors = [
                'input[name="csrf_token"]',
                'input[name="csrf-token"]',
                'meta[name="csrf-token"]',
                'meta[name="csrf_token"]',
                '[data-csrf-token]'
            ];
            
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element) {
                    token = element.value || element.content || element.dataset.csrfToken;
                    if (token) break;
                }
            }
            return token;
        }

        async verificarAutenticacion() {
            try {
                // Consultamos al backend quién es el usuario
                const response = await fetch('/api/carrito/debug', {
                    method: 'GET',
                    headers: { 'Accept': 'application/json', 'Cache-Control': 'no-cache' }
                });
                
                if (response.status === 401) {
                    // Es un invitado, pero PERMITIMOS que use el carrito
                    this.usuarioAutenticado = false;
                    this.actualizarContadorCarrito(); // Actualizamos igual por si tiene items en cookie
                    return;
                }
                
                const data = await response.json();
                
                if (data.success && data.user) {
                    this.usuarioAutenticado = true;
                    console.log('✅ Usuario detectado:', data.user);
                } else {
                    this.usuarioAutenticado = false;
                    console.log('ℹ️ Navegando como invitado');
                }
                
                // En ambos casos (Auth o Invitado) actualizamos el carrito
                await this.actualizarContadorCarrito();
                
            } catch (error) {
                console.warn('⚠️ No se pudo verificar sesión (posiblemente offline o error de red)', error);
                this.usuarioAutenticado = false;
            }
        }

        initEventListeners() {
            // Click en "Agregar al carrito"
            document.addEventListener('click', (e) => {
                const botonCarrito = e.target.closest('.btn-agregar-carrito');
                
                if (botonCarrito) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // ¡OJO! ACÁ QUITAMOS EL BLOQUEO DE LOGIN
                    // Ya no verificamos "if (!this.usuarioAutenticado)"
                    
                    this.agregarProducto(botonCarrito);
                }
            });

            // Actualizar al volver a la pestaña
            document.addEventListener('visibilitychange', () => {
                if (!document.hidden) {
                    this.actualizarContadorCarrito();
                }
            });
        }

        mostrarLoginRequired(boton) {
            // Este método queda por si lo necesitas para el Checkout final, 
            // pero ya no se usa al agregar productos.
            if (window.mostrarToast) {
                window.mostrarToast('🔐 Inicia sesión para continuar', 'warning');
            }
        }

        async agregarProducto(boton) {
            // 1. Validaciones básicas del botón
            if (!boton || !boton.dataset) return;
            
            const productoId = boton.dataset.productoId;
            const productoNombre = boton.dataset.productoNombre;
            
            if (!productoId) {
                this.mostrarError('Error: ID de producto no encontrado');
                return;
            }
            
            // 2. Feedback visual (Loading)
            const originalText = boton.innerHTML;
            boton.innerHTML = '🔄 ...';
            boton.disabled = true;
            
            try {
                // 3. Enviamos al backend (El backend debe manejar si es User o Session anónima)
                const response = await fetch('/api/carrito/agregar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken || '', // Enviamos token si existe
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        producto_id: parseInt(productoId),
                        cantidad: 1
                    })
                });

                // Si el backend devuelve 401 es porque explícitamente rechaza anónimos.
                // (Idealmente tu app.py debería devolver 200 y guardar en sesión)
                if (response.status === 401) {
                    this.mostrarLoginRequired(boton);
                    return; 
                }
                
                const data = await response.json();
                
                if (data.success) {
                    // ÉXITO
                    this.mostrarNotificacion(`✅ <strong>${productoNombre}</strong> agregado`);
                    
                    // Actualizamos contador (badge)
                    const nuevosItems = data.total_items || data.cantidad_items || this.totalItems + 1;
                    this.totalItems = nuevosItems;
                    this.actualizarBadgeCarrito(nuevosItems);
                    
                    // Si el backend devuelve stock actual, actualizamos la UI
                    if (data.stock_actual !== undefined) {
                        this.actualizarStockUI(productoId, data.stock_actual, boton);
                    }
                    
                } else {
                    // ERROR DEL NEGOCIO (Ej: Sin stock)
                    this.mostrarError(data.error || 'No se pudo agregar');
                }
                
            } catch (error) {
                console.error('Error:', error);
                this.mostrarError('Error de conexión');
            } finally {
                // 4. Restauramos el botón
                setTimeout(() => {
                    if (!boton.innerHTML.includes('Sin Stock')) {
                        boton.innerHTML = originalText;
                        boton.disabled = false;
                    }
                }, 500);
            }
        }

        actualizarStockUI(productoId, stockActual, boton) {
            // Busca donde se muestra el stock y lo actualiza
            const stockSelectors = [
                `.stock-${productoId}`,
                `[data-stock-producto="${productoId}"]`
            ];
            
            let stockElement = null;
            for (const selector of stockSelectors) {
                stockElement = document.querySelector(selector);
                if (stockElement) break;
            }
            
            if (stockElement) {
                stockElement.textContent = `📦 Stock: ${stockActual}`;
                if (stockActual < 5) stockElement.style.color = 'red';
            }
            
            if (stockActual === 0) {
                boton.disabled = true;
                boton.innerHTML = '❌ Sin Stock';
            }
        }

        async actualizarContadorCarrito() {
            try {
                // Pedimos cantidad actual al servidor
                const response = await fetch('/api/carrito', {
                    headers: { 'Accept': 'application/json' }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        const total = data.total_items || data.cantidad_items || 0;
                        this.totalItems = total;
                        this.actualizarBadgeCarrito(total);
                    }
                }
            } catch (error) {
                console.error('Error actualizando carrito:', error);
            }
        }

        actualizarBadgeCarrito(totalItems) {
            // Busca el badge en el header/nav
            let contador = document.getElementById('contador-carrito');
            
            // Si no existe, intenta crearlo en el link del carrito
            if (!contador) {
                const linkCarrito = document.querySelector('a[href*="carrito"]');
                if (linkCarrito) {
                    contador = document.createElement('span');
                    contador.id = 'contador-carrito';
                    contador.className = 'badge bg-danger rounded-pill ms-1'; // Clases Bootstrap
                    contador.style.fontSize = '0.7em';
                    linkCarrito.appendChild(contador);
                }
            }
            
            if (contador) {
                contador.textContent = totalItems;
                contador.style.display = totalItems > 0 ? 'inline-block' : 'none';
            }
        }

        mostrarNotificacion(mensaje) {
            // Usa Toastify o crea un elemento flotante simple
            if (window.mostrarToast) {
                window.mostrarToast(mensaje, 'success');
                return;
            }
            // Fallback simple: crear div
            const div = document.createElement('div');
            div.innerHTML = mensaje;
            div.style.cssText = 'position:fixed; top:20px; right:20px; background:#28a745; color:white; padding:10px 20px; border-radius:5px; z-index:9999;';
            document.body.appendChild(div);
            setTimeout(() => div.remove(), 3000);
        }

        mostrarError(mensaje) {
            if (window.mostrarToast) {
                window.mostrarToast(mensaje, 'error');
                return;
            }
            alert(mensaje);
        }
        
        // Método público
        actualizarCarrito() {
            this.actualizarContadorCarrito();
        }
    }

    // Inicializar
    window.CarritoManager = CarritoManager;
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.carritoManager = new CarritoManager());
    } else {
        window.carritoManager = new CarritoManager();
    }
    
    // Helper global
    window.actualizarCarrito = () => window.carritoManager?.actualizarCarrito();

} else {
    console.log('ℹ️ CarritoManager ya estaba cargado');
}