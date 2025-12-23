const { app, BrowserWindow, screen } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

// Variables globales para los procesos
let pythonProcess = null;
let nodeProcess = null;
let mainWindow = null;

// Configuración de entorno
const isDev = !app.isPackaged;
const PY_DIST_FOLDER = 'cerebro_dist'; // Para cuando compilemos Python (futuro)
const PY_FOLDER = 'cerebro';
const PY_MODULE = 'mente_maestra.py';

const NODE_FOLDER = 'nucleo';
const NODE_SCRIPT = 'servidor_api.js';

// --- GESTIÓN DE SUBPROCESOS ---

const startPythonBackend = () => {
    console.log('🐍 Iniciando Cerebro (Python)...');
    // En desarrollo usamos python directamente. En prod usaremos el ejecutable compilado.
    const scriptPath = path.join(__dirname, '..', PY_FOLDER, PY_MODULE);

    pythonProcess = spawn('python', [scriptPath], {
        cwd: path.join(__dirname, '..'), // Root del proyecto
        stdio: 'inherit' // Ver logs en la consola principal
    });

    pythonProcess.on('error', (err) => {
        console.error('❌ Error iniciando Python:', err);
    });
};

const startNodeBackend = () => {
    console.log('🟢 Iniciando Motor (Node.js)...');
    const scriptPath = path.join(__dirname, '..', NODE_FOLDER, NODE_SCRIPT);

    nodeProcess = spawn('node', [scriptPath], {
        cwd: path.join(__dirname, '..'),
        stdio: 'inherit'
    });

    nodeProcess.on('error', (err) => {
        console.error('❌ Error iniciando Node:', err);
    });
};

const killSubprocesses = () => {
    console.log('💀 Matando subprocesos...');
    if (pythonProcess) pythonProcess.kill();
    if (nodeProcess) nodeProcess.kill();
};

// --- VENTANA PRINCIPAL ---

const createWindow = () => {
    const { width, height } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: width,
        height: height,
        backgroundColor: '#000000',
        titleBarStyle: 'hidden', // Sin barra de título estándar
        titleBarOverlay: {
            color: '#000000',
            symbolColor: '#00ff9d',
            height: 30
        },
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false, // Permitir require en renderer (para simplificar por ahora)
            preload: path.join(__dirname, 'precarga.cjs')
        },
        icon: path.join(__dirname, '../public/favicon.ico')
    });

    // Cargar la URL
    if (isDev) {
        // En desarrollo, esperamos a que Vite levante (lo lanzaremos con concurrently)
        mainWindow.loadURL('http://localhost:3000');
        mainWindow.webContents.openDevTools();
    } else {
        // En producción, cargamos el index.html compilado
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
};

// --- MANEJO DE ERRORES GLOBAL ---
process.on('uncaughtException', (error) => {
    console.error('🔥 CRITICAL ELECTRON ERROR:', error);
});

// --- CICLO DE VIDA DE LA APP ---

app.whenReady().then(() => {
    startPythonBackend();
    startNodeBackend();

    // Esperar un poco a que los backends arranquen antes de mostrar la UI
    setTimeout(createWindow, 2000);

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        killSubprocesses();
        app.quit();
    }
});

app.on('before-quit', () => {
    killSubprocesses();
});

// --- MAJENO DE CARGA FALLIDA ---
// Inyectamos esto en createWindow después de definir mainWindow
const originalCreateWindow = createWindow;
createWindow = () => {
    originalCreateWindow();
    if (mainWindow) {
        mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
            console.error('❌ FALLÓ LA CARGA DE LA UI:', errorCode, errorDescription);
            // Fallback a modo texto si falla el servidor dev
            mainWindow.loadURL(`data:text/html;charset=utf-8,
            <html><body style="background:black;color:red;font-family:monospace;padding:20px;">
            <h1>⚠️ FALLO DE ARRANQUE (BOOT FAILURE)</h1>
            <p>El servidor de interfaz (Vite) no respondió.</p>
            <p>Error: ${errorDescription} (${errorCode})</p>
            <button onclick="location.reload()">REINTENTAR CONEXIÓN</button>
            </body></html>`);
        });
    }
};
