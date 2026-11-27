import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { ArrowRight, ArrowLeft } from 'lucide-react';

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resetToken, setResetToken] = useState(null); // Displayed in dev preview for testing convenience
  const { error, success } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await api.post('/auth/forgot-password', { email });
      setSubmitted(true);
      success('Password reset instructions processed.');
      if (res.data.reset_token) {
        setResetToken(res.data.reset_token);
      }
    } catch {
      error('Failed to request password reset.');
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
          <span className="text-xs font-mono uppercase tracking-widest text-neutral-500">Account Recovery</span>
          <h1 className="text-xl font-bold tracking-tight uppercase mt-1">Forgot Password</h1>
          <p className="text-xs text-neutral-600 mt-1">
            Enter your corporate email address. If registered, a reset confirmation token will be issued.
          </p>
        </div>

        {submitted ? (
          <div className="space-y-4">
            <div className="p-4 bg-neutral-50 border border-neutral-200 text-xs text-neutral-800 leading-relaxed">
              If an account exists for <span className="font-semibold">{email}</span>, password reset instructions have been generated.
            </div>

            {resetToken && (
              <div className="p-3 bg-neutral-100 border border-neutral-300 text-xs font-mono break-all">
                <span className="font-bold block text-neutral-500 text-[10px] uppercase">Dev Preview Reset Token:</span>
                {resetToken}
                <div className="mt-2">
                  <Link
                    to={`/reset-password?token=${resetToken}`}
                    className="inline-block bg-black text-white px-3 py-1.5 text-[11px] uppercase font-mono"
                  >
                    Proceed to Reset
                  </Link>
                </div>
              </div>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full px-3.5 py-2.5 border border-neutral-300 focus:border-black focus:outline-hidden text-sm rounded-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-2 flex items-center justify-center gap-2 bg-black text-white hover:bg-neutral-800 py-3 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
            >
              <span>{submitting ? 'Sending...' : 'Send Recovery Token'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
