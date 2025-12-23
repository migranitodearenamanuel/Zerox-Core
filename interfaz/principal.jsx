import React from 'react'
import ReactDOM from 'react-dom/client'
import Aplicacion from './Aplicacion.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error("🔥 CRITICAL UI ERROR:", error, errorInfo);
        this.setState({ errorInfo });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: '20px', background: '#000', color: '#ff0033', height: '100vh', fontFamily: 'monospace' }}>
                    <h1 style={{ fontSize: '2em', fontWeight: 'bold' }}>⚠️ SISTEMA VISUAL CRÍTICO COMPROMETIDO</h1>
                    <h2 style={{ color: '#fff' }}>{this.state.error && this.state.error.toString()}</h2>
                    <pre style={{ color: '#666', fontSize: '10px', overflow: 'auto' }}>
                        {this.state.errorInfo && this.state.errorInfo.componentStack}
                    </pre>
                    <button onClick={() => window.location.reload()} style={{ marginTop: '20px', padding: '10px 20px', background: '#333', color: '#fff', border: '1px solid #fff', cursor: 'pointer' }}>
                        REINICIAR SISTEMA
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <ErrorBoundary>
            <Aplicacion />
        </ErrorBoundary>
    </React.StrictMode>,
)
