import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { PageHeader } from '../components/UIComponents';
import { ArrowRight, Upload, X, FileText, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export const CreateTicketPage = () => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category_id: '',
    priority: 'medium',
  });
  const [categories, setCategories] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const { error, success } = useToast();
  const navigate = useNavigate();

  // Allowed MIME types and extensions: .png, .jpg, .jpeg, .pdf, .txt, .log
  const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB limit
  const ALLOWED_EXTS = ['.png', '.jpg', '.jpeg', '.pdf', '.txt', '.log'];

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await api.get('/tickets/categories');
        const cats = res.data || [];
        setCategories(cats);
        if (cats.length > 0) {
          setFormData((prev) => ({ ...prev, category_id: cats[0].id }));
        }
      } catch {
        // Fallback default categories
        setCategories([
          { id: 1, name: 'Hardware & Workstations' },
          { id: 2, name: 'Software & Productivity Tools' },
          { id: 3, name: 'Network & VPN Infrastructure' },
          { id: 4, name: 'Security & Access Control' },
        ]);
        setFormData((prev) => ({ ...prev, category_id: 1 }));
      }
    };
    fetchCategories();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'category_id' ? parseInt(value, 10) : value,
    }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setFileError('');
    if (!file) {
      setSelectedFile(null);
      return;
    }

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setFileError(`Invalid file format (${ext}). Supported: PNG, JPG, JPEG, PDF, TXT, LOG.`);
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setFileError(`File exceeds maximum size of 5 MB (Current size: ${(file.size / (1024 * 1024)).toFixed(1)} MB).`);
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const validate = () => {
    const errs = {};
    if (!formData.title.trim()) {
      errs.title = 'Please provide a concise subject summary.';
    } else if (formData.title.trim().length < 5) {
      errs.title = 'Subject summary must be at least 5 characters long.';
    }

    if (!formData.description.trim()) {
      errs.description = 'Please detail the technical issue encountered.';
    } else if (formData.description.trim().length < 15) {
      errs.description = 'Detailed description must be at least 15 characters long.';
    }

    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      // 1. Create ticket
      const res = await api.post('/tickets', {
        title: formData.title,
        description: formData.description,
        category_id: formData.category_id || 1,
        priority: formData.priority,
      });

      const ticketId = res.data.id;
      const ticketNum = res.data.ticket_number;

      // 2. Upload attachment if attached
      if (selectedFile) {
        const uploadData = new FormData();
        uploadData.append('file', selectedFile);
        try {
          await api.post(`/tickets/${ticketId}/attachments`, uploadData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });
        } catch {
          // Log but proceed
        }
      }

      success(`Ticket ${ticketNum} created successfully.`);
      navigate(`/tickets/${ticketId}`);
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to submit service ticket.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in font-sans">
      <PageHeader
        category="Service Request"
        title="Submit Helpdesk Ticket"
        description="Provide comprehensive details and diagnostic attachments to allow IT Engineers to triage and resolve your incident swiftly."
        backLink="/employee/tickets"
        backLabel="Return to Ticket Directory"
      />

      <form onSubmit={handleSubmit} className="border border-neutral-200 p-8 bg-white space-y-6" noValidate>
        {/* Subject */}
        <div>
          <label htmlFor="ticket-title" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-2">
            Subject Summary <span className="text-red-600">*</span>
          </label>
          <input
            id="ticket-title"
            type="text"
            required
            name="title"
            value={formData.title}
            onChange={handleChange}
            placeholder="e.g. Swollen laptop battery, VPN authentication failing on macOS"
            aria-invalid={Boolean(fieldErrors.title)}
            className={`w-full px-4 py-3 border text-sm rounded-none focus:outline-none focus:border-black ${
              fieldErrors.title ? 'border-red-500 bg-red-50/20' : 'border-neutral-300'
            }`}
          />
          {fieldErrors.title && (
            <p className="text-[11px] font-mono text-red-600 mt-1 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{fieldErrors.title}</span>
            </p>
          )}
        </div>

        {/* Category & Urgency */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="ticket-category" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-2">
              Service Category <span className="text-red-600">*</span>
            </label>
            <select
              id="ticket-category"
              name="category_id"
              value={formData.category_id}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-neutral-300 focus:border-black focus:outline-none text-sm rounded-none bg-white font-mono"
            >
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="ticket-priority" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-2">
              Business Impact & Priority
            </label>
            <select
              id="ticket-priority"
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              className="w-full px-4 py-3 border border-neutral-300 focus:border-black focus:outline-none text-sm rounded-none bg-white font-mono uppercase"
            >
              <option value="low">Low Priority (General question)</option>
              <option value="medium">Medium Priority (Standard request)</option>
              <option value="high">High Priority (Work impaired)</option>
              <option value="critical">Critical / Workstation Outage</option>
            </select>
          </div>
        </div>

        {/* Detailed Description */}
        <div>
          <label htmlFor="ticket-desc" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-2">
            Detailed Description <span className="text-red-600">*</span>
          </label>
          <textarea
            id="ticket-desc"
            required
            rows={6}
            name="description"
            value={formData.description}
            onChange={handleChange}
            placeholder="Please detail steps to reproduce, device serial numbers, exact error codes, or affected cloud services..."
            aria-invalid={Boolean(fieldErrors.description)}
            className={`w-full p-4 border text-sm rounded-none leading-relaxed focus:outline-none focus:border-black ${
              fieldErrors.description ? 'border-red-500 bg-red-50/20' : 'border-neutral-300'
            }`}
          />
          {fieldErrors.description && (
            <p className="text-[11px] font-mono text-red-600 mt-1 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5 shrink-0" />
              <span>{fieldErrors.description}</span>
            </p>
          )}
        </div>

        {/* Diagnostic Attachment Guidance */}
        <div>
          <label className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-2">
            Diagnostic Attachment (Optional)
          </label>
          <div className="border border-dashed border-neutral-300 p-6 bg-neutral-50 flex flex-col items-center justify-center text-center">
            <Upload className="w-6 h-6 text-neutral-400 mb-2" />
            <label
              htmlFor="ticket-file"
              className="cursor-pointer text-xs font-mono uppercase text-black font-bold hover:underline"
            >
              <span>Select File from Device</span>
              <input
                id="ticket-file"
                type="file"
                onChange={handleFileChange}
                accept=".png,.jpg,.jpeg,.pdf,.txt,.log"
                className="sr-only"
              />
            </label>
            <p className="text-[11px] font-mono text-neutral-500 mt-1">
              Supported formats: PNG, JPG, PDF, TXT, LOG (Max file size: 5 MB)
            </p>

            {selectedFile && (
              <div className="mt-4 p-2.5 bg-white border border-neutral-200 flex items-center gap-3 text-xs font-mono">
                <FileText className="w-4 h-4 text-emerald-600" />
                <span className="font-semibold text-black">{selectedFile.name}</span>
                <span className="text-neutral-500">({(selectedFile.size / 1024).toFixed(0)} KB)</span>
                <button
                  type="button"
                  onClick={() => setSelectedFile(null)}
                  className="text-neutral-400 hover:text-black ml-2"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {fileError && (
              <p className="text-[11px] font-mono text-red-600 mt-2 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{fileError}</span>
              </p>
            )}
          </div>
        </div>

        {/* Form Actions */}
        <div className="pt-4 border-t border-neutral-200 flex items-center justify-between">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-5 py-2.5 text-xs font-mono uppercase text-neutral-600 hover:text-black border border-neutral-300 hover:bg-neutral-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="flex items-center gap-2 px-6 py-3 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50 focus:ring-2 focus:ring-black focus:outline-none"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Dispatching Ticket...</span>
              </>
            ) : (
              <>
                <span>Dispatch Ticket</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
