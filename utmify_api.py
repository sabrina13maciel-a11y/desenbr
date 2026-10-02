import os
import re
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('utmify')

UTMIFY_API_URL = "https://api.utmify.com.br/api-credentials/orders"
DEFAULT_TOKEN = "eieWvaCRVzozsag9MueRkZeCCh7ElqdvIaPL"

# Cache em memória para guardar dados de pedidos pendentes para envio posterior do "paid"
_ORDERS_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()


def get_utmify_token() -> str:
    """Obtém o token da Utmify da variável de ambiente ou padrão."""
    return os.environ.get("UTMIFY_API_TOKEN", DEFAULT_TOKEN).strip()


def sanitize_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos do CPF."""
    return re.sub(r'[^0-9]', '', str(cpf or ''))


def sanitize_phone(phone: str) -> Optional[str]:
    """Limpa e formata o telefone para dígitos apenas."""
    digits = re.sub(r'[^0-9]', '', str(phone or ''))
    return digits if len(digits) >= 10 else None


def format_tracking_parameters(tracking: Optional[Dict[str, Any]] = None) -> Dict[str, Optional[str]]:
    """Garante a estrutura correta de parâmetros de tracking."""
    tracking = tracking or {}
    return {
        "src": tracking.get("src") or None,
        "sck": tracking.get("sck") or None,
        "utm_source": tracking.get("utm_source") or None,
        "utm_campaign": tracking.get("utm_campaign") or None,
        "utm_medium": tracking.get("utm_medium") or None,
        "utm_content": tracking.get("utm_content") or None,
        "utm_term": tracking.get("utm_term") or None,
    }


def _send_payload_request(payload: Dict[str, Any]) -> bool:
    """Executa a requisição HTTP POST para a API da Utmify."""
    token = get_utmify_token()
    if not token:
        logger.warning("[UTMIFY] Token não configurado. Envio ignorado.")
        return False

    headers = {
        "Content-Type": "application/json",
        "x-api-token": token
    }

    try:
        logger.info(f"[UTMIFY] Enviando pedido {payload.get('orderId')} com status '{payload.get('status')}'...")
        response = requests.post(UTMIFY_API_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            logger.info(f"[UTMIFY] Sucesso para {payload.get('orderId')}: {response.text}")
            return True
        else:
            logger.error(f"[UTMIFY] Erro {response.status_code} para {payload.get('orderId')}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"[UTMIFY] Falha na requisição para {payload.get('orderId')}: {e}")
        return False


def send_order_async(payload: Dict[str, Any]):
    """Dispara o envio para a Utmify em segundo plano para não onerar o fluxo HTTP do cliente."""
    thread = threading.Thread(target=_send_payload_request, args=(payload,), daemon=True)
    thread.start()


def track_waiting_payment(
    order_id: str,
    amount: float,
    customer: Dict[str, Any],
    product_name: str = "Quitação de Dívidas - Acordo Desenrola Brasil",
    product_id: str = "desenrola-acordo",
    tracking: Optional[Dict[str, Any]] = None,
    ip: str = "127.0.0.1",
    is_test: bool = False
):
    """
    Envia evento de venda pendente ('waiting_payment') para a Utmify e guarda no cache.
    """
    if not order_id:
        return

    clean_cpf = sanitize_cpf(customer.get("cpf", ""))
    clean_phone = sanitize_phone(customer.get("phone", ""))
    price_in_cents = int(round(float(amount) * 100))
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    clean_tracking = format_tracking_parameters(tracking)

    customer_payload = {
        "name": str(customer.get("nome") or customer.get("name") or "CLIENTE").strip(),
        "email": str(customer.get("email") or "cliente@desenrolabrasil.gov.br").strip(),
        "phone": clean_phone,
        "document": clean_cpf if clean_cpf else None,
        "country": "BR",
        "ip": ip or "127.0.0.1"
    }

    products_payload = [
        {
            "id": product_id,
            "name": product_name,
            "planId": None,
            "planName": None,
            "quantity": 1,
            "priceInCents": price_in_cents
        }
    ]

    commission_payload = {
        "totalPriceInCents": price_in_cents,
        "gatewayFeeInCents": 0,
        "userCommissionInCents": price_in_cents,
        "currency": "BRL"
    }

    payload = {
        "orderId": str(order_id),
        "platform": "BravoPay",
        "paymentMethod": "pix",
        "status": "waiting_payment",
        "createdAt": created_at,
        "approvedDate": None,
        "refundedAt": None,
        "customer": customer_payload,
        "products": products_payload,
        "trackingParameters": clean_tracking,
        "commission": commission_payload,
        "isTest": is_test
    }

    # Salva em cache para uso quando a transação for aprovada
    with _CACHE_LOCK:
        _ORDERS_CACHE[str(order_id)] = {
            "orderId": str(order_id),
            "amount": amount,
            "priceInCents": price_in_cents,
            "customer": customer_payload,
            "products": products_payload,
            "trackingParameters": clean_tracking,
            "commission": commission_payload,
            "createdAt": created_at,
            "paid_sent": False
        }

    send_order_async(payload)


def track_paid(
    order_id: str,
    amount: Optional[float] = None,
    customer: Optional[Dict[str, Any]] = None,
    product_name: str = "Quitação de Dívidas - Acordo Desenrola Brasil",
    product_id: str = "desenrola-acordo",
    tracking: Optional[Dict[str, Any]] = None,
    ip: str = "127.0.0.1",
    is_test: bool = False
):
    """
    Envia evento de venda paga ('paid') para a Utmify.
    Recupera dados salvos do cache para garantir integridade.
    Evita envios duplicados de 'paid' para o mesmo order_id.
    """
    if not order_id:
        return

    order_key = str(order_id)
    cached = None

    with _CACHE_LOCK:
        cached = _ORDERS_CACHE.get(order_key)
        if cached and cached.get("paid_sent"):
            logger.info(f"[UTMIFY] Evento 'paid' já enviado anteriormente para {order_key}. Ignorando duplicata.")
            return
        if cached:
            cached["paid_sent"] = True

    approved_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    if cached:
        payload = {
            "orderId": cached["orderId"],
            "platform": "BravoPay",
            "paymentMethod": "pix",
            "status": "paid",
            "createdAt": cached["createdAt"],
            "approvedDate": approved_date,
            "refundedAt": None,
            "customer": cached["customer"],
            "products": cached["products"],
            "trackingParameters": cached["trackingParameters"],
            "commission": cached["commission"],
            "isTest": is_test
        }
    else:
        # Se não estiver em cache, monta com os dados fornecidos
        amount_val = float(amount or 148.37)
        price_in_cents = int(round(amount_val * 100))
        created_at = approved_date
        clean_cpf = sanitize_cpf((customer or {}).get("cpf", ""))
        clean_phone = sanitize_phone((customer or {}).get("phone", ""))
        clean_tracking = format_tracking_parameters(tracking)

        customer_payload = {
            "name": str((customer or {}).get("nome") or (customer or {}).get("name") or "CLIENTE").strip(),
            "email": str((customer or {}).get("email") or "cliente@desenrolabrasil.gov.br").strip(),
            "phone": clean_phone,
            "document": clean_cpf if clean_cpf else None,
            "country": "BR",
            "ip": ip or "127.0.0.1"
        }

        products_payload = [
            {
                "id": product_id,
                "name": product_name,
                "planId": None,
                "planName": None,
                "quantity": 1,
                "priceInCents": price_in_cents
            }
        ]

        commission_payload = {
            "totalPriceInCents": price_in_cents,
            "gatewayFeeInCents": 0,
            "userCommissionInCents": price_in_cents,
            "currency": "BRL"
        }

        payload = {
            "orderId": order_key,
            "platform": "BravoPay",
            "paymentMethod": "pix",
            "status": "paid",
            "createdAt": created_at,
            "approvedDate": approved_date,
            "refundedAt": None,
            "customer": customer_payload,
            "products": products_payload,
            "trackingParameters": clean_tracking,
            "commission": commission_payload,
            "isTest": is_test
        }

    send_order_async(payload)
