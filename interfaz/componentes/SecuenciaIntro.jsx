import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

import synth from '../sonidos/Sintetizador'; // Importamos el nuevo motor de audio

const SecuenciaIntro = ({ onComplete }) => {
    const [lines, setLines] = useState([]);

    // Secuencia de arranque estilo BIOS / Kernel Linux
    const sequence = [
        "CARGANDO NÚCLEO ZEROX V2.0.4... [RELEASE]",
        "DETECTANDO CPU... [OK] MOTOR NEURONAL RECONOCIDO",
        "INICIALIZANDO BANCOS DE MEMORIA... [OK] 32GB ASIGNADOS",
        "CARGANDO CONTROLADORES... [OK] NÚCLEOS NVIDIA CUDA EN LÍNEA",
        "CONECTANDO ENLACE SATELITAL... [ESTABLECIDO]",
        "DESCIFRANDO CLAVES SEGURAS... [ÉXITO]",
        "MONTANDO SISTEMA DE ARCHIVOS... /RAIZ [LECTURA/ESCRITURA]",
        "INICIANDO INTERFAZ NEURONAL...",
        "SISTEMA LISTO."
    ];

    useEffect(() => {
        // Iniciar audio al montar (requiere interacción previa del usuario en algunos navegadores, 
        // pero en Electron funcionará mejor. Si falla, el click inicial lo activará).
        const startAudio = async () => {
            try {
                synth.inicializar();
                synth.playBoot();
            } catch (e) {
                console.log("Esperando interacción para audio...");
            }
        };
        startAudio();

        let currentLine = 0;

        const interval = setInterval(() => {
            if (currentLine < sequence.length) {
                setLines(prev => [...prev, sequence[currentLine]]);
                try { synth.playClick(); } catch (e) { /* Audio falló, ignorar */ }
                currentLine++;
            } else {
                clearInterval(interval);
                try { synth.playSuccess(); } catch (e) { /* Audio falló, ignorar */ }
                setTimeout(onComplete, 1000);
            }
        }, 400); // Velocidad de líneas

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="fixed inset-0 bg-black text-[#00ff9d] font-mono p-10 z-50 flex flex-col justify-end pb-20">
            {/* Efecto CRT Scanline */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-10 bg-[length:100%_2px,3px_100%]"></div>

            <div className="max-w-3xl w-full mx-auto space-y-2">
                {lines.map((line, index) => (
                    <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="text-lg md:text-xl tracking-wider shadow-[#00ff9d] drop-shadow-[0_0_5px_rgba(0,255,157,0.5)]"
                    >
                        <span className="text-gray-500 mr-4">[{new Date().toLocaleTimeString()}]</span>
                        {line}
                    </motion.div>
                ))}
                <motion.div
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ repeat: Infinity, duration: 0.8 }}
                    className="w-4 h-6 bg-[#00ff9d] inline-block ml-2"
                />
            </div>
        </div>
    );
};

export default SecuenciaIntro;
