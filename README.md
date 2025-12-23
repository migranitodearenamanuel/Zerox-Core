# ⚡ ZEROX-CORE | Autonomous Trading Intelligence

> **Suite de Inteligencia Artificial aplicada a Mercados Financieros.**
> *Arquitectura Híbrida: Python (Cerebro) + React/Electron (Control) + IA Local (RAG).*

![Status](https://img.shields.io/badge/Status-Beta_Functional-green?style=for-the-badge)
![Tech](https://img.shields.io/badge/Stack-Python_|_React_|_Electron-blue?style=for-the-badge)

## 📖 Descripción
**ZEROX-CORE** no es un simple bot de trading. Es un **sistema operativo financiero** diseñado para operar de forma autónoma. Combina modelos de lenguaje locales (LLMs) para el análisis de sentimiento y estrategia, con algoritmos cuantitativos para la gestión de riesgo.

El sistema ingiere documentación técnica (PDFs/EPUBs), aprende estrategias y ejecuta operaciones conectándose a exchanges (Bitget) bajo una supervisión estricta de riesgo.

## 🏗️ Arquitectura del Sistema

El proyecto sigue una estructura modular tipo Monorepo:

| Módulo | Directorio | Descripción | Tecnologías |
| :--- | :--- | :--- | :--- |
| **🧠 Inteligencia** | `/inteligencia` | Cerebro del sistema. Contiene agentes, RAG y modelos locales. | `Python` `LangChain` `ChromaDB` `Ollama` |
| **⚛️ Interfaz** | `/interfaz` | Dashboard de control visual en tiempo real. | `React` `Vite` `Tailwind` |
| **🖥️ Electron** | `/electron` | Empaquetado de escritorio para ejecución nativa. | `Electron.js` |
| **⚙️ Núcleo** | `/nucleo` | Servidor API y conectores de mercado. | `FastAPI` `WebSockets` |
| **📚 Conocimiento** | `/conocimiento` | Biblioteca vectorial de documentos ingeridos. | `PDF Processing` `Embeddings` |

## 🚀 Instalación y Despliegue

Este es un sistema complejo que requiere entornos de Python y Node.js configurados.

### Prerrequisitos
* **Python 3.10+**
* **Node.js 18+**
* **Bitget API Key** (configurada en `.env`)
* **Ollama** (ejecutándose localmente para los modelos de IA)

### Pasos rápidos

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/migranitodearenamanuel/Zerox-Core.git](https://github.com/migranitodearenamanuel/Zerox-Core.git)
2. **Instalar dependencias Python (Cerebro):**
   ```bash
   pip install -r requisitos.txt
3. **Instalar dependencias Interfaz:**
   ````bash
   npm install
4. **Lanzar Sistema: Ejecutar el script maestro en Windows (inicia backend + frontend + electron):**
   ````DOS
   LANZAR_TODO.bat
## 🛠️ Scripts de Utilidad

El proyecto incluye herramientas de automatización en la raíz:

* `auto_actualizador.py`: Mantiene el sistema al día.
* `limpieza_emergencia.py`: Script de pánico para cerrar procesos o limpiar caché.
* `verificar_saldo_real.py`: Auditoría rápida de conexión con el Exchange.

---

## 🛡️ Aviso de Responsabilidad (Disclaimer)

> Este software es un prototipo de investigación y desarrollo avanzado. El trading con criptomonedas conlleva un alto riesgo. Este código se proporciona "tal cual" sin garantías de rentabilidad. El autor no se hace responsable de pérdidas financieras derivadas de su uso.

**Desarrollado por Manuel Marco del Pino**
