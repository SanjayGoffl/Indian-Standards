import React, { useEffect, useState } from 'react';
import * as api from '../services/api';

import './AdminDashboard.css';

export default function AdminDashboard({ onNavigate = () => {} }) {

  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    try {
      setLoading(true);
      setError('');

      const data = await api.getAdminOverview();
      setOverview(data);
    } catch (err) {
      console.error('Failed to load admin overview:', err);
      setError(
        err.message || 'Failed to load admin overview.'
      );
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="admin-loading">
          Loading admin overview...
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">

      {/* =========================
          ADMIN NAVIGATION
      ========================= */}

      <div className="admin-navigation">

        <button
          type="button"
          className="admin-nav-btn active"
          onClick={() => onNavigate('admin')}
        >
          Overview
        </button>

        <button
          type="button"
          className="admin-nav-btn"
          onClick={() => onNavigate('admin-users')}
        >
          Users
        </button>

        <button
          type="button"
          className="admin-nav-btn"
          onClick={() => onNavigate('admin-documents')}
        >
          Documents
        </button>

        <button
          type="button"
          className="admin-nav-btn"
          onClick={() => onNavigate('admin-analytics')}
        >
          Analytics
        </button>

      </div>

      {/* =========================
          PAGE HEADER
      ========================= */}

      <div className="admin-page-header">
        <div>
          <h1>Admin Dashboard</h1>

          <p>
            Monitor users, documents, queries, and
            knowledge gaps.
          </p>
        </div>

        <button
          type="button"
          className="admin-refresh-btn"
          onClick={loadOverview}
        >
          Refresh
        </button>
      </div>

      {/* =========================
          ERROR
      ========================= */}

      {error && (
        <div className="admin-error">
          {error}
        </div>
      )}

      {/* =========================
          OVERVIEW CARDS
      ========================= */}

      {overview && (
        <div className="admin-stats-grid">

          <div className="admin-stat-card">
            <h3>Total Users</h3>
            <p>
              {overview.total_users ?? 0}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Total Documents</h3>
            <p>
              {overview.total_documents ?? 0}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Total Queries</h3>
            <p>
              {overview.total_queries ?? 0}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Answered Queries</h3>
            <p>
              {overview.answered_queries ?? 0}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Unanswered Queries</h3>
            <p>
              {overview.unanswered_queries ?? 0}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Average Confidence</h3>
            <p>
              {overview.average_confidence != null
                ? Number(
                    overview.average_confidence
                  ).toFixed(2)
                : '0.00'}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Average Response Time</h3>
            <p>
              {overview.average_response_time != null
                ? `${Number(
                    overview.average_response_time
                  ).toFixed(2)}s`
                : '0.00s'}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Total Knowledge Gaps</h3>
            <p>
              {overview.total_knowledge_gaps ?? 0}
            </p>
          </div>

          <div className="admin-stat-card">
            <h3>Most Common Gap Reason</h3>
            <p className="admin-stat-text">
              {overview.most_common_gap_reason ||
                'None'}
            </p>
          </div>

        </div>
      )}

    </div>
  );
}