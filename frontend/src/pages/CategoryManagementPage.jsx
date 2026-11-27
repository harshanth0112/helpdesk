import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { LoadingState } from '../components/TableControls';
import { FolderTree, Plus, CheckCircle2, XCircle, Edit2, Trash2, ShieldAlert } from 'lucide-react';

export const CategoryManagementPage = () => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [formData, setFormData] = useState({ name: '', description: '', is_active: true });
  const [saving, setSaving] = useState(false);

  // Soft delete state
  const [deleteModalCategory, setDeleteModalCategory] = useState(null);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleting, setDeleting] = useState(false);

  const { success, error } = useToast();

  const fetchCategories = async () => {
    try {
      setLoading(true);
      const res = await api.get('/admin/categories');
      setCategories(res.data);
    } catch {
      error('Failed to load categories.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const handleOpenCreateModal = () => {
    setEditingCategory(null);
    setFormData({ name: '', description: '', is_active: true });
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (cat) => {
    setEditingCategory(cat);
    setFormData({
      name: cat.name,
      description: cat.description || '',
      is_active: cat.is_active,
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    setSaving(true);
    try {
      if (editingCategory) {
        await api.patch(`/admin/categories/${editingCategory.id}`, formData);
        success(`Category "${formData.name}" updated successfully.`);
      } else {
        await api.post('/admin/categories', formData);
        success(`Category "${formData.name}" created successfully.`);
      }
      setIsModalOpen(false);
      fetchCategories();
    } catch (err) {
      error(err.response?.data?.detail || 'Operation failed.');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleStatus = async (cat) => {
    try {
      await api.patch(`/admin/categories/${cat.id}`, { is_active: !cat.is_active });
      success(`Category "${cat.name}" is now ${!cat.is_active ? 'Active' : 'Inactive'}.`);
      fetchCategories();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to update category status.');
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteModalCategory) return;
    setDeleting(true);
    try {
      await api.delete(`/admin/categories/${deleteModalCategory.id}`, {
        data: { deletion_reason: deleteReason.trim() || null },
      });
      success(`Category "${deleteModalCategory.name}" soft-deleted successfully.`);
      setDeleteModalCategory(null);
      setDeleteReason('');
      fetchCategories();
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to delete category.');
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <LoadingState message="Fetching system categories..." />;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-neutral-200">
        <div>
          <span className="text-xs font-mono uppercase tracking-widest text-neutral-500">System Administration</span>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase mt-1 flex items-center gap-2">
            <FolderTree className="w-7 h-7 text-neutral-800" />
            <span>Support Categories</span>
          </h1>
          <p className="text-xs text-neutral-600 mt-1">
            Configure ticketing classification domains and service routing categories.
          </p>
        </div>
        <button
          onClick={handleOpenCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add Category</span>
        </button>
      </div>

      {/* Categories Table */}
      <div className="overflow-x-auto border border-neutral-200 bg-white">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-neutral-50 border-b border-neutral-200 font-mono uppercase tracking-wider text-neutral-600">
              <th className="p-3.5 font-semibold w-16">ID</th>
              <th className="p-3.5 font-semibold">Category Name</th>
              <th className="p-3.5 font-semibold">Description</th>
              <th className="p-3.5 font-semibold">Status</th>
              <th className="p-3.5 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-200">
            {categories.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-xs font-mono text-neutral-400 uppercase">
                  No categories defined.
                </td>
              </tr>
            ) : (
              categories.map((cat) => (
                <tr key={cat.id} className="hover:bg-neutral-50/70 transition-colors">
                  <td className="p-3.5 font-mono text-neutral-500">#{cat.id}</td>
                  <td className="p-3.5 font-bold text-neutral-900 font-mono">{cat.name}</td>
                  <td className="p-3.5 text-neutral-600 max-w-md">{cat.description || '—'}</td>
                  <td className="p-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono uppercase font-bold border ${
                        cat.is_active
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                          : 'bg-neutral-100 text-neutral-600 border-neutral-300'
                      }`}
                    >
                      {cat.is_active ? <CheckCircle2 className="w-3 h-3 text-emerald-600" /> : <XCircle className="w-3 h-3 text-neutral-400" />}
                      <span>{cat.is_active ? 'Active' : 'Inactive'}</span>
                    </span>
                  </td>
                  <td className="p-3.5 text-right space-x-2">
                    <button
                      onClick={() => handleOpenEditModal(cat)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono uppercase border border-neutral-300 text-neutral-700 hover:bg-neutral-100 transition-colors"
                    >
                      <Edit2 className="w-3 h-3" />
                      <span>Edit</span>
                    </button>
                    <button
                      onClick={() => handleToggleStatus(cat)}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono uppercase border transition-colors ${
                        cat.is_active
                          ? 'border-neutral-300 text-neutral-600 hover:bg-neutral-100'
                          : 'border-emerald-500 text-emerald-700 hover:bg-emerald-50'
                      }`}
                    >
                      <span>{cat.is_active ? 'Deactivate' : 'Activate'}</span>
                    </button>
                    <button
                      onClick={() => {
                        setDeleteModalCategory(cat);
                        setDeleteReason('');
                      }}
                      className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-mono uppercase border border-red-300 text-red-700 hover:bg-red-50 transition-colors"
                      title="Soft delete category"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Delete</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModalCategory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white border border-neutral-300 max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="p-2 border border-red-200 bg-red-50 text-red-700 shrink-0">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-mono uppercase font-bold tracking-wider text-black">
                  Soft Delete Category
                </h2>
                <p className="text-xs text-neutral-600 mt-1">
                  Are you sure you want to soft delete category "{deleteModalCategory.name}"?
                  It will be moved to the Recycle Bin and hidden from ticket forms.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
                Reason for deletion (optional)
              </label>
              <textarea
                rows={2}
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Optional audit reason..."
                className="w-full p-2 border border-neutral-300 focus:border-black focus:outline-hidden text-xs rounded-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-200">
              <button
                type="button"
                onClick={() => setDeleteModalCategory(null)}
                disabled={deleting}
                className="px-4 py-2 border border-neutral-300 text-xs font-mono uppercase hover:bg-neutral-100 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={deleting}
                className="px-4 py-2 bg-red-600 text-white text-xs font-mono uppercase font-semibold hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Confirm Soft Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal for Create / Edit */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white border border-neutral-300 max-w-md w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
              <h2 className="text-sm font-mono uppercase font-bold tracking-wider text-black">
                {editingCategory ? 'Edit Category' : 'Create New Category'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-neutral-400 hover:text-black font-mono text-sm"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
                  Category Name <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Identity & Permissions"
                  className="w-full p-2.5 border border-neutral-300 focus:border-black focus:outline-hidden text-xs rounded-none"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Summary of issues covered by this domain..."
                  className="w-full p-2.5 border border-neutral-300 focus:border-black focus:outline-hidden text-xs rounded-none"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="category_is_active"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="rounded-none border-neutral-300"
                />
                <label htmlFor="category_is_active" className="text-xs font-mono text-neutral-700 cursor-pointer">
                  Category is Active and available for new tickets
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-neutral-200">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-neutral-300 text-xs font-mono uppercase hover:bg-neutral-100 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-black text-white text-xs font-mono uppercase font-semibold hover:bg-neutral-800 transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving...' : editingCategory ? 'Save Changes' : 'Create Category'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
