import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { TicketTable } from '../components/TicketTable';
import { Pagination } from '../components/TableControls';
import { PageHeader, TableSkeleton, EmptyState, ErrorState } from '../components/UIComponents';
import { PlusCircle, Search } from 'lucide-react';

export const MyTicketsPage = () => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [scopeFilter, setScopeFilter] = useState('all'); // 'all' | 'mine' | 'assigned_to_me'
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const { error } = useToast();
  const { user } = useAuth();

  const fetchTickets = async () => {
    setLoading(true);
    setErrorState(false);
    try {
      const params = {
        page,
        page_size: 10,
        search: search.trim() || undefined,
        status: status || undefined,
        priority: priority || undefined,
        requester_id: scopeFilter === 'mine' && user?.id ? user.id : undefined,
        assigned_to: scopeFilter === 'assigned_to_me' && user?.id ? user.id : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      const res = await api.get('/tickets', { params });
      setTickets(res.data.items);
      setTotalPages(res.data.total_pages);
      setTotal(res.data.total);
    } catch {
      setErrorState(true);
      error('Failed to load tickets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [page, status, priority, scopeFilter, sortBy, sortOrder]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchTickets();
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
    setPage(1);
  };

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      {/* Page Header */}
      <PageHeader
        category="Global Ticket Visibility"
        title="Tickets Directory"
        description="Comprehensive directory of all system tickets across departments, with role-specific views and quick filters."
        actions={
          <Link
            to="/employee/create-ticket"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors shrink-0"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create Ticket</span>
          </Link>
        }
      />

      {/* Filter and Search Bar */}
      <div className="p-4 border border-neutral-200 bg-neutral-50 flex flex-col md:flex-row gap-3 justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-neutral-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by ticket ID or subject..."
              className="w-full pl-9 pr-3 py-1.5 text-xs border border-neutral-300 focus:border-black focus:outline-none bg-white rounded-none"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-1.5 bg-neutral-900 text-white text-xs font-mono uppercase hover:bg-black transition-colors"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={scopeFilter}
            onChange={(e) => {
              setScopeFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 border border-neutral-300 text-xs font-mono uppercase bg-white rounded-none focus:outline-none focus:border-black"
          >
            <option value="all">Directory: All Tickets</option>
            <option value="mine">Created By Me</option>
            {(user?.role === 'technician' || user?.role === 'admin') && (
              <option value="assigned_to_me">Assigned to Me</option>
            )}
          </select>

          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 border border-neutral-300 text-xs font-mono uppercase bg-white rounded-none focus:outline-none focus:border-black"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="assigned">Assigned</option>
            <option value="in_progress">In Progress</option>
            <option value="pending">Pending</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>

          <select
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 border border-neutral-300 text-xs font-mono uppercase bg-white rounded-none focus:outline-none focus:border-black"
          >
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
      </div>

      {/* Table Content */}
      {loading ? (
        <TableSkeleton rows={8} cols={6} />
      ) : errorState ? (
        <ErrorState onRetry={fetchTickets} />
      ) : tickets.length === 0 ? (
        <EmptyState
          title="No Tickets Found"
          message={
            search || status || priority || scopeFilter !== 'all'
              ? 'No tickets match your active filter criteria. Try adjusting your search query or reset filters.'
              : 'The global support directory is currently empty.'
          }
          action={
            <Link
              to="/employee/create-ticket"
              className="px-4 py-2 bg-black text-white text-xs font-mono uppercase hover:bg-neutral-800"
            >
              Submit First Ticket
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          <TicketTable
            tickets={tickets}
            onSort={handleSort}
            sortBy={sortBy}
            sortOrder={sortOrder}
            currentUserId={user?.id}
          />
          <Pagination
            page={page}
            totalPages={totalPages}
            total={total}
            pageSize={10}
            onPageChange={(p) => setPage(p)}
          />
        </div>
      )}
    </div>
  );
};
