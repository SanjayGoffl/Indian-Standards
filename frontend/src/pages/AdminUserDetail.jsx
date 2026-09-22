import React, { useEffect, useState } from 'react';
import * as api from '../services/api';
import './AdminDashboard.css';

const actionButtonBaseStyle = {
  border: '1px solid rgba(255, 255, 255, 0.12)',
  borderRadius: '10px',
  padding: '10px 14px',
  fontWeight: 700,
  cursor: 'pointer',
};

export default function AdminUserDetail({ userId, onNavigateBack = () => {} }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');

  useEffect(() => {
    loadUser();
  }, [userId]);

  const loadUser = async () => {
    try {
      setLoading(true);
      setError('');
      setActionError('');
      const data = await api.getAdminUser(userId);
      setUser(data);
    } catch (err) {
      setError(err.message || 'Failed to load user details.');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!user) return;
    const nextActiveState = !user.is_active;

    if (!window.confirm(
      nextActiveState
        ? `Unblock ${user.full_name || user.email}?`
        : `Block ${user.full_name || user.email}? They will no longer be able to log in or use the application.`,
    )) return;

    try {
      setActionLoading(true);
      setActionError('');
      const updatedUser = await api.updateAdminUserStatus(user.id, nextActiveState);
      setUser(updatedUser);
    } catch (err) {
      setActionError(err.message || 'Failed to update the user status.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRoleChange = async () => {
    if (!user) return;

    const nextRole = user.role === 'Admin' ? 'User' : 'Admin';
    const actionText = nextRole === 'Admin' ? 'promote' : 'demote';
    const confirmation = nextRole === 'Admin'
      ? `Promote ${user.full_name || user.email} to Admin? This grants access to the admin dashboard and account-management tools.`
      : `Demote ${user.full_name || user.email} to User? They will no longer have access to the admin dashboard or admin-only tools.`;

    if (!window.confirm(confirmation)) return;

    try {
      setActionLoading(true);
      setActionError('');
      const updatedUser = await api.updateAdminUserRole(user.id, nextRole);
      setUser(updatedUser);
    } catch (err) {
      setActionError(err.message || `Failed to ${actionText} the user.`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!user) return;

    if (!window.confirm(
      `Permanently remove ${user.full_name || user.email}? This deletes the account and its associated application data. This action cannot be undone.`,
    )) return;

    try {
      setActionLoading(true);
      setActionError('');
      await api.deleteAdminUser(user.id);
      onNavigateBack();
    } catch (err) {
      setActionError(err.message || 'Failed to remove the user account.');
      setActionLoading(false);
    }
  };

  if (loading) {
    return <div className="admin-page"><div className="admin-loading">Loading user details...</div></div>;
  }

  if (error) {
    return (
      <div className="admin-page">
        <button type="button" className="admin-back-btn" onClick={() => onNavigateBack()}>
          ← Back to Users
        </button>
        <div className="admin-error">{error}</div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="admin-page">
        <button type="button" className="admin-back-btn" onClick={() => onNavigateBack()}>
          ← Back to Users
        </button>
        <div className="admin-empty">User not found.</div>
      </div>
    );
  }

  const isAdmin = user.role === 'Admin';
  const isActive = user.is_active !== false;

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>User Details</h1>
        <button type="button" className="admin-back-btn" onClick={() => onNavigateBack()} disabled={actionLoading}>
          ← Back to Users
        </button>
      </div>

      <div className="admin-user-info">
        <div className="admin-info-card">
          <p><strong>Name:</strong> {user.full_name || 'N/A'}</p>
          <p><strong>Email:</strong> {user.email || 'N/A'}</p>
          <p><strong>Role:</strong> {user.role || 'N/A'}</p>
        </div>

        <div className="admin-info-card">
          <p><strong>Status:</strong> {isActive ? 'Active' : 'Blocked'}</p>
          <p><strong>Documents:</strong> {user.document_count ?? 0}</p>
          <p><strong>Queries:</strong> {user.query_count ?? 0}</p>
        </div>

        <div className="admin-info-card">
          <p>
            <strong>Created:</strong>{' '}
            {user.created_at ? new Date(user.created_at).toLocaleString() : 'N/A'}
          </p>
        </div>
      </div>

      <section className="admin-section">
        <div className="admin-section-header">
          <div>
            <h2>Account Actions</h2>
            <p>Manage this account without changing its stored data unless the account is permanently removed.</p>
          </div>
        </div>

        {actionError && (
          <div className="admin-error" style={{ marginBottom: '16px' }}>{actionError}</div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          <button
            type="button"
            onClick={handleToggleStatus}
            disabled={actionLoading}
            style={{
              ...actionButtonBaseStyle,
              background: isActive ? 'rgba(245, 158, 11, 0.14)' : 'rgba(34, 197, 94, 0.14)',
              color: isActive ? '#fbbf24' : '#86efac',
            }}
          >
            {actionLoading ? 'Processing...' : isActive ? 'Block User' : 'Unblock User'}
          </button>

          <button
            type="button"
            onClick={handleRoleChange}
            disabled={actionLoading}
            style={{
              ...actionButtonBaseStyle,
              background: isAdmin ? 'rgba(148, 163, 184, 0.14)' : 'rgba(59, 130, 246, 0.14)',
              color: isAdmin ? '#cbd5e1' : '#93c5fd',
            }}
          >
            {actionLoading ? 'Processing...' : isAdmin ? 'Make User' : 'Make Admin'}
          </button>

          <button
            type="button"
            onClick={handleDelete}
            disabled={actionLoading}
            style={{ ...actionButtonBaseStyle, background: 'rgba(239, 68, 68, 0.14)', color: '#fca5a5' }}
          >
            {actionLoading ? 'Processing...' : 'Remove Account'}
          </button>
        </div>
      </section>

      <section className="admin-section">
        <div className="admin-section-header"><h2>User Documents</h2></div>

        {user.documents && user.documents.length > 0 ? (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr><th>Filename</th><th>Type</th><th>Status</th><th>Created</th></tr>
              </thead>
              <tbody>
                {user.documents.map((document) => (
                  <tr key={document.id}>
                    <td>{document.filename || 'N/A'}</td>
                    <td>{document.file_type || 'N/A'}</td>
                    <td>{document.status || 'N/A'}</td>
                    <td>{document.created_at ? new Date(document.created_at).toLocaleString() : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="admin-empty">This user has no documents.</div>
        )}
      </section>
    </div>
  );
}
