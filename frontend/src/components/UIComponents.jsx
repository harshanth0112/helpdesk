import React from 'react';
import { Inbox, AlertTriangle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

/**
 * PageHeader: Consistent editorial SaaS header with role breadcrumbs, title, subtitle & action controls
 */
export const PageHeader = ({ category, title, description, actions, backLink, backLabel }) => {
  return (
    <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-6 border-b border-neutral-200">
      <div>
        {backLink && (
          <div className="mb-2">
            <Link
              to={backLink}
              className="inline-flex items-center gap-1.5 text-xs font-mono uppercase text-neutral-500 hover:text-black transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{backLabel || 'Back'}</span>
            </Link>
          </div>
        )}
        {category && (
          <span className="text-[11px] font-mono uppercase tracking-widest text-neutral-500 block">
            {category}
          </span>
        )}
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase mt-1 text-black">
          {title}
        </h1>
        {description && (
          <p className="text-xs text-neutral-600 mt-1 max-w-2xl leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
};

/**
 * StatCard: Professional enterprise metric cards
 */
export const StatCard = ({ label, value, subtext, icon: Icon }) => {
  return (
    <div className="p-5 md:p-6 border border-neutral-200 bg-white relative overflow-hidden transition-all duration-200 hover:border-neutral-400">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-mono uppercase tracking-wider text-neutral-500">
          {label}
        </span>
        {Icon && <Icon className="w-4 h-4 text-neutral-400" />}
      </div>
      <div className="text-3xl md:text-4xl font-bold font-mono tracking-tight text-black">
        {value}
      </div>
      {subtext && (
        <p className="text-[11px] font-mono text-neutral-500 mt-2">
          {subtext}
        </p>
      )}
    </div>
  );
};

/**
 * TableSkeleton: Loading skeletons for tabular data
 */
export const TableSkeleton = ({ rows = 5, cols = 5 }) => {
  return (
    <div className="border border-neutral-200 bg-white overflow-hidden animate-pulse">
      <div className="h-10 bg-neutral-100 border-b border-neutral-200" />
      <div className="divide-y divide-neutral-200">
        {Array.from({ length: rows }).map((_, rIdx) => (
          <div key={rIdx} className="p-4 flex items-center gap-4">
            {Array.from({ length: cols }).map((_, cIdx) => (
              <div
                key={cIdx}
                className="h-4 bg-neutral-200 rounded-none flex-1"
                style={{ maxWidth: cIdx === 0 ? '80px' : cIdx === 1 ? '220px' : '100px' }}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

/**
 * EmptyState: Standardized empty container
 */
export const EmptyState = ({ title = 'No records found', message, action, icon: Icon = Inbox }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-neutral-300 bg-neutral-50/50 my-4">
      <Icon className="w-8 h-8 text-neutral-400 mb-2" />
      <h3 className="text-sm font-bold uppercase font-mono text-black">{title}</h3>
      {message && <p className="text-xs text-neutral-600 mt-1 max-w-sm mb-4 leading-normal">{message}</p>}
      {action}
    </div>
  );
};

/**
 * ErrorState: Error boundary / API failure presentation
 */
export const ErrorState = ({ title = 'Unable to Load Content', message, onRetry }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border border-red-200 bg-red-50/30 my-4">
      <AlertTriangle className="w-8 h-8 text-red-600 mb-2" />
      <h3 className="text-sm font-bold uppercase font-mono text-red-950">{title}</h3>
      <p className="text-xs text-red-800 mt-1 max-w-sm mb-4 leading-normal">
        {message || 'An unexpected server error occurred while retrieving this record.'}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-black text-white text-xs font-mono uppercase tracking-wider hover:bg-neutral-800 transition-colors"
        >
          Retry Request
        </button>
      )}
    </div>
  );
};
