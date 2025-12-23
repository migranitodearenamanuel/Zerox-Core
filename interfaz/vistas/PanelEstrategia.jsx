import React, { useState } from 'react';
import useSonidos from '../ganchos/useSonidos';
import { Shield, Zap, Crosshair, HelpCircle } from 'lucide-react';

const TarjetaOpcion = ({ titulo, icono: Icon, descripcion, seleccionado, onClick, color }) => (
    <button
        onClick={onClick}
        className={`
            relative p-6 rounded-xl border-2 text-left transition-all duration-300 w-full group
            ${seleccionado
                ? `bg-${color}-500/10 border-${color}-500 shadow-[0_0_30px_rgba(var(--${color}-rgb),0.3)] scale-[1.02]`
                : 'bg-[#111] border-[#333] hover:border-gray-500 hover:bg-[#1a1a1a]'}
        `}
    >
        <div className="flex justify-between items-start mb-3">
            <Icon size={32} className={seleccionado ? `text-${color}-500` : 'text-gray-500'} />
            {seleccionado && <div className={`w-3 h-3 rounded-full bg-${color}-500 animate-pulse`} />}
        </div>
        <h3 className={`text-lg font-bold mb-1 ${seleccionado ? 'text-white' : 'text-gray-400'}`}>{titulo}</h3>
        <p className="text-xs text-gray-500 leading-relaxed group-hover:text-gray-300">{descripcion}</p>
    </button>
);

const PanelEstrategia = () => {
    const { playClick, playAlert } = useSonidos();
    const [riesgo, setRiesgo] = useState('equilibrado');
    const [confirmado, setConfirmado] = useState(false);

    const guardar = () => {
        playClick();
        setConfirmado(true);
        setTimeout(() => setConfirmado(false), 2000);
    };

    return (
        <div className="p-6 h-full zerox-bg relative overflow-y-auto custom-scrollbar">

            <header className="mb-10 border-b border-white/10 pb-4">
                <h1 className="text-3xl font-black text-white italic tracking-tighter">
                    <span className="text-[#0088ff]">MODO</span> DE COMBATE
                </h1>
                <p className="text-gray-500 text-sm mt-1 flex items-center gap-2">
                    <HelpCircle size={14} /> Selecciona cómo debe operar la IA
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
                <TarjetaOpcion
                    titulo="DEFENSIVO"
                    icono={Shield}
                    color="blue"
                    descripcion="Prioriza proteger el capital. Operaciones seguras, bajo apalancamiento (x2). Ideal para empezar."
                    seleccionado={riesgo === 'conservador'}
                    onClick={() => { playClick(); setRiesgo('conservador'); }}
                />

                <TarjetaOpcion
                    titulo="EQUILIBRADO"
                    icono={Zap}
                    color="yellow"
                    descripcion="Balance entre riesgo y beneficio. Apalancamiento medio (x5). La opción recomendada."
                    seleccionado={riesgo === 'equilibrado'}
                    onClick={() => { playClick(); setRiesgo('equilibrado'); }}
                />

                <TarjetaOpcion
                    titulo="DEPREDADOR"
                    icono={Crosshair}
                    color="red"
                    descripcion="Máxima agresividad. Busca 2000€ rápidos. Alto apalancamiento (x20). SOLO EXPERTOS."
                    seleccionado={riesgo === 'agresivo'}
                    onClick={() => { playClick(); playAlert(); setRiesgo('agresivo'); }}
                />
            </div>

            <div className="bg-[#111] border border-[#333] rounded-xl p-6 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-1 h-full bg-[#0088ff]"></div>
                <h3 className="text-lg font-bold text-white mb-4">Resumen de Configuración</h3>

                <div className="grid grid-cols-2 gap-8 text-sm">
                    <div>
                        <span className="block text-gray-500 mb-1">Apalancamiento Auto-Ajustado</span>
                        <span className="text-2xl font-mono text-white font-bold">
                            {riesgo === 'conservador' ? '2x' : riesgo === 'equilibrado' ? '5x' : '20x'}
                        </span>
                    </div>
                    <div>
                        <span className="block text-gray-500 mb-1">Objetivo de Ganancia</span>
                        <span className="text-2xl font-mono text-[#00ff9d] font-bold">
                            {riesgo === 'conservador' ? 'Pequeño' : 'Ilimitado'}
                        </span>
                    </div>
                </div>

                <button
                    onClick={guardar}
                    className={`mt-8 w-full py-4 rounded font-black tracking-widest transition-all
                    ${confirmado
                            ? 'bg-[#00ff9d] text-black shadow-[0_0_30px_#00ff9d]'
                            : 'bg-white text-black hover:bg-gray-200'}
                    `}
                >
                    {confirmado ? '¡CONFIGURACIÓN APLICADA!' : 'ACTIVAR ESTRATEGIA'}
                </button>
            </div>

        </div>
    );
};

export default PanelEstrategia;
