// Gerenciador Centralizado de Múltiplos Pixels do TikTok Ads
(function() {
    // Lista de Pixels do TikTok Ads ativos na conta
    window.TIKTOK_PIXELS = [
        'D5JG0KRC77U2KB72JBVG',
        'DA835D3C77UES9745010',
        'DATMBQJC77U2INVDDEIG',
        'DAU5QIRC77U36HVUOSU0'
        // Novos pixels adicionados aqui conforme solicitado
    ];

    // Inicialização da biblioteca oficial do TikTok Pixel
    !function(w,d,t){
        w.TiktokAnalyticsObject=t;
        var ttq=w[t]=w[t]||[];
        ttq.methods=["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie","holdConsent","revokeConsent","grantConsent"];
        ttq.setAndDefer=function(t,e){t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}};
        for(var i=0;i<ttq.methods.length;i++)ttq.setAndDefer(ttq,ttq.methods[i]);
        ttq.instance=function(t){for(var e=ttq._i[t]||[],n=0;n<ttq.methods.length;n++)ttq.setAndDefer(e,ttq.methods[n]);return e};
        ttq.load=function(e,n){
            var r="https://analytics.tiktok.com/i18n/pixel/events.js",o=n&&n.partner;
            ttq._i=ttq._i||{},ttq._i[e]=[],ttq._i[e]._u=r,ttq._t=ttq._t||{},ttq._t[e]=+new Date,ttq._o=ttq._o||{},ttq._o[e]=n||{};
            n=document.createElement("script");n.type="text/javascript";n.async=!0;n.src=r+"?sdkid="+e+"&lib="+t;
            e=document.getElementsByTagName("script")[0];e.parentNode.insertBefore(n,e)
        };

        // Carrega automaticamente todos os pixels configurados
        if (window.TIKTOK_PIXELS && window.TIKTOK_PIXELS.length) {
            for (var p = 0; p < window.TIKTOK_PIXELS.length; p++) {
                ttq.load(window.TIKTOK_PIXELS[p]);
            }
        }
        ttq.page();
    }(window, document, 'ttq');

    // Função para rastrear VENDA PENDENTE (PIX Gerado) como conversão no TikTok Ads (CPA)
    window.trackTikTokPendingSale = function(val, name, txId) {
        if (!window.ttq) return;
        var tx = txId || ('tx_' + Date.now());
        var numVal = Number(val) || 0;
        var cName = name || 'desenrola-acordo';

        // 1. CompletePayment com status pending (dispara conversão no CPA do TikTok)
        ttq.track('CompletePayment', {
            value: numVal,
            currency: 'BRL',
            content_name: cName,
            content_id: cName,
            event_id: 'pending_' + tx,
            status: 'pending'
        });

        // 2. PlaceAnOrder (outro evento padrão de pedido criado)
        ttq.track('PlaceAnOrder', {
            value: numVal,
            currency: 'BRL',
            content_name: cName,
            content_id: cName,
            event_id: 'order_' + tx
        });

        // 3. InitiateCheckout
        ttq.track('InitiateCheckout', {
            value: numVal,
            currency: 'BRL',
            content_name: cName,
            content_id: cName,
            event_id: 'checkout_' + tx
        });

        console.log('[TikTok Multi-Pixel] Venda PENDENTE rastreada para todos os pixels:', { value: numVal, name: cName, tx: tx });
    };

    // Função para rastrear VENDA PAGA (PIX Aprovado) como conversão no TikTok Ads (CPA)
    window.trackTikTokPaidSale = function(val, name, txId) {
        if (!window.ttq) return;
        var tx = txId || ('tx_' + Date.now());
        var numVal = Number(val) || 0;
        var cName = name || 'desenrola-acordo';

        // 1. CompletePayment com status paid (dispara conversão no CPA do TikTok sem conflito)
        ttq.track('CompletePayment', {
            value: numVal,
            currency: 'BRL',
            content_name: cName,
            content_id: cName,
            event_id: 'paid_' + tx,
            status: 'paid'
        });

        // 2. Purchase (evento definitivo de compra realizada)
        ttq.track('Purchase', {
            value: numVal,
            currency: 'BRL',
            content_name: cName,
            content_id: cName,
            event_id: 'purchase_' + tx
        });

        console.log('[TikTok Multi-Pixel] Venda PAGA rastreada para todos os pixels:', { value: numVal, name: cName, tx: tx });
    };
})();
