import WebSocket from 'ws';
import fetch from 'node-fetch';
import fs from 'fs';
import ccxt from 'ccxt';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

// ============================================================================
// 🏎️ MOTOR DE CONEXIÓN A MERCADO (ZEROX CORE)
// ============================================================================
// ARCHIVO: cliente_mercado.js
// PROPÓSITO: Conectar con Bitget para ejecutar órdenes reales.
// Escucha precios en tiempo real y ejecuta las decisiones del cerebro.
// ============================================================================

const URL_CEREBRO = 'http://127.0.0.1:8000'; // Donde vive nuestra IA (Python)
const URL_BITGET_WS = 'wss://ws.bitget.com/v2/ws/public'; // Dirección del WebSocket de Bitget

// 🌍 LISTA DE ACTIVOS (TOP 10 VOLATILIDAD/LIQUIDEZ)
const LISTA_ACTIVOS = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
    'PEPEUSDT', 'WIFUSDT', 'BNBUSDT', 'ADAUSDT', 'LINKUSDT'
];

// --- LOGGING SYSTEM ---
function logToFile(msg) {
    const timestamp = new Date().toISOString();
    const logLine = `[${timestamp}] ${msg}\n`;
    try {
        const logPath = path.join(path.dirname(fileURLToPath(import.meta.url)), 'logs_mercado.txt');
        fs.appendFileSync(logPath, logLine);
    } catch (e) {
        // Ignore logging errors
    }
}

console.log("🏎️ INICIANDO MOTOR DE ALTA FRECUENCIA (MULTI-ACTIVO)...");
logToFile("🏎️ INICIANDO MOTOR DE ALTA FRECUENCIA (MULTI-ACTIVO)...");

class MotorMercado {
    constructor() {
        this.ws = null; // Aquí guardaremos la conexión WebSocket
        this.ultimosPrecios = {}; // Mapa para guardar precio de cada activo
        this.saldoInicial = null; // Para control de PnL Real
        this.pensamientos = []; // Stream de pensamientos de la IA
        this.ocupado = false; // Semáforo para el Cerebro
    }

    // 1. CONECTAR AL MERCADO (El enchufe)
    conectarMercado() {
        this.iniciarSincronizacionUI(); // Arrancar puente visual
        try {
            this.ws = new WebSocket(URL_BITGET_WS);

            // Cuando se abre la conexión...
            this.ws.on('open', () => {
                console.log('✅ CONECTADO A BITGET (Tubería de datos abierta)');
                logToFile('✅ CONECTADO A BITGET');
                this.suscribirseAlTicker();
            });

            // Cuando llega un mensaje (precio nuevo)...
            this.ws.on('message', (datos) => {
                this.procesarDatosMercado(datos);
            });

            // Si se corta la conexión...
            this.ws.on('close', () => {
                console.log('⚠️ Desconectado. Reintentando en 1 segundo...');
                logToFile('⚠️ Desconectado.');
                setTimeout(() => this.conectarMercado(), 1000);
            });

            // Si hay un error...
            this.ws.on('error', (err) => {
                console.error('❌ Error en el motor:', err.message);
                logToFile(`❌ Error WS: ${err.message}`);
            });

        } catch (error) {
            console.error('❌ Error fatal al conectar:', error);
            logToFile(`❌ Error fatal: ${error.message}`);
        }
    }

    // 2. SUSCRIPCIÓN (Decirle a Bitget qué queremos ver)
    suscribirseAlTicker() {
        // Generamos la lista de argumentos para suscribirnos a TODOS los activos
        const args = LISTA_ACTIVOS.map(moneda => ({
            instType: 'USDT-FUTURES',
            channel: 'ticker',
            instId: moneda
        }));

        const mensajeSuscripcion = {
            op: 'subscribe',
            args: args
        };

        this.ws.send(JSON.stringify(mensajeSuscripcion));
        console.log(`📡 ESCANEANDO ${LISTA_ACTIVOS.length} ACTIVOS EN TIEMPO REAL...`);
        console.log(`🎯 OBJETIVOS: ${LISTA_ACTIVOS.join(', ')}`);
    }

    // 3. PROCESAR EL LATIDO (El bucle infinito)
    async procesarDatosMercado(datosRaw) {
        // 'pong' es la respuesta al ping para mantener la conexión viva
        if (datosRaw.toString() === 'pong') return;

        try {
            const mensaje = JSON.parse(datosRaw);

            // Si es una actualización de precio (ticker)
            if (mensaje.action === 'snapshot' || mensaje.action === 'update') {
                const datosTicker = mensaje.data[0];
                const moneda = datosTicker.instId; // Ej: BTCUSDT

                // Bitget V2 usa 'lastPr' para el último precio.
                const rawPrice = datosTicker.lastPr || datosTicker.last;
                const precioActual = parseFloat(rawPrice);

                // VALIDACIÓN ROBUSTA
                if (isNaN(precioActual) || precioActual <= 0) return;

                // Solo si el precio cambió para ESTA moneda...
                if (precioActual !== this.ultimosPrecios[moneda]) {
                    this.ultimosPrecios[moneda] = precioActual;

                    // AQUÍ OCURRE LA MAGIA: Preguntamos al cerebro
                    // El semáforo (this.ocupado) asegura que no saturemos la IA.
                    // El primero que llegue cuando esté libre, entra.
                    if (!this.ocupado) {
                        await this.consultarCerebroIA(moneda, precioActual);
                    }
                }
            }
        } catch (e) {
            // Ignorar errores de parseo
        }
    }

    // --- SINCRONIZACIÓN VISUAL (JSON PUENTE) ---
    iniciarSincronizacionUI() {
        // Usamos ruta absoluta para no fallar según desde dónde se lance
        const __filename = fileURLToPath(import.meta.url);
        const __dirname = path.dirname(__filename);
        // Estamos en /nucleo, queremos ir a /interfaz/public
        const RUTA_JSON_UI = path.join(__dirname, '..', 'interfaz', 'public', 'estado_bot.json');

        console.log(`[UI] Sincronizando estado en: ${RUTA_JSON_UI}`);

        setInterval(async () => {
            try {
                // Obtener capital real para PnL
                const saldoActual = await obtenerCapitalReal();
                if (saldoActual !== null) {
                    if (this.saldoInicial === null) {
                        this.saldoInicial = saldoActual;
                        console.log(`[SISTEMA] Saldo Inicial Fijado: ${this.saldoInicial} USDT`);
                    }
                }
                const saldoParaCalculo = saldoActual !== null ? saldoActual : (this.saldoInicial || 0);
                // Calcular PnL relativo al inicio de ESTA sesión
                const pnl = (saldoParaCalculo - (this.saldoInicial || saldoParaCalculo)).toFixed(2);
                const pnlSigno = pnl >= 0 ? "+" : "";

                // Leemos estado existente para no machacar info del cerebro
                let estadoExistente = {};
                if (fs.existsSync(RUTA_JSON_UI)) {
                    try {
                        const raw = fs.readFileSync(RUTA_JSON_UI, 'utf8');
                        estadoExistente = JSON.parse(raw);
                    } catch (e) { }
                }

                // Mezclamos
                const nuevoEstado = {
                    ...estadoExistente,
                    precios: this.ultimosPrecios,
                    timestamp_mercado: Date.now(),
                    saldo_cuenta: saldoParaCalculo.toFixed(2),
                    ultima_operacion_pnl: `${pnlSigno}${pnl}`,

                    // STREAM DE PENSAMIENTOS DE LA IA (MATRIX)
                    pensamientos: this.pensamientos,

                    estado_sistema: Object.keys(this.ultimosPrecios).length > 0 ? "ESCANEANDO MERCADO 📡" : "CONECTANDO...",
                    color_estado: Object.keys(this.ultimosPrecios).length > 0 ? "verde" : "amarillo"
                };

                // Escribimos atómicamente
                fs.writeFileSync(RUTA_JSON_UI, JSON.stringify(nuevoEstado, null, 2));

            } catch (error) {
                // Silencio para no saturar consola
            }
        }, 1000); // Actualizar UI cada 1 segundo
    }

    // 4. EL PUENTE NEURONAL (Node -> Python)
    async consultarCerebroIA(moneda, precio) {
        this.ocupado = true; // Bloqueamos para no saturar 
        try {
            const paqueteDeDatos = {
                precio: precio,
                moneda: moneda,
                timestamp: Date.now()
            };

            const respuesta = await fetch(`${URL_CEREBRO}/analizar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(paqueteDeDatos)
            });

            if (!respuesta.ok) return;

            const decision = await respuesta.json();

            if (decision.accion === 'COMPRAR' || decision.accion === 'VENDER') {
                const msg = `🧠 CEREBRO ORDENA (${moneda}): ${decision.accion} | Razón: ${decision.razon}`;
                console.log(msg);
                logToFile(msg);
                await this.ejecutarOperacion(moneda, decision);
            }

            // REGISTRO DE PENSAMIENTO (NEURAL STREAM)
            // Guardamos TOODOS los pensamientos, incluso si decide esperar
            const pensamiento = {
                id: Date.now() + Math.random(), // ID único
                timestamp: new Date().toLocaleTimeString(),
                moneda: moneda,
                precio: precio,
                accion: decision.accion || decision.decision || "ESPERAR",
                razon: decision.razon,
                confianza: decision.confianza || "N/A"
            };

            // Guardamos en memoria (FIFO - Últimos 50)
            if (this.pensamientos) {
                this.pensamientos.unshift(pensamiento);
                if (this.pensamientos.length > 50) this.pensamientos.pop();
            }

            if (!(decision.accion === 'COMPRAR' || decision.accion === 'VENDER')) {
                // Loguear solo ocasionalmente para no saturar disco log.txt
                if (Math.random() > 0.95) {
                    logToFile(`🧠 CEREBRO ESPERA (${moneda}): ${decision.razon}`);
                }
            }

        } catch (error) {
            // Error conectando a AI
        } finally {
            this.ocupado = false;
        }
    }

    // 5. EL GATILLO (Ejecutar la orden real)
    async ejecutarOperacion(moneda, decision) {
        console.log(`🚀 EJECUTANDO OPERACIÓN REAL EN ${moneda}...`);
        logToFile(`🚀 EJECUTANDO OPERACIÓN REAL (${moneda}): ${decision.accion} ${decision.cantidad} USDT`);

        try {
            const exchange = new ccxt.bitget({
                apiKey: process.env.BITGET_API_KEY,
                secret: process.env.BITGET_SECRET,
                password: process.env.BITGET_PASSWORD,
                enableRateLimit: true,
            });

            const symbol = moneda;
            const type = 'market';
            const side = decision.accion === 'COMPRAR' ? 'buy' : 'sell';

            const precioActual = this.ultimosPrecios[moneda];

            // Decimales simplificados
            let decimales = 4;
            if (moneda.startsWith('BTC')) decimales = 6;
            if (moneda.startsWith('ETH')) decimales = 5;
            if (moneda.startsWith('PEPE')) decimales = 0;

            const amount = (decision.cantidad / precioActual).toFixed(decimales);

            const order = await exchange.createOrder(symbol, type, side, parseFloat(amount));

            console.log(`✅ ORDEN ${moneda} EJECUTADA: ID ${order.id}`);
            logToFile(`✅ ORDEN EJECUTADA: ${order.id}`);

        } catch (error) {
            console.error(`❌ ERROR CRÍTICO AL EJECUTAR ORDEN (${moneda}):`, error.message);
            logToFile(`❌ ERROR CRÍTICO: ${error.message}`);
        }
    }
}

// 6. FUNCIÓN EXPORTABLE PARA CONSULTAR CAPITAL
export async function obtenerCapitalReal() {
    try {
        const exchange = new ccxt.bitget({
            apiKey: process.env.BITGET_API_KEY,
            secret: process.env.BITGET_SECRET,
            password: process.env.BITGET_PASSWORD,
            options: { defaultType: 'future' }
        });

        const balance = await exchange.fetchBalance();
        const capital = balance['USDT'] ? balance['USDT']['total'] : 0;
        return parseFloat(capital);
    } catch (error) {
        return null;
    }
}

// ARRANCAR MOTORES
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const motor = new MotorMercado();
    motor.conectarMercado();
}
