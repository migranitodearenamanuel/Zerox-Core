import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ error, errorInfo });
        console.error("🔥 ERROR EN UI:", error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="fixed inset-0 bg-black text-[#ff0033] p-10 font-mono z-[9999] overflow-auto">
                    <h1 className="text-4xl font-bold mb-4">⚠️ FALLO CRÍTICO DE SISTEMA</h1>
                    <div className="border border-[#ff0033] p-4 bg-gray-900 rounded mb-4">
                        <h2 className="text-xl mb-2">Traza de Error:</h2>
                        <pre className="whitespace-pre-wrap text-sm">{this.state.error?.toString()}</pre>
                    </div>
                    <div className="text-gray-400">
                        <h3 className="text-lg">Detalles del Componente:</h3>
                        <pre className="whitespace-pre-wrap text-xs">{this.state.errorInfo?.componentStack}</pre>
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="mt-8 px-6 py-2 bg-[#ff0033] text-black font-bold hover:bg-red-600 transition"
                    >
                        REINICIAR SISTEMA
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
