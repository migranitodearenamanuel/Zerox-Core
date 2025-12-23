import React from 'react';
import { Clock, Target, ArrowRight, Activity, Trash2 } from 'lucide-react';

const PanelPendientes = ({ datos }) => {
    // Si no hay datos, array vacío
    const pendientes = datos?.pendientes || [];

    return (
        <div className="flex flex-col h-full bg-[#050505] p-6 lg:p-10">
            {/* CABECERA */}
            <div className="flex items-center justify-between mb-8 pb-6 border-b border-[#1a1a1a]">
                <div>
                    <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
                        <Clock className="text-yellow-500" size={32} />
                        OPERACIONES PENDIENTES
                    </h1>
                    <p className="text-sm text-gray-400 mt-2 font-mono uppercase tracking-widest pl-12">
                        BÚFER DE EJECUCIÓN VIRTUAL | MAX 30 SLOTS
                    </p>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-[#111] rounded-lg border border-[#222]">
                    <div className={`w-2 h-2 rounded-full ${pendientes.length > 0 ? 'bg-yellow-500 animate-pulse' : 'bg-gray-600'}`}></div>
                    <span className="text-xs font-bold text-gray-300">
                        {pendientes.length} / 30 EN COLA
                    </span>
                </div>
            </div>

            {/* TABLA DE ÓRDENES */}
            <div className="flex-1 overflow-auto rounded-xl border border-[#1a1a1a] bg-[#0a0a0a] shadow-xl relative custom-scrollbar">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-[#111] text-xs uppercase text-gray-500 font-bold sticky top-0 z-10">
                        <tr>
                            <th className="p-4 border-b border-[#222]">Símbolo</th>
                            <th className="p-4 border-b border-[#222]">Tipo</th>
                            <th className="p-4 border-b border-[#222]">Rol</th>
                            <th className="p-4 border-b border-[#222]">Gatillo</th>
                            <th className="p-4 border-b border-[#222]">Precio Actual</th>
                            <th className="p-4 border-b border-[#222]">Distancia</th>
                            <th className="p-4 border-b border-[#222] text-right">Estado</th>
                        </tr>
                    </thead>
                    <tbody className="font-mono text-sm">
                        {pendientes.length > 0 ? (
                            pendientes.map((orden, i) => {
                                const distancia = ((orden.precio_actual - orden.precio_gatillo) / orden.precio_gatillo) * 100;
                                const distanciaAbs = Math.abs(distancia).toFixed(2);
                                const cerca = Math.abs(distancia) < 0.5;

                                return (
                                    <tr key={i} className="group hover:bg-[#151515] transition-colors border-b border-[#1a1a1a]">
                                        <td className="p-4 font-bold text-white group-hover:text-yellow-400 transition-colors">
                                            {orden.simbolo}
                                        </td>
                                        <td className="p-4">
                                            <span className={`
                                                px-2 py-1 rounded text-[10px] font-bold border
                                                ${orden.lado === 'LONG' ? 'bg-green-900/20 border-green-900/50 text-green-400' : 'bg-red-900/20 border-red-900/50 text-red-400'}
                                            `}>
                                                {orden.lado}
                                            </span>
                                        </td>
                                        <td className="p-4 font-bold text-xs text-gray-400">
                                            {orden.tipo === 'TP' ? (
                                                <span className="text-green-500 flex items-center gap-1"><Target size={12} /> TAKE PROFIT</span>
                                            ) : (
                                                <span className="text-red-500 flex items-center gap-1"><Activity size={12} /> STOP LOSS</span>
                                            )}
                                        </td>
                                        <td className="p-4 font-bold text-white text-lg">
                                            {Number(orden.precio_gatillo).toFixed(4)}
                                        </td>
                                        <td className="p-4 text-gray-400">
                                            {Number(orden.precio_actual).toFixed(4)}
                                        </td>
                                        <td className="p-4">
                                            <span className={`font-bold ${cerca ? 'text-yellow-500 animate-pulse' : 'text-gray-500'}`}>
                                                {distanciaAbs}%
                                            </span>
                                        </td>
                                        <td className="p-4 text-right">
                                            <span className="text-[10px] bg-[#111] px-2 py-1 rounded text-gray-400 border border-[#222]">
                                                EN ESPERA
                                            </span>
                                        </td>
                                    </tr>
                                );
                            })
                        ) : (
                            <tr>
                                <td colSpan="7" className="p-20 text-center">
                                    <Clock size={48} className="mx-auto mb-4 text-[#222]" />
                                    <p className="text-gray-600 font-bold text-lg">SIN ÓRDENES PENDIENTES</p>
                                    <p className="text-gray-700 text-xs mt-2 max-w-md mx-auto">
                                        ZeroX activará órdenes virtuales aquí en lugar de enviarlas al exchange para ocultar intenciones ("Ghost Orders").
                                    </p>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default PanelPendientes;
