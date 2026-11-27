import React from 'react';
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  PlayCircle,
  Shield,
  Wrench,
  User,
  ArrowUp,
  ArrowDown,
  Minus,
  Flame,
} from 'lucide-react';

/**
 * StatusBadge: Accessible, color-contrast compliant badge with unambiguous shape icons
 */
export const StatusBadge = ({ status }) => {
  const normalized = (status || '').toLowerCase().replace('_', ' ');

  const config = {
    open: {
      style: 'bg-neutral-100 text-neutral-800 border-neutral-300',
      icon: Clock,
      label: 'Open',
    },
    assigned: {
      style: 'bg-indigo-50 text-indigo-900 border-indigo-200',
      icon: HelpCircle,
      label: 'Assigned',
    },
    'in progress': {
      style: 'bg-blue-50 text-blue-900 border-blue-200',
      icon: PlayCircle,
      label: 'In Progress',
    },
    pending: {
      style: 'bg-amber-50 text-amber-900 border-amber-300',
      icon: AlertCircle,
      label: 'Pending',
    },
    resolved: {
      style: 'bg-emerald-50 text-emerald-900 border-emerald-300',
      icon: CheckCircle2,
      label: 'Resolved',
    },
    closed: {
      style: 'bg-neutral-900 text-white border-neutral-900',
      icon: CheckCircle2,
      label: 'Closed',
    },
  };

  const item = config[normalized] || {
    style: 'bg-neutral-100 text-neutral-800 border-neutral-300',
    icon: Clock,
    label: normalized,
  };
  const Icon = item.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-mono uppercase tracking-wider border rounded-none ${item.style}`}
      aria-label={`Status: ${item.label}`}
    >
      <Icon className="w-3 h-3 shrink-0" aria-hidden="true" />
      <span>{item.label}</span>
    </span>
  );
};

/**
 * PriorityBadge: High-contrast, distinguishable indicators with directional icons
 */
export const PriorityBadge = ({ priority }) => {
  const normalized = (priority || '').toLowerCase();

  const config = {
    low: {
      style: 'text-neutral-700 border-neutral-300 bg-neutral-50',
      icon: ArrowDown,
      label: 'Low',
    },
    medium: {
      style: 'text-sky-900 border-sky-300 bg-sky-50',
      icon: Minus,
      label: 'Medium',
    },
    high: {
      style: 'text-amber-900 border-amber-300 bg-amber-50 font-semibold',
      icon: ArrowUp,
      label: 'High',
    },
    critical: {
      style: 'text-red-950 border-red-400 bg-red-100 font-bold',
      icon: Flame,
      label: 'Critical',
    },
  };

  const item = config[normalized] || {
    style: 'text-neutral-700 border-neutral-300 bg-neutral-50',
    icon: Minus,
    label: normalized,
  };
  const Icon = item.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-mono uppercase tracking-wider border rounded-none ${item.style}`}
      aria-label={`Priority: ${item.label}`}
    >
      <Icon className="w-3 h-3 shrink-0" aria-hidden="true" />
      <span>{item.label}</span>
    </span>
  );
};

/**
 * RoleBadge: Clear enterprise roles
 */
export const RoleBadge = ({ role }) => {
  const normalized = (role || '').toLowerCase();

  const config = {
    admin: {
      style: 'bg-black text-white border-black font-semibold',
      icon: Shield,
      label: 'Admin',
    },
    technician: {
      style: 'bg-neutral-800 text-white border-neutral-800 font-medium',
      icon: Wrench,
      label: 'Technician',
    },
    employee: {
      style: 'bg-neutral-100 text-neutral-800 border-neutral-300',
      icon: User,
      label: 'Employee',
    },
  };

  const item = config[normalized] || {
    style: 'bg-neutral-100 text-neutral-800 border-neutral-300',
    icon: User,
    label: normalized,
  };
  const Icon = item.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-mono uppercase tracking-wider border rounded-none ${item.style}`}
      aria-label={`Role: ${item.label}`}
    >
      <Icon className="w-3 h-3 shrink-0" aria-hidden="true" />
      <span>{item.label}</span>
    </span>
  );
};

/**
 * ApprovalStatusBadge: Approval states
 */
export const ApprovalStatusBadge = ({ status }) => {
  const normalized = (status || '').toLowerCase();
  const config = {
    approved: {
      style: 'bg-emerald-50 text-emerald-900 border-emerald-300',
      icon: CheckCircle2,
      label: 'Approved',
    },
    pending: {
      style: 'bg-amber-50 text-amber-950 border-amber-300 font-semibold',
      icon: Clock,
      label: 'Pending',
    },
    rejected: {
      style: 'bg-red-50 text-red-900 border-red-300',
      icon: AlertCircle,
      label: 'Rejected',
    },
    suspended: {
      style: 'bg-neutral-200 text-neutral-900 border-neutral-400',
      icon: Shield,
      label: 'Suspended',
    },
  };

  const item = config[normalized] || {
    style: 'bg-neutral-100 text-neutral-800 border-neutral-300',
    icon: Clock,
    label: normalized || 'Approved',
  };
  const Icon = item.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[10px] font-mono uppercase border rounded-none ${item.style}`}
      aria-label={`Approval Status: ${item.label}`}
    >
      <Icon className="w-2.5 h-2.5 shrink-0" aria-hidden="true" />
      <span>{item.label}</span>
    </span>
  );
};
