import requests

TELEGRAM_TOKEN = "8562882529:AAGG4oGoUcnQcoZUYAFhY2upgoxcXuCQswk"
TELEGRAM_CHAT_ID = "1638205295"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
respuesta = requests.post(url, data={
    "chat_id": TELEGRAM_CHAT_ID,
    "text": "✅ Conexión con el dashboard funcionando correctamente!"
})

print(respuesta.json())