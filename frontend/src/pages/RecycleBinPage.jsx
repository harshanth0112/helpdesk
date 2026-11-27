import React, { useState, useEffect, useCallback } from 'react';
import {
  Trash2,
  RotateCcw,
  Search,
  Filter,
  ArrowUpDown,
  RefreshCw,
  AlertTriangle,
  User,
  Ticket,
  MessageSquare,
  Paperclip,
  FolderTree,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

const TABS = [
  { id: 'users', label: 'Users', icon: User },
  { id: 'tickets', label: 'Tickets', icon: Ticket },
  { id: 'comments', label: 'Comments', icon: MessageSquare },
  { id: 'attachments', label: 'Attachments', icon: Paperclip },
  { id: 'categories', label: 'Categories', icon: FolderTree },
];

export const RecycleBinPage = () => {
  const { addToast } = useToast();
  const [activeTab, setActiveTab] = useState('users');
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState('deleted_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // Confirmation Modal State
  const [restoreModalItem, setRestoreModalItem] = useState(null);
  const [restoring, setRestoring] = useState(false);

  const fetchRecycleBin = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      if (search.trim()) params.search = search.trim();
      if (statusFilter.trim()) params.status_filter = statusFilter.trim();

      const res = await api.get(`/admin/recycle-bin/${activeTab}`, { params });
      setItems(res.data.items || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 1);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to load Recycle Bin items.';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  }, [activeTab, page, pageSize, search, statusFilter, sortBy, sortOrder, addToast]);

  useEffect(() => {
    fetchRecycleBin();
  }, [fetchRecycleBin]);

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setPage(1);
    setSearch('');
    setStatusFilter('');
  };

  const handleRestore = async () => {
    if (!restoreModalItem) return;
    setRestoring(true);
    try {
      const res = await api.post(`/admin/recycle-bin/${activeTab}/${restoreModalItem.id}/restore`);
      addToast(res.data?.message || 'Record successfully restored.', 'success');
      setRestoreModalItem(null);
      fetchRecycleBin();
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to restore record.';
      addToast(msg, 'error');
    } finally {
      setRestoring(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-neutral-200 dark:border-neutral-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Trash2 className="w-6 h-6 text-neutral-900 dark:text-neutral-100" />
            <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
              Recycle Bin
            </h1>
          </div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
            Admin recovery management for soft-deleted users, tickets, comments, attachments, and categories.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchRecycleBin()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono uppercase tracking-wider border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-neutral-200 dark:border-neutral-800 space-x-1 overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 text-xs font-mono uppercase tracking-wider border-b-2 transition-all ${
                isActive
                  ? 'border-neutral-900 dark:border-neutral-100 text-neutral-900 dark:text-neutral-100 font-semibold bg-neutral-50 dark:bg-neutral-900/40'
                  : 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Controls: Search, Sort, Filter */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-neutral-400" />
          <input
            type="text"
            placeholder={`Search deleted ${activeTab}...`}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-1 focus:ring-neutral-900 dark:focus:ring-neutral-100"
          />
        </div>

        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-4 h-4 text-neutral-400 shrink-0" />
          <select
            value={`${sortBy}-${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split('-');
              setSortBy(sb);
              setSortOrder(so);
            }}
            className="w-full py-2 px-3 text-sm border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100 focus:outline-none"
          >
            <option value="deleted_at-desc">Deletion Date (Newest first)</option>
            <option value="deleted_at-asc">Deletion Date (Oldest first)</option>
            <option value="id-desc">ID (Descending)</option>
            <option value="id-asc">ID (Ascending)</option>
          </select>
        </div>

        <div className="flex items-center justify-end text-xs font-mono text-neutral-500">
          Showing {items.length} of {total} deleted items
        </div>
      </div>

      {/* Table */}
      <div className="border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 overflow-x-auto">
        {loading ? (
          <div className="py-16 text-center text-sm font-mono text-neutral-400 flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-neutral-900 dark:text-neutral-100" />
            Loading deleted items...
          </div>
        ) : items.length === 0 ? (
          <div className="py-16 text-center text-neutral-500 dark:text-neutral-400 flex flex-col items-center justify-center gap-2">
            <Trash2 className="w-8 h-8 text-neutral-300 dark:text-neutral-700" />
            <p className="text-sm font-medium">Recycle bin is empty for {activeTab}.</p>
            <p className="text-xs text-neutral-400">No soft-deleted records found matching criteria.</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-neutral-200 dark:border-neutral-800 bg-neutral-50 dark:bg-neutral-900/60 font-mono text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
                <th className="py-2.5 px-4 font-semibold">ID / Target</th>
                <th className="py-2.5 px-4 font-semibold">Title / Description</th>
                <th className="py-2.5 px-4 font-semibold">Status / Role</th>
                <th className="py-2.5 px-4 font-semibold">Deleted At</th>
                <th className="py-2.5 px-4 font-semibold">Deleted By</th>
                <th className="py-2.5 px-4 font-semibold">Reason</th>
                <th className="py-2.5 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-neutral-50 dark:hover:bg-neutral-900/40 transition"
                >
                  <td className="py-3 px-4 font-mono font-medium text-neutral-900 dark:text-neutral-100">
                    #{item.id} {item.identifier ? `(${item.identifier})` : ''}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-medium text-neutral-900 dark:text-neutral-100 max-w-xs truncate">
                      {item.title || item.name || 'Untitled'}
                    </div>
                    {item.subtitle && (
                      <div className="text-[11px] text-neutral-500 truncate max-w-xs">{item.subtitle}</div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider border border-neutral-300 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-900">
                      {item.status || item.role || 'DELETED'}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-neutral-500 whitespace-nowrap">
                    {item.deleted_at ? new Date(item.deleted_at).toLocaleString() : 'N/A'}
                  </td>
                  <td className="py-3 px-4 font-mono text-neutral-600 dark:text-neutral-400">
                    {item.deleted_by_name || (item.deleted_by ? `User #${item.deleted_by}` : 'System')}
                  </td>
                  <td className="py-3 px-4 text-neutral-500 max-w-xs truncate">
                    {item.deletion_reason || '—'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => setRestoreModalItem(item)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono uppercase tracking-wider border border-neutral-900 dark:border-neutral-100 hover:bg-neutral-900 hover:text-white dark:hover:bg-neutral-100 dark:hover:text-neutral-900 transition"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Restore
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-neutral-200 dark:border-neutral-800 pt-3 text-xs font-mono">
          <div className="text-neutral-500">
            Page {page} of {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 px-3 py-1 border border-neutral-300 dark:border-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 px-3 py-1 border border-neutral-300 dark:border-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
            >
              Next
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Restore Confirmation Dialog */}
      {restoreModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md bg-white dark:bg-neutral-950 border border-neutral-200 dark:border-neutral-800 shadow-xl p-6 space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 border border-neutral-300 dark:border-neutral-700 bg-neutral-100 dark:bg-neutral-900 shrink-0">
                <RotateCcw className="w-5 h-5 text-neutral-900 dark:text-neutral-100" />
              </div>
              <div>
                <h3 className="text-base font-bold text-neutral-900 dark:text-neutral-100">
                  Restore Record
                </h3>
                <p className="text-xs text-neutral-500 mt-1">
                  Are you sure you want to restore {activeTab.slice(0, -1)} #{restoreModalItem.id} (
                  <span className="font-semibold text-neutral-800 dark:text-neutral-200">
                    {restoreModalItem.title || restoreModalItem.name || 'Untitled'}
                  </span>
                  )?
                </p>
              </div>
            </div>

            {activeTab === 'users' && (
              <div className="flex items-start gap-2 p-3 bg-neutral-50 dark:bg-neutral-900/60 border border-neutral-200 dark:border-neutral-800 text-[11px] text-neutral-600 dark:text-neutral-400">
                <ShieldAlert className="w-4 h-4 text-neutral-700 dark:text-neutral-300 shrink-0 mt-0.5" />
                <span>
                  Safeguard: Restoring this user clears deletion metadata only. Any previous pending, rejected, or suspended account status remains intact.
                </span>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setRestoreModalItem(null)}
                disabled={restoring}
                className="px-4 py-1.5 text-xs font-mono uppercase tracking-wider border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRestore}
                disabled={restoring}
                className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-mono uppercase tracking-wider bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 hover:opacity-90 transition font-semibold"
              >
                {restoring ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
                Confirm Restore
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
