"""
TikTok Conversions API (CAPI) — server-side event tracking
Pixel: D5JG0KRC77U2KB72JBVG
"""
import hashlib
import time
import uuid
import requests
import logging

TIKTOK_PIXEL_CODES = [
    'D5JG0KRC77U2KB72JBVG',
    'DA835D3C77UES9745010',
    'DATMBQJC77U2INVDDEIG',
    'DAU5QIRC77U36HVUOSU0',
]
TIKTOK_PIXEL_CODE = TIKTOK_PIXEL_CODES[0]
TIKTOK_ACCESS_TOKEN = '604ceaa89ad255b22c669094ada45989e02f6952'
TIKTOK_EVENTS_URL  = 'https://business-api.tiktok.com/open_api/v1.3/event/track/'

logger = logging.getLogger(__name__)


def _sha256(value: str) -> str:
    """Hash a string with SHA-256 (lowercase + stripped)."""
    if not value:
        return ''
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def send_purchase(
    *,
    event_id: str,
    value: float,
    currency: str = 'BRL',
    content_id: str = 'desenrola-acordo',
    cpf: str = '',
    email: str = '',
    phone: str = '',
    ip: str = '',
    user_agent: str = '',
    ttclid: str = '',
    ttp: str = '',
    page_url: str = '',
):
    """Fire a Purchase event to TikTok CAPI."""
    try:
        # Normalise phone to E.164 (+55...)
        phone_norm = ''.join(filter(str.isdigit, phone))
        if phone_norm and not phone_norm.startswith('55'):
            phone_norm = '55' + phone_norm

        results = []
        for pcode in TIKTOK_PIXEL_CODES:
            properties = {
                'pixel_code': pcode,
                'event':      'Purchase',
                'event_id':   f"{event_id}_{pcode}",
                'timestamp':  int(time.time()),
                'context': {
                    'user': {
                        'external_id': _sha256(cpf) if cpf else '',
                        'email':       _sha256(email) if email else '',
                        'phone_number': _sha256(phone_norm) if phone_norm else '',
                        'ip':          ip,
                        'user_agent':  user_agent,
                        'ttclid':      ttclid,
                        'ttp':         ttp,
                    },
                    'page': {
                        'url': page_url,
                    }
                },
                'properties': {
                    'value':      value,
                    'currency':   currency,
                    'content_id': content_id,
                    'content_type': 'product',
                }
            }

            headers = {
                'Access-Token': TIKTOK_ACCESS_TOKEN,
                'Content-Type': 'application/json',
            }

            resp = requests.post(
                TIKTOK_EVENTS_URL,
                json={'data': [properties]},
                headers=headers,
                timeout=8,
            )
            result = resp.json()
            logger.info(f"[TIKTOK_CAPI] Purchase sent pixel={pcode} event_id={event_id} → {result}")
            results.append(result)

        return results[0] if results else None

    except Exception as e:
        logger.error(f"[TIKTOK_CAPI] Erro ao enviar Purchase: {e}")
        return None


def send_initiate_checkout(
    *,
    event_id: str,
    value: float,
    currency: str = 'BRL',
    cpf: str = '',
    ip: str = '',
    user_agent: str = '',
    page_url: str = '',
):
    """Fire an InitiateCheckout event to TikTok CAPI for all configured pixels."""
    try:
        results = []
        for pcode in TIKTOK_PIXEL_CODES:
            properties = {
                'pixel_code': pcode,
                'event':      'InitiateCheckout',
                'event_id':   f"{event_id}_{pcode}",
                'timestamp':  int(time.time()),
                'context': {
                    'user': {
                        'external_id': _sha256(cpf) if cpf else '',
                        'ip':          ip,
                        'user_agent':  user_agent,
                    },
                    'page': {'url': page_url}
                },
                'properties': {
                    'value':    value,
                    'currency': currency,
                }
            }

            headers = {
                'Access-Token': TIKTOK_ACCESS_TOKEN,
                'Content-Type': 'application/json',
            }

            resp = requests.post(
                TIKTOK_EVENTS_URL,
                json={'data': [properties]},
                headers=headers,
                timeout=8,
            )
            result = resp.json()
            logger.info(f"[TIKTOK_CAPI] InitiateCheckout sent pixel={pcode} event_id={event_id} → {result}")
            results.append(result)

        return results[0] if results else None

    except Exception as e:
        logger.error(f"[TIKTOK_CAPI] Erro ao enviar InitiateCheckout: {e}")
        return None
