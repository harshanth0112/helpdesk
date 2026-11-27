import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { ArrowRight, Eye, EyeOff, Check, AlertCircle } from 'lucide-react';

export const RegisterPage = () => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    department: '',
    phone: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [registeredMessage, setRegisteredMessage] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const { error, success } = useToast();
  const navigate = useNavigate();

  // Password rules
  const passwordCriteria = {
    length: formData.password.length >= 8,
    hasLetter: /[a-zA-Z]/.test(formData.password),
    hasDigit: /\d/.test(formData.password),
    hasSpecial: /[^a-zA-Z0-9]/.test(formData.password),
  };
  const passwordStrengthScore = Object.values(passwordCriteria).filter(Boolean).length;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (fieldErrors[name]) {
      setFieldErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const errs = {};
    if (!formData.first_name.trim()) errs.first_name = 'First name is required.';
    if (!formData.last_name.trim()) errs.last_name = 'Last name is required.';
    if (!formData.email.trim() || !/\S+@\S+\.\S+/.test(formData.email)) {
      errs.email = 'Please provide a valid corporate email address.';
    }
    if (formData.password.length < 8) {
      errs.password = 'Password must be at least 8 characters long.';
    } else if (!/[a-zA-Z]/.test(formData.password) || !/\d/.test(formData.password)) {
      errs.password = 'Password must contain at least one letter and one number.';
    }
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      const res = await api.post('/auth/register', formData);
      const msg =
        res.data?.message ||
        'Your registration has been submitted successfully. Your account is awaiting administrator approval.';
      setRegisteredMessage(msg);
      success('Registration submitted for approval.');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 400 && typeof detail === 'string' && detail.toLowerCase().includes('email')) {
        setFieldErrors((prev) => ({ ...prev, email: detail }));
        error(detail);
      } else {
        error(detail || 'Registration failed. Please check your information.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Dedicated Pending Approval Screen
  if (registeredMessage) {
    return (
      <div className="min-h-screen bg-neutral-50 text-black flex items-center justify-center p-6 antialiased">
        <div className="max-w-xl w-full border border-neutral-300 bg-white p-8 md:p-12 shadow-sm space-y-6">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-3 h-3 bg-amber-600" />
            <span className="text-xs font-mono uppercase tracking-widest text-amber-800 font-bold">
              Account Status: Pending Approval
            </span>
          </div>

          <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase text-black">
            Registration Submitted
          </h1>

          <div className="p-4 border border-amber-300 bg-amber-50 text-xs font-mono text-amber-950 leading-relaxed space-y-2">
            <p className="font-semibold text-sm">
              Your registration has been submitted successfully.
            </p>
            <p className="text-neutral-700">
              Your account is awaiting administrator approval. You will be able to access the application after an administrator approves your account and assigns your role.
            </p>
          </div>

          <div className="border border-neutral-200 p-4 bg-neutral-50 space-y-2 text-xs font-mono text-neutral-600">
            <div className="flex justify-between">
              <span>Applicant:</span>
              <strong className="text-black">{formData.first_name} {formData.last_name}</strong>
            </div>
            <div className="flex justify-between">
              <span>Email:</span>
              <span className="text-black">{formData.email}</span>
            </div>
            {formData.department && (
              <div className="flex justify-between">
                <span>Department:</span>
                <span className="text-black">{formData.department}</span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => navigate('/login')}
            className="w-full flex items-center justify-center gap-2 bg-black text-white hover:bg-neutral-800 py-3.5 text-xs font-mono uppercase tracking-wider font-semibold transition-colors focus:ring-2 focus:ring-black focus:outline-none"
          >
            <span>Return to Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 text-black flex items-center justify-center p-6 antialiased">
      <div className="max-w-xl w-full border border-neutral-300 bg-white p-8 md:p-12 shadow-sm">
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2.5 h-2.5 bg-black" />
            <span className="text-xs font-mono uppercase tracking-widest text-neutral-500 font-bold">
              Employee Onboarding
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase mt-1">Register Account</h1>
          <p className="text-xs text-neutral-600 mt-1.5 leading-relaxed">
            Standard employee registration only. Technician and Administrator accounts are assigned by IT Management upon approval.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="first_name" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
                First Name <span className="text-red-600">*</span>
              </label>
              <input
                id="first_name"
                type="text"
                required
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
                aria-invalid={Boolean(fieldErrors.first_name)}
                aria-describedby={fieldErrors.first_name ? 'fn-err' : undefined}
                className={`w-full px-3.5 py-2.5 border text-sm rounded-none focus:outline-none focus:border-black ${
                  fieldErrors.first_name ? 'border-red-500 bg-red-50/20' : 'border-neutral-300'
                }`}
              />
              {fieldErrors.first_name && (
                <p id="fn-err" className="text-[11px] font-mono text-red-600 mt-1">
                  {fieldErrors.first_name}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="last_name" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
                Last Name <span className="text-red-600">*</span>
              </label>
              <input
                id="last_name"
                type="text"
                required
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
                aria-invalid={Boolean(fieldErrors.last_name)}
                aria-describedby={fieldErrors.last_name ? 'ln-err' : undefined}
                className={`w-full px-3.5 py-2.5 border text-sm rounded-none focus:outline-none focus:border-black ${
                  fieldErrors.last_name ? 'border-red-500 bg-red-50/20' : 'border-neutral-300'
                }`}
              />
              {fieldErrors.last_name && (
                <p id="ln-err" className="text-[11px] font-mono text-red-600 mt-1">
                  {fieldErrors.last_name}
                </p>
              )}
            </div>
          </div>

          <div>
            <label htmlFor="email" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
              Corporate Email Address <span className="text-red-600">*</span>
            </label>
            <input
              id="email"
              type="email"
              required
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="jane.doe@company.com"
              aria-invalid={Boolean(fieldErrors.email)}
              aria-describedby={fieldErrors.email ? 'email-err' : undefined}
              className={`w-full px-3.5 py-2.5 border text-sm rounded-none focus:outline-none focus:border-black ${
                fieldErrors.email ? 'border-red-500 bg-red-50/20' : 'border-neutral-300'
              }`}
            />
            {fieldErrors.email && (
              <p id="email-err" className="text-[11px] font-mono text-red-600 mt-1 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>{fieldErrors.email}</span>
              </p>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="password" className="block text-xs font-mono uppercase tracking-wider text-neutral-700">
                Password <span className="text-red-600">*</span>
              </label>
            </div>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••••••"
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby="password-rules"
                className={`w-full px-3.5 py-2.5 border text-sm rounded-none focus:outline-none focus:border-black pr-10 ${
                  fieldErrors.password ? 'border-red-500 bg-red-50/20' : 'border-neutral-300'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-neutral-500 hover:text-black focus:outline-none"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>

            {/* Password strength & validation indicators */}
            <div id="password-rules" className="mt-2.5 space-y-2">
              <div className="flex items-center gap-1.5 h-1.5 w-full bg-neutral-200">
                <div
                  className={`h-full transition-all duration-300 ${
                    passwordStrengthScore <= 1
                      ? 'w-1/4 bg-red-500'
                      : passwordStrengthScore === 2
                      ? 'w-2/4 bg-amber-500'
                      : passwordStrengthScore === 3
                      ? 'w-3/4 bg-sky-500'
                      : 'w-full bg-emerald-600'
                  }`}
                />
              </div>

              <div className="grid grid-cols-2 gap-1.5 text-[11px] font-mono text-neutral-600">
                <span className={`flex items-center gap-1 ${passwordCriteria.length ? 'text-emerald-700' : ''}`}>
                  {passwordCriteria.length ? <Check className="w-3 h-3 text-emerald-600" /> : <span className="w-3 h-3 inline-block">•</span>}
                  8+ characters
                </span>
                <span className={`flex items-center gap-1 ${passwordCriteria.hasLetter ? 'text-emerald-700' : ''}`}>
                  {passwordCriteria.hasLetter ? <Check className="w-3 h-3 text-emerald-600" /> : <span className="w-3 h-3 inline-block">•</span>}
                  At least 1 letter
                </span>
                <span className={`flex items-center gap-1 ${passwordCriteria.hasDigit ? 'text-emerald-700' : ''}`}>
                  {passwordCriteria.hasDigit ? <Check className="w-3 h-3 text-emerald-600" /> : <span className="w-3 h-3 inline-block">•</span>}
                  At least 1 number
                </span>
                <span className={`flex items-center gap-1 ${passwordCriteria.hasSpecial ? 'text-emerald-700' : ''}`}>
                  {passwordCriteria.hasSpecial ? <Check className="w-3 h-3 text-emerald-600" /> : <span className="w-3 h-3 inline-block">•</span>}
                  Special symbol (optional)
                </span>
              </div>
            </div>
            {fieldErrors.password && (
              <p className="text-[11px] font-mono text-red-600 mt-1">{fieldErrors.password}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="department" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
                Department
              </label>
              <input
                id="department"
                type="text"
                name="department"
                value={formData.department}
                onChange={handleChange}
                placeholder="Engineering, Finance, Ops..."
                className="w-full px-3.5 py-2.5 border border-neutral-300 focus:border-black focus:outline-none text-sm rounded-none"
              />
            </div>
            <div>
              <label htmlFor="phone" className="block text-xs font-mono uppercase tracking-wider text-neutral-700 mb-1">
                Office Phone
              </label>
              <input
                id="phone"
                type="text"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="+1 555-0199"
                className="w-full px-3.5 py-2.5 border border-neutral-300 focus:border-black focus:outline-none text-sm rounded-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-2 flex items-center justify-center gap-2 bg-black text-white hover:bg-neutral-800 py-3.5 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50 focus:ring-2 focus:ring-black focus:outline-none"
          >
            <span>{submitting ? 'Submitting Registration...' : 'Request Account Approval'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-neutral-200 text-center">
          <p className="text-xs text-neutral-600">
            Already have an active account?{' '}
            <Link to="/login" className="font-semibold text-black hover:underline uppercase font-mono">
              Sign In here
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
