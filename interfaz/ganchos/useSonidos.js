import { useCallback } from 'react';
// import useSound from 'use-sound';

// Importar sonidos (Descomentar cuando existan los archivos)
// import clickSfx from '../assets/sonidos/click.mp3';
// import bootSfx from '../assets/sonidos/boot.mp3';
// import alertSfx from '../assets/sonidos/message.mp3';

const useSonidos = () => {
    // const [playClickSound] = useSound(clickSfx, { volume: 0.5 });
    // const [playBootSound] = useSound(bootSfx, { volume: 0.5 });
    // const [playAlertSound] = useSound(alertSfx, { volume: 0.5 });

    const playClick = useCallback(() => {
        // playClickSound();
        console.log("🔊 SFX: CLICK");
    }, []);

    const playBoot = useCallback(() => {
        // playBootSound();
        console.log("🔊 SFX: BOOT SEQUENCE");
    }, []);

    const playAlert = useCallback(() => {
        // playAlertSound();
        console.log("🔊 SFX: INCOMING ALERT");
    }, []);

    const playTyping = useCallback(() => {
        // console.log("🔊 SFX: TV STATIC / TYPING");
    }, []);

    return { playClick, playBoot, playAlert, playTyping };
};

export default useSonidos;
