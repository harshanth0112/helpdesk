import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { RoleBadge } from '../components/Badges';
import { User, Lock } from 'lucide-react';

export const ProfilePage = () => {
  const { user } = useAuth();
  const { success, error } = useToast();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [updating, setUpdating] = useState(false);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      error('New passwords do not match.');
      return;
    }
    setUpdating(true);
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      success('Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      error(err.response?.data?.detail || 'Failed to change password.');
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div className="border-b border-neutral-200 pb-5">
        <span className="text-xs font-mono uppercase tracking-widest text-neutral-500">Account Credentials</span>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight uppercase mt-1">Profile & Security</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* User Profile Overview */}
        <div className="border border-neutral-200 p-6 bg-white space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-neutral-200">
            <User className="w-5 h-5 text-neutral-700" />
            <h2 className="text-xs font-mono uppercase tracking-widest font-bold">User Identity</h2>
          </div>

          <div className="space-y-3 text-xs font-mono">
            <div>
              <span className="text-neutral-500 block uppercase text-[10px]">Full Name</span>
              <span className="text-sm font-bold text-black">{user?.first_name} {user?.last_name}</span>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase text-[10px]">Email Address</span>
              <span className="text-neutral-800">{user?.email}</span>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase text-[10px]">Department</span>
              <span className="text-neutral-800">{user?.department || 'General IT'}</span>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase text-[10px]">Authorization Role</span>
              <div className="mt-1">
                <RoleBadge role={user?.role} />
              </div>
            </div>
            <div>
              <span className="text-neutral-500 block uppercase text-[10px]">Member Since</span>
              <span className="text-neutral-600">{new Date(user?.created_at).toLocaleDateString()}</span>
            </div>
          </div>
        </div>

        {/* Change Password Form */}
        <div className="border border-neutral-200 p-6 bg-white space-y-4">
          <div className="flex items-center gap-3 pb-3 border-b border-neutral-200">
            <Lock className="w-5 h-5 text-neutral-700" />
            <h2 className="text-xs font-mono uppercase tracking-widest font-bold">Change Password</h2>
          </div>

          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
                Current Password
              </label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full p-2.5 border border-neutral-300 text-xs rounded-none"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
                New Password (Min 8 chars, 1 letter, 1 number)
              </label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full p-2.5 border border-neutral-300 text-xs rounded-none"
              />
            </div>

            <div>
              <label className="block text-xs font-mono uppercase text-neutral-700 mb-1">
                Confirm New Password
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full p-2.5 border border-neutral-300 text-xs rounded-none"
              />
            </div>

            <button
              type="submit"
              disabled={updating}
              className="w-full py-2.5 bg-black text-white hover:bg-neutral-800 text-xs font-mono uppercase tracking-wider font-semibold transition-colors disabled:opacity-50"
            >
              {updating ? 'Updating...' : 'Save Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
