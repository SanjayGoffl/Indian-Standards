import React, { useEffect, useState } from 'react';
import * as api from '../services/api';
import './AdminDashboard.css';

export default function AdminUsers({ onNavigateBack = () => {}, onNavigateToUser = () => {} }) {

  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await api.getAdminUsers();

      setUsers(Array.isArray(data?.users) ? data.users : []);
      setTotalUsers(data?.total_users ?? 0);
    } catch (err) {
      console.error('Failed to load admin users:', err);
      setError(err.message || 'Failed to load users.');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (date) => {
    if (!date) return '-';

    return new Date(date).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading">
          Loading users...
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Users</h1>
          <p>View all registered users and their activity.</p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="admin-back-btn"
            onClick={onNavigateBack}
          >
            ← Overview
          </button>
          <button
            type="button"
            className="admin-refresh-btn"
            onClick={loadUsers}
          >
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="admin-error">
          {error}
        </div>
      )}

      <p className="admin-summary-text">
        Total Users: <strong>{totalUsers}</strong>
      </p>

      {users.length === 0 ? (
        <div className="admin-empty">
          No users available.
        </div>
      ) : (
        <div className="admin-table-wrapper">
          <table className="admin-table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Documents</th>
                <th>Queries</th>
                <th>Created</th>
              </tr>
            </thead>

            <tbody>
              {users.map((item) => (
                <tr
                  key={item.id}
                  className="admin-clickable-row"
                  onClick={() =>
                    onNavigateToUser(item.id)
                  }
                >
                  <td>
                    {item.full_name || '-'}
                  </td>

                  <td>
                    {item.email || '-'}
                  </td>

                  <td>
                    <span className="admin-role">
                      {item.role || '-'}
                    </span>
                  </td>

                  <td>
                    {item.document_count ?? 0}
                  </td>

                  <td>
                    {item.query_count ?? 0}
                  </td>

                  <td>
                    {formatDate(item.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}