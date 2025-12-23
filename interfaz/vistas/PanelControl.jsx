import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, Shield, TrendingUp, Cpu, Server, Radio, Database, AlertTriangle, Check, ChevronLeft, ChevronRight } from 'lucide-react';
import TerminalNeuronal from '../componentes/TerminalNeuronal';


// --- COMPONENTES UI (TARJETA RED/BLUE) ---
const Tarjeta = ({ children, className = "", titulo, color = "blue" }) => {
    const borderColor = color === 'red' ? 'border-[#ff0033]' : 'border-[#0088ff]';
    const textColor = color === 'red' ? 'text-[#ff0033]' : 'text-[#0088ff]';

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`
                bg-[#080808] border ${borderColor}/30 rounded-lg relative overflow-hidden group
                shadow-[0_0_20px_rgba(0,0,0,0.5)] hover:border-${color}-500/50 transition-all duration-300
                ${className}
            `}
        >
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-${borderColor} to-transparent opacity-50`}></div>
            {titulo && (
                <div className="flex justify-between items-center px-4 py-2 border-b border-white/5 bg-white/5">
                    <h3 className={`text-xs font-bold tracking-[0.2em] uppercase ${textColor}`}>{titulo}</h3>
                    <Activity size={12} className={textColor} />
                </div>
            )}
            <div className="p-5 h-full relative z-10">{children}</div>
        </motion.div>
    );
};

// --- COMPONENTE TICKET PRECIO (GRANULAR) ---
const TickerActivo = ({ par, precio, delay }) => (
    <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: delay * 0.05 }}
        className="bg-white/5 border border-white/5 rounded p-3 flex flex-col items-center justify-between hover:bg-white/10 transition-colors"
    >
        <div className="text-[10px] text-gray-400 font-bold tracking-widest">{par.replace("USDT", "")}</div>
        <div className="text-sm font-mono font-bold text-white">{precio.toFixed(pricePrecision(par))}</div>
        <div className="w-full h-[1px] bg-gradient-to-r from-transparent via-[#0088ff] to-transparent opacity-50 mt-2"></div>
    </motion.div>
);

const pricePrecision = (par) => {
    if (par.includes("PEPE")) return 7;
    if (par.includes("DOGE") || par.includes("WIF")) return 4;
    return 2;
};

// --- COMPONENTE SCANNER VISUAL (PAGINADO) ---
const ScannerVisual = ({ estado }) => {
    // Escáner V2 (Lee de objeto mercado o fallback)
    const precios = estado.mercado?.precios || estado.precios || {};
    // ORDENAR ALFABÉTICAMENTE (Fix Flicker)
    const listaPares = Object.entries(precios).sort((a, b) => a[0].localeCompare(b[0]));
    const totalItems = listaPares.length;

    // Estado de Paginación
    const [pagina, setPagina] = useState(0);
    const itemsPorPagina = 10;
    const totalPaginas = Math.ceil(totalItems / itemsPorPagina);

    // MODO CARGA: Si hay muy pocos items (<5), asumimos que está "calentando"
    if (totalItems > 0 && totalItems < 5) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-4">
                <div className="flex items-center gap-2 text-[#0088ff] animate-pulse mb-2">
                    <Radio size={16} />
                    <span className="text-xs font-bold tracking-widest">INICIANDO ESCANEO GLOBAL...</span>
                </div>
                <div className="text-[10px] text-gray-500">Sincronizando feed de precios ({totalItems} detectados)</div>
            </div>
        );
    }

    // MODO VISUALIZACIÓN COMPLETA
    if (totalItems >= 5) {
        const inicio = pagina * itemsPorPagina;
        const itemsVisibles = listaPares.slice(inicio, inicio + itemsPorPagina);

        const siguientePagina = () => setPagina((prev) => (prev + 1) % totalPaginas);
        const anteriorPagina = () => setPagina((prev) => (prev - 1 + totalPaginas) % totalPaginas);

        return (
            <div className="p-4 h-full flex flex-col">
                {/* Header con Controles */}
                <div className="flex justify-between items-center mb-2 px-1">
                    <div className="text-[10px] text-[#0088ff] animate-pulse uppercase tracking-widest font-bold">
                        📡 MERCADO GLOBAL ({totalItems})
                    </div>

                    {totalPaginas > 1 && (
                        <div className="flex items-center gap-2">
                            <span className="text-[9px] text-gray-500 mr-1">PÁG {pagina + 1}/{totalPaginas}</span>
                            <button onClick={anteriorPagina} className="p-1 hover:bg-white/10 rounded transition-colors text-white bg-white/5">
                                <ChevronLeft size={14} />
                            </button>
                            <button onClick={siguientePagina} className="p-1 hover:bg-white/10 rounded transition-colors text-white bg-white/5">
                                <ChevronRight size={14} />
                            </button>
                        </div>
                    )}
                </div>

                {/* Grid 5 Columnas */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 flex-1">
                    {itemsVisibles.map(([par, precio], index) => (
                        <TickerActivo key={par} par={par} precio={precio} delay={index} />
                    ))}
                </div>
            </div>
        );
    }

    // Fallback: Modo antiguo (Solo 1 precio)
    return (
        <div className="h-full flex items-center justify-center bg-black/50 rounded border border-white/5 relative overflow-hidden">
            <div className="text-center z-10 animate-pulse">
                <div className="text-sm text-[#0088ff] font-mono tracking-widest uppercase">
                    {estado.estado === "OPERANDO 🟢" ? "VIGILANCIA ACTIVA" : "ESCANEO SILENCIOSO"}
                </div>
                <div className="text-[10px] text-gray-500 mt-2">Buscando oportunidades en el Top 30...</div>
            </div>
        </div>
    );
};

const PanelControl = ({ datos }) => {
    // Usamos los datos que vienen por props (Hook Centralizado)
    const estado = datos || {};

    // Hooks para Historial de Lecciones
    const [mostrarHistorial, setMostrarHistorial] = useState(false);
    const [historialLecciones, setHistorialLecciones] = useState([]);
    const [cargandoLecciones, setCargandoLecciones] = useState(false);

    // BLINDAJE ANTI-CRASH
    const sistemaStatus = estado.estado_sistema || "CARGANDO...";
    const esError = sistemaStatus.includes("ERROR") || sistemaStatus.includes("ROJO");
    const colorSistema = esError ? "red" : "blue";
    const listaPosiciones = estado.posiciones || [];

    return (
        <div className="p-6 h-full overflow-y-auto custom-scrollbar zerox-bg relative">

            {/* CABECERA GOD MODE */}
            <header className="mb-8 flex items-end justify-between border-b border-white/10 pb-4">
                <div>
                    <h1 className="text-5xl font-black italic tracking-tighter text-white" style={{ textShadow: '0 0 20px rgba(0, 136, 255, 0.5)' }}>
                        <span className="text-[#0088ff]">GOD</span><span className="text-white">MODE</span>
                    </h1>
                    <div className="flex gap-4 mt-2 text-xs font-mono text-gray-400">
                        <span className="flex items-center gap-1">
                            <Shield size={10} className={esError ? "text-red-500" : "text-green-500"} />
                            {sistemaStatus}
                        </span>
                        <span className="flex items-center gap-1">
                            <Radio size={10} className="text-[#0088ff] animate-pulse" />
                            SYNC ACTIVO
                        </span>
                        <span className="flex items-center gap-1">
                            <Cpu size={10} className="text-purple-400" />
                            {estado.cerebro_info || "CEREBRO: DESCONOCIDO"}
                        </span>
                        <span className="flex items-center gap-1">
                            <Database size={10} className="text-red-500 animate-pulse" />
                            MODO: REAL
                        </span>
                    </div>
                </div>
                <div className="text-right hidden md:block">
                    <div className="text-xl font-mono text-white font-bold">{estado.confianza_ia || "100%"}</div>
                    <div className="text-[10px] text-gray-500 font-mono">CONFIANZA IA</div>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">

                {/* 1. SECCIÓN SUPERIOR: SALDO Y ROAD TO 10M */}
                <Tarjeta className="md:col-span-8" color={colorSistema}>
                    <div className="flex flex-col gap-6">
                        {/* Saldo Principal */}
                        <div className="flex justify-between items-end">
                            <div>
                                <div className="text-xs text-gray-500 font-bold tracking-widest uppercase mb-1">SALDO EN BILLETERA (USDT)</div>
                                <div className="text-6xl font-mono font-bold text-white tracking-tighter shadow-blue-glow">
                                    {estado.saldo_cuenta || "0.00"}<span className="text-2xl text-gray-600">€</span>
                                </div>
                            </div>
                            <div className="text-right">
                                <div className="text-xs text-[#ffd700] font-bold tracking-widest mb-1 animate-pulse">ROAD TO 10M</div>
                                <div className="text-xl text-yellow-500 font-mono font-bold">{(estado.progreso_10m || 0).toFixed(6)}%</div>
                            </div>
                        </div>

                        {/* Barra de Progreso Dorada */}
                        <div className="relative w-full h-4 bg-gray-900 rounded-full overflow-hidden border border-yellow-900/30">
                            <motion.div
                                className="h-full bg-gradient-to-r from-yellow-700 via-yellow-400 to-yellow-100 relative"
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.max((estado.progreso_10m || 0) * 1000, 1)}%` }}
                                transition={{ duration: 1 }}
                            >
                                <div className="absolute inset-0 bg-white/20 animate-[shimmer_2s_infinite]"></div>
                            </motion.div>
                        </div>
                    </div>
                </Tarjeta>

                {/* 2. SUPERVISOR 24/7 (Movido) */}
                <Tarjeta className="md:col-span-4" titulo="SUPERVISOR (24/7)" color="purple">
                    <div className="space-y-3 font-mono text-xs">
                        {/* ESTADO GENERAL */}
                        <div className="flex items-center justify-between p-2 bg-gray-700/50 rounded">
                            <span className="text-gray-400">Estado</span>
                            <div className="text-right">
                                <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${estado.color_estado && estado.color_estado.includes('rojo') ? 'bg-red-900/50 text-red-400' : 'bg-green-900/50 text-green-400'}`}>
                                    {estado.estado_sistema || 'INICIANDO...'}
                                </span>
                            </div>
                        </div>

                        {/* WATCHDOG */}
                        <div className="flex items-center justify-between p-2 bg-gray-700/50 rounded">
                            <span className="text-gray-400">Watchdog</span>
                            <span className="text-yellow-400 font-bold">
                                {estado.heartbeat ? "ACTIVO 🐶" : "ESPERANDO..."}
                            </span>
                        </div>

                        {/* BITGET CLOCK */}
                        <div className="flex items-center justify-between p-2 bg-gray-700/50 rounded">
                            <span className="text-gray-400">Reloj Bitget</span>
                            <div className="text-right">
                                <div className={`font-bold ${estado.info_tiempo?.status === 'OK' ? 'text-green-400' : 'text-red-400'}`}>
                                    {estado.info_tiempo?.status === 'OK' ? 'SYNC' : 'DESFASE'}
                                </div>
                                <div className="text-[9px] text-gray-500">
                                    Offset: {estado.info_tiempo?.offset || 0} ms
                                </div>
                            </div>
                        </div>
                    </div>
                </Tarjeta>

                {/* 3. TABLA DE POSICIONES ACTIVAS (NUEVO) */}
                <Tarjeta className="md:col-span-8" titulo="POSICIONES ACTIVAS" color="green">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs font-mono">
                            <thead>
                                <tr className="text-gray-500 border-b border-white/5">
                                    <th className="py-2">PAR</th>
                                    <th className="py-2">TIPO</th>
                                    <th className="py-2">ENTRADA</th>
                                    <th className="py-2">MARK</th>
                                    <th className="py-2 text-right">PnL (USDT)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {listaPosiciones.length > 0 ? (
                                    listaPosiciones.map((pos, i) => (
                                        <tr key={i} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                            <td className="py-3 font-bold text-white">{pos.simbolo || "???"}</td>
                                            <td className={`py-3 font-bold ${pos.tipo === 'LARGO' ? 'text-green-400' : 'text-red-400'}`}>
                                                {pos.tipo || "---"}
                                            </td>
                                            <td className="py-3 text-gray-400">{parseFloat(pos.entrada || 0).toFixed(4)}</td>
                                            <td className="py-3 text-gray-400">{parseFloat(pos.marca || 0).toFixed(4)}</td>
                                            <td className={`py-3 text-right font-bold ${parseFloat(pos.pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                                {pos.pnl || "0.00"}
                                            </td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="5" className="py-8 text-center text-gray-600 italic">
                                            Sin posiciones activas. El depredador está acechando...
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </Tarjeta>

                {/* 4. CÓRTEX IA (Auto-Mejora) */}
                <Tarjeta className="md:col-span-4" titulo="CÓRTEX IA (Auto-Mejora)" color="purple">
                    <div className="h-full flex flex-col gap-2">
                        {estado.ultimas_lecciones && estado.ultimas_lecciones.length > 0 ? (
                            estado.ultimas_lecciones.map((leccion, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.1 }}
                                    className="p-3 bg-purple-900/10 border border-purple-500/20 rounded text-[10px] text-purple-200"
                                >
                                    <span className="text-purple-500 mr-2">✦</span>
                                    {leccion}
                                </motion.div>
                            ))
                        ) : (
                            <div className="text-center text-gray-600 text-xs py-4 flex flex-col items-center gap-3">
                                <div>El Córtex IA recopila "lecciones" cuando se detectan operaciones relevantes (p. ej. pérdidas). Actualmente no hay entradas.</div>
                                <div className="flex gap-2 mt-2">
                                    <button
                                        onClick={async () => {
                                            try {
                                                const res = await fetch('/api/chat', {
                                                    method: 'POST',
                                                    headers: { 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({ mensaje: 'FORZAR_AUTOMEJORA' })
                                                });
                                                const data = await res.json();
                                                alert('Solicitud enviada al sistema. Revisa el panel en unos segundos.');
                                            } catch (e) {
                                                alert('Error solicitando análisis.');
                                            }
                                        }}
                                        className="px-3 py-1 bg-purple-600 text-white rounded text-[12px] hover:bg-purple-500"
                                    >Forzar análisis</button>

                                    <button
                                        onClick={async () => {
                                            setCargandoLecciones(true);
                                            try {
                                                const res = await fetch('/api/lecciones');
                                                const data = await res.json();
                                                setHistorialLecciones(data || []);
                                                setMostrarHistorial(true);
                                            } catch (e) {
                                                alert('No se pudo leer historial.');
                                            }
                                            setCargandoLecciones(false);
                                        }}
                                        className="px-3 py-1 bg-white/5 text-white rounded text-[12px] hover:bg-white/10"
                                    >Ver historial</button>
                                </div>
                                <div className="text-[10px] text-gray-500 mt-2">Consejo: las lecciones se generan tras analizar trades cerrados (pérdida) o ejecución manual.</div>
                            </div>
                        )}
                        <div className="mt-auto pt-2 text-[8px] text-center text-gray-500 uppercase tracking-widest">
                            Aprendizaje Continuo Activado
                        </div>
                    </div>
                </Tarjeta>

                {/* 5. TERMINAL NEURONAL (MATRIX) */}
                <div className="md:col-span-12">
                    <TerminalNeuronal pensamientos={estado.pensamientos || []} />
                </div>

                {/* Modal de Historial de Lecciones */}
                {mostrarHistorial && (
                    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                        <div className="bg-[#0b0b0b] border border-white/5 rounded-lg p-4 w-11/12 max-w-2xl">
                            <div className="flex justify-between items-center mb-2">
                                <h3 className="text-sm font-bold text-white">Historial de Lecciones</h3>
                                <button className="text-xs text-gray-400" onClick={() => setMostrarHistorial(false)}>Cerrar</button>
                            </div>
                            <div className="max-h-72 overflow-y-auto text-[12px] text-gray-300">
                                {historialLecciones && historialLecciones.length > 0 ? (
                                    historialLecciones.map((l, idx) => (
                                        <div key={idx} className="p-2 border-b border-white/5">{l.leccion || l}</div>
                                    ))
                                ) : (
                                    <div className="text-gray-500">Sin lecciones guardadas.</div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

            </div>
        </div>
    );
};

export default PanelControl;
