import React, { useState, useMemo } from 'react';
import { History, CheckCircle2, Trash2, Download, FileText, MessageCircle, Search, Copy, ExternalLink, Scan, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '../utils/cn';
import { ScannedCode } from '../types';

interface ScanHistoryProps {
  scannedCodes: ScannedCode[];
  loadedRoute: any;
  deleteSelected: () => void;
  deleteItem: (id: string) => void;
  exportToCSV: () => void;
  exportActiveFolderPDF: () => void;
  shareToWhatsApp: () => void;
  isSelectMode: boolean;
  setIsSelectMode: (v: boolean) => void;
  selectedIds: Set<string>;
  toggleSelect: (id: string) => void;
  setSelectedIds: (v: Set<string>) => void;
  setConfirmModal: (modal: any) => void;
}

export const ScanHistory: React.FC<ScanHistoryProps> = ({
  scannedCodes,
  loadedRoute,
  deleteSelected,
  deleteItem,
  exportToCSV,
  exportActiveFolderPDF,
  shareToWhatsApp,
  isSelectMode,
  setIsSelectMode,
  selectedIds,
  toggleSelect,
  setSelectedIds,
  setConfirmModal
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCodes = useMemo(() => {
    return scannedCodes.filter(item => 
      item.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.format.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [scannedCodes, searchQuery]);

  const isUrl = (text: string) => {
    try {
      new URL(text);
      return true;
    } catch (_) {
      return false;
    }
  };

  return (
    <div className="w-full lg:w-[450px] bg-[#0D0D0D] border-l border-white/5 flex flex-col">
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <History className="text-zinc-500" size={20} />
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-lg tracking-tight">Log History</h2>
              <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-[10px] font-black rounded-full border border-emerald-500/20">
                {scannedCodes.length}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isSelectMode ? (
              <div className="flex items-center gap-2 bg-zinc-900/60 p-1 rounded-xl border border-white/5">
                <button 
                  onClick={deleteSelected}
                  disabled={selectedIds.size === 0}
                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-all disabled:opacity-30"
                  title="Excluir selecionados"
                >
                  <Trash2 size={16} />
                </button>
                <button 
                  onClick={() => {
                    setIsSelectMode(false);
                    setSelectedIds(new Set());
                  }}
                  className="px-2.5 py-1 text-xs font-black bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white rounded-lg transition-all uppercase tracking-wider"
                >
                  Cancelar
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 bg-zinc-900/60 p-1 rounded-xl border border-white/5">
                <button 
                  onClick={() => setIsSelectMode(true)}
                  disabled={scannedCodes.length === 0}
                  className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all disabled:opacity-20 disabled:hover:bg-transparent"
                  title="Selecionar múltiplos itens"
                >
                  <CheckCircle2 size={16} />
                </button>
                <button 
                  onClick={exportToCSV}
                  disabled={scannedCodes.length === 0}
                  className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all disabled:opacity-20 disabled:hover:bg-transparent"
                  title="Exportar como planilha CSV"
                >
                  <Download size={16} />
                </button>
                <button 
                  onClick={exportActiveFolderPDF}
                  disabled={scannedCodes.length === 0}
                  className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all disabled:opacity-20 disabled:hover:bg-transparent"
                  title="Exportar como relatório diário em PDF"
                >
                  <FileText size={16} />
                </button>
                <button 
                  onClick={shareToWhatsApp}
                  disabled={scannedCodes.length === 0}
                  className="p-2 text-emerald-500 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-all disabled:opacity-20 disabled:hover:bg-transparent"
                  title="Enviar resumo das leituras via WhatsApp"
                >
                  <MessageCircle size={16} />
                </button>
              </div>
            )}
          </div>
        </div>

        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600" size={16} />
          <input 
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-900/50 border border-white/5 rounded-xl py-3 pl-11 pr-4 text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition-all"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 pt-0 space-y-3 custom-scrollbar">
        <AnimatePresence initial={false}>
          {filteredCodes.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center opacity-20">
              <Scan size={48} className="mb-4" />
              <p className="text-sm font-medium">No records found</p>
            </div>
          ) : (
            filteredCodes.map((item) => (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                onClick={() => isSelectMode && toggleSelect(item.id)}
                className={cn(
                  "group border rounded-2xl p-4 transition-all cursor-pointer",
                  isSelectMode && selectedIds.has(item.id) 
                    ? "bg-emerald-500/10 border-emerald-500/50" 
                    : "bg-[#161616] border-white/5 hover:border-emerald-500/30 hover:bg-[#1A1A1A]"
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {isSelectMode && (
                        <div className={cn(
                          "w-4 h-4 rounded border transition-all flex items-center justify-center",
                          selectedIds.has(item.id) ? "bg-emerald-500 border-emerald-500" : "border-white/20"
                        )}>
                          {selectedIds.has(item.id) && <CheckCircle2 size={10} className="text-black" />}
                        </div>
                      )}
                      {loadedRoute && item.isValid !== undefined && (
                        <div className={cn(
                          "flex items-center gap-1.5 px-2 py-0.5 rounded-md uppercase tracking-wider text-[9px] font-bold",
                          item.isValid 
                            ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" 
                            : "bg-red-500/10 text-red-500 border border-red-500/20"
                        )}>
                          {item.isValid ? <CheckCircle2 size={10} /> : <AlertCircle size={10} />}
                          {item.isValid ? "VÁLIDO" : "INVÁLIDO"}
                        </div>
                      )}
                      <span className="text-[9px] font-bold bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded-md uppercase tracking-wider">
                        {item.format}
                      </span>
                      <span className="text-[10px] text-zinc-600 font-mono">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <p className={cn(
                      "font-mono text-sm break-all font-medium selection:bg-emerald-500/40",
                      loadedRoute && item.isValid === false ? "text-red-400" : "text-zinc-200"
                    )}>
                      {item.code}
                    </p>
                    {item.address && (
                      <p className="text-[10px] text-emerald-500 truncate">
                        📍 {item.address}
                      </p>
                    )}
                    {(item.buyerName || item.phone) && (
                      <p className="text-[10px] text-zinc-400 truncate">
                        👤 {item.buyerName || '-'}
                        {item.phone && (
                          <a
                            href={`tel:${item.phone}`}
                            onClick={(e) => e.stopPropagation()}
                            className="ml-2 text-emerald-500 font-bold"
                          >
                            📞 {item.phone}
                          </a>
                        )}
                      </p>
                    )}
                    {!isSelectMode && (
                      <div className="flex items-center gap-3 pt-1">
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            navigator.clipboard.writeText(item.code);
                          }}
                          className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-500 hover:text-emerald-500 transition-colors uppercase tracking-widest"
                        >
                          <Copy size={12} />
                          Copy
                        </button>
                        {isUrl(item.code) && (
                          <a 
                            href={item.code} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="flex items-center gap-1.5 text-[10px] font-bold text-blue-500 hover:text-blue-400 transition-colors uppercase tracking-widest"
                          >
                            <ExternalLink size={12} />
                            Open
                          </a>
                        )}
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmModal({
                              isOpen: true,
                              title: 'Excluir Item',
                              message: 'Deseja excluir este registro do log?',
                              type: 'danger',
                              onConfirm: () => {
                                deleteItem(item.id);
                                setConfirmModal((prev: any) => ({ ...prev, isOpen: false }));
                              }
                            });
                          }}
                          className="flex items-center gap-1.5 text-[10px] font-bold text-red-500/60 hover:text-red-500 transition-colors uppercase tracking-widest"
                        >
                          <Trash2 size={12} />
                          Excluir
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="w-8 h-8 bg-zinc-900 rounded-lg flex items-center justify-center text-zinc-700 group-hover:text-emerald-500 transition-colors">
                    <Scan size={14} />
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
