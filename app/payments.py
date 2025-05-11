import os
import json
import requests

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

def obtener_token_paypal():
    url = "https://api-m.paypal.com/v1/oauth2/token"
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data, auth=auth)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print("Error al obtener token de PayPal:", response.text)
        return None

def generar_enlace_de_pago(user_id):
    token = obtener_token_paypal()
    if not token:
        return "Error al obtener token de PayPal."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    body = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": "1.00"
                },
                "custom_id": user_id
            }
        ],
        "application_context": {
            "return_url": f"https://example.com/return/{user_id}",
            "cancel_url": f"https://example.com/cancel/{user_id}"
        }
    }

    url = "https://api-m.paypal.com/v2/checkout/orders"
    response = requests.post(url, headers=headers, json=body)
    result = response.json()

    for link in result.get("links", []):
        if link["rel"] == "approve":
            return link["href"]
    return "Error al generar el enlace de pago."

def verificar_pago(user_id):
    token = obtener_token_paypal()
    if not token:
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    url = f"https://api-m.paypal.com/v2/checkout/orders?custom_id={user_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        orders = response.json().get("orders", [])
        for order in orders:
            if order.get("status") == "COMPLETED":
                return True
    return False

