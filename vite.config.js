import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// ============================================================================
// 🛠️ CONFIGURACIÓN VITE (FRONTEND)
// ============================================================================
// ARCHIVO: vite.config.js
// PROPÓSITO: Configurar cómo se compila y sirve la página web (React).
// Apunta a la carpeta /interfaz como raíz del proyecto visual.
// ============================================================================

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
        root: 'interfaz', // 👈 AQUÍ DEFINIMOS LA NUEVA RAÍZ
        publicDir: 'public', // La carpeta public está dentro de interfaz
        server: {
            port: 3000,
            host: '0.0.0.0',
            watch: {
                ignored: ['**/inteligencia/**', '**/nucleo/**', '**/node_modules/**'],
            },
        },
        plugins: [react()],
        // Integración con Gemini eliminada — no inyectamos GEMINI_API_KEY en el bundle
        define: {},
        resolve: {
            alias: {
                '@': path.resolve(__dirname, 'interfaz'), // Alias @ apunta a /interfaz
            }
        },
        build: {
            outDir: '../dist', // Construir fuera de interfaz
            emptyOutDir: true,
        }
    };
});
