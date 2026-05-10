with open('C:\\dashboard_trading\\dashboard.py', 'r', encoding='utf-8') as f:
    contenido = f.read()

contenido_corregido = contenido.expandtabs(4)

with open('C:\\dashboard_trading\\dashboard.py', 'w', encoding='utf-8') as f:
    f.write(contenido_corregido)

print('Indentacion corregida correctamente')