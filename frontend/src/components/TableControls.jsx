import React from 'react';
import { ChevronLeft, ChevronRight, Loader2, Inbox } from 'lucide-react';

export const Pagination = ({ page, totalPages, total, pageSize, onPageChange }) => {
  if (totalPages <= 1) return null;

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between py-4 border-t border-neutral-200 text-xs font-mono uppercase tracking-wider text-neutral-600">
      <div>
        Showing {start}-{end} of {total} records
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-1.5 border border-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-neutral-100 transition-colors"
          title="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="px-2">
          Page {page} / {totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1.5 border border-neutral-300 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-neutral-100 transition-colors"
          title="Next page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export const LoadingState = ({ message = 'Loading data...' }) => (
  <div className="flex flex-col items-center justify-center p-12 text-neutral-500">
    <Loader2 className="w-7 h-7 animate-spin text-black mb-3" />
    <span className="text-xs font-mono uppercase tracking-wider">{message}</span>
  </div>
);

export const EmptyState = ({ message = 'No records found.', action }) => (
  <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-neutral-300 bg-neutral-50/50 my-4">
    <Inbox className="w-8 h-8 text-neutral-400 mb-2" />
    <p className="text-sm font-medium text-neutral-600 mb-3">{message}</p>
    {action}
  </div>
);
