import React, { useState, useEffect, useCallback } from 'react';
import {
  Trash2,
  RotateCcw,
  Search,
  ArrowUpDown,
  RefreshCw,
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
import { PageHeader, TableSkeleton, EmptyState } from '../components/UIComponents';
import { Modal } from '../components/Modal';

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
    <div className="space-y-6 animate-fade-in font-sans">
      {/* Header */}
      <PageHeader
        category="System Recovery"
        title="Recycle Bin"
        description="Admin recovery management for soft-deleted users, tickets, comments, attachments, and categories."
        actions={
          <button
            type="button"
            onClick={() => fetchRecycleBin()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-mono uppercase tracking-wider border border-neutral-300 bg-white text-black hover:bg-neutral-100 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        }
      />

      {/* Tabs */}
      <div className="flex border-b border-neutral-200 space-x-1 overflow-x-auto bg-white">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => handleTabChange(tab.id)}
              className={`inline-flex items-center gap-2 px-4 py-3 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors whitespace-nowrap ${
                isActive
                  ? 'border-black text-black font-semibold bg-neutral-50'
                  : 'border-transparent text-neutral-500 hover:text-black hover:bg-neutral-50/50'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Controls: Search, Sort, Count */}
      <div className="border border-neutral-200 bg-white p-4 grid grid-cols-1 md:grid-cols-3 gap-3 items-center">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 pointer-events-none" />
          <input
            type="text"
            placeholder={`Search deleted ${activeTab}...`}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 text-xs font-mono border border-neutral-300 bg-white text-black rounded-none focus:outline-none focus:border-black"
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
            className="w-full py-2 px-3 text-xs font-mono border border-neutral-300 bg-white text-black rounded-none focus:outline-none focus:border-black"
          >
            <option value="deleted_at-desc">Deletion Date (Newest first)</option>
            <option value="deleted_at-asc">Deletion Date (Oldest first)</option>
            <option value="id-desc">ID (Descending)</option>
            <option value="id-asc">ID (Ascending)</option>
          </select>
        </div>

        <div className="flex items-center md:justify-end text-xs font-mono text-neutral-500">
          Showing {items.length} of {total} deleted items
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <TableSkeleton rows={5} cols={7} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Trash2}
          title={`Recycle bin is empty for ${activeTab}`}
          message="No soft-deleted records found matching your current criteria."
        />
      ) : (
        <div className="border border-neutral-200 bg-white overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 font-mono text-neutral-600 uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4 font-semibold">ID / Target</th>
                <th className="py-3 px-4 font-semibold">Title / Description</th>
                <th className="py-3 px-4 font-semibold">Status / Role</th>
                <th className="py-3 px-4 font-semibold">Deleted At</th>
                <th className="py-3 px-4 font-semibold">Deleted By</th>
                <th className="py-3 px-4 font-semibold">Reason</th>
                <th className="py-3 px-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-neutral-50 transition-colors">
                  <td className="py-3 px-4 font-mono font-semibold text-black whitespace-nowrap">
                    #{item.id} {item.identifier ? `(${item.identifier})` : ''}
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-semibold text-black max-w-xs truncate">
                      {item.title || item.name || 'Untitled'}
                    </div>
                    {item.subtitle && (
                      <div className="text-[11px] font-mono text-neutral-500 truncate max-w-xs">
                        {item.subtitle}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider border border-neutral-300 bg-neutral-100 text-neutral-800">
                      {item.status || item.role || 'DELETED'}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-neutral-600 whitespace-nowrap">
                    {item.deleted_at ? new Date(item.deleted_at).toLocaleString() : 'N/A'}
                  </td>
                  <td className="py-3 px-4 font-mono text-neutral-700 whitespace-nowrap">
                    {item.deleted_by_name || (item.deleted_by ? `User #${item.deleted_by}` : 'System')}
                  </td>
                  <td className="py-3 px-4 text-neutral-600 max-w-xs truncate">
                    {item.deletion_reason || '—'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      type="button"
                      onClick={() => setRestoreModalItem(item)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-mono uppercase tracking-wider border border-black text-black bg-white hover:bg-black hover:text-white transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Restore</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between border-t border-neutral-200 pt-4 text-xs font-mono">
          <div className="text-neutral-500">
            Page {page} of {totalPages}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-neutral-300 bg-white text-black disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-100 transition-colors"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>Prev</span>
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 px-3 py-1.5 border border-neutral-300 bg-white text-black disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-100 transition-colors"
            >
              <span>Next</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Restore Confirmation Dialog */}
      <Modal
        isOpen={Boolean(restoreModalItem)}
        onClose={() => !restoring && setRestoreModalItem(null)}
        title="Restore Record"
      >
        {restoreModalItem && (
          <div className="space-y-4 text-xs font-mono">
            <div className="p-3 bg-neutral-50 border border-neutral-200 text-neutral-800">
              <p>
                Are you sure you want to restore{' '}
                <strong className="uppercase">{activeTab.slice(0, -1)}</strong>{' '}
                <strong>#{restoreModalItem.id}</strong> (
                <span className="font-semibold text-black">
                  {restoreModalItem.title || restoreModalItem.name || 'Untitled'}
                </span>
                )?
              </p>
            </div>

            {activeTab === 'users' && (
              <div className="flex items-start gap-2 p-3 bg-neutral-50 border border-neutral-200 text-[11px] text-neutral-600">
                <ShieldAlert className="w-4 h-4 text-black shrink-0 mt-0.5" />
                <span>
                  Safeguard: Restoring this user clears deletion metadata only. Any previous pending, rejected, or suspended account status remains intact.
                </span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-neutral-200">
              <button
                type="button"
                onClick={() => setRestoreModalItem(null)}
                disabled={restoring}
                className="px-4 py-2 text-xs font-mono uppercase tracking-wider border border-neutral-300 bg-white text-black hover:bg-neutral-100 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleRestore}
                disabled={restoring}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-mono uppercase tracking-wider bg-black text-white hover:bg-neutral-800 transition-colors font-semibold disabled:opacity-50"
              >
                {restoring ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RotateCcw className="w-3.5 h-3.5" />
                )}
                <span>{restoring ? 'Restoring...' : 'Confirm Restore'}</span>
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
