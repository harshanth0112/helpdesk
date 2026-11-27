import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Zap, Lock } from 'lucide-react';

export const HomePage = () => {
  return (
    <div className="min-h-screen bg-white text-black selection:bg-black selection:text-white flex flex-col justify-between">
      {/* Navigation Header */}
      <header className="border-b border-neutral-200 px-6 md:px-12 py-5 flex items-center justify-between bg-white sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <img src="/logo.png" alt="Smart Helpdesk Logo" className="w-6 h-6 object-contain" />
          <span className="font-mono text-sm tracking-widest uppercase font-bold">SMART HELPDESK</span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="text-xs font-mono uppercase tracking-wider text-neutral-700 hover:text-black transition-colors"
          >
            Sign In
          </Link>
          <Link
            to="/register"
            className="px-4 py-2 bg-black text-white text-xs font-mono uppercase tracking-wider font-semibold hover:bg-neutral-800 transition-colors"
          >
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero Section (ui.md Section 12) */}
      <main className="flex-1">
        <section className="px-6 md:px-12 py-20 md:py-32 max-w-6xl mx-auto border-b border-neutral-200">
          <div className="inline-block px-3 py-1 bg-neutral-100 text-neutral-800 text-xs font-mono uppercase tracking-widest mb-6">
            Enterprise ITSM Platform
          </div>
          <h1 className="text-5xl md:text-8xl font-black uppercase tracking-tighter leading-none mb-8">
            IT SUPPORT,
            <br />
            SIMPLIFIED.
          </h1>
          <p className="text-base md:text-xl text-neutral-600 max-w-2xl font-normal leading-relaxed mb-10">
            A bold, high-performance IT helpdesk management suite engineered for modern enterprises. Role-scoped visibility, cryptographically secure audit trails, and automated queue dispatch.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            <Link
              to="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-black text-white text-xs font-mono uppercase tracking-widest font-semibold hover:bg-neutral-800 transition-colors"
            >
              <span>Deploy Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-neutral-300 text-xs font-mono uppercase tracking-widest text-neutral-800 hover:bg-neutral-100 transition-colors"
            >
              <span>Employee Portal</span>
            </Link>
          </div>
        </section>

        {/* Feature Grid */}
        <section className="px-6 md:px-12 py-20 max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="border border-neutral-200 p-8 space-y-4">
            <ShieldCheck className="w-7 h-7 text-black" />
            <h3 className="text-base font-bold uppercase font-mono tracking-tight">Role-Based Access</h3>
            <p className="text-xs text-neutral-600 leading-relaxed">
              Strict RBAC enforcement across Employee, Technician, and Admin domains preventing IDOR and privilege escalation.
            </p>
          </div>

          <div className="border border-neutral-200 p-8 space-y-4">
            <Zap className="w-7 h-7 text-black" />
            <h3 className="text-base font-bold uppercase font-mono tracking-tight">State Engine</h3>
            <p className="text-xs text-neutral-600 leading-relaxed">
              Finite ticket state transitions from ingestion to resolution with resolution summaries and audit logging.
            </p>
          </div>

          <div className="border border-neutral-200 p-8 space-y-4">
            <Lock className="w-7 h-7 text-black" />
            <h3 className="text-base font-bold uppercase font-mono tracking-tight">Argon2id Security</h3>
            <p className="text-xs text-neutral-600 leading-relaxed">
              OWASP-compliant password hashing, JWT refresh token rotation with reuse detection, and login rate limiting.
            </p>
          </div>
        </section>
      </main>

      {/* Dark Footer */}
      <footer className="bg-[#0A0A0A] text-white px-6 md:px-12 py-12 border-t border-neutral-900">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="w-3 h-3 bg-white" />
              <span className="font-mono text-xs uppercase tracking-widest font-bold">SMART IT HELPDESK</span>
            </div>
            <p className="text-[11px] font-mono text-neutral-500 uppercase">
              Production Release Phase 7
            </p>
          </div>
          <div className="text-xs font-mono text-neutral-500">
            © {new Date().getFullYear()} Enterprise Systems Inc. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};
