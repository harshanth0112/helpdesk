import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { StatusBadge, PriorityBadge } from '../components/Badges';
import { PageHeader, TableSkeleton, EmptyState, ErrorState } from '../components/UIComponents';
import { Modal } from '../components/Modal';
import {
  ArrowLeft,
  MessageSquare,
  Clock,
  Send,
  Lock,
  Paperclip,
  Download,
  Upload,
  FileText,
  Trash2,
} from 'lucide-react';

export const TicketDetailsPage = () => {
  const { ticketId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { success, error } = useToast();

  const [ticket, setTicket] = useState(null);
  const [comments, setComments] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorState, setErrorState] = useState(false);

  // Comment input state
  const [commentText, setCommentText] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);

  // Attachment upload state
  const [uploading, setUploading] = useState(false);

  // Technician / Admin status controls
  const [newStatus, setNewStatus] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [isConfirmStatusModalOpen, setIsConfirmStatusModalOpen] = useState(false);

  // Admin assignment state
  const [assigneeId, setAssigneeId] = useState('');
  const [technicians, setTechnicians] = useState([]);

  // Soft Delete modals state
  const [deleteTicketModal, setDeleteTicketModal] = useState(false);
  const [deleteCommentModal, setDeleteCommentModal] = useState(null);
  const [deleteAttachmentModal, setDeleteAttachmentModal] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);

  const fetchTicketData = async () => {
    try {
      setLoading(true);
      setErrorState(false);
      const [ticketRes, commentsRes, attachmentsRes, historyRes] = await Promise.all([
        api.get(`/tickets/${ticketId}`),
        api.get(`/tickets/${ticketId}/comments`),
        api.get(`/tickets/${ticketId}/attachments`).catch(() => ({ data: [] })),
        api.get(`/tickets/${ticketId}/history`).catch(() => ({ data: [] })),
      ]);

      setTicket(ticketRes.data);
      setNewStatus(ticketRes.data.status);
      setComments(commentsRes.data || []);
      setAttachments(attachmentsRes.data || []);
      setHistory(historyRes.data || []);

      if (user?.role === 'admin') {
        const usersRes = await api.get('/admin/users');
        setTechnicians(usersRes.data.filter((u) => u.role === 'technician' || u.role === 'admin'));
      }
    } catch (err) {
      setErrorState(true);
      error(err.response?.data?.detail || 'Failed to load ticket details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicketData();
  }, [ticketId]);

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    setSubmittingComment(true);
    try {
      await api.post(`/tickets/${ticketId}/comments`, {
        comment_text: commentText,
        is_internal: isInternal,
      });
      setCommentText('');
      setIsInternal(false);
      success('Comment added.');
      fetchTicketData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to post comment.');
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const allowed = ['.png', '.jpg', '.jpeg', '.pdf', '.txt', '.log'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      error(`File format not supported. Supported: ${allowed.join(', ')}`);
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      error('File exceeds 5MB size limit.');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/tickets/${ticketId}/attachments`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      success('Attachment uploaded successfully.');
      fetchTicketData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to upload attachment.');
    } finally {
      setUploading(false);
    }
  };

  const handleDownloadAttachment = async (att) => {
    try {
      const res = await api.get(`/tickets/attachments/${att.id}/download`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', att.file_name);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      error('Failed to download attachment file.');
    }
  };

  const handleDeleteTicket = async () => {
    setDeleting(true);
    try {
      await api.delete(`/tickets/${ticketId}`, {
        data: { deletion_reason: deleteReason.trim() || null },
      });
      success(`Ticket #${ticket.ticket_number} moved to Recycle Bin.`);
      setDeleteTicketModal(false);
      navigate(user?.role === 'admin' ? '/admin/tickets' : '/dashboard');
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to delete ticket.');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteComment = async () => {
    if (!deleteCommentModal) return;
    setDeleting(true);
    try {
      await api.delete(`/tickets/${ticketId}/comments/${deleteCommentModal.id}`, {
        data: { deletion_reason: deleteReason.trim() || null },
      });
      success('Comment moved to Recycle Bin.');
      setDeleteCommentModal(null);
      setDeleteReason('');
      fetchTicketData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to delete comment.');
    } finally {
      setDeleting(false);
    }
  };

  const handleDeleteAttachment = async () => {
    if (!deleteAttachmentModal) return;
    setDeleting(true);
    try {
      await api.delete(`/tickets/${ticketId}/attachments/${deleteAttachmentModal.id}`, {
        data: { deletion_reason: deleteReason.trim() || null },
      });
      success('Attachment moved to Recycle Bin.');
      setDeleteAttachmentModal(null);
      setDeleteReason('');
      fetchTicketData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to delete attachment.');
    } finally {
      setDeleting(false);
    }
  };

  const handleUpdateStatus = async () => {
    setUpdatingStatus(true);
    try {
      await api.patch(`/tickets/${ticketId}/status`, {
        status: newStatus,
        resolution_notes: resolutionNotes || undefined,
      });
      success(`Ticket status updated to ${newStatus}.`);
      setIsConfirmStatusModalOpen(false);
      fetchTicketData();
    } catch (err) {
      error(err.response?.data?.detail || 'Invalid status transition.');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleAssign = async () => {
    try {
      await api.patch(`/tickets/${ticketId}/assign`, {
        assigned_to: assigneeId ? parseInt(assigneeId, 10) : null,
      });
      success('Technician assignment updated.');
      fetchTicketData();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to assign technician.');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="h-12 bg-neutral-100 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="h-40 bg-neutral-100 border border-neutral-200 animate-pulse" />
            <div className="h-60 bg-neutral-100 border border-neutral-200 animate-pulse" />
          </div>
          <div className="h-80 bg-neutral-100 border border-neutral-200 animate-pulse" />
        </div>
      </div>
    );
  }

  if (errorState || !ticket) {
    return (
      <ErrorState
        title="Ticket Not Found or Access Denied"
        message="The requested ticket could not be retrieved. Please verify the ticket ID or ensure your role has authorization."
        onRetry={fetchTicketData}
      />
    );
  }

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      {/* Page Header */}
      <PageHeader
        category={`TICKET #${ticket.ticket_number}`}
        title={ticket.title}
        backLink={
          user?.role === 'admin'
            ? '/admin/tickets'
            : user?.role === 'technician'
            ? '/technician/tickets'
            : '/employee/tickets'
        }
        backLabel="Return to Ticket Directory"
        actions={
          <div className="flex items-center gap-2">
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Description, Attachments, Comments, Audit Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {/* Ticket Description */}
          <div className="border border-neutral-200 p-6 bg-white space-y-3">
            <span className="text-[11px] font-mono uppercase tracking-widest text-neutral-500 font-bold block">
              Problem Description
            </span>
            <p className="text-sm text-neutral-800 whitespace-pre-wrap leading-relaxed font-sans">
              {ticket.description}
            </p>

            {ticket.resolution_notes && (
              <div className="mt-4 p-4 bg-emerald-50/50 border border-emerald-300">
                <span className="block text-xs font-mono uppercase font-bold text-emerald-950 mb-1">
                  Official Resolution Summary:
                </span>
                <p className="text-xs text-neutral-800 leading-normal">{ticket.resolution_notes}</p>
              </div>
            )}
          </div>

          {/* Attachments Section */}
          <div className="border border-neutral-200 p-6 bg-white space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-200">
              <span className="text-xs font-mono uppercase tracking-widest text-neutral-700 font-bold flex items-center gap-2">
                <Paperclip className="w-4 h-4" />
                <span>Diagnostic Attachments ({attachments.length})</span>
              </span>
              <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1 text-xs font-mono uppercase border border-neutral-300 hover:bg-neutral-100 transition-colors">
                <Upload className="w-3.5 h-3.5" />
                <span>{uploading ? 'Uploading...' : 'Add Attachment'}</span>
                <input
                  type="file"
                  onChange={handleFileUpload}
                  disabled={uploading}
                  accept=".png,.jpg,.jpeg,.pdf,.txt,.log"
                  className="sr-only"
                />
              </label>
            </div>

            {attachments.length === 0 ? (
              <p className="text-xs font-mono uppercase text-neutral-400 py-2">
                No diagnostic files or screenshots attached to this ticket.
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="p-3 border border-neutral-200 bg-neutral-50 flex items-center justify-between text-xs font-mono"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileText className="w-4 h-4 text-neutral-600 shrink-0" />
                      <div className="truncate">
                        <div className="font-semibold text-black truncate">{att.file_name}</div>
                        <span className="text-[10px] text-neutral-500">
                          {(att.file_size / 1024).toFixed(0)} KB
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleDownloadAttachment(att)}
                        className="p-1.5 hover:bg-white text-neutral-700 hover:text-black border border-transparent hover:border-neutral-300"
                        title="Download file"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      {user?.role === 'admin' && (
                        <button
                          type="button"
                          onClick={() => {
                            setDeleteAttachmentModal(att);
                            setDeleteReason('');
                          }}
                          className="p-1.5 hover:bg-red-50 text-red-600 border border-transparent hover:border-red-200"
                          title="Soft delete attachment"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Comments & Activity Section */}
          <div className="border border-neutral-200 p-6 bg-white space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-neutral-200">
              <span className="text-xs font-mono uppercase tracking-widest text-neutral-700 font-bold flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                <span>Discussion & Technical Notes ({comments.length})</span>
              </span>
            </div>

            {/* Comments List */}
            <div className="space-y-4">
              {comments.length === 0 ? (
                <p className="text-xs text-neutral-400 font-mono uppercase py-4">No comments posted yet.</p>
              ) : (
                comments.map((c) => (
                  <div
                    key={c.id}
                    className={`p-4 border text-xs ${
                      c.is_internal ? 'bg-amber-50/60 border-amber-300' : 'bg-neutral-50 border-neutral-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-neutral-900">User #{c.user_id}</span>
                        {c.is_internal && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase bg-amber-200 text-amber-950 px-1.5 py-0.5 font-bold">
                            <Lock className="w-2.5 h-2.5" /> Internal Staff Note
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono text-neutral-500">
                          {new Date(c.created_at).toLocaleString()}
                        </span>
                        {user?.role === 'admin' && (
                          <button
                            type="button"
                            onClick={() => {
                              setDeleteCommentModal(c);
                              setDeleteReason('');
                            }}
                            className="p-1 hover:bg-red-50 text-neutral-400 hover:text-red-600 transition-colors"
                            title="Soft delete comment"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                    <p className="text-neutral-800 leading-relaxed whitespace-pre-wrap">{c.comment_text}</p>
                  </div>
                ))
              )}
            </div>

            {/* Add Comment Form */}
            <form onSubmit={handleAddComment} className="pt-4 border-t border-neutral-200 space-y-3">
              <textarea
                required
                rows={3}
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Write an update, provide technical details, or ask a question..."
                className="w-full p-3 border border-neutral-300 focus:border-black focus:outline-none text-xs rounded-none"
              />

              <div className="flex items-center justify-between">
                {user?.role !== 'employee' ? (
                  <label className="flex items-center gap-2 text-xs font-mono text-neutral-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isInternal}
                      onChange={(e) => setIsInternal(e.target.checked)}
                      className="rounded-none border-neutral-300 focus:ring-black"
                    />
                    <span>Post as Internal Note (Staff Only)</span>
                  </label>
                ) : <div />}

                <button
                  type="submit"
                  disabled={submittingComment}
                  className="flex items-center gap-1.5 px-4 py-2 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{submittingComment ? 'Posting...' : 'Post Comment'}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Audit Timeline */}
          <div className="border border-neutral-200 p-6 bg-white space-y-4">
            <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 font-bold flex items-center gap-2 pb-3 border-b border-neutral-200">
              <Clock className="w-4 h-4" />
              <span>Event Audit Timeline ({history.length} updates)</span>
            </span>
            <div className="divide-y divide-neutral-100 text-xs font-mono">
              {history.map((h) => (
                <div key={h.id} className="py-2.5 flex items-start justify-between">
                  <div>
                    <span className="font-semibold text-black uppercase">{h.action}</span>
                    <span className="text-neutral-500 ml-2">by Actor #{h.actor_id || 'System'}</span>
                  </div>
                  <span className="text-neutral-400 text-[11px]">{new Date(h.created_at).toLocaleTimeString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right 1 Column: Metadata & Workflow Controls */}
        <div className="space-y-6">
          {/* Metadata Card */}
          <div className="border border-neutral-200 p-6 bg-neutral-50/50 space-y-4 text-xs font-mono">
            <h3 className="uppercase tracking-widest text-neutral-500 font-bold border-b border-neutral-200 pb-2">
              Ticket Parameters
            </h3>

            <div className="space-y-3">
              <div>
                <span className="text-neutral-500 block uppercase text-[10px]">Requester</span>
                <span className="font-bold text-black">User #{ticket.requester_id}</span>
              </div>
              <div>
                <span className="text-neutral-500 block uppercase text-[10px]">Assigned Technician</span>
                <span className="font-bold text-black">
                  {ticket.assigned_to ? `User #${ticket.assigned_to}` : 'Unassigned'}
                </span>
              </div>
              <div>
                <span className="text-neutral-500 block uppercase text-[10px]">Created Date</span>
                <span>{new Date(ticket.created_at).toLocaleString()}</span>
              </div>
              <div>
                <span className="text-neutral-500 block uppercase text-[10px]">Last Updated</span>
                <span>{new Date(ticket.updated_at).toLocaleString()}</span>
              </div>
              {ticket.resolved_at && (
                <div>
                  <span className="text-neutral-500 block uppercase text-[10px]">Resolved At</span>
                  <span>{new Date(ticket.resolved_at).toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>

          {/* Workflow Action Panel: Role-Permitted Status Transitions */}
          {(user?.role === 'admin' ||
            (user?.role === 'technician' && ticket.assigned_to === user?.id) ||
            (user?.role === 'employee' && ticket.requester_id === user?.id && ticket.status === 'resolved')) && (
            <div className="border border-neutral-200 p-6 bg-white space-y-4">
              <h3 className="text-xs font-mono uppercase tracking-widest text-neutral-700 font-bold border-b border-neutral-200 pb-2">
                Workflow Actions
              </h3>

              {/* Status Update Form */}
              <div className="space-y-3">
                <label className="block text-xs font-mono uppercase text-neutral-600">
                  Update Lifecycle Status
                </label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full p-2.5 border border-neutral-300 text-xs font-mono rounded-none uppercase focus:outline-none focus:border-black"
                >
                  {user?.role === 'admin' && (
                    <>
                      <option value="open">Open</option>
                      <option value="assigned">Assigned</option>
                      <option value="in_progress">In Progress</option>
                      <option value="pending">Pending</option>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </>
                  )}
                  {user?.role === 'technician' && (
                    <>
                      <option value="assigned">Assigned</option>
                      <option value="in_progress">In Progress</option>
                      <option value="pending">Pending</option>
                      <option value="resolved">Resolved</option>
                    </>
                  )}
                  {user?.role === 'employee' && (
                    <>
                      <option value="resolved">Resolved</option>
                      <option value="closed">Closed</option>
                    </>
                  )}
                </select>

                {(newStatus === 'resolved' || newStatus === 'closed') && (
                  <div>
                    <label className="block text-[11px] font-mono uppercase text-neutral-600 mb-1">
                      Resolution Summary
                    </label>
                    <textarea
                      rows={2}
                      value={resolutionNotes}
                      onChange={(e) => setResolutionNotes(e.target.value)}
                      placeholder="Detail root cause and steps taken to resolve incident..."
                      className="w-full p-2.5 border border-neutral-300 text-xs rounded-none focus:outline-none focus:border-black"
                    />
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => setIsConfirmStatusModalOpen(true)}
                  disabled={updatingStatus || newStatus === ticket.status}
                  className="w-full py-2.5 bg-neutral-900 text-white hover:bg-black text-xs font-mono uppercase tracking-wider font-semibold disabled:opacity-40 transition-colors"
                >
                  Apply Status Transition
                </button>
              </div>

              {/* Admin Assignment Control */}
              {user?.role === 'admin' && (
                <div className="pt-4 border-t border-neutral-200 space-y-3">
                  <label className="block text-xs font-mono uppercase text-neutral-600">
                    Assign Technician
                  </label>
                  <select
                    value={assigneeId}
                    onChange={(e) => setAssigneeId(e.target.value)}
                    className="w-full p-2.5 border border-neutral-300 text-xs font-mono rounded-none focus:outline-none focus:border-black"
                  >
                    <option value="">Unassigned</option>
                    {technicians.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.first_name} {t.last_name} ({t.email})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAssign}
                    className="w-full py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors"
                  >
                    Save Assignment
                  </button>
                </div>
              )}

              {/* Admin Soft Delete Ticket */}
              {user?.role === 'admin' && (
                <div className="pt-4 border-t border-neutral-200 space-y-2">
                  <label className="block text-xs font-mono uppercase text-red-600 font-semibold">
                    Danger Zone
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setDeleteTicketModal(true);
                      setDeleteReason('');
                    }}
                    className="w-full py-2.5 border border-red-300 text-red-700 hover:bg-red-50 text-xs font-mono uppercase tracking-wider font-semibold transition-colors flex items-center justify-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    Soft Delete Ticket
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Dialog for Status Change */}
      <Modal
        isOpen={isConfirmStatusModalOpen}
        onClose={() => setIsConfirmStatusModalOpen(false)}
        title="Confirm Status Transition"
      >
        <div className="space-y-4 text-xs font-mono">
          <p>
            Are you sure you want to transition ticket <strong>#{ticket.ticket_number}</strong> from{' '}
            <strong className="uppercase">{ticket.status}</strong> to <strong className="uppercase">{newStatus}</strong>?
          </p>
          <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsConfirmStatusModalOpen(false)}
              className="px-4 py-2 border border-neutral-300 text-xs font-mono uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={updatingStatus}
              onClick={handleUpdateStatus}
              className="px-4 py-2 bg-black text-white text-xs font-mono uppercase hover:bg-neutral-800 disabled:opacity-50"
            >
              {updatingStatus ? 'Updating...' : 'Confirm Transition'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete Ticket Confirmation Modal */}
      <Modal
        isOpen={deleteTicketModal}
        onClose={() => setDeleteTicketModal(false)}
        title="Soft Delete Ticket"
      >
        <div className="space-y-4 text-xs font-mono">
          <div className="p-3 bg-red-50 border border-red-200 text-red-800">
            <p className="font-semibold">Move Ticket #{ticket.ticket_number} to Recycle Bin?</p>
            <p className="mt-1 text-red-700">
              The ticket will be hidden from normal lists. All comments, attachments, and history remain intact and can be restored from the Recycle Bin.
            </p>
          </div>
          <div>
            <label className="block uppercase text-neutral-600 mb-1">Reason for Deletion (Optional)</label>
            <textarea
              rows={2}
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              placeholder="Reason for archiving/deleting..."
              className="w-full p-2 border border-neutral-300 text-xs rounded-none focus:outline-none focus:border-black font-mono"
            />
          </div>
          <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setDeleteTicketModal(false)}
              className="px-4 py-2 border border-neutral-300 uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deleting}
              onClick={handleDeleteTicket}
              className="px-4 py-2 bg-red-600 text-white uppercase hover:bg-red-700 disabled:opacity-50 font-semibold"
            >
              {deleting ? 'Deleting...' : 'Confirm Soft Delete'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete Comment Confirmation Modal */}
      <Modal
        isOpen={Boolean(deleteCommentModal)}
        onClose={() => setDeleteCommentModal(null)}
        title="Soft Delete Comment"
      >
        <div className="space-y-4 text-xs font-mono">
          <p>
            Move comment #{deleteCommentModal?.id} to the Recycle Bin?
          </p>
          <div>
            <label className="block uppercase text-neutral-600 mb-1">Reason for Deletion (Optional)</label>
            <textarea
              rows={2}
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              placeholder="Audit reason..."
              className="w-full p-2 border border-neutral-300 text-xs rounded-none focus:outline-none focus:border-black font-mono"
            />
          </div>
          <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setDeleteCommentModal(null)}
              className="px-4 py-2 border border-neutral-300 uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deleting}
              onClick={handleDeleteComment}
              className="px-4 py-2 bg-red-600 text-white uppercase hover:bg-red-700 disabled:opacity-50 font-semibold"
            >
              {deleting ? 'Deleting...' : 'Confirm Soft Delete'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Delete Attachment Confirmation Modal */}
      <Modal
        isOpen={Boolean(deleteAttachmentModal)}
        onClose={() => setDeleteAttachmentModal(null)}
        title="Soft Delete Attachment"
      >
        <div className="space-y-4 text-xs font-mono">
          <p>
            Move attachment "{deleteAttachmentModal?.file_name}" to the Recycle Bin? The file is kept on server storage.
          </p>
          <div>
            <label className="block uppercase text-neutral-600 mb-1">Reason for Deletion (Optional)</label>
            <textarea
              rows={2}
              value={deleteReason}
              onChange={(e) => setDeleteReason(e.target.value)}
              placeholder="Audit reason..."
              className="w-full p-2 border border-neutral-300 text-xs rounded-none focus:outline-none focus:border-black font-mono"
            />
          </div>
          <div className="pt-3 border-t border-neutral-200 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setDeleteAttachmentModal(null)}
              className="px-4 py-2 border border-neutral-300 uppercase hover:bg-neutral-100"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={deleting}
              onClick={handleDeleteAttachment}
              className="px-4 py-2 bg-red-600 text-white uppercase hover:bg-red-700 disabled:opacity-50 font-semibold"
            >
              {deleting ? 'Deleting...' : 'Confirm Soft Delete'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
