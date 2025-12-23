import React, { useState, useEffect } from 'react';
import { ClipboardList, ShieldAlert, Target, TrendingUp, Brain, FileText, ChevronRight, AlertTriangle } from 'lucide-react';

const PanelOperaciones = ({ datos }) => {
    // Usamos props (Hook Centralizado)
    const data = datos || { posiciones: [] };
    const [simboloSeleccionado, setSimboloSeleccionado] = useState(null);

    // Auto-selección inicial
    useEffect(() => {
        if (data.posiciones && data.posiciones.length > 0 && !simboloSeleccionado) {
            setSimboloSeleccionado(data.posiciones[0].simbolo);
        }
    }, [data.posiciones, simboloSeleccionado]);

    // Derivar la dato real de las props (Renderizado Siempre Fresco)
    const seleccionada = data.posiciones?.find(p => p.simbolo === simboloSeleccionado) || null;

    return (
        <div className="flex h-full bg-[#050505] text-white overflow-hidden">

            {/* 1. IZQUIERDA: LISTA DE OPERACIONES */}
            <div className="w-1/2 flex flex-col border-r border-[#1a1a1a]">
                <div className="p-6 border-b border-[#1a1a1a] flex items-center justify-between bg-[#0a0a0a]">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-900/20 rounded-lg text-blue-400">
                            <ClipboardList size={24} />
                        </div>
                        <div>
                            <h2 className="text-lg font-black tracking-tight">OPERACIONES ACTIVAS</h2>
                            <p className="text-xs text-gray-500 uppercase tracking-widest font-bold">
                                {data.posiciones?.length || 0} EN COMBATE
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-2">
                    {data.posiciones && data.posiciones.length > 0 ? (
                        data.posiciones.map((pos, idx) => (
                            <div
                                key={idx}
                                onClick={() => setSimboloSeleccionado(pos.simbolo)} // Solo guardamos ID
                                className={`
                                    cursor-pointer p-4 rounded-xl border transition-all duration-300
                                    flex items-center justify-between group
                                    ${simboloSeleccionado === pos.simbolo
                                        ? 'bg-[#111] border-blue-500/50 shadow-[0_0_20px_rgba(0,100,255,0.1)]'
                                        : 'bg-[#0a0a0a] border-[#1a1a1a] hover:bg-[#151515] hover:border-gray-700'}
                                `}
                            >
                                {/* Info Principal */}
                                <div className="flex items-center gap-4">
                                    <div className={`
                                        w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs
                                        ${pos.tipo === 'LARGO' ? 'bg-green-900/20 text-green-400' : 'bg-red-900/20 text-red-400'}
                                    `}>
                                        {pos.tipo === 'LARGO' ? 'L' : 'C'}
                                    </div>
                                    <div>
                                        <div className="font-bold text-sm tracking-wide">{pos.simbolo}</div>
                                        <div className="text-xs text-gray-500 font-mono">
                                            {pos.pnl} USDT
                                        </div>
                                    </div>
                                </div>

                                {/* Status Blindaje */}
                                <div className="flex flex-col items-end gap-1">
                                    {(!pos.tp || pos.tp === 0 || !pos.sl || pos.sl === 0) ? (
                                        <span className="flex items-center gap-1 text-[10px] bg-red-900/30 text-red-400 px-2 py-1 rounded border border-red-500/30 animate-pulse font-bold">
                                            <ShieldAlert size={10} /> SIN BLINDAJE
                                        </span>
                                    ) : (
                                        <span className="text-[10px] text-green-600 font-bold flex items-center gap-1">
                                            <ShieldCheckIcon /> PROTEGIDO
                                        </span>
                                    )}
                                    <ChevronRight size={16} className={`text-gray-600 transition-transform ${simboloSeleccionado === pos.simbolo ? 'translate-x-1 text-blue-400' : ''}`} />
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-gray-600 opacity-50">
                            <Target size={48} className="mb-4 text-gray-800" />
                            <p className="text-sm font-bold">SIN OPERACIONES</p>
                            <p className="text-sm font-bold mt-2 text-yellow-500/50">MODO DEMO ACTIVO</p>
                            <p className="text-xs">El sistema está escaneando...</p>
                        </div>
                    )}
                </div>
            </div>

            {/* 2. DERECHA: INFORME DE INTELIGENCIA */}
            <div className="w-1/2 bg-[#080808] flex flex-col relative">
                {seleccionada ? (
                    <div className="flex-1 flex flex-col h-full overflow-hidden">
                        {/* Header Informe */}
                        <div className="p-6 border-b border-[#1a1a1a] bg-[#0a0a0a]/50 backdrop-blur-sm sticky top-0 z-10">
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <h3 className="text-xl font-black text-white flex items-center gap-2">
                                        <Brain className="text-purple-500" /> INFORME DE MENTE MAESTRA
                                    </h3>
                                    <p className="text-xs text-gray-400 mt-1 font-mono">
                                        ID: {seleccionada.simbolo} | ENTRADA: {seleccionada.entrada}
                                    </p>
                                </div>
                                <div className={`text-2xl font-black ${parseFloat(seleccionada.pnl) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                    {seleccionada.pnl} $
                                </div>
                            </div>

                            {/* Niveles Tácticos */}
                            <div className="grid grid-cols-2 gap-3 mb-2">
                                <div className="bg-[#111] p-2 rounded border border-[#222]">
                                    <div className="text-[10px] text-green-500 font-bold mb-1">TAKE PROFIT (Target)</div>
                                    <div className="font-mono text-lg font-bold text-white">
                                        {seleccionada.tp ? Number(seleccionada.tp).toFixed(4) : <span className="text-red-500 text-xs">NO DEFINIDO</span>}
                                    </div>
                                </div>
                                <div className="bg-[#111] p-2 rounded border border-[#222]">
                                    <div className="text-[10px] text-red-500 font-bold mb-1">STOP LOSS (Riesgo)</div>
                                    <div className="font-mono text-lg font-bold text-white">
                                        {seleccionada.sl ? Number(seleccionada.sl).toFixed(4) : <span className="text-red-500 text-xs">NO DEFINIDO</span>}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Cuerpo del Informe (Scrollable) */}
                        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">

                            {/* 1. Análisis Técnico */}
                            <div className="group">
                                <h4 className="flex items-center gap-2 text-sm font-bold text-blue-400 mb-2 uppercase tracking-wider">
                                    <TrendingUp size={16} /> Justificación Técnica
                                </h4>
                                <div className="p-4 bg-blue-900/10 border border-blue-900/30 rounded-lg text-sm text-gray-300 leading-relaxed group-hover:bg-blue-900/20 transition-colors">
                                    {seleccionada.analisis?.tecnico || "Esperando análisis de Mente Maestra..."}
                                </div>
                            </div>

                            {/* 2. Psicología */}
                            <div className="group">
                                <h4 className="flex items-center gap-2 text-sm font-bold text-purple-400 mb-2 uppercase tracking-wider">
                                    <Brain size={16} /> Perfil Psicológico
                                </h4>
                                <div className="p-4 bg-purple-900/10 border border-purple-900/30 rounded-lg text-sm text-gray-300 leading-relaxed italic group-hover:bg-purple-900/20 transition-colors">
                                    "{seleccionada.analisis?.psicologia || "Analizando sesgo de mercado..."}"
                                </div>
                            </div>

                            {/* 3. Fuentes */}
                            <div className="group">
                                <h4 className="flex items-center gap-2 text-sm font-bold text-yellow-500 mb-2 uppercase tracking-wider">
                                    <FileText size={16} /> Inteligencia de Fuentes
                                </h4>
                                <div className="p-4 bg-yellow-900/10 border border-yellow-900/30 rounded-lg text-xs text-gray-400 font-mono leading-relaxed group-hover:bg-yellow-900/20 transition-colors">
                                    {seleccionada.analisis?.fuentes || "Escaneando cerebro para correlaciones..."}
                                </div>
                            </div>

                        </div>
                    </div>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-700">
                        <Brain size={64} className="mb-4 opacity-20" />
                        <p className="text-sm font-bold uppercase tracking-widest opacity-50">Selecciona una operación</p>
                    </div>
                )}
            </div>
        </div>
    );
};

// Icono helper
const ShieldCheckIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-shield-check"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /><path d="m9 12 2 2 4-4" /></svg>
);

export default PanelOperaciones;
