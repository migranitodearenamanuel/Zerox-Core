import React from 'react';
import useSonidos from '../ganchos/useSonidos';
import { Home, ClipboardList, Settings, Newspaper, ShieldCheck, Power, RefreshCw, Clock } from 'lucide-react';

const BotonMenu = ({ Icono, etiqueta, activo, onClick, color = "white" }) => (
    <button
        onClick={onClick}
        className={`
            group relative w-full h-24 flex flex-col items-center justify-center transition-all duration-300
            ${activo
                ? 'bg-gradient-to-r from-red-900/40 to-transparent'
                : 'hover:bg-white/5'}
        `}
    >
        {/* Indicador Lateral Activo */}
        {activo && (
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#ff0033] shadow-[0_0_15px_#ff0033]"></div>
        )}

        {/* Icono */}
        <div className={`
            mb-2 transition-transform duration-300 
            ${activo ? 'scale-110 text-[#ff0033] drop-shadow-[0_0_8px_rgba(255,0,51,0.5)]' : 'text-gray-500 group-hover:text-white group-hover:scale-105'}
        `}>
            <Icono size={28} strokeWidth={activo ? 2.5 : 2} />
        </div>

        {/* Etiqueta */}
        <span className={`
            text-[10px] uppercase font-bold tracking-widest
            ${activo ? 'text-white' : 'text-gray-600 group-hover:text-gray-400'}
        `}>
            {etiqueta}
        </span>
    </button>
);

const BarraLateral = ({ vistaActiva, cambiarVista }) => {
    const { playClick } = useSonidos();

    const navegar = (vista) => {
        playClick();
        cambiarVista(vista);
    };

    return (
        <nav className="h-screen w-28 bg-[#050505] border-r border-[#1a1a1a] flex flex-col items-center py-6 z-50 shrink-0 shadow-[5px_0_30px_rgba(0,0,0,0.5)]">

            {/* LOGO */}
            <div className="mb-12">
                <div className="w-14 h-14 bg-[#111] rounded-2xl border border-[#333] flex items-center justify-center shadow-[0_0_20px_rgba(255,0,51,0.2)] group hover:border-[#ff0033] transition-colors duration-500">
                    <span className="text-[#ff0033] font-black text-2xl italic">Z</span>
                </div>
            </div>

            {/* MENÚ */}
            <div className="flex-1 w-full flex flex-col gap-1">
                <BotonMenu
                    Icono={Home}
                    etiqueta="Inicio"
                    activo={vistaActiva === 'dashboard'}
                    onClick={() => navegar('dashboard')}
                />

                <BotonMenu
                    Icono={ClipboardList}
                    etiqueta="OPERACIONES"
                    activo={vistaActiva === 'estrategia'}
                    onClick={() => navegar('estrategia')}
                />

                <BotonMenu
                    Icono={Clock}
                    etiqueta="PENDIENTES"
                    activo={vistaActiva === 'pendientes'}
                    onClick={() => navegar('pendientes')}
                />

                <BotonMenu
                    Icono={Newspaper}
                    etiqueta="EL PERIÓDICO"
                    activo={vistaActiva === 'logs'}
                    onClick={() => navegar('logs')}
                />

                <BotonMenu
                    Icono={Settings}
                    etiqueta="Ajustes"
                    activo={vistaActiva === 'ajustes'}
                    onClick={() => navegar('ajustes')}
                />
            </div>

            {/* SYSTEM POWER CONTROLS */}
            <div className="mb-6 flex flex-col gap-3 w-full px-4">

                {/* RESTART BUTTON */}
                <button
                    onClick={() => {
                        playClick();
                        try {
                            const fs = window.require('fs');
                            const path = window.require('path');
                            // Asumimos estructura: zerox-core/interfaz/public/ -> zerox-core/inteligencia/
                            // BarraLateral está en zerox-core/interfaz/componentes
                            // __dirname no existe en navegador, pero podemos usar ruta relativa o absoluta si estamos en electron
                            // Mejor usar ruta relativa al proceso principal si es posible, o hardcoded relativa

                            // TRUCO: Escribir en 'public' que es accesible
                            // Ruta objetivo: zerox-core/inteligencia/instruccion_bot.json

                            // En electron renderer (con nodeIntegration), process.cwd() suele ser la raiz del proyecto si se lanzó desde ahí
                            const rootDir = window.require('process').cwd();
                            const targetPath = path.join(rootDir, 'inteligencia', 'instruccion_bot.json');

                            fs.writeFileSync(targetPath, JSON.stringify({ comando: "RESET", timestamp: Date.now() }));
                            console.log("Comando RESET enviado a: " + targetPath);

                            setTimeout(() => window.location.reload(), 2000);
                        } catch (e) {
                            console.error("No se pudo enviar comando (No Electron?):", e);
                            window.location.reload();
                        }
                    }}
                    className="group flex flex-col items-center justify-center p-2 rounded-lg hover:bg-white/5 transition-all text-gray-600 hover:text-[#00ff9d]"
                    title="Reiniciar Interfaz + Bot"
                >
                    <RefreshCw size={18} className="group-hover:rotate-180 transition-transform duration-700" />
                    <span className="text-[8px] font-bold mt-1 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">Reset</span>
                </button>

                {/* SHUTDOWN BUTTON */}
                <button
                    onClick={() => {
                        playClick();
                        if (window.confirm("¿APAGAR SISTEMA ZEROX COMPLETAMENTE?")) {
                            try {
                                const fs = window.require('fs');
                                const path = window.require('path');
                                const rootDir = window.require('process').cwd();
                                const targetPath = path.join(rootDir, 'inteligencia', 'instruccion_bot.json');

                                fs.writeFileSync(targetPath, JSON.stringify({ comando: "SHUTDOWN", timestamp: Date.now() }));
                                console.log("Comando SHUTDOWN enviado.");

                                document.body.innerHTML = "<div style='background:black;color:red;height:100vh;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:30px'>SISTEMA APAGADO. CERRANDO...</div>";
                                setTimeout(() => window.close(), 3000);
                            } catch (e) {
                                console.error("Error enviando shutdown:", e);
                                window.close();
                            }
                        }
                    }}
                    className="group flex flex-col items-center justify-center p-2 rounded-lg hover:bg-red-900/20 transition-all text-gray-600 hover:text-red-500"
                    title="Apagar Sistema"
                >
                    <Power size={18} className="group-hover:scale-110 transition-transform" />
                    <span className="text-[8px] font-bold mt-1 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">Off</span>
                </button>

                <div className="h-[1px] w-full bg-[#1a1a1a] my-1"></div>

                <div className="flex flex-col items-center">
                    <ShieldCheck size={12} className="text-[#0088ff] mb-1" />
                    <span className="text-[8px] text-[#0088ff] font-bold shadow-blue-500">ONLINE</span>
                </div>
            </div>

        </nav>
    );
};

export default BarraLateral;
