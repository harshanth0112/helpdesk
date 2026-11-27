import React, { useState, useEffect, useMemo } from 'react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { RoleBadge, ApprovalStatusBadge } from '../components/Badges';
import { Pagination } from '../components/TableControls';
import { PageHeader, TableSkeleton, EmptyState, ErrorState } from '../components/UIComponents';
import { Modal } from '../components/Modal';
import {
  CheckCircle2,
  XCircle,
  ShieldAlert,
  UserCheck,
  Clock,
  Users,
  UserX,
  Search,
  ArrowUpDown,
  Filter,
} from 'lucide-react';

export const UserManagementPage = () => {
  const [activeTab, setActiveTab] = useState('pending'); // 'pending' | 'all' | 'active' | 'suspended'
  const [users, setUsers] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState(false);
  const [approvalRoles, setApprovalRoles] = useState({});

  // Search & Filter & Sort state
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [sortField, setSortField] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  // Pagination state
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Role edit modal
  const [selectedUser, setSelectedUser] = useState(null);
  const [newRole, setNewRole] = useState('');
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);

  // Reject modal
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);

  // Confirmation modal for Approve / Suspend / Reactivate
  const [confirmAction, setConfirmAction] = useState(null);

  const [saving, setSaving] = useState(false);
  const { success, error } = useToast();

  const fetchAllData = async () => {
    try {
      setLoading(true);
      setErrorState(false);
      const [allRes, pendingRes] = await Promise.all([
        api.get('/admin/users'),
        api.get('/admin/users/pending'),
      ]);
      setUsers(allRes.data);
      setPendingUsers(pendingRes.data);

      // Initialize default approval roles ('employee') for pending users
      const initialRoles = {};
      pendingRes.data.forEach((u) => {
        initialRoles[u.id] = approvalRoles[u.id] || 'employee';
      });
      setApprovalRoles((prev) => ({ ...initialRoles, ...prev }));
    } catch {
      setErrorState(true);
      error('Failed to load user directory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  // Filtered dataset according to active tab, search, role, and sort
  const filteredData = useMemo(() => {
    let dataset = [];
    if (activeTab === 'pending') {
      dataset = pendingUsers;
    } else if (activeTab === 'all') {
      dataset = users;
    } else if (activeTab === 'active') {
      dataset = users.filter((u) => u.approval_status === 'approved' && u.is_active);
    } else if (activeTab === 'suspended') {
      dataset = users.filter((u) => u.approval_status === 'suspended' || !u.is_active);
    }

    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      dataset = dataset.filter(
        (u) =>
          u.email?.toLowerCase().includes(q) ||
          u.first_name?.toLowerCase().includes(q) ||
          u.last_name?.toLowerCase().includes(q) ||
          u.department?.toLowerCase().includes(q)
      );
    }

    if (roleFilter && activeTab !== 'pending') {
      dataset = dataset.filter((u) => u.role === roleFilter);
    }

    // Sort
    return [...dataset].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (typeof aVal === 'string') aVal = aVal.toLowerCase();
      if (typeof bVal === 'string') bVal = bVal.toLowerCase();
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });
  }, [activeTab, users, pendingUsers, searchTerm, roleFilter, sortField, sortOrder]);

  const totalPages = Math.ceil(filteredData.length / pageSize) || 1;
  const paginatedData = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, page]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
    setPage(1);
  };

  const handleOpenRoleModal = (u) => {
    setSelectedUser(u);
    setNewRole(u.role);
    setIsRoleModalOpen(true);
  };

  const handleSaveRole = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch(`/admin/users/${selectedUser.id}/role`, { role: newRole });
      success(`Updated role for ${selectedUser.email} to ${newRole}.`);
      setIsRoleModalOpen(false);
      fetchAllData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to update user role.');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenRejectModal = (u) => {
    setRejectTarget(u);
    setRejectionReason('');
    setIsRejectModalOpen(true);
  };

  const handleConfirmReject = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch(`/admin/users/${rejectTarget.id}/reject`, {
        rejection_reason: rejectionReason.trim() || null,
      });
      success(`Registration for ${rejectTarget.email} has been rejected.`);
      setIsRejectModalOpen(false);
      fetchAllData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to reject registration.');
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmSensitiveAction = async () => {
    if (!confirmAction) return;
    setSaving(true);
    try {
      if (confirmAction.type === 'approve') {
        const assignedRole = approvalRoles[confirmAction.user.id] || 'employee';
        await api.patch(`/admin/users/${confirmAction.user.id}/approve`, {
          role: assignedRole,
        });
        success(`Approved ${confirmAction.user.email} as ${assignedRole}.`);
      } else if (confirmAction.type === 'suspend') {
        await api.patch(`/admin/users/${confirmAction.user.id}/status`, {
          action: 'suspend',
        });
        success(`Suspended account ${confirmAction.user.email}.`);
      } else if (confirmAction.type === 'reactivate') {
        await api.patch(`/admin/users/${confirmAction.user.id}/status`, {
          action: 'reactivate',
        });
        success(`Reactivated account ${confirmAction.user.email}.`);
      }
      setConfirmAction(null);
      fetchAllData();
    } catch (err) {
      error(err.response?.data?.detail || 'Action failed.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      <PageHeader
        category="Administration"
        title="User & Access Governance"
        description="Review pending employee onboarding requests, assign enterprise roles, and audit account lifecycle states."
      />

      {/* Tabs */}
      <div className="flex border-b border-neutral-200 overflow-x-auto gap-2">
        <button
          type="button"
          onClick={() => {
            setActiveTab('pending');
            setPage(1);
          }}
          className={`px-4 py-2.5 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors flex items-center gap-2 shrink-0 ${
            activeTab === 'pending'
              ? 'border-black text-black font-bold'
              : 'border-transparent text-neutral-500 hover:text-black'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Pending Registrations</span>
          {pendingUsers.length > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] bg-amber-200 text-amber-950 font-bold font-mono">
              {pendingUsers.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('all');
            setPage(1);
          }}
          className={`px-4 py-2.5 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors flex items-center gap-2 shrink-0 ${
            activeTab === 'all'
              ? 'border-black text-black font-bold'
              : 'border-transparent text-neutral-500 hover:text-black'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>All Users ({users.length})</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('active');
            setPage(1);
          }}
          className={`px-4 py-2.5 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors flex items-center gap-2 shrink-0 ${
            activeTab === 'active'
              ? 'border-black text-black font-bold'
              : 'border-transparent text-neutral-500 hover:text-black'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5" />
          <span>Active Accounts ({users.filter((u) => u.approval_status === 'approved' && u.is_active).length})</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('suspended');
            setPage(1);
          }}
          className={`px-4 py-2.5 text-xs font-mono uppercase tracking-wider border-b-2 transition-colors flex items-center gap-2 shrink-0 ${
            activeTab === 'suspended'
              ? 'border-black text-black font-bold'
              : 'border-transparent text-neutral-500 hover:text-black'
          }`}
        >
          <UserX className="w-3.5 h-3.5" />
          <span>Suspended ({users.filter((u) => u.approval_status === 'suspended' || !u.is_active).length})</span>
        </button>
      </div>

      {/* Search and Filters */}
      <div className="p-4 border border-neutral-200 bg-neutral-50 flex flex-col md:flex-row gap-3 justify-between">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-neutral-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
            placeholder="Search by name, email, department..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-neutral-300 focus:border-black focus:outline-none bg-white rounded-none"
          />
        </div>

        {activeTab !== 'pending' && (
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-neutral-500" />
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-1.5 border border-neutral-300 text-xs font-mono uppercase bg-white rounded-none focus:outline-none focus:border-black"
            >
              <option value="">All Roles</option>
              <option value="admin">Admin</option>
              <option value="technician">Technician</option>
              <option value="employee">Employee</option>
            </select>
          </div>
        )}
      </div>

      {/* Main Table Content */}
      {loading ? (
        <TableSkeleton rows={6} cols={6} />
      ) : errorState ? (
        <ErrorState onRetry={fetchAllData} />
      ) : filteredData.length === 0 ? (
        <EmptyState
          title={
            activeTab === 'pending'
              ? 'No Pending Registrations'
              : 'No matching users found'
          }
          message={
            activeTab === 'pending'
              ? 'There are currently no new employee registration requests awaiting administrator approval.'
              : 'Adjust your search query or filter parameters to find corporate user accounts.'
          }
        />
      ) : activeTab === 'pending' ? (
        /* Pending Registrations Table */
        <div className="border border-neutral-200 overflow-x-auto bg-white">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 font-mono uppercase tracking-wider text-neutral-600">
                <th
                  className="p-3.5 cursor-pointer hover:text-black transition-colors"
                  onClick={() => handleSort('id')}
                >
                  <div className="flex items-center gap-1">
                    <span>ID</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="p-3.5 cursor-pointer hover:text-black transition-colors"
                  onClick={() => handleSort('first_name')}
                >
                  <div className="flex items-center gap-1">
                    <span>Applicant</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3.5">Department & Phone</th>
                <th
                  className="p-3.5 cursor-pointer hover:text-black transition-colors"
                  onClick={() => handleSort('created_at')}
                >
                  <div className="flex items-center gap-1">
                    <span>Requested</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3.5">Assign Role</th>
                <th className="p-3.5 text-right">Review Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {paginatedData.map((u) => (
                <tr key={u.id} className="hover:bg-neutral-50/70 transition-colors">
                  <td className="p-3.5 font-mono text-neutral-500">{u.id}</td>
                  <td className="p-3.5">
                    <div className="font-bold text-black">{u.first_name} {u.last_name}</div>
                    <div className="font-mono text-neutral-500 text-[11px]">{u.email}</div>
                  </td>
                  <td className="p-3.5 text-neutral-700">
                    <div>{u.department || '—'}</div>
                    {u.phone && <div className="font-mono text-[11px] text-neutral-500">{u.phone}</div>}
                  </td>
                  <td className="p-3.5 font-mono text-neutral-500 text-[11px] whitespace-nowrap">
                    {new Date(u.created_at).toLocaleString()}
                  </td>
                  <td className="p-3.5">
                    <select
                      value={approvalRoles[u.id] || 'employee'}
                      onChange={(e) =>
                        setApprovalRoles((prev) => ({ ...prev, [u.id]: e.target.value }))
                      }
                      className="p-1.5 border border-neutral-300 text-xs font-mono uppercase bg-white rounded-none focus:outline-none focus:border-black"
                    >
                      <option value="employee">Employee</option>
                      <option value="technician">Technician</option>
                    </select>
                  </td>
                  <td className="p-3.5 text-right space-x-2 whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => setConfirmAction({ type: 'approve', user: u })}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-mono uppercase bg-black text-white hover:bg-neutral-800 transition-colors"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleOpenRejectModal(u)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-mono uppercase border border-red-300 text-red-700 hover:bg-red-50 transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-3">
            <Pagination
              page={page}
              totalPages={totalPages}
              total={filteredData.length}
              pageSize={pageSize}
              onPageChange={(p) => setPage(p)}
            />
          </div>
        </div>
      ) : (
        /* All Users / Active / Suspended Table */
        <div className="border border-neutral-200 overflow-x-auto bg-white">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 font-mono uppercase tracking-wider text-neutral-600">
                <th
                  className="p-3.5 cursor-pointer hover:text-black transition-colors"
                  onClick={() => handleSort('id')}
                >
                  <div className="flex items-center gap-1">
                    <span>ID</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  className="p-3.5 cursor-pointer hover:text-black transition-colors"
                  onClick={() => handleSort('first_name')}
                >
                  <div className="flex items-center gap-1">
                    <span>User Information</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3.5">Department</th>
                <th className="p-3.5">Account Status</th>
                <th className="p-3.5">Role</th>
                <th
                  className="p-3.5 cursor-pointer hover:text-black transition-colors"
                  onClick={() => handleSort('created_at')}
                >
                  <div className="flex items-center gap-1">
                    <span>Registered</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-200">
              {paginatedData.map((u) => (
                <tr key={u.id} className="hover:bg-neutral-50/70 transition-colors">
                  <td className="p-3.5 font-mono text-neutral-500">{u.id}</td>
                  <td className="p-3.5">
                    <div className="font-bold text-black">{u.first_name} {u.last_name}</div>
                    <div className="font-mono text-neutral-500 text-[11px]">{u.email}</div>
                  </td>
                  <td className="p-3.5 text-neutral-700">{u.department || '—'}</td>
                  <td className="p-3.5">
                    <ApprovalStatusBadge status={u.approval_status} />
                  </td>
                  <td className="p-3.5">
                    <RoleBadge role={u.role} />
                  </td>
                  <td className="p-3.5 font-mono text-neutral-500 text-[11px] whitespace-nowrap">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-3.5 text-right space-x-2 whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => handleOpenRoleModal(u)}
                      className="px-2.5 py-1 text-xs font-mono uppercase tracking-wider border border-neutral-300 text-neutral-800 hover:bg-black hover:text-white transition-colors"
                    >
                      Edit Role
                    </button>
                    {u.approval_status === 'suspended' || !u.is_active ? (
                      <button
                        type="button"
                        onClick={() => setConfirmAction({ type: 'reactivate', user: u })}
                        className="px-2.5 py-1 text-xs font-mono uppercase tracking-wider border border-emerald-500 text-emerald-700 hover:bg-emerald-50 transition-colors"
                      >
                        Reactivate
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmAction({ type: 'suspend', user: u })}
                        className="px-2.5 py-1 text-xs font-mono uppercase tracking-wider border border-red-300 text-red-700 hover:bg-red-50 transition-colors"
                      >
                        Suspend
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="p-3">
            <Pagination
              page={page}
              totalPages={totalPages}
              total={filteredData.length}
              pageSize={pageSize}
              onPageChange={(p) => setPage(p)}
            />
          </div>
        </div>
      )}

      {/* Role Management Modal */}
      <Modal isOpen={isRoleModalOpen} onClose={() => setIsRoleModalOpen(false)} title="Modify User Role">
        <form onSubmit={handleSaveRole} className="space-y-4">
          <div>
            <span className="block text-xs font-mono uppercase text-neutral-500 mb-1">Target Account</span>
            <div className="p-2.5 bg-neutral-100 text-xs font-mono text-neutral-800">
              {selectedUser?.first_name} {selectedUser?.last_name} ({selectedUser?.email})
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">Assign Role</label>
            <select
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              className="w-full p-2.5 border border-neutral-300 text-xs font-mono rounded-none uppercase focus:outline-none focus:border-black"
            >
              <option value="employee">Employee</option>
              <option value="technician">Technician</option>
              <option value="admin">Administrator</option>
            </select>
          </div>

          <div className="pt-4 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsRoleModalOpen(false)}
              className="px-4 py-2 border border-neutral-300 text-xs font-mono uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-black text-white text-xs font-mono uppercase hover:bg-neutral-800 disabled:opacity-50"
            >
              {saving ? 'Updating...' : 'Save Role'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Reject Registration Modal */}
      <Modal isOpen={isRejectModalOpen} onClose={() => setIsRejectModalOpen(false)} title="Reject Registration">
        <form onSubmit={handleConfirmReject} className="space-y-4">
          <div>
            <span className="block text-xs font-mono uppercase text-neutral-500 mb-1">Applicant</span>
            <div className="p-2.5 bg-neutral-100 text-xs font-mono text-neutral-800">
              {rejectTarget?.first_name} {rejectTarget?.last_name} ({rejectTarget?.email})
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
              Rejection Reason (Optional)
            </label>
            <textarea
              rows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Reason for rejecting this registration request..."
              className="w-full p-2.5 border border-neutral-300 text-xs rounded-none focus:outline-none focus:border-black"
            />
          </div>

          <div className="pt-4 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsRejectModalOpen(false)}
              className="px-4 py-2 border border-neutral-300 text-xs font-mono uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-red-600 text-white text-xs font-mono uppercase hover:bg-red-700 disabled:opacity-50"
            >
              {saving ? 'Rejecting...' : 'Confirm Reject'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Confirmation Modal for Approve / Suspend / Reactivate */}
      <Modal
        isOpen={Boolean(confirmAction)}
        onClose={() => setConfirmAction(null)}
        title={
          confirmAction?.type === 'approve'
            ? 'Confirm Account Approval'
            : confirmAction?.type === 'suspend'
            ? 'Confirm Account Suspension'
            : 'Confirm Account Reactivation'
        }
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-3 bg-neutral-50 border border-neutral-200 text-xs font-mono">
            <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              {confirmAction?.type === 'approve' && (
                <p>
                  Approve <strong>{confirmAction.user.email}</strong> with role{' '}
                  <strong className="uppercase">{approvalRoles[confirmAction.user.id] || 'employee'}</strong>?
                </p>
              )}
              {confirmAction?.type === 'suspend' && (
                <p>
                  Suspend <strong>{confirmAction.user.email}</strong>? Their active sessions will be blocked immediately.
                </p>
              )}
              {confirmAction?.type === 'reactivate' && (
                <p>
                  Reactivate <strong>{confirmAction.user.email}</strong> and restore workspace access?
                </p>
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setConfirmAction(null)}
              className="px-4 py-2 border border-neutral-300 text-xs font-mono uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={handleConfirmSensitiveAction}
              className={`px-4 py-2 text-white text-xs font-mono uppercase disabled:opacity-50 ${
                confirmAction?.type === 'suspend'
                  ? 'bg-red-600 hover:bg-red-700'
                  : 'bg-black hover:bg-neutral-800'
              }`}
            >
              {saving ? 'Processing...' : 'Confirm'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
