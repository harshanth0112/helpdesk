import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { ArrowRight, Eye, EyeOff, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';

export const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [statusNotice, setStatusNotice] = useState(null);

  const { login } = useAuth();
  const { error, success } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setStatusNotice(null);

    try {
      const userData = await login(email, password);
      success('Authentication successful.');
      // Direct user based on their specific role
      if (userData?.role === 'admin') {
        navigate('/admin/dashboard');
      } else if (userData?.role === 'technician') {
        navigate('/technician/dashboard');
      } else {
        navigate('/employee/dashboard');
      }
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (!err.response) {
        setStatusNotice({
          type: 'network',
          title: 'Network Connection Offline',
          message: 'Unable to reach the authentication service. Please verify your internet connection or try again later.',
        });
        error('Network connection error.');
      } else if (status === 403) {
        // Specific account approval or suspension status message
        const lowerDetail = (typeof detail === 'string' ? detail : '').toLowerCase();
        let title = 'Account Access Restricted';
        if (lowerDetail.includes('pending')) {
          title = 'Account Awaiting Administrator Approval';
        } else if (lowerDetail.includes('suspended')) {
          title = 'Account Suspended';
        } else if (lowerDetail.includes('rejected')) {
          title = 'Registration Application Rejected';
        }
        setStatusNotice({
          type: 'account_status',
          title,
          message: detail || 'Your account does not have active authorization to access this workspace.',
        });
        error(detail || 'Access forbidden.');
      } else if (status === 401) {
        setStatusNotice({
          type: 'credentials',
          title: 'Invalid Credentials',
          message: detail || 'The email address or password entered does not match our corporate records.',
        });
        error(detail || 'Invalid email or password.');
      } else if (status >= 500) {
        setStatusNotice({
          type: 'server',
          title: 'Server Error (500)',
          message: 'A backend service error occurred while processing authentication. Please notify your IT administrator.',
        });
        error('Internal server error occurred.');
      } else {
        setStatusNotice({
          type: 'general',
          title: 'Authentication Failed',
          message: detail || 'An unexpected error occurred during sign in.',
        });
        error(detail || 'Authentication failed.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-white text-black antialiased">
      {/* Left Column: Bold Editorial Branding */}
      <div className="w-full md:w-1/2 bg-[#0A0A0A] text-white p-8 md:p-16 flex flex-col justify-between border-b md:border-b-0 md:border-r border-neutral-900">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <img src="/logo.png" alt="Smart Helpdesk Logo" className="w-7 h-7 object-contain invert" />
            <span className="font-mono text-sm tracking-widest uppercase font-bold">SMART HELPDESK</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-black tracking-tighter uppercase leading-none mb-6">
            IT SUPPORT,
            <br />
            SIMPLIFIED.
          </h1>
          <p className="text-neutral-400 text-sm md:text-base max-w-md font-normal leading-relaxed">
            Enterprise-grade resolution tracking, role-based workflows, and full audit accountability.
          </p>
        </div>

        <div className="mt-12 pt-8 border-t border-neutral-800 text-xs font-mono text-neutral-500 uppercase tracking-wider flex justify-between">
          <span>Enterprise Workspace</span>
          <span>Security Protocol 4.0</span>
        </div>
      </div>

      {/* Right Column: Minimalist Login Form */}
      <div className="w-full md:w-1/2 p-8 md:p-16 flex flex-col justify-center max-w-lg mx-auto">
        <div className="mb-8">
          <span className="text-xs font-mono uppercase tracking-widest text-neutral-500">Sign In</span>
          <h2 className="text-2xl font-bold tracking-tight uppercase mt-1">Access Workspace</h2>
        </div>

        {statusNotice && (
          <div
            role="alert"
            className={`mb-6 p-4 border text-xs font-mono leading-relaxed space-y-1 ${
              statusNotice.type === 'account_status'
                ? 'border-amber-400 bg-amber-50 text-amber-950'
                : statusNotice.type === 'network' || statusNotice.type === 'server'
                ? 'border-red-400 bg-red-50 text-red-950'
                : 'border-neutral-300 bg-neutral-100 text-neutral-900'
            }`}
          >
            <div className="flex items-center gap-2 font-bold uppercase tracking-wider">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{statusNotice.title}</span>
            </div>
            <p className="text-neutral-700 pl-6">{statusNotice.message}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div>
            <label htmlFor="login-email" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-2">
              Corporate Email Address
            </label>
            <input
              id="login-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="w-full px-4 py-3 border border-neutral-300 focus:border-black focus:outline-none text-sm rounded-none transition-colors"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label htmlFor="login-password" className="block text-xs font-mono uppercase tracking-wider text-neutral-700">
                Password
              </label>
              <Link to="/forgot-password" className="text-xs font-mono text-neutral-500 hover:text-black uppercase">
                Forgot Password?
              </Link>
            </div>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-3 border border-neutral-300 focus:border-black focus:outline-none text-sm rounded-none transition-colors pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3.5 text-neutral-500 hover:text-black focus:outline-none"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-4 flex items-center justify-center gap-2 bg-black text-white hover:bg-neutral-800 py-3.5 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50 focus:ring-2 focus:ring-black focus:outline-none"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Authenticating Workspace...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-neutral-200 text-center">
          <p className="text-xs text-neutral-600">
            Need an employee account?{' '}
            <Link to="/register" className="font-semibold text-black hover:underline uppercase font-mono">
              Register here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
