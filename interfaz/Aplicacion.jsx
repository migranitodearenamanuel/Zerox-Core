import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import BarraLateral from './componentes/BarraLateral';
import PanelControl from './vistas/PanelControl';
import PanelOperaciones from './vistas/PanelOperaciones';
import PanelAjustes from './vistas/PanelAjustes';
import PanelPeriodico from './vistas/PanelPeriodico';
import PanelPendientes from './vistas/PanelPendientes';
// import ChatTactico from './componentes/ChatTactico'; // DESACTIVADO
import PanelDerecho from './componentes/PanelDerecho'; // NUEVO COCKPIT
import SecuenciaIntro from './componentes/SecuenciaIntro';
import useCerebro from './ganchos/useCerebro';
import synth from './sonidos/Sintetizador';

// ============================================================================
// 🖥️ APP PRINCIPAL (EL CEREBRO VISUAL)
// ============================================================================

function Aplicacion() {
    // 1. HOOK CENTRALIZADO (Optimización de Rendimiento)
    // Lee todos los JSONs aquí una sola vez.
    const cerebro = useCerebro();

    // Estado para saber en qué pantalla estamos (Por defecto: 'dashboard')
    const [vista, setVista] = useState('dashboard');

    // Estado para saber si estamos cargando la intro (Por defecto: sí)
    const [cargando, setCargando] = useState(true);

    // Si está cargando, mostramos la secuencia de inicio (Intro Cyberpunk)
    if (cargando) {
        return <SecuenciaIntro onComplete={() => {
            setCargando(false);
            synth.startDrone(); // Iniciar ambiente al entrar
        }} />;
    }

    return (
        // Contenedor Principal (Toda la pantalla)
        <div className="flex h-screen bg-black text-white overflow-hidden font-sans selection:bg-[#ff0033] selection:text-white">

            {/* 1. BARRA LATERAL (Menú Izquierdo) */}
            <BarraLateral vistaActiva={vista} cambiarVista={setVista} />

            {/* 2. CONTENEDOR CENTRAL (Donde pasa la acción) */}
            <div className="flex flex-col flex-1 relative min-w-0 border-r border-[#1a1a1a]">

                {/* Fondo decorativo (Cuadrícula sutil) */}
                <div className="absolute inset-0 z-0 pointer-events-none opacity-20"
                    style={{
                        backgroundImage: 'linear-gradient(#1f1f1f 1px, transparent 1px), linear-gradient(90deg, #1f1f1f 1px, transparent 1px)',
                        backgroundSize: '40px 40px'
                    }}>
                </div>

                {/* VISTA ACTIVA (Cambia según el menú) */}
                <div className="flex-1 overflow-y-auto relative z-10 custom-scrollbar overflow-x-hidden">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={vista}
                            initial={{ opacity: 0, x: 20 }} // Empieza invisible y desplazado
                            animate={{ opacity: 1, x: 0 }}  // Aparece suavemente
                            exit={{ opacity: 0, x: -20 }}   // Se va hacia la izquierda
                            transition={{ duration: 0.1 }}  // Más rápido (0.1s)
                            className="h-full"
                        >
                            {/* PASAMOS DATOS COMO PROPS (Cero Lag) */}
                            {vista === 'dashboard' && <PanelControl datos={cerebro.estado} />}
                            {vista === 'estrategia' && <PanelOperaciones datos={cerebro.estado} />}
                            {vista === 'pendientes' && <PanelPendientes datos={cerebro.estado} />}
                            {vista === 'ajustes' && <PanelAjustes />}
                            {vista === 'logs' && <PanelPeriodico datos={cerebro.noticias} />}
                        </motion.div>
                    </AnimatePresence>
                </div>

            </div>

            {/* 3. BARRA LATERAL DERECHA (EL COCKPIT TÁCTICO) */}
            {/* Reemplaza al Chat. Siempre visible. */}
            <PanelDerecho />

        </div>
    );
}

export default Aplicacion;
