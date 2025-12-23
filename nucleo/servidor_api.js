import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import fetch from 'node-fetch';
import fs from 'fs';
import path from 'path';

// ============================================================================
// 🔌 SERVIDOR API - SISTEMA NERVIOSO CENTRAL (AUTÓNOMO)
// ============================================================================
// ARCHIVO: servidor.js (Antes servidor_api.js)
// PROPÓSITO: Conectar el Frontend (React) con el Backend y el Cerebro.
// Es como el "Router" de tu casa, dirigiendo el tráfico de información.
// ============================================================================

const app = express();
const PUERTO = 3001; // El puerto donde vivirá nuestra API
const URL_CEREBRO = 'http://localhost:8000'; // Dirección de la IA Python

app.use(cors()); // Permite conexiones desde el Frontend
app.use(bodyParser.json()); // Permite entender mensajes en formato JSON

// --- CONFIGURACIÓN TELEGRAM ---
const TELEGRAM_BOT_TOKEN = 'TU_TOKEN_AQUI'; // Pídeselo a @BotFather
const TELEGRAM_CHAT_ID = 'TU_CHAT_ID_AQUI'; // Pídeselo a @userinfobot

async function enviarTelegram(mensaje) {
    if (TELEGRAM_BOT_TOKEN === 'TU_TOKEN_AQUI') return; // No configurado
    try {
        const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                chat_id: TELEGRAM_CHAT_ID,
                text: `🤖 ALERTA ZEROX:\n${mensaje}`
            })
        });
    } catch (e) {
        console.error("❌ Error enviando Telegram:", e.message);
    }
}

// --- ESTADO GLOBAL (MEMORIA RAM) ---
// Aquí guardamos los datos mientras el bot está encendido.
let estadoSistema = {
    saldo: 0, // Se actualizará con el 100% del saldo real
    capital_inicial: null, // Guardaremos el primer saldo detectado
    precio_btc: 65000.00,
    volatilidad: 0,
    objetivo: 10000000, // 10 Millones
    progreso: 0
};

// Historial de Logs (En memoria)
let logsSistema = [
    { id: 1, hora: new Date().toLocaleTimeString(), origen: "SISTEMA", tipo: "INFO", evento: "Servidor API iniciado correctamente." }
];

// Función para guardar un evento en el historial
const agregarLog = (origen, tipo, evento) => {
    const nuevoLog = {
        id: Date.now(),
        hora: new Date().toLocaleTimeString(),
        origen,
        tipo,
        evento
    };
    logsSistema.push(nuevoLog);
    // Mantener solo los últimos 50 logs para no llenar la memoria
    if (logsSistema.length > 50) logsSistema.shift();
};

// --- BUCLE AUTÓNOMO (LATIDO DEL CORAZÓN) ---
// Esto se ejecuta cada 20 segundos para mantener el sistema vivo sin saturar GPU
setInterval(async () => {
    // 1. Simular movimiento de mercado (Solo para demo visual si no hay datos reales)
    const variacion = (Math.random() - 0.5) * 200; // +/- 100 USD
    estadoSistema.precio_btc += variacion;

    // Actualizar volatilidad simulada (simple)
    estadoSistema.volatilidad = Math.abs(variacion / estadoSistema.precio_btc * 100 * 10).toFixed(2);

    // 2. Consultar al Cerebro (IA) - DESACTIVADO EN MODO REAL PARA NO SATURAR
    // El análisis real lo hace conexion_mercado.js
    /*
    try {
        const respuesta = await fetch(`${URL_CEREBRO}/analizar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                precio: estadoSistema.precio_btc,
                moneda: "BTC/USDT",
                timestamp: Date.now(),
                saldo_actual: estadoSistema.saldo
            })
        });

        if (respuesta.ok) {
            const decision = await respuesta.json();

            // 3. Ejecutar Decisión (Simulado para logs)
            if (decision.decision.includes("COMPRA")) {
                agregarLog("CEREBRO", "TRADE", `COMPRA BTC @ ${estadoSistema.precio_btc.toFixed(2)} | Razón: ${decision.razon}`);
                // estadoSistema.saldo -= 10; // Ya no simulamos gasto aquí, usamos saldo real
                enviarTelegram(`🚨 COMPRA EJECUTADA\nPrecio: ${estadoSistema.precio_btc.toFixed(2)}\nRazón: ${decision.razon}`);
            } else if (decision.decision.includes("VENTA")) {
                agregarLog("CEREBRO", "TRADE", `VENTA BTC @ ${estadoSistema.precio_btc.toFixed(2)} | Razón: ${decision.razon}`);
                // estadoSistema.saldo += 12; // Ya no simulamos ganancia aquí
                enviarTelegram(`🚨 VENTA EJECUTADA\nPrecio: ${estadoSistema.precio_btc.toFixed(2)}\nRazón: ${decision.razon}`);
            } else if (decision.decision.includes("PÁNICO")) {
                agregarLog("CEREBRO", "ERROR", `STOP LOSS ACTIVADO | ${decision.razon}`);
                enviarTelegram(`⚠️ PÁNICO: STOP LOSS ACTIVADO\n${decision.razon}`);
            } else {
                // Solo loguear "ESPERAR" ocasionalmente para no saturar
                if (Math.random() > 0.9) {
                    agregarLog("CEREBRO", "INFO", `Monitoreando... Volatilidad: ${estadoSistema.volatilidad}%`);
                }
            }
        }
    } catch (error) {
        // console.error("Error en ciclo autónomo:", error.message);
    }
    */

}, 20000); // Cada 20 segundos para no saturar la GPU local

// --- ENDPOINTS (PUNTOS DE ACCESO) ---

import { obtenerCapitalReal } from './cliente_mercado.js';

// 1. OBTENER ESTADO DEL SISTEMA (Para el Frontend)
app.get('/api/estado', async (req, res) => {
    // 1. Intentar obtener saldo real de Bitget
    const saldoRealTotal = await obtenerCapitalReal();

    // 2. Si falla la API, usar una variable de memoria (fallback)
    let saldoFinal = estadoSistema.saldo;

    if (saldoRealTotal !== null) {
        saldoFinal = saldoRealTotal; // Usar el 100% del saldo real

        // Si es la primera vez que detectamos saldo, lo fijamos como Capital Inicial
        if (estadoSistema.capital_inicial === null && saldoFinal > 0) {
            estadoSistema.capital_inicial = saldoFinal;
            console.log(`[SISTEMA] Capital Inicial Fijado: ${estadoSistema.capital_inicial.toFixed(2)} USDT (Saldo Real)`);
        }
    }

    // 3. Actualizar memoria
    estadoSistema.saldo = saldoFinal;

    // 4. Calcular progreso hacia 10M
    const progreso = (saldoFinal / 10000000) * 100;

    res.json({
        ...estadoSistema,
        saldo: saldoFinal,
        capital_inicial: estadoSistema.capital_inicial || 30, // Default visual
        progreso: progreso,
        modo_dios: true, // Siempre true en producción
        logs_recientes: logsSistema.slice(-5)
    });
});

// 2. OBTENER LOGS COMPLETOS
app.get('/api/logs', (req, res) => {
    res.json(logsSistema.reverse()); // Lo más nuevo primero
});

// 2.b OBTENER LECCIONES (Auto-Mejora)
app.get('/api/lecciones', (req, res) => {
    const ruta = path.join(__dirname, '..', 'inteligencia', 'lecciones.json');
    try {
        if (!fs.existsSync(ruta)) return res.json([]);
        const contenido = fs.readFileSync(ruta, 'utf8');
        const data = JSON.parse(contenido || '[]');
        return res.json(data);
    } catch (e) {
        console.error('Error leyendo lecciones:', e.message);
        return res.json([]);
    }
});

// 3. CHAT TÁCTICO (Hablar con la IA)
app.post('/api/chat', async (req, res) => {
    const { mensaje } = req.body;
    console.log(`💬 CHAT RECIBIDO: "${mensaje}"`);
    agregarLog("USUARIO", "INFO", `Comando recibido: ${mensaje}`);

    try {
        console.log("➡️ Enviando a Cerebro...");
        const respuestaCerebro = await fetch(`${URL_CEREBRO}/analizar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                precio: estadoSistema.precio_btc,
                moneda: "CHAT",
                timestamp: Date.now(),
                mensaje_usuario: mensaje,
                saldo_actual: estadoSistema.saldo
            })
        });

        console.log(`⬅️ Respuesta Cerebro Status: ${respuestaCerebro.status}`);

        if (!respuestaCerebro.ok) {
            throw new Error(`Error HTTP Cerebro: ${respuestaCerebro.status}`);
        }

        const datos = await respuestaCerebro.json();
        console.log(`✅ Datos Cerebro:`, datos);
        res.json({ respuesta: datos.respuesta });

    } catch (error) {
        console.error(`❌ ERROR CHAT: ${error.message}`);
        res.json({ respuesta: "⚠️ Error: Enlace neuronal interrumpido." });
    }
});

// INICIAR EL SERVIDOR
app.listen(PUERTO, () => {
    console.log(`✅ SERVIDOR INICIADO CORRECTAMENTE EN PUERTO ${PUERTO}`);
});
