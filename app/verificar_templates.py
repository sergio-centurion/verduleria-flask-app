# verificar_templates.py
import os
import re

print("🔍 Verificando templates...")

problemas = []

for filename in os.listdir('templates'):
    if filename.endswith('.html'):
        filepath = os.path.join('templates', filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Contar endblocks
            endblock_count = content.count('{% endblock %}')
            
            # Verificar si hay endblocks duplicados consecutivos
            duplicados = re.search(r'{% endblock %}\s*{% endblock %}', content)
            
            print(f"{filename}: {endblock_count} endblocks")
            
            if endblock_count > 2:
                problemas.append(f"{filename}: {endblock_count} endblocks (más de 2)")
            elif duplicados:
                problemas.append(f"{filename}: endblocks duplicados consecutivos")
            elif endblock_count == 0:
                problemas.append(f"{filename}: 0 endblocks")
                
        except Exception as e:
            problemas.append(f"{filename}: ERROR - {e}")

print("\n" + "="*50)
if problemas:
    print("❌ PROBLEMAS ENCONTRADOS:")
    for problema in problemas:
        print(f"   - {problema}")
else:
    print("✅ Todos los templates están correctos!")