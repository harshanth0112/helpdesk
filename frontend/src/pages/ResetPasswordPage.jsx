import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { ArrowRight, ArrowLeft } from 'lucide-react';

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { error, success } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const urlToken = searchParams.get('token');
    if (urlToken) setToken(urlToken);
  }, [searchParams]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      error('New passwords do not match. Please verify both entries.');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/auth/reset-password', {
        token,
        new_password: newPassword,
      });
      success('Password reset successfully. Please log in with your new password.');
      navigate('/login');
    } catch (err) {
      error(err.response?.data?.detail || 'Invalid or expired reset token.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-white text-black flex items-center justify-center p-6">
      <div className="max-w-md w-full border border-neutral-300 p-8 shadow-xs">
        <Link to="/login" className="inline-flex items-center gap-1.5 text-xs font-mono uppercase text-neutral-500 hover:text-black mb-6">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Sign In</span>
        </Link>

        <div className="mb-6">
          <span className="text-xs font-mono uppercase tracking-widest text-neutral-500">Security Credentials</span>
          <h1 className="text-xl font-bold tracking-tight uppercase mt-1">Set New Password</h1>
          <p className="text-xs text-neutral-600 mt-1">
            Enter the reset token received in your email and confirm your new password below.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
              Reset Token
            </label>
            <input
              type="text"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste token string from your email"
              className="w-full px-3.5 py-2.5 border border-neutral-300 focus:border-black focus:outline-hidden text-sm font-mono rounded-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
              New Password (Min 8 chars, 1 letter, 1 number)
            </label>
            <input
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3.5 py-2.5 border border-neutral-300 focus:border-black focus:outline-hidden text-sm rounded-none"
            />
          </div>

          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3.5 py-2.5 border border-neutral-300 focus:border-black focus:outline-hidden text-sm rounded-none"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-2 flex items-center justify-center gap-2 bg-black text-white hover:bg-neutral-800 py-3 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
          >
            <span>{submitting ? 'Updating Password...' : 'Confirm Reset'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
