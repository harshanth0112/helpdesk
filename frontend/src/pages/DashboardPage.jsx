import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { TicketTable } from '../components/TicketTable';
import { PageHeader, StatCard, TableSkeleton, EmptyState } from '../components/UIComponents';
import {
  PlusCircle,
  ArrowRight,
  Clock,
  Ticket,
  CheckCircle2,
  Users,
  AlertCircle,
  HelpCircle,
  Wrench,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

export const DashboardPage = () => {
  const { user } = useAuth();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    open: 0,
    inProgress: 0,
    pending: 0,
    resolved: 0,
    pendingUsers: 0,
    totalUsers: 0,
    approvedUsers: 0,
    suspendedUsers: 0,
    assignedToMe: 0,
  });

  useEffect(() => {
    const loadDashboardData = async () => {
      try {
        setLoading(true);
        // Load role-scoped DB stats and recent tickets concurrently
        const [statsRes, ticketsRes] = await Promise.all([
          api.get('/tickets/stats/dashboard'),
          api.get('/tickets', { params: { page: 1, page_size: 5 } }),
        ]);

        const statsData = statsRes.data;
        setStats({
          total: statsData.total || 0,
          open: statsData.open || 0,
          inProgress: statsData.in_progress || 0,
          pending: statsData.pending || 0,
          resolved: statsData.resolved || 0,
          pendingUsers: statsData.pending_users || 0,
          totalUsers: statsData.total_users || 0,
          approvedUsers: statsData.approved_users || 0,
          suspendedUsers: statsData.suspended_users || 0,
          assignedToMe: statsData.assigned_to_me || 0,
        });

        setTickets(ticketsRes.data.items || []);
      } catch {
        // Fallback for dashboard
      } finally {
        setLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  // Format data for Recharts
  const statusData = [
    { name: 'Open', count: stats.open },
    { name: 'In Progress', count: stats.inProgress },
    { name: 'Pending', count: stats.pending },
    { name: 'Resolved', count: stats.resolved },
  ];

  const COLORS = ['#737373', '#2563eb', '#d97706', '#16a34a'];

  if (loading) {
    return (
      <div className="space-y-8 animate-fade-in">
        <div className="h-14 bg-neutral-100 animate-pulse" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-neutral-100 border border-neutral-200 animate-pulse" />
          ))}
        </div>
        <TableSkeleton rows={4} cols={5} />
      </div>
    );
  }

  const role = user?.role || 'employee';

  return (
    <div className="space-y-8 animate-fade-in font-sans">
      {/* Header */}
      <PageHeader
        category={`${role.toUpperCase()} WORKSPACE`}
        title={`Welcome, ${user?.first_name || 'Team Member'}`}
        description="System operational. Real-time overview of ticket queues, service requests, and workspace health."
        actions={
          role === 'employee' ? (
            <Link
              to="/employee/create-ticket"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors shrink-0"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Create New Ticket</span>
            </Link>
          ) : role === 'admin' ? (
            <Link
              to="/admin/users"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors shrink-0"
            >
              <Users className="w-4 h-4" />
              <span>Manage Directory</span>
            </Link>
          ) : null
        }
      />

      {/* Admin Action Notice: Pending Registrations */}
      {role === 'admin' && stats.pendingUsers > 0 && (
        <div className="p-4 border border-amber-300 bg-amber-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div>
              <span className="text-[11px] font-mono uppercase tracking-widest text-amber-900 font-bold block">
                Attention Required — Pending User Registrations
              </span>
              <p className="text-xs text-amber-950 mt-0.5 font-mono">
                {stats.pendingUsers} new account{stats.pendingUsers === 1 ? '' : 's'} awaiting administrative review and role delegation.
              </p>
            </div>
          </div>
          <Link
            to="/admin/users"
            className="inline-flex items-center gap-2 px-4 py-2 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold shrink-0"
          >
            <span>Review Pending ({stats.pendingUsers})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* Stat Cards Matrix based on User Role */}
      {role === 'admin' ? (
        <div className="space-y-4">
          <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 block">
            System Operations & Tickets
          </span>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            <StatCard label="Total Tickets" value={stats.total} icon={Ticket} subtext="Global ticket ledger" />
            <StatCard label="Open Queues" value={stats.open} icon={HelpCircle} subtext="Unresolved / queued" />
            <StatCard label="In Progress" value={stats.inProgress} icon={Clock} subtext="Under active technician review" />
            <StatCard label="Resolved" value={stats.resolved} icon={CheckCircle2} subtext="Closed / completed solutions" />
          </div>

          <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 block pt-2">
            User Lifecycle & Directory
          </span>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            <StatCard label="Total Users" value={stats.totalUsers || stats.approvedUsers + stats.pendingUsers} icon={Users} subtext="Registered accounts" />
            <StatCard label="Pending Approval" value={stats.pendingUsers} icon={Clock} subtext="Awaiting verification" />
            <StatCard label="Approved Users" value={stats.approvedUsers || stats.totalUsers - stats.pendingUsers} icon={CheckCircle2} subtext="Active access" />
            <StatCard label="Suspended" value={stats.suspendedUsers} icon={AlertCircle} subtext="Revoked permissions" />
          </div>
        </div>
      ) : role === 'technician' ? (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 md:gap-6">
          <StatCard label="Total Tickets" value={stats.total} icon={Ticket} subtext="Global directory" />
          <StatCard label="Assigned to Me" value={stats.assignedToMe} icon={Wrench} subtext="Your direct workload" />
          <StatCard label="In Progress" value={stats.inProgress} icon={Clock} subtext="Active diagnostics" />
          <StatCard label="Pending" value={stats.pending} icon={HelpCircle} subtext="Awaiting response" />
          <StatCard label="Resolved" value={stats.resolved} icon={CheckCircle2} subtext="Successfully resolved" />
        </div>
      ) : (
        /* Employee Dashboard Stats */
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 md:gap-6">
          <StatCard label="Total Tickets" value={stats.total} icon={Ticket} subtext="Global visibility" />
          <StatCard label="Open Tickets" value={stats.open} icon={HelpCircle} subtext="Awaiting assignment" />
          <StatCard label="In Progress" value={stats.inProgress} icon={Clock} subtext="Being worked on" />
          <StatCard label="Pending Info" value={stats.pending} icon={AlertCircle} subtext="Need user feedback" />
          <StatCard label="Resolved" value={stats.resolved} icon={CheckCircle2} subtext="Completed requests" />
        </div>
      )}

      {/* Visual Analytics Split Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 border border-neutral-200 bg-white p-6">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-neutral-100">
            <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 font-bold">
              Ticket Status Distribution
            </span>
            <span className="text-[11px] font-mono text-neutral-400 uppercase">Live Metrics</span>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusData}>
                <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: '#f5f5f5' }}
                  contentStyle={{
                    backgroundColor: '#000000',
                    border: 'none',
                    borderRadius: '0px',
                    color: '#ffffff',
                    fontSize: '11px',
                    fontFamily: 'monospace',
                  }}
                />
                <Bar dataKey="count" fill="#171717" radius={[0, 0, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="border border-neutral-200 bg-white p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4 pb-2 border-b border-neutral-100">
              <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 font-bold">
                Resolution Ratio
              </span>
              <span className="text-[11px] font-mono text-neutral-400 uppercase">Overview</span>
            </div>
            <div className="h-44 w-full flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusData}
                    innerRadius={45}
                    outerRadius={65}
                    paddingAngle={3}
                    dataKey="count"
                  >
                    {statusData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#000000',
                      border: 'none',
                      borderRadius: '0px',
                      color: '#ffffff',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="space-y-1.5 pt-4 border-t border-neutral-100 text-xs font-mono">
            <div className="flex justify-between items-center text-neutral-600">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-[#737373]" /> Open
              </span>
              <span className="font-bold text-black">{stats.open}</span>
            </div>
            <div className="flex justify-between items-center text-neutral-600">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-[#2563eb]" /> In Progress
              </span>
              <span className="font-bold text-black">{stats.inProgress}</span>
            </div>
            <div className="flex justify-between items-center text-neutral-600">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-[#d97706]" /> Pending
              </span>
              <span className="font-bold text-black">{stats.pending}</span>
            </div>
            <div className="flex justify-between items-center text-neutral-600">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-[#16a34a]" /> Resolved
              </span>
              <span className="font-bold text-black">{stats.resolved}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Tickets Section */}
      <div className="border border-neutral-200 bg-white p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-neutral-200">
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 font-bold block">
              Recent Workspace Activity
            </span>
            <p className="text-xs text-neutral-600 mt-0.5">
              The latest support requests submitted across all organizational departments.
            </p>
          </div>
          <Link
            to={
              role === 'admin'
                ? '/admin/tickets'
                : role === 'technician'
                ? '/technician/tickets'
                : '/employee/tickets'
            }
            className="inline-flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-black font-semibold hover:underline"
          >
            <span>View Full Directory</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {tickets.length === 0 ? (
          <EmptyState
            title="No Tickets Recorded"
            message="There are no active or historical tickets present in the database."
          />
        ) : (
          <TicketTable tickets={tickets} />
        )}
      </div>
    </div>
  );
};
