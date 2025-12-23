import dotenv from 'dotenv';
import axios from 'axios';

// Cargar variables de entorno (.env)
dotenv.config();

// ============================================================================
// 📢 NOTIFICADOR DISCORD - LA VOZ DEL SISTEMA
// ============================================================================
// ARCHIVO: notificador_discord.js
// PROPÓSITO: Enviar mensajes a tu servidor de Discord.
// Útil para saber qué hace el bot sin mirar la pantalla todo el rato.
// ============================================================================

export async function enviarAlerta(titulo, mensaje, tipo) {
    const url = process.env.DISCORD_WEBHOOK_URL;

    // Verificar si tenemos la URL del Webhook configurada
    if (!url || url === 'TU_WEBHOOK_AQUI') {
        console.error("❌ ERROR: Falta DISCORD_WEBHOOK_URL en el archivo .env");
        return;
    }

    // Colores Decimales para Discord:
    // PROFIT (Verde Neón): 5763719   -> Ganancias
    // LOSS (Rojo Sangre): 15548997   -> Pérdidas
    // INFO (Azul Tech): 3447003      -> Información general
    // ALERTA (Amarillo): 16776960    -> Advertencias
    // ANTIGRAVITY (Morado): 10181046 -> Modo especial

    let color = 3447003; // Por defecto azul (INFO)
    if (tipo === 'PROFIT') color = 5763719;
    if (tipo === 'LOSS') color = 15548997;
    if (tipo === 'ANTIGRAVITY') color = 10181046;
    if (tipo === 'ALERTA') color = 16776960;

    // Construimos el mensaje (Payload)
    const payload = {
        embeds: [{
            title: `⚡ ZEROX: ${titulo}`,
            description: `> ${mensaje}`,
            color: color,
            footer: { text: `ZEROX ARMOURY • ${new Date().toLocaleTimeString()}` }
        }]
    };

    try {
        // Enviamos el mensaje a Discord
        await axios.post(url, payload);
        console.log(`[DISCORD] Alerta enviada: ${titulo}`);
    } catch (error) {
        console.error(`[DISCORD] Fallo al enviar: ${error.message}`);
    }
}
