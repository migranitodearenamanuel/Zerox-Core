# ⚡ ZEROX-CORE | Autonomous Trading Intelligence

> **Suite de Inteligencia Artificial aplicada a Mercados Financieros.**
> *Arquitectura Híbrida: Python (Cerebro) + React/Electron (Control) + IA Local (RAG).*

![Status](https://img.shields.io/badge/Status-Beta_Functional-green?style=for-the-badge)
![Tech](https://img.shields.io/badge/Stack-Python_|_React_|_Electron-blue?style=for-the-badge)

## 📖 Descripción
**ZEROX-CORE** no es un simple bot de trading. Es un **sistema operativo financiero** diseñado para operar de forma autónoma. Combina modelos de lenguaje locales (LLMs) para el análisis de sentimiento y estrategia, con algoritmos cuantitativos para la gestión de riesgo.

El sistema ingiere documentación técnica (PDFs/EPUBs), aprende estrategias y ejecuta operaciones conectándose a exchanges (Bitget) bajo una supervisión estricta de riesgo.

## 🏗️ Arquitectura del Sistema

El proyecto sigue una estructura modular:

| Módulo | Descripción | Tecnologías |
| :--- | :--- | :--- |
| **🧠 Inteligencia** | Cerebro del sistema. Contiene agentes, RAG y modelos. | `Python` `LangChain` `ChromaDB` |
| **⚛️ Interfaz** | Dashboard de control visual en tiempo real. | `React` `Vite` `Tailwind` |
| **🖥️ Electron** | Empaquetado de escritorio para ejecución nativa. | `Electron.js` |
| **⚙️ Núcleo** | Servidor API y conectores con el Exchange. | `FastAPI` `WebSockets` |
| **📚 Conocimiento** | Biblioteca vectorial de documentos ingeridos. | `PDF/Text Processing` |

## 🚀 Instalación y Despliegue

Este es un sistema complejo que requiere entornos de Python y Node.js.

### Prerrequisitos
* Python 3.10+
* Node.js 18+
* Clave API de Bitget (configurada en `.env`)

### Pasos rápidos
1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/migranitodearenamanuel/Zerox-Core.git](https://github.com/migranitodearenamanuel/Zerox-Core.git)
