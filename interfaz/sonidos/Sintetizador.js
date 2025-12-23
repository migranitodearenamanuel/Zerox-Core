// ============================================================================
// 🔊 SINTETIZADOR DE AUDIO PROCEDURAL (ZEROX CORE)
// ============================================================================
// Genera efectos de sonido Sci-Fi en tiempo real usando Web Audio API.
// Sin archivos mp3 pesados. Pura matemática sonora.
// ============================================================================

class Sintetizador {
    constructor() {
        this.ctx = null;
        this.masterGain = null;
        this.droneOsc = null;
        this.droneGain = null;
        this.inicializado = false;
    }

    inicializar() {
        if (this.inicializado) return;

        // Crear contexto de audio (soporte cross-browser)
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.ctx = new AudioContext();

        // Canal Maestro (Volumen General)
        this.masterGain = this.ctx.createGain();
        this.masterGain.gain.value = 0.3; // 30% volumen por defecto
        this.masterGain.connect(this.ctx.destination);

        this.inicializado = true;
        console.log("🔊 SISTEMA DE AUDIO: ONLINE");
    }

    // --- EFECTOS DE SONIDO (SFX) ---

    // 1. Sonido de "Boot" (Arranque de nave/PC retro)
    playBoot() {
        if (!this.inicializado) this.inicializar();
        const t = this.ctx.currentTime;

        // Oscilador de barrido (Sweep)
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(50, t);
        osc.frequency.exponentialRampToValueAtTime(2000, t + 0.5); // Subida rápida

        gain.gain.setValueAtTime(0, t);
        gain.gain.linearRampToValueAtTime(0.5, t + 0.1);
        gain.gain.exponentialRampToValueAtTime(0.01, t + 1.5);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(t);
        osc.stop(t + 1.5);
    }

    // 2. Sonido de "Tecleo" (Click mecánico futurista)
    playClick() {
        if (!this.inicializado) this.inicializar();
        const t = this.ctx.currentTime;

        // Ruido blanco muy corto + tono alto
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'square';
        osc.frequency.setValueAtTime(800 + Math.random() * 200, t); // Variación random

        gain.gain.setValueAtTime(0.1, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.05);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(t);
        osc.stop(t + 0.05);
    }

    // 3. Sonido de "Acceso Concedido" (Éxito)
    playSuccess() {
        if (!this.inicializado) this.inicializar();
        const t = this.ctx.currentTime;

        // Acorde mayor arpegiado rápido
        [440, 554.37, 659.25].forEach((freq, i) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, t + i * 0.1);

            gain.gain.setValueAtTime(0, t + i * 0.1);
            gain.gain.linearRampToValueAtTime(0.2, t + i * 0.1 + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.001, t + i * 0.1 + 0.5);

            osc.connect(gain);
            gain.connect(this.masterGain);

            osc.start(t + i * 0.1);
            osc.stop(t + i * 0.1 + 0.6);
        });
    }

    // 4. Sonido de "Alerta/Error" (Grave)
    playAlert() {
        if (!this.inicializado) this.inicializar();
        const t = this.ctx.currentTime;

        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(150, t);
        osc.frequency.linearRampToValueAtTime(100, t + 0.3);

        gain.gain.setValueAtTime(0.3, t);
        gain.gain.linearRampToValueAtTime(0, t + 0.3);

        osc.connect(gain);
        gain.connect(this.masterGain);

        osc.start(t);
        osc.stop(t + 0.3);
    }

    // --- AMBIENTE (DRONE) ---

    startDrone() {
        if (!this.inicializado) this.inicializar();
        if (this.droneOsc) return; // Ya está sonando

        const t = this.ctx.currentTime;

        this.droneOsc = this.ctx.createOscillator();
        this.droneGain = this.ctx.createGain();

        // Sonido grave y profundo (Sub-bass)
        this.droneOsc.type = 'sine';
        this.droneOsc.frequency.setValueAtTime(55, t); // La (A1)

        // LFO para modular el volumen (Efecto pulsante)
        const lfo = this.ctx.createOscillator();
        lfo.frequency.value = 0.2; // Lento (0.2 Hz)
        const lfoGain = this.ctx.createGain();
        lfoGain.gain.value = 0.05; // Intensidad de la modulación

        lfo.connect(lfoGain);
        lfoGain.connect(this.droneGain.gain);
        lfo.start();

        this.droneGain.gain.setValueAtTime(0, t);
        this.droneGain.gain.linearRampToValueAtTime(0.1, t + 5); // Fade in lento

        this.droneOsc.connect(this.droneGain);
        this.droneGain.connect(this.masterGain);

        this.droneOsc.start(t);
    }

    stopDrone() {
        if (this.droneOsc) {
            const t = this.ctx.currentTime;
            this.droneGain.gain.linearRampToValueAtTime(0, t + 2); // Fade out
            this.droneOsc.stop(t + 2);
            this.droneOsc = null;
        }
    }
}

// Exportamos una instancia única (Singleton)
const synth = new Sintetizador();
export default synth;
