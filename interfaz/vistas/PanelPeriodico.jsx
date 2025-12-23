import React, { useState, useEffect } from 'react';
import { Newspaper, Tv, ExternalLink, Globe, Clock } from 'lucide-react';

const PanelPeriodico = ({ datos }) => {
    // Usamos props (Hook Centralizado)
    const data = datos || { noticias: [], videos: [] };

    // Loading se maneja en App.jsx o useCerebro inicial

    return (
        <div className="h-full bg-[#050505] overflow-y-auto custom-scrollbar p-6">

            {/* HERADER */}
            <div className="flex items-center justify-between mb-8 border-b border-[#222] pb-4">
                <div>
                    <h1 className="text-4xl font-black text-white italic tracking-tighter">
                        ZEROX <span className="text-[#ff0033]">DAILY</span>
                    </h1>
                    <p className="text-xs text-gray-400 font-mono mt-1">
                        EDICIÓN: {data.meta?.edicion || "EN VIVO"} | ESTADO: {data.meta?.estado || "ONLINE"}
                    </p>
                </div>
                <div className="p-3 bg-[#111] rounded-full border border-[#222]">
                    <Newspaper className="text-gray-400" />
                </div>
            </div>

            {/* SECCIÓN 1: CINE (VIDEOS) */}
            <div className="mb-10">
                <div className="flex items-center gap-2 mb-4 text-[#ff0033] font-bold tracking-widest uppercase text-sm">
                    <Tv size={16} /> Transmisiones Satelitales
                </div>
                <div className="grid grid-cols-3 gap-4">
                    {data.videos?.map((vid, idx) => (
                        <div key={idx} className="bg-[#111] overflow-hidden rounded-lg border border-[#222] group hover:border-gray-600 transition-colors">
                            <div className="aspect-video bg-black relative">
                                <iframe
                                    src={`https://www.youtube.com/embed/${vid.id_youtube}`}
                                    title={vid.titulo}
                                    className="w-full h-full"
                                    frameBorder="0"
                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                    allowFullScreen
                                ></iframe>
                            </div>
                            <div className="p-3">
                                <div className="text-[10px] text-[#0088ff] font-bold mb-1">{vid.canal}</div>
                                <h3 className="text-xs font-bold text-gray-300 line-clamp-2 leading-tight group-hover:text-white">
                                    {vid.titulo}
                                </h3>
                            </div>
                        </div>
                    ))}
                    {(!data.videos || data.videos.length === 0) && (
                        <div className="col-span-3 text-center py-10 text-gray-600 border border-dashed border-[#222] rounded">
                            NO HAY SEÑAL DE VIDEO
                        </div>
                    )}
                </div>
            </div>

            {/* SECCIÓN 2: TELETIPO (NOTICIAS) */}
            <div>
                <div className="flex items-center gap-2 mb-4 text-[#00ff9d] font-bold tracking-widest uppercase text-sm">
                    <Globe size={16} /> Cables Globales
                </div>
                <div className="bg-[#0a0a0a] border border-[#222] rounded-xl overflow-hidden">
                    {data.noticias?.map((news, idx) => (
                        <div key={idx} className="p-4 border-b border-[#1a1a1a] flex items-start justify-between hover:bg-[#111] transition-colors group">
                            <div className="flex-1 pr-4">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className="text-[10px] bg-gray-800 text-gray-300 px-2 py-0.5 rounded font-bold">
                                        {news.fuente}
                                    </span>
                                    <span className="text-[10px] text-gray-600 font-mono flex items-center gap-1">
                                        <Clock size={8} /> {new Date(news.fecha).toLocaleTimeString()}
                                    </span>
                                </div>
                                <a
                                    href={news.link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm font-medium text-gray-300 group-hover:text-[#00ff9d] transition-colors"
                                >
                                    {news.titulo}
                                </a>
                            </div>
                            <a
                                href={news.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-gray-600 group-hover:text-white transition-colors"
                            >
                                <ExternalLink size={16} />
                            </a>
                        </div>
                    ))}
                    {(!data.noticias || data.noticias.length === 0) && (
                        <div className="text-center py-10 text-gray-600">
                            SIN NOTICIAS RECIENTES
                        </div>
                    )}
                </div>
            </div>

        </div>
    );
};

export default PanelPeriodico;
