import React from 'react';
import { X } from 'lucide-react';

export const Modal = ({ isOpen, onClose, title, children, maxWidth = 'max-w-md' }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-fade-in">
      <div className={`relative w-full ${maxWidth} bg-white border border-neutral-900 shadow-2xl p-6`}>
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200 mb-5">
          <h3 className="text-lg font-bold tracking-tight uppercase font-mono">{title}</h3>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-black transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
};
