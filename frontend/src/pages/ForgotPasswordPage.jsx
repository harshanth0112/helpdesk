import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { ArrowRight, ArrowLeft, Mail } from 'lucide-react';

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { error, success } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSubmitted(true);
      success('Password reset instructions sent. Please check your email.');
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
            Enter your corporate email address. If registered, a password reset link will be sent directly to your inbox.
          </p>
        </div>

        {submitted ? (
          <div className="space-y-4">
            <div className="p-4 bg-neutral-50 border border-neutral-200 text-xs text-neutral-800 leading-relaxed space-y-2">
              <div className="flex items-center gap-2 text-black font-semibold uppercase font-mono text-[11px]">
                <Mail className="w-4 h-4 text-black shrink-0" />
                <span>Check Your Mail</span>
              </div>
              <p>
                If an account exists for <span className="font-semibold">{email}</span>, a password reset link has been dispatched to your email address.
              </p>
              <p className="text-neutral-500 text-[11px]">
                Please check your inbox and spam folder. Click the secure reset link inside the email to choose your new password.
              </p>
            </div>

            <div className="pt-2 text-center">
              <button
                type="button"
                onClick={() => setSubmitted(false)}
                className="text-xs font-mono text-neutral-500 hover:text-black uppercase underline"
              >
                Send to a different email address
              </button>
            </div>
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
              <span>{submitting ? 'Sending...' : 'Send Reset Link to Mail'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
