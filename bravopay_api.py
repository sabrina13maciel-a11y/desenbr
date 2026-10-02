import os
import uuid
import logging
import requests

logger = logging.getLogger("bravopay")

class BravoPayAPI:
    BASE_URL = "https://bravopay.club/api/v1"

    def __init__(self, secret_key=None):
        self.secret_key = (secret_key or os.environ.get('BRAVOPAY_SECRET_KEY', '')).strip()
        if not self.secret_key:
            # Fallback para a chave fornecida
            self.secret_key = "bp_live_9oTQegc-PM9LmscTLi6N3CdFHRxYYfsAIFR_LA"

        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info("[BRAVOPAY] API Client inicializado com sucesso.")

    def create_transaction(self, customer_data, amount, description="DBR", external_reference=None, utm=None):
        """
        Cria uma cobrança PIX via BravoPay.
        amount em reais (ex: 148.37) -> convertido para centavos (14837).
        """
        try:
            amount_cents = int(round(float(amount) * 100))
            if amount_cents < 500:
                amount_cents = 500  # Mínimo exigido pela BravoPay é R$ 5,00 (500 cents)

            customer_name = customer_data.get('nome', 'Cliente').strip() or 'Cliente'
            customer_cpf = ''.join(filter(str.isdigit, customer_data.get('cpf', '00000000000')))
            customer_email = customer_data.get('email', 'cliente@email.com').strip()
            
            raw_phone = customer_data.get('phone', '11999999999').strip()
            clean_phone = ''.join(filter(str.isdigit, raw_phone))
            if clean_phone and not clean_phone.startswith('55') and len(clean_phone) in [10, 11]:
                clean_phone = f"55{clean_phone}"

            ext_ref = external_reference or f"dbr_{uuid.uuid4().hex[:12]}"

            # Nome do produto/descrição definido estritamente como DBR
            product_label = "DBR"

            payload = {
                "amount_cents": amount_cents,
                "method": "pix",
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                    "cpf": customer_cpf
                },
                "description": product_label,
                "items": [
                    {
                        "title": product_label,
                        "unit_price_cents": amount_cents,
                        "quantity": 1,
                        "tangible": False
                    }
                ],
                "external_reference": ext_ref
            }

            if clean_phone:
                payload["customer"]["phone"] = clean_phone

            if utm and isinstance(utm, dict):
                payload["utm"] = utm

            logger.info(f"[BRAVOPAY] Criando transação PIX - Nome: {customer_name}, CPF: {customer_cpf}, R${amount} ({amount_cents} cents)")

            response = requests.post(
                f"{self.BASE_URL}/transactions",
                headers=self.headers,
                json=payload,
                timeout=25
            )

            logger.info(f"[BRAVOPAY] Resposta status: {response.status_code}")

            if response.status_code in [200, 201]:
                data = response.json()
                tx_id = data.get('id', '')
                pix_data = data.get('pix') or {}
                copy_paste = pix_data.get('copy_paste', '')
                qr_code = pix_data.get('qr_code', '')

                logger.info(f"[BRAVOPAY] Transação PIX criada com sucesso: {tx_id}")

                return {
                    'success': True,
                    'transaction_id': tx_id,
                    'order_id': tx_id,
                    'qr_code': copy_paste,
                    'pixCode': copy_paste,
                    'pixQrCode': qr_code,
                    'amount': amount,
                    'status': data.get('status', 'PENDING'),
                    'raw_response': data
                }
            else:
                error_msg = f"Erro na API BravoPay ({response.status_code})"
                try:
                    err_json = response.json()
                    error_msg = err_json.get('error', {}).get('message', str(err_json))
                except Exception:
                    error_msg = response.text

                logger.error(f"[BRAVOPAY] Falha ao criar transação: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }

        except Exception as e:
            logger.error(f"[BRAVOPAY] Erro na requisição: {e}", exc_info=True)
            return {
                'success': False,
                'error': f"Erro interno de conexão: {str(e)}"
            }

    def get_transaction(self, transaction_id):
        """
        Consulta o status de uma transação na BravoPay.
        """
        try:
            logger.info(f"[BRAVOPAY] Consultando transação: {transaction_id}")
            response = requests.get(
                f"{self.BASE_URL}/transactions/{transaction_id}",
                headers=self.headers,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                status_raw = str(data.get('status', '')).upper()

                status_norm = 'pending'
                if status_raw in ['PAID', 'APPROVED', 'PAGO']:
                    status_norm = 'approved'
                elif status_raw in ['EXPIRED', 'FAILED', 'REJECTED']:
                    status_norm = 'failed'
                elif status_raw in ['REFUNDED', 'CHARGEBACK']:
                    status_norm = 'refunded'

                return {
                    'success': True,
                    'status': status_norm,
                    'status_raw': status_raw,
                    'transaction_id': transaction_id,
                    'data': data
                }
            else:
                logger.error(f"[BRAVOPAY] Erro ao consultar transação ({response.status_code})")
                return {
                    'success': False,
                    'status': 'unknown',
                    'error': f"Transação não encontrada ({response.status_code})"
                }

        except Exception as e:
            logger.error(f"[BRAVOPAY] Erro na consulta de transação: {e}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e)
            }


def create_bravopay_api(secret_key=None):
    return BravoPayAPI(secret_key=secret_key)
