import React, { useState, useEffect, useRef } from 'react';
import useSonidos from '../ganchos/useSonidos';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Terminal, User, ShieldAlert, Minimize2, Maximize2 } from 'lucide-react';

// --- SYSTEM MESSAGE COMPONENT (The Core) ---
const SystemMessage = ({ texto, animar }) => {
    // Parser simple para detectar comandos o alertas en el texto
    const isAlert = texto.includes("ALERTA") || texto.includes("ERROR");

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className={`relative mb-4 pl-4 border-l-2 ${isAlert ? 'border-red-500' : 'border-[#00ff9d]'}`}
        >
            <div className={`text-[10px] font-bold tracking-widest mb-1 uppercase ${isAlert ? 'text-red-400' : 'text-[#00ff9d]/70'}`}>
                {isAlert ? '⚠️ SYSTEM OVERRIDE' : '🟢 NÚCLEO ZEROX'}
            </div>
            <div className={`font-mono text-xs md:text-sm leading-relaxed ${isAlert ? 'text-red-100' : 'text-[#e0e0e0]'}`}>
                {animar ? (
                    <Typewriter text={texto} speed={10} />
                ) : (
                    texto
                )}
            </div>
            {/* Background element for decoration */}
            <div className="absolute inset-0 bg-gradient-to-r from-[#00ff9d]/5 to-transparent pointer-events-none -z-10" />
        </motion.div>
    );
};

// --- USER MESSAGE COMPONENT (The Commander) ---
const UserMessage = ({ texto }) => (
    <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex justify-end mb-4"
    >
        <div className="bg-[#1a1a1a] border border-gray-700/50 rounded-lg rounded-tr-none px-4 py-3 max-w-[85%] shadow-lg relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-2 h-2 bg-blue-500/50"></div>
            <div className="text-[10px] text-blue-400 font-bold mb-1 text-right tracking-widest">COMANDANTE</div>
            <div className="text-gray-200 font-sans text-sm">{texto}</div>

            {/* Hover glow effect */}
            <div className="absolute inset-0 bg-blue-500/0 group-hover:bg-blue-500/5 transition-colors duration-300"></div>
        </div>
    </motion.div>
);

// --- TYPEWRITER EFFECT ---
const Typewriter = ({ text, speed = 15, onComplete }) => {
    const [displayed, setDisplayed] = useState('');
    const index = useRef(0);

    useEffect(() => {
        index.current = 0;
        setDisplayed('');
        const timer = setInterval(() => {
            setDisplayed((prev) => prev + text.charAt(index.current));
            index.current++;
            if (index.current >= text.length) {
                clearInterval(timer);
                if (onComplete) onComplete();
            }
        }, speed);
        return () => clearInterval(timer);
    }, [text, speed, onComplete]);

    return <span>{displayed}</span>;
}

const ChatTactico = () => {
    const { playAlert, playClick, playTyping } = useSonidos();
    const [input, setInput] = useState('');
    const [mensajes, setMensajes] = useState([
        { remitente: 'sistema', texto: 'Enlace neuronal seguro establecido. ZEROX a la espera de instrucciones.', esSistema: true, animar: true }
    ]);
    const [procesando, setProcesando] = useState(false);
    const [minimizado, setMinimizado] = useState(false);
    const finalRef = useRef(null);

    // Scroll al final automático
    useEffect(() => {
        finalRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [mensajes, procesando, minimizado]);

    const enviar = async (e) => {
        e.preventDefault();
        if (!input.trim() || procesando) return;

        playClick();
        const texto = input;
        setInput('');
        setProcesando(true);

        // 1. Add User Msg
        setMensajes(prev => [...prev, { remitente: 'usuario', texto, esSistema: false }]);

        try {
            // SIMULACIÓN LOCAL (Ya que el servidor API está apagado en God Mode)
            await new Promise(resolve => setTimeout(resolve, 600)); // Latencia simulada

            const respuestas = [
                "⚠️ CANAL DE VOZ DESACTIVADO EN MODO DIOS.",
                "Recibido. La IA está concentrada en el scanning de mercado.",
                "Para chat completo, inicie el modo MENTE MAESTRA.",
                "Orden guardada en registro local."
            ];

            // Elegir respuesta (o fija)
            const respuesta = "⚠️ COMUNICACIÓN LIMITADA. El núcleo está dedicado al 100% al Trading. Chat desactivado para ahorrar latencia.";

            // 3. Add AI Msg
            playAlert();
            setMensajes(prev => [...prev, {
                remitente: 'sistema',
                texto: respuesta,
                esSistema: true,
                animar: true
            }]);

        } catch (err) {
            // ...
        } finally {
            setProcesando(false);
        }
    };

    if (minimizado) {
        return (
            <motion.button
                layoutId="chat-window"
                onClick={() => setMinimizado(false)}
                className="w-full h-12 bg-black/90 border border-[#00ff9d]/50 flex items-center justify-between px-4 rounded-t-lg shadow-[0_0_20px_rgba(0,255,157,0.2)] backdrop-blur-md group hover:border-[#00ff9d] transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-[#00ff9d] rounded-full animate-pulse" />
                    <span className="text-[#00ff9d] font-mono text-xs font-bold tracking-widest">CANAL SEGURO</span>
                </div>
                <Maximize2 size={14} className="text-[#00ff9d] opacity-50 group-hover:opacity-100" />
            </motion.button>
        );
    }

    return (
        <motion.div
            layoutId="chat-window"
            className="flex flex-col h-[600px] w-full bg-[#050505]/95 backdrop-blur-xl border border-[#333] rounded-lg shadow-2xl overflow-hidden relative font-sans text-sm"
            style={{ boxShadow: '0 0 40px rgba(0,0,0,0.8), 0 0 10px rgba(0, 255, 157, 0.1)' }}
        >
            {/* --- DECORATIVE HUD ELEMENTS --- */}
            {/* Top Right Corner */}
            <div className="absolute top-0 right-0 w-0 h-0 border-t-[40px] border-r-[40px] border-t-[#00ff9d]/20 border-r-transparent pointer-events-none z-20"></div>
            {/* Grid Overlay */}
            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none z-0"></div>
            <div className="absolute inset-0 pointer-events-none z-0 optacity-10"
                style={{ backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))', backgroundSize: '100% 2px, 3px 100%' }}>
            </div>

            {/* --- HEADER --- */}
            <div className="h-10 bg-[#0a0a0a] border-b border-[#333] flex items-center justify-between px-3 shrink-0 relative z-10">
                <div className="flex items-center gap-2">
                    <Terminal size={14} className="text-[#00ff9d]" />
                    <h2 className="text-[#00ff9d] text-xs font-bold tracking-[0.2em] uppercase">ZeroxAI-Chat</h2>
                    <span className="bg-[#00ff9d]/20 text-[#00ff9d] text-[9px] px-1 rounded">V2.4</span>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex gap-1">
                        <div className="w-1 h-1 bg-[#00ff9d] rounded-full animate-ping"></div>
                        <div className="w-1 h-1 bg-[#00ff9d] rounded-full"></div>
                        <div className="w-1 h-1 bg-[#00ff9d] rounded-full"></div>
                    </div>
                    <button onClick={() => setMinimizado(true)} className="text-gray-500 hover:text-white transition-colors">
                        <Minimize2 size={14} />
                    </button>
                </div>
            </div>

            {/* --- MESSAGE AREA --- */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 relative z-10 custom-scrollbar">
                <AnimatePresence>
                    {mensajes.map((msg, i) => (
                        msg.esSistema
                            ? <SystemMessage key={i} {...msg} />
                            : <UserMessage key={i} {...msg} />
                    ))}
                </AnimatePresence>

                {procesando && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="pl-4 border-l-2 border-yellow-500/50 text-yellow-500/80 text-xs font-mono animate-pulse">
                        ▊ ANALIZANDO VECTORES...
                    </motion.div>
                )}
                <div ref={finalRef} />
            </div>

            {/* --- INPUT AREA --- */}
            <div className="p-3 bg-[#0a0a0a] border-t border-[#333] relative z-10">
                <form onSubmit={enviar} className="flex gap-2 items-center bg-[#111] border border-[#333] p-1 rounded-md focus-within:border-[#00ff9d] focus-within:shadow-[0_0_15px_rgba(0,255,157,0.15)] transition-all">
                    <span className="pl-2 text-[#00ff9d] animate-pulse">{'>'}</span>
                    <input
                        className="flex-1 bg-transparent text-gray-200 text-sm font-mono p-2 focus:outline-none placeholder-gray-700"
                        placeholder="Ingrese comando táctico..."
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        autoFocus
                    />
                    <button
                        type="submit"
                        disabled={!input.trim()}
                        className="p-2 bg-[#00ff9d]/10 text-[#00ff9d] rounded hover:bg-[#00ff9d] hover:text-black transition-all disabled:opacity-20 disabled:hover:bg-transparent disabled:hover:text-[#00ff9d]"
                    >
                        <Send size={16} />
                    </button>
                </form>
                {/* Decorative footer line */}
                <div className="flex justify-between mt-1 text-[8px] text-gray-700 font-mono">
                    <span>SECURE CHANNEL ENCRYPTED</span>
                    <span>LATENCY: 12ms</span>
                </div>
            </div>
        </motion.div>
    );
};

export default ChatTactico;
