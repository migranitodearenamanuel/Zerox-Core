import React, { useState } from 'react';
import useSonidos from '../ganchos/useSonidos';
import { Key, Lock, ShieldCheck, ToggleLeft, ToggleRight } from 'lucide-react';

const PanelAjustes = () => {
    const { playClick } = useSonidos();
    const [apiKey, setApiKey] = useState('bg_******************');
    const [apiSecret, setApiSecret] = useState('********************');
    const [modoSimulacion, setModoSimulacion] = useState(false);

    // Estado visual simple
    const [guardado, setGuardado] = useState(false);

    const guardar = () => {
        playClick();
        setGuardado(true);
        setTimeout(() => setGuardado(false), 2000);
    };

    return (
        <div className="p-6 h-full zerox-bg relative overflow-y-auto custom-scrollbar">

            <header className="mb-10 border-b border-white/10 pb-4">
                <h1 className="text-3xl font-black text-white italic tracking-tighter">
                    AJUSTES <span className="text-[#ff0033]">DEL SISTEMA</span>
                </h1>
                <p className="text-gray-500 text-sm mt-1">Configura las llaves de acceso a Bitget</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-12 max-w-4xl">

                {/* Columna 1: Seguridad */}
                <div className="space-y-6">
                    <div className="flex items-center gap-2 mb-4 text-[#0088ff]">
                        <ShieldCheck size={20} />
                        <h3 className="font-bold tracking-widest uppercase text-sm">LLAVES DE ACCESO (API)</h3>
                    </div>

                    <div className="group">
                        <label className="block text-xs font-bold text-gray-500 mb-2 uppercase flex items-center gap-2">
                            <Key size={12} /> Public Key
                        </label>
                        <input
                            type="password"
                            value={apiKey}
                            onChange={e => setApiKey(e.target.value)}
                            className="w-full bg-[#111] border border-[#333] text-white p-4 rounded-lg focus:border-[#0088ff] focus:outline-none transition-colors font-mono tracking-widest"
                        />
                    </div>

                    <div className="group">
                        <label className="block text-xs font-bold text-gray-500 mb-2 uppercase flex items-center gap-2">
                            <Lock size={12} /> Secret Key
                        </label>
                        <input
                            type="password"
                            value={apiSecret}
                            onChange={e => setApiSecret(e.target.value)}
                            className="w-full bg-[#111] border border-[#333] text-white p-4 rounded-lg focus:border-[#0088ff] focus:outline-none transition-colors font-mono tracking-widest"
                        />
                    </div>
                </div>

                {/* Columna 2: Modo de Operación */}
                <div className="space-y-6">
                    <div className="flex items-center gap-2 mb-4 text-[#ff0033]">
                        <ToggleRight size={20} />
                        <h3 className="font-bold tracking-widest uppercase text-sm">MODO OPERATIVO</h3>
                    </div>

                    <div className={`p-6 rounded-xl border-2 transition-all cursor-pointer ${modoSimulacion ? 'border-[#00ff9d] bg-[#00ff9d]/5' : 'border-[#333] bg-[#111]'}`}
                        onClick={() => { playClick(); setModoSimulacion(!modoSimulacion); }}>

                        <div className="flex justify-between items-center mb-2">
                            <span className={`font-bold ${modoSimulacion ? 'text-[#00ff9d]' : 'text-gray-400'}`}>
                                {modoSimulacion ? 'MODO SIMULACIÓN (PAPER)' : 'MODO REAL (LIVE)'}
                            </span>
                            <div className={`w-12 h-6 rounded-full relative transition-colors ${modoSimulacion ? 'bg-[#00ff9d]' : 'bg-gray-700'}`}>
                                <div className={`absolute top-1 w-4 h-4 bg-black rounded-full shadow transition-all ${modoSimulacion ? 'left-7' : 'left-1'}`}></div>
                            </div>
                        </div>

                        <p className="text-xs text-gray-500 leading-relaxed">
                            {modoSimulacion
                                ? "El sistema opera con dinero virtual ('Paper Trading'). Perfecto para pruebas sin riesgo."
                                : "⚠️ ATENCIÓN: El sistema usará tu saldo real de Bitget. Las pérdidas son reales."}
                        </p>
                    </div>

                    <button
                        onClick={guardar}
                        className={`w-full py-4 rounded font-black tracking-widest transition-all shadow-lg
                        ${guardado
                                ? 'bg-[#00ff9d] text-black translate-y-1'
                                : 'bg-[#ff0033] text-white hover:bg-red-600 hover:-translate-y-1'}
                        `}
                    >
                        {guardado ? 'AJUSTES GUARDADOS' : 'GUARDAR CAMBIOS'}
                    </button>

                </div>
            </div>

        </div>
    );
};

export default PanelAjustes;
