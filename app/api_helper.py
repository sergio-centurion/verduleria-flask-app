import requests
import json

def buscar_producto_openfoodfacts(nombre):
    """Buscar producto en Open Food Facts"""
    try:
        print(f"🔍 Buscando en API: {nombre}")
        
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            'search_terms': nombre,
            'json': 1,
            'page_size': 3
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('products') and len(data['products']) > 0:
                producto = data['products'][0]
                return {
                    'encontrado': True,
                    'nombre': producto.get('product_name', nombre),
                    'categoria': producto.get('categories', 'General').split(',')[0] if producto.get('categories') else 'General',
                    'imagen_url': producto.get('image_url', ''),
                    'marca': producto.get('brands', ''),
                    'ingredientes': producto.get('ingredients_text', '')
                }
        
        return {'encontrado': False, 'mensaje': 'No encontrado en API'}
        
    except Exception as e:
        print(f"❌ Error en API: {e}")
        return {'encontrado': False, 'error': str(e)}
