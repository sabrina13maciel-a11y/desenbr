#!/bin/bash

# Configurar porta padrão se não estiver definida
export PORT=${PORT:-5000}

# Exibir configuração
echo "🚀 Iniciando aplicação na porta: $PORT"

# Iniciar gunicorn com porta configurável
exec gunicorn --bind 0.0.0.0:$PORT --reuse-port --reload main:app