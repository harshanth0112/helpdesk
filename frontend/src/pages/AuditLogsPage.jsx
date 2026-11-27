import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { LoadingState } from '../components/TableControls';
import { ShieldAlert, Clock, ChevronLeft, ChevronRight } from 'lucide-react';

export const AuditLogsPage = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const { error } = useToast();

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = {
        page,
        page_size: pageSize,
      };
      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity_type = entityFilter;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) params.end_date = new Date(endDate).toISOString();

      const res = await api.get('/admin/audit-logs', { params });
      if (res.data && res.data.items) {
        setLogs(res.data.items);
        setTotal(res.data.total);
        setTotalPages(res.data.total_pages);
      } else {
        setLogs(Array.isArray(res.data) ? res.data : []);
      }
    } catch (err) {
      error('Failed to load system audit logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [page, actionFilter, entityFilter]);

  const handleApplyFilters = (e) => {
    e.preventDefault();
    setPage(1);
    fetchAuditLogs();
  };

  const handleResetFilters = () => {
    setActionFilter('');
    setEntityFilter('');
    setStartDate('');
    setEndDate('');
    setPage(1);
  };

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      <div className="border-b border-neutral-200 pb-5">
        <span className="text-xs font-mono uppercase tracking-widest text-neutral-500">Security & Governance</span>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase mt-1">Audit Logs & Access History</h1>
        <p className="text-xs text-neutral-600 mt-1">
          Immutable production ledger tracking authentication attempts, user lifecycle, ticket state changes, and role assignments.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="border border-neutral-200 bg-white p-4">
        <form onSubmit={handleApplyFilters} className="grid grid-cols-1 md:grid-cols-5 gap-3 text-xs">
          <div>
            <label className="block font-mono uppercase text-neutral-600 mb-1 text-[10px]">Action</label>
            <input
              type="text"
              placeholder="e.g. login_success, status_change"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-neutral-300 rounded-none font-mono text-xs focus:outline-none focus:border-black"
            />
          </div>
          <div>
            <label className="block font-mono uppercase text-neutral-600 mb-1 text-[10px]">Entity Type</label>
            <select
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-neutral-300 rounded-none font-mono text-xs bg-white focus:outline-none focus:border-black"
            >
              <option value="">All Entities</option>
              <option value="ticket">Ticket</option>
              <option value="user">User</option>
              <option value="auth">Auth</option>
            </select>
          </div>
          <div>
            <label className="block font-mono uppercase text-neutral-600 mb-1 text-[10px]">From Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-neutral-300 rounded-none font-mono text-xs focus:outline-none focus:border-black"
            />
          </div>
          <div>
            <label className="block font-mono uppercase text-neutral-600 mb-1 text-[10px]">To Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-2.5 py-1.5 border border-neutral-300 rounded-none font-mono text-xs focus:outline-none focus:border-black"
            />
          </div>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              className="flex-1 py-2 px-3 bg-black text-white hover:bg-neutral-800 font-mono uppercase tracking-wider text-[11px] font-semibold transition-colors"
            >
              Filter
            </button>
            <button
              type="button"
              onClick={handleResetFilters}
              className="py-2 px-3 border border-neutral-300 hover:bg-neutral-100 font-mono uppercase tracking-wider text-[11px] transition-colors"
            >
              Reset
            </button>
          </div>
        </form>
      </div>

      {loading ? (
        <LoadingState message="Retrieving immutable audit records..." />
      ) : (
        <div className="space-y-4">
          <div className="border border-neutral-200 overflow-x-auto bg-white">
            <table className="w-full text-left text-xs border-collapse font-mono">
              <thead>
                <tr className="bg-neutral-50 border-b border-neutral-200 uppercase tracking-wider text-neutral-600">
                  <th className="p-3">ID</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Entity</th>
                  <th className="p-3">Actor</th>
                  <th className="p-3">Diff / State</th>
                  <th className="p-3">IP / Client</th>
                  <th className="p-3 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-200">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="p-6 text-center text-neutral-400 uppercase tracking-wider">
                      No matching audit records found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-neutral-50/70 transition-colors">
                      <td className="p-3 text-neutral-400">#{log.id}</td>
                      <td className="p-3 uppercase font-semibold text-neutral-900">
                        <span className="inline-block px-1.5 py-0.5 bg-neutral-100 border border-neutral-200 text-[10px]">
                          {log.action}
                        </span>
                      </td>
                      <td className="p-3 text-neutral-700">
                        {log.entity_type} {log.entity_id || log.ticket_id ? `#${log.entity_id || log.ticket_id}` : '—'}
                      </td>
                      <td className="p-3 text-neutral-800">
                        {log.actor_id ? `User #${log.actor_id}` : 'System / Unauth'}
                      </td>
                      <td className="p-3 max-w-xs truncate text-neutral-600">
                        {log.new_values ? (
                          <span title={JSON.stringify(log.new_values, null, 2)}>
                            {JSON.stringify(log.new_values)}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="p-3 text-neutral-500 text-[11px] truncate max-w-[140px]" title={log.user_agent || ''}>
                        {log.ip_address || '—'}
                      </td>
                      <td className="p-3 text-right text-neutral-500 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="flex items-center justify-between border-t border-neutral-200 pt-3 text-xs font-mono">
            <span className="text-neutral-500">
              Showing {logs.length} of {total} records (Page {page} of {totalPages})
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 border border-neutral-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-100"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 border border-neutral-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-neutral-100"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
