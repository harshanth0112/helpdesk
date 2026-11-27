import React, { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Ticket,
  PlusCircle,
  Users,
  Wrench,
  FolderTree,
  BarChart3,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { RoleBadge } from '../components/Badges';

export const DashboardLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Build role-aware navigation links
  const getNavLinks = () => {
    const role = user?.role || 'employee';

    if (role === 'admin') {
      return [
        { name: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
        { name: 'All Tickets', path: '/admin/tickets', icon: Ticket },
        { name: 'User Management', path: '/admin/users', icon: Users },
        { name: 'Technicians', path: '/admin/technicians', icon: Wrench },
        { name: 'Categories', path: '/admin/categories', icon: FolderTree },
        { name: 'Analytics', path: '/admin/analytics', icon: BarChart3 },
        { name: 'Audit Logs', path: '/admin/audit-logs', icon: FileText },
        { name: 'Profile & Settings', path: '/profile', icon: Settings },
      ];
    }

    if (role === 'technician') {
      return [
        { name: 'Dashboard', path: '/technician/dashboard', icon: LayoutDashboard },
        { name: 'All Tickets', path: '/technician/tickets', icon: Ticket },
        { name: 'Workload & Queue', path: '/technician/workload', icon: Wrench },
        { name: 'Profile', path: '/profile', icon: UserIcon },
      ];
    }

    // Default: Employee
    return [
      { name: 'Dashboard', path: '/employee/dashboard', icon: LayoutDashboard },
      { name: 'All Tickets', path: '/employee/tickets', icon: Ticket },
      { name: 'Create Ticket', path: '/employee/create-ticket', icon: PlusCircle },
      { name: 'Profile', path: '/profile', icon: UserIcon },
    ];
  };

  const navLinks = getNavLinks();

  return (
    <div className="min-h-screen bg-neutral-50/50 text-black flex flex-col md:flex-row antialiased selection:bg-black selection:text-white">
      {/* Mobile Topbar */}
      <header className="md:hidden flex items-center justify-between p-4 border-b border-neutral-200 bg-white sticky top-0 z-40">
        <div className="flex items-center gap-2.5">
          <img src="/logo.png" alt="Smart Helpdesk Logo" className="w-6 h-6 object-contain" />
          <span className="font-mono text-xs uppercase tracking-widest font-bold">SMART HELPDESK</span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="min-h-[44px] min-w-[44px] flex items-center justify-center p-2 border border-neutral-300 text-neutral-800 hover:text-black focus:outline-none focus:ring-2 focus:ring-black"
          aria-label={mobileOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Backdrop for mobile navigation drawer */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 bg-black/40 z-45 md:hidden"
          aria-hidden="true"
        />
      )}

      {/* Sidebar Navigation: pinned to viewport height with internal scroll so the User Profile & Logout always stay visible in screen */}
      <aside
        aria-label="Main Navigation"
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-neutral-200 flex flex-col justify-between h-screen md:sticky md:top-0 transform transition-transform duration-300 ease-in-out md:translate-x-0 ${
          mobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-neutral-200 flex items-center justify-between shrink-0 bg-white">
          <div>
            <div className="flex items-center gap-2.5 mb-1">
              <img src="/logo.png" alt="Smart Helpdesk Logo" className="w-5 h-5 object-contain" />
              <span className="font-mono text-xs uppercase tracking-widest font-black text-black">
                SMART HELPDESK
              </span>
            </div>
            <p className="text-[10px] font-mono text-neutral-500 uppercase tracking-wider">
              IT Enterprise Suite
            </p>
          </div>
          {mobileOpen && (
            <button
              onClick={() => setMobileOpen(false)}
              className="md:hidden min-h-[44px] min-w-[44px] flex items-center justify-center text-neutral-500 hover:text-black"
              aria-label="Close navigation"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Scrollable Nav Links Area */}
        <nav className="p-3 space-y-1 overflow-y-auto flex-1">
          {navLinks.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-3 py-2 text-xs font-mono uppercase tracking-wider transition-all duration-200 border ${
                  isActive
                    ? 'bg-black text-white border-black font-semibold shadow-xs'
                    : 'text-neutral-700 border-transparent hover:bg-neutral-100 hover:text-black'
                } focus:outline-none focus:ring-1 focus:ring-black`}
              >
                <Icon className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span className="truncate">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sticky User Profile & Logout Footer - Always securely fit inside screen */}
        <div className="p-4 border-t border-neutral-200 bg-neutral-50/80 shrink-0">
          <div className="flex items-center gap-2.5 mb-2.5">
            <div className="w-8 h-8 shrink-0 bg-black text-white flex items-center justify-center font-mono text-xs font-bold">
              {user?.first_name ? user.first_name[0].toUpperCase() : 'U'}
            </div>
            <div className="truncate flex-1 min-w-0">
              <div className="text-xs font-bold truncate text-black leading-tight">
                {user?.first_name} {user?.last_name}
              </div>
              <div className="text-[10px] font-mono text-neutral-500 truncate" title={user?.email}>
                {user?.email}
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 pt-2 border-t border-neutral-200/80">
            <RoleBadge role={user?.role} />
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-mono uppercase font-semibold text-neutral-700 hover:text-black hover:bg-neutral-200/60 border border-neutral-300 rounded-none transition-colors focus:outline-none focus:ring-1 focus:ring-black shrink-0"
              title="Sign out of workspace"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-10 max-w-7xl mx-auto w-full overflow-x-hidden min-w-0">
        {children}
      </main>
    </div>
  );
};
