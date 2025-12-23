import React, { useState, useEffect } from 'react';
import { Clock, AlertTriangle, CheckCircle, Terminal } from 'lucide-react';

const EventoTimeline = ({ log }) => {
    let icono = <Terminal size={16} />;
    let color = "text-gray-400";
    let borde = "border-gray-800";
    let bg = "bg-gray-900";

    if (log.tipo === 'ERROR') {
        icono = <AlertTriangle size={16} />;
        color = "text-[#ff0033]";
        borde = "border-[#ff0033]/50";
        bg = "bg-[#ff0033]/10";
    } else if (log.tipo === 'TRADE') {
        icono = <CheckCircle size={16} />;
        color = "text-[#00ff9d]";
        borde = "border-[#00ff9d]/50";
        bg = "bg-[#00ff9d]/10";
    }

    return (
        <div className="flex gap-4 group">
            <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${bg} ${color} border ${borde} z-10 relative`}>
                    {icono}
                </div>
                <div className="h-full w-px bg-gray-800 group-last:hidden mt-2"></div>
            </div>
            <div className="pb-8 flex-1">
                <div className="flex justify-between items-start mb-1">
                    <span className={`text-xs font-bold tracking-wider ${color}`}>{log.tipo}</span>
                    <span className="text-[10px] font-mono text-gray-600 flex items-center gap-1">
                        <Clock size={10} /> {log.hora}
                    </span>
                </div>
                <div className="p-3 bg-[#111] border border-[#222] rounded-lg text-sm text-gray-300 font-mono shadow-sm group-hover:border-gray-600 transition-colors">
                    <span className="text-blue-500 font-bold">[{log.origen}]</span> {log.evento}
                </div>
            </div>
        </div>
    );
};

const PanelLogs = () => {
    const [logs, setLogs] = useState([]);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                // Leemos el estado compartido (mismo que PanelControl)
                const res = await fetch('/estado_bot.json?t=' + Date.now());
                if (res.ok) {
                    const data = await res.json();
                    // Mapeamos los pensamientos del JSON al formato que espera este componente
                    // pensamientos: [{ timestamp, accion, razaon, moneda }]
                    const logsMapeados = (data.pensamientos || []).map((p, i) => ({
                        id: i,
                        tipo: p.accion.includes('ERROR') ? 'ERROR' : p.accion.includes('COMPRA') || p.accion.includes('VENTA') ? 'TRADE' : 'INFO',
                        hora: p.timestamp,
                        origen: 'CEREBRO',
                        evento: `[${p.moneda}] ${p.accion}: ${p.razon}`
                    }));
                    setLogs(logsMapeados);
                }
            } catch (error) { console.error("Error leyendo logs visuales:", error); }
        };

        fetchLogs(); // Primera carga
        const interval = setInterval(fetchLogs, 1000); // Polling más rápido (1s)
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="p-6 h-full zerox-bg relative overflow-y-auto custom-scrollbar">
            <header className="mb-8 pb-4 border-b border-white/10 flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-black text-white italic tracking-tighter">
                        HISTORIAL <span className="text-gray-600">DEL NÚCLEO</span>
                    </h1>
                    <p className="text-gray-500 text-xs mt-1">Registro inmutable de todas las acciones de la IA</p>
                </div>
                <div className="text-xs font-mono text-[#00ff9d] bg-[#00ff9d]/10 px-2 py-1 rounded">
                    SISTEMA ONLINE
                </div>
            </header>

            <div className="max-w-3xl">
                {logs.length > 0 ? (
                    logs.slice().reverse().map((log, i) => (
                        <EventoTimeline key={i} log={log} />
                    ))
                ) : (
                    <div className="text-center py-20 text-gray-600">
                        <Terminal size={48} className="mx-auto mb-4 opacity-20" />
                        <p>El sistema está limpio. Esperando eventos...</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PanelLogs;
