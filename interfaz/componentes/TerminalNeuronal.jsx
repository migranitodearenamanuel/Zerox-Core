import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Cpu, Activity, ShieldAlert } from 'lucide-react';

const TerminalNeuronal = ({ pensamientos }) => {
    // Si no hay pensamientos, mostramos placeholders
    const datos = pensamientos || [];

    return (
        <div className="w-full bg-black/90 border border-green-500/30 rounded-lg p-4 font-mono text-xs h-96 flex flex-col shadow-[0_0_20px_rgba(0,255,0,0.1)] overflow-hidden relative">
            {/* CABECERA */}
            <div className="flex items-center justify-between mb-2 border-b border-green-500/30 pb-2">
                <div className="flex items-center gap-2 text-green-400">
                    <Terminal size={14} />
                    <span className="font-bold tracking-widest">FLUJO NEURONAL</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="animate-pulse text-green-500 text-[10px]">● EN VIVO</span>
                    <span className="text-green-500/50">{datos.length} eventos</span>
                </div>
            </div>

            {/* CUERPO DEL LOG (SCROLLABLE) */}
            <div className="flex-1 overflow-y-auto space-y-1 pr-2 custom-scrollbar">
                <AnimatePresence initial={false}>
                    {datos.map((log) => (
                        <motion.div
                            key={log.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className={`
                                p-2 border-l-2 mb-1 bg-black/50 hover:bg-green-900/10 cursor-default transition-colors
                                ${(log.accion && log.accion.includes('COMPRA')) ? 'border-yellow-400 text-yellow-100' :
                                    (log.accion && log.accion.includes('VENTA')) ? 'border-red-400 text-red-100' :
                                        'border-green-600/30 text-green-400/80'}
                            `}
                        >
                            <div className="flex justify-between items-start">
                                <span className="text-green-600/50 text-[10px] min-w-[60px]">{log.timestamp}</span>
                                <span className={`font-bold mx-2 ${log.accion === 'ESPERAR' ? 'text-gray-500' : 'text-white'
                                    }`}>
                                    [{log.moneda}] {log.accion}
                                </span>
                                <span className="flex-1 text-right truncate opacity-80" title={log.razon}>
                                    {log.razon}
                                </span>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {datos.length === 0 && (
                    <div className="text-center text-green-800 mt-20 animate-pulse">
                        ESPERANDO PRIMERA SINAPSIS...
                    </div>
                )}
            </div>

            {/* SCANLINES DECORATIVAS */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-10 bg-[length:100%_2px,3px_100%] opacity-20"></div>
        </div>
    );
};

export default TerminalNeuronal;
