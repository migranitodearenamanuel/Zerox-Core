import { useState, useEffect } from 'react';

const useCerebro = () => {
    const [cerebro, setCerebro] = useState({
        estado: {
            estado_sistema: "CARGANDO...",
            simbolo: "---",
            precio: 0,
            rsi: 50,
            saldo_cuenta: "0.00",
            posicion: null,
            posiciones: [], // Lista segura
            razonamiento_actual: "Conectando con núcleo...",
            progreso: 0,
            pensamientos: []
        },
        noticias: {
            meta: { edicion: "OFFLINE", ultimahora: "Cargando sistema de noticias..." },
            noticias: [],
            videos: []
        },
        cargando: true
    });

    useEffect(() => {
        const fetchDatos = async () => {
            try {
                // 1. Fetch Estado Bot (Bajo coste, cada 1s)
                const resEstado = await fetch('/estado_bot.json?t=' + Date.now());
                const dataEstado = resEstado.ok ? await resEstado.json() : null;

                // 2. Fetch Noticias (Cacheable, pero leemos cada 1s por si hay update manual)
                // Realmente las noticias cambian cada 30min, pero leer el JSON local es barato.
                const resNoticias = await fetch('/noticias.json?t=' + Date.now());
                const dataNoticias = resNoticias.ok ? await resNoticias.json() : null;

                setCerebro(prev => ({
                    ...prev,
                    estado: dataEstado ? { ...prev.estado, ...dataEstado } : prev.estado,
                    noticias: dataNoticias ? { ...prev.noticias, ...dataNoticias } : prev.noticias,
                    cargando: false
                }));

            } catch (error) {
                console.error("⚠️ Error Sincronizando Cerebro:", error);
            }
        };

        fetchDatos(); // Primer fetch inmediato
        const intervalo = setInterval(fetchDatos, 500); // Polling 500ms (Alta Frecuencia)

        return () => clearInterval(intervalo);
    }, []);

    return cerebro;
};

export default useCerebro;
