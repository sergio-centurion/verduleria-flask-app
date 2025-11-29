// static/js/tarjeta.js - VERSIÓN CORREGIDA Y DEFINITIVA
document.addEventListener("DOMContentLoaded", function () {
    // Elementos del DOM
    const numeroInput = document.getElementById("numero_tarjeta");
    const iconoTarjeta = document.getElementById("icono_tarjeta");
    const tipoTarjetaInput = document.getElementById("tipo_tarjeta");
    const feedbackDiv = document.getElementById("tipo-detection-feedback");
    const tipoDetectadoSpan = document.getElementById("tipo_detectado");
    const cvvInput = document.getElementById("cvv");
    const fechaInput = document.getElementById("fecha_vencimiento");
    
    // Si no hay campo de número de tarjeta, salir
    if (!numeroInput) return;

    // Configuración de tipos de tarjeta
    const tiposTarjeta = {
        visa: {
            nombre: "Visa",
            patrones: [/^4/],
            longitudes: [13, 16, 19],
            cvvLength: 3,
            formato: [4, 4, 4, 4]
        },
        mastercard: {
            nombre: "MasterCard",
            patrones: [/^5[1-5]/, /^2[2-7]/],
            longitudes: [16],
            cvvLength: 3,
            formato: [4, 4, 4, 4]
        },
        amex: {
            nombre: "American Express",
            patrones: [/^3[47]/],
            longitudes: [15],
            cvvLength: 4,
            formato: [4, 6, 5]
        },
        discover: {
            nombre: "Discover",
            patrones: [/^6011/, /^62/, /^64[4-9]/, /^65/],
            longitudes: [16, 19],
            cvvLength: 3,
            formato: [4, 4, 4, 4]
        }
    };

    // ========== EVENT LISTENERS ==========

    // Formateo automático del número de tarjeta
    numeroInput.addEventListener("input", function (e) {
        const input = e.target;
        const selectionStart = input.selectionStart;
        const valorOriginal = input.value;
        
        // Limpiar solo números
        const soloNumeros = valorOriginal.replace(/\D/g, "");
        
        // Detectar tipo de tarjeta
        const tipoDetectado = detectarTipoTarjeta(soloNumeros);
        
        // Formatear según el tipo
        let valorFormateado = formatearNumeroTarjeta(soloNumeros, tipoDetectado);
        
        // Actualizar valor manteniendo cursor
        input.value = valorFormateado;
        
        // Restaurar posición del cursor
        const nuevoCursorPos = calcularNuevaPosicionCursor(valorOriginal, valorFormateado, selectionStart);
        input.setSelectionRange(nuevoCursorPos, nuevoCursorPos);
        
        // Actualizar interfaz (Icono, CVV, etc)
        actualizarInterfazTarjeta(tipoDetectado, soloNumeros);
    });

    // Validación al perder foco
    numeroInput.addEventListener("blur", function() {
        const soloNumeros = this.value.replace(/\D/g, "");
        const tipoDetectado = detectarTipoTarjeta(soloNumeros);
        
        if (soloNumeros.length > 0) {
            validarTarjetaCompleta(soloNumeros, tipoDetectado);
        }
    });

    // Formatear fecha de vencimiento
    if (fechaInput) {
        fechaInput.addEventListener('input', function(e) {
            // 1. Guardamos la posición del cursor
            let start = this.selectionStart;

            // 2. Limpiamos todo lo que no sea número
            let input = this.value.replace(/\D/g, '');
             
            // 3. Lógica de Mes (no permitir mes 13, 14, etc)
            if(input.length >= 1){
                const primerDigito = parseInt(input.charAt(0));
                if (primerDigito > 1){
                    // Si escribe un 2..9 al principio, asumimos "02", "03", etc.
                    input = '0' + input;
                    start++;
                }
            }
            
            // 4. Formatear con la barra /
            let formatted = '';
            if(input.length > 2){
                formatted = input.substring(0, 2) + '/' + input.substring(2, 4);
            } else {
                formatted = input;
            }

            this.value = formatted;
            
            // 5. Manejo de borrado (backspace) para que no se trabe en la barra
            if (e.inputType === 'deleteContentBackward' && this.value.length === 2) {
                // Comportamiento natural
            }
        });
    }

    // Validar input de CVV (solo números)
    if (cvvInput) {
        cvvInput.addEventListener('input', function() {
            this.value = this.value.replace(/\D/g, '');
        });
    }

    // ========== FUNCIONES PRINCIPALES ==========

    // Función para detectar tipo de tarjeta
    function detectarTipoTarjeta(numero) {
        if (!numero || numero.length === 0) return null;
        
        for (const [tipo, config] of Object.entries(tiposTarjeta)) {
            for (const patron of config.patrones) {
                if (patron.test(numero)) {
                    return tipo;
                }
            }
        }
        return null;
    }

    // Función para formatear número de tarjeta
    function formatearNumeroTarjeta(numero, tipo) {
        if (!numero) return "";
        
        const config = tiposTarjeta[tipo];
        
        if (config && tipo === "amex") {
            // American Express: formato 4-6-5
            if (numero.length <= 4) return numero;
            if (numero.length <= 10) return numero.substring(0, 4) + " " + numero.substring(4);
            return numero.substring(0, 4) + " " + numero.substring(4, 10) + " " + numero.substring(10, 15);
        } else if (config) {
            // Otras tarjetas: grupos de 4 dígitos
            return numero.replace(/(.{4})/g, '$1 ').trim();
        } else {
            // Tipo desconocido: grupos de 4 por defecto
            return numero.replace(/(.{4})/g, '$1 ').trim();
        }
    }

    // Función para calcular posición del cursor
    function calcularNuevaPosicionCursor(valorAnterior, valorNuevo, cursorAnterior) {
        const digitosAntesDelCursor = valorAnterior.substring(0, cursorAnterior).replace(/\D/g, '').length;
        let digitosEncontrados = 0;
        
        for (let i = 0; i < valorNuevo.length; i++) {
            if (digitosEncontrados >= digitosAntesDelCursor) {
                return i;
            }
            if (/\d/.test(valorNuevo[i])) {
                digitosEncontrados++;
            }
        }
        return valorNuevo.length;
    }

    // Función para actualizar toda la interfaz (Icono, Input oculto, CVV)
    function actualizarInterfazTarjeta(tipo, numero) {
        const config = tiposTarjeta[tipo];
        
        // 1. Actualizar restricciones de CVV dinámicamente
        if (cvvInput) {
            // Si es AMEX, permitimos 4. Si es otra, solo 3.
            const longitudCVV = (tipo === 'amex') ? 4 : 3;
            
            cvvInput.maxLength = longitudCVV;
            cvvInput.placeholder = '0'.repeat(longitudCVV);
            
            // Si el usuario ya escribió 4 dígitos y cambiamos a Visa, cortamos el sobrante
            if (cvvInput.value.length > longitudCVV) {
                cvvInput.value = cvvInput.value.slice(0, longitudCVV);
            }
        }

        // 2. Actualizar UI según tipo detectado
        if (config) {
            // Actualizar icono
            mostrarLogoTarjeta(tipo);
            
            // Actualizar select/input oculto
            if (tipoTarjetaInput) {
                tipoTarjetaInput.value = tipo;
            }
            
            // Mostrar feedback visual
            if (feedbackDiv && tipoDetectadoSpan) {
                tipoDetectadoSpan.textContent = config.nombre;
                feedbackDiv.style.display = 'block';
                feedbackDiv.className = 'detection-feedback valid';
            }
            
            // Actualizar restricciones de longitud
            actualizarLongitudMaxima(tipo);
            
            // Validación visual preliminar (colores verde/amarillo)
            if (numero.length > 0) {
                const esLongitudValida = config.longitudes.includes(numero.length);
                numeroInput.classList.toggle('input-valid', esLongitudValida);
                numeroInput.classList.toggle('input-warning', !esLongitudValida && numero.length > 0);
            }
        } else {
            // Tipo desconocido
            if (iconoTarjeta) iconoTarjeta.style.display = 'none';
            if (feedbackDiv) feedbackDiv.style.display = 'none';
            numeroInput.classList.remove('input-valid', 'input-warning');
            
            // Restablecer CVV por defecto
            if (cvvInput) {
                cvvInput.maxLength = 3;
                cvvInput.placeholder = '123';
            }
        }
    }

    // Función para mostrar logo de tarjeta
    function mostrarLogoTarjeta(tipo) {
        if (!iconoTarjeta) return;
        
        const logos = {
            visa: "/static/icons/visa.svg",
            mastercard: "/static/icons/mastercard.svg", 
            amex: "/static/icons/amex.svg",
            discover: "/static/icons/discover.svg"
        };
        
        if (logos[tipo]) {
            iconoTarjeta.src = logos[tipo];
            iconoTarjeta.style.display = 'inline-block';
            iconoTarjeta.alt = tipo;
            
            iconoTarjeta.onerror = function() {
                this.style.display = 'none';
            };
        } else {
            iconoTarjeta.style.display = 'none';
        }
    }

    // Función para actualizar longitud máxima del input
    function actualizarLongitudMaxima(tipo) {
        const config = tiposTarjeta[tipo];
        if (config && numeroInput) {
            const longitudMax = Math.max(...config.longitudes);
            const espaciosExtra = tipo === "amex" ? 2 : 3;
            numeroInput.maxLength = longitudMax + espaciosExtra;
        }
    }

    // Función para validación completa
    function validarTarjetaCompleta(numero, tipo) {
        const config = tiposTarjeta[tipo];
        
        if (!config) {
            // Si hay números pero no se reconoce el tipo
            if (numero.length > 0) mostrarError("Tarjeta no reconocida");
            return false;
        }
        
        // Validar longitud
        if (!config.longitudes.includes(numero.length)) {
            mostrarError(`${config.nombre} debe tener ${config.longitudes.join(' o ')} dígitos`);
            return false;
        }
        
        // Validar algoritmo de Luhn
        if (!validarAlgoritmoLuhn(numero)) {
            mostrarError("Número de tarjeta inválido");
            return false;
        }
        
        // Éxito
        mostrarExito(`${config.nombre} válida`);
        return true;
    }

    // Algoritmo de Luhn para validación matemática
    function validarAlgoritmoLuhn(numero) {
        let sum = 0;
        let alternar = false;
        
        for (let i = numero.length - 1; i >= 0; i--) {
            let digito = parseInt(numero[i]);
            
            if (alternar) {
                digito *= 2;
                if (digito > 9) {
                    digito -= 9;
                }
            }
            
            sum += digito;
            alternar = !alternar;
        }
        
        return sum % 10 === 0;
    }

    // Función para mostrar error visual
    function mostrarError(mensaje) {
        numeroInput.classList.add('input-error');
        numeroInput.classList.remove('input-valid', 'input-warning');
        
        if (feedbackDiv) {
            feedbackDiv.className = 'detection-feedback error';
            tipoDetectadoSpan.textContent = mensaje;
            feedbackDiv.style.display = 'block';
        }
    }

    // Función para mostrar éxito visual
    function mostrarExito(mensaje) {
        numeroInput.classList.remove('input-error', 'input-warning');
        numeroInput.classList.add('input-valid');
        
        if (feedbackDiv) {
            feedbackDiv.className = 'detection-feedback valid';
            tipoDetectadoSpan.textContent = mensaje;
        }
    }

    console.log("✅ tarjeta.js cargado correctamente");
});