#!/bin/bash

# Script para configurar porta customizada
# Uso: ./set-port.sh [PORTA]

if [ "$1" ]; then
    export PORT=$1
    echo "✅ Porta configurada para: $PORT"
else
    export PORT=${PORT:-5000}
    echo "✅ Usando porta padrão: $PORT"
fi

echo "🔧 Para iniciar a aplicação com esta porta, execute:"
echo "   ./start.sh"
echo ""
echo "📝 Para configurar permanentemente, adicione nas variáveis de ambiente:"
echo "   export PORT=$PORT"