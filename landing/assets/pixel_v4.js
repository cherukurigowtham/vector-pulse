/**
 * Vantix Universal Pixel v4.0
 * Cognitive Behavioral Intelligence Capture.
 */
(function() {
    const CONFIG = {
        endpoint: '/v1/behavior/ingest',
        flushInterval: 5000, // Flush every 5s
        maxEvents: 50,
        apiKey: new URLSearchParams(document.currentScript.src.split('?')[1]).get('id')
    };

    let eventQueue = [];
    let sessionId = sessionStorage.getItem('vantix_sid') || 'v4_' + Math.random().toString(36).substr(2, 16);
    sessionStorage.setItem('vantix_sid', sessionId);

    function capture(type, data = {}) {
        eventQueue.push({
            event_type: type,
            path: window.location.pathname,
            timestamp: Date.now() / 1000,
            ...data
        });
        if (eventQueue.length >= CONFIG.maxEvents) flush();
    }

    async function flush() {
        if (eventQueue.length === 0 || !CONFIG.apiKey) return;
        
        const payload = {
            session_id: sessionId,
            events: [...eventQueue],
            client_metadata: {
                ua: navigator.userAgent,
                res: `${window.innerWidth}x${window.innerHeight}`,
                lang: navigator.language
            }
        };
        
        eventQueue = []; // Clear local queue immediately
        
        try {
            await fetch(CONFIG.endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': CONFIG.apiKey
                },
                body: JSON.stringify(payload)
            });
        } catch (e) {
            console.warn('Vantix Pixel: Ingestion delayed.');
        }
    }

    // Auto-capture life cycle events
    window.addEventListener('click', (e) => {
        capture('click', { element: e.target.tagName, x: e.clientX, y: e.clientY });
    });

    window.addEventListener('scroll', () => {
        // Debounced or simple sampling? Simple for now.
        if (Math.random() > 0.95) capture('scroll', { y: window.scrollY });
    });

    // Form interaction speed
    let focusTime = 0;
    window.addEventListener('focusin', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
            focusTime = Date.now();
            capture('focus', { element: e.target.name || e.target.id });
        }
    });

    window.addEventListener('focusout', (e) => {
        if (focusTime > 0) {
            const dwell = Date.now() - focusTime;
            capture('blur', { element: e.target.name || e.target.id, dwell_time_ms: dwell });
            focusTime = 0;
        }
    });

    // Periodic flush
    setInterval(flush, CONFIG.flushInterval);

    // Initial load signal
    capture('pageview');

    console.log('Vantix v4.0 Pixel: Neural link active.');
})();
