import React, { useState, useEffect } from 'react';
import { Activity, Brain, Target, Crosshair, TrendingUp, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';

const PanelDerecho = () => {
    const [data, setData] = useState({
        estado: "OFFLINE",
        simbolo: "---",
        precio: 0,
        rsi: 50,
        razonamiento_ia: "Esperando conexión con el núcleo...",
        posicion: null,
        posiciones: [] // Lista de posiciones
    });

    const [indicePosicion, setIndicePosicion] = useState(0);

    // Auto-fetch local para ser independiente (o recibir props, pero el usuario pidió que funcione)
    // El usuario dijo "Borra ChatTactico... Crea PanelDerecho". 
    // Lo haremos independiente para que sea plug & play en App.jsx
    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('/estado_bot.json?t=' + Date.now());
                if (res.ok) {
                    const json = await res.json();
                    setData(prev => ({ ...prev, ...json }));
                }
            } catch (e) {
                console.error("Error fetching cockpit data", e);
            }
        };
        const interval = setInterval(fetchData, 1000);
        return () => clearInterval(interval);
    }, []);

    // Helpers UI
    const rsiColor = data.rsi > 70 ? 'bg-red-500' : data.rsi < 30 ? 'bg-green-500' : 'bg-blue-500';
    const rsiWidth = `${Math.min(Math.max(data.rsi, 0), 100)}%`;

    // Determinar qué mostrar
    const listaPosiciones = data.posiciones && data.posiciones.length > 0 ? data.posiciones : (data.posicion ? [data.posicion] : []);
    const posicionActual = listaPosiciones[indicePosicion] || listaPosiciones[0];
    const totalPosiciones = listaPosiciones.length;

    // Handlers
    const siguientePosicion = () => setIndicePosicion((prev) => (prev + 1) % totalPosiciones);
    const anteriorPosicion = () => setIndicePosicion((prev) => (prev - 1 + totalPosiciones) % totalPosiciones);

    return (
        <div className="w-[350px] h-full bg-[#050505] border-l border-[#1a1a1a] flex flex-col font-mono text-xs overflow-hidden">

            {/* HEADER */}
            <div className="p-4 border-b border-[#1a1a1a] flex justify-between items-center bg-[#0a0a0a]">
                <div className="flex items-center gap-2 text-[#0088ff] font-bold tracking-widest uppercase">
                    <Crosshair size={14} /> COCKPIT
                </div>
                <div className={`px-2 py-1 rounded text-[10px] font-bold ${data.estado.includes("OPERANDO") ? "bg-green-900/30 text-green-400" : "bg-gray-800 text-gray-500"}`}>
                    {data.estado}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar p-4 flex flex-col gap-6">

                {/* MÓDULO 1: TELEMETRÍA */}
                <div className="bg-[#0f0f0f] border border-[#1a1a1a] rounded p-3">
                    <div className="flex items-center gap-2 mb-3 text-gray-400 font-bold">
                        <Activity size={12} /> TELEMETRÍA TÁCTICA
                    </div>

                    {/* Precio Jumbo */}
                    <div className="text-2xl font-black text-white mb-4 tracking-tighter">
                        {data.precio?.toLocaleString()} <span className="text-gray-600 text-sm">USDT</span>
                    </div>

                    {/* RSI Bar */}
                    <div className="mb-4">
                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                            <span>RSI</span>
                            <span className={data.rsi > 70 || data.rsi < 30 ? "text-yellow-400 animate-pulse" : ""}>{data.rsi?.toFixed(1)}</span>
                        </div>
                        <div className="h-2 bg-gray-800 rounded-full overflow-hidden relative">
                            <div className={`h-full transition-all duration-500 ${rsiColor}`} style={{ width: rsiWidth }}></div>
                            {/* Zonas clave */}
                            <div className="absolute top-0 bottom-0 left-[30%] w-[1px] bg-white/10"></div>
                            <div className="absolute top-0 bottom-0 left-[70%] w-[1px] bg-white/10"></div>
                        </div>
                    </div>

                    {/* MACD Mini (Simulado visualmente si no hay dato complejo) */}
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                        <div className="bg-[#050505] p-2 rounded border border-[#1a1a1a] text-center">
                            <div className="text-gray-500">VOLUMEN (24h)</div>
                            <div className="text-white mt-1 font-bold">{data.datos_tecnicos?.volumen_24h || "---"}</div>
                        </div>
                        <div className="bg-[#050505] p-2 rounded border border-[#1a1a1a] text-center">
                            <div className="text-gray-500">TENDENCIA</div>
                            <div className={data.rsi > 50 ? "text-green-500 mt-1 font-bold" : "text-red-500 mt-1 font-bold"}>
                                {data.datos_tecnicos?.tendencia || "NEUTRO"}
                            </div>
                        </div>
                    </div>
                </div>

                {/* MÓDULO 2: ORDEN ACTIVA (CON CARROUSEL) */}
                {posicionActual ? (
                    <div className="bg-[#0f0f0f] border border-green-900/30 rounded p-3 relative overflow-hidden group">
                        <div className="absolute top-0 left-0 w-1 h-full bg-green-500"></div>

                        {/* Header con Navegación */}
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2 text-green-400 font-bold">
                                <Target size={12} className="animate-pulse" />
                                TARGET LOCKED ({totalPosiciones > 1 ? `${indicePosicion + 1}/${totalPosiciones}` : '1/1'})
                            </div>

                            {totalPosiciones > 1 && (
                                <div className="flex gap-1">
                                    <button onClick={anteriorPosicion} className="p-1 hover:bg-white/10 rounded transition-colors text-white">
                                        <ChevronLeft size={14} />
                                    </button>
                                    <button onClick={siguientePosicion} className="p-1 hover:bg-white/10 rounded transition-colors text-white">
                                        <ChevronRight size={14} />
                                    </button>
                                </div>
                            )}
                        </div>

                        <div className="text-lg font-bold text-white mb-2">{posicionActual.simbolo}</div>

                        <div className="space-y-2 text-[11px]">
                            <div className="flex justify-between border-b border-white/5 pb-1">
                                <span className="text-gray-500">TIPO</span>
                                <span className={`font-bold ${posicionActual.tipo === 'LARGO' ? 'text-green-400' : 'text-red-400'}`}>
                                    {posicionActual.tipo}
                                </span>
                            </div>
                            <div className="flex justify-between border-b border-white/5 pb-1">
                                <span className="text-gray-500">ENTRADA</span>
                                <span className="text-white font-mono">{posicionActual.entrada}</span>
                            </div>
                            <div className="flex justify-between border-b border-white/5 pb-1">
                                <span className="text-gray-500">TAKE PROFIT</span>
                                <span className="text-green-500 font-mono font-bold">{posicionActual.tp || data.datos_tecnicos?.tp_precio || "---"}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-500">STOP LOSS</span>
                                <span className="text-red-500 font-mono font-bold">{posicionActual.sl || data.datos_tecnicos?.sl_precio || "---"}</span>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="bg-[#0f0f0f] border border-[#1a1a1a] rounded p-4 text-center opacity-50 border-dashed">
                        <Target size={20} className="mx-auto mb-2 text-gray-600" />
                        <div className="text-gray-500">ESPERANDO SEÑAL...</div>
                    </div>
                )}

                {/* MÓDULO 3: CEREBRO RAG (LOGS) */}
                <div className="flex-1 min-h-[200px] bg-[#000] border border-[#1a1a1a] rounded p-3 flex flex-col">
                    <div className="flex items-center gap-2 mb-2 text-purple-400 font-bold border-b border-purple-900/20 pb-2">
                        <Brain size={12} /> CEREBRO (RAG MEMORY)
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar text-gray-300 leading-relaxed text-[11px] whitespace-pre-wrap font-sans">
                        {/* Fecha simulada para efecto log */}
                        <div className="text-purple-700 font-mono text-[9px] mb-1">
                            [{new Date().toLocaleTimeString()}] INFERENCIA ACTIVA:
                        </div>
                        {data.razonamiento_ia || "Cargando módulos de análisis cognitivo..."}
                    </div>
                    <div className="mt-2 text-[9px] text-center text-gray-600 uppercase tracking-widest">
                        Basado en Conocimiento Ingestado
                    </div>
                </div>

            </div>
        </div>
    );
};

export default PanelDerecho;
