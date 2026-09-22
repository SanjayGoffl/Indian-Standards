import React, { useEffect, useState } from 'react';
import * as api from '../services/api';
import './AdminDashboard.css';

export default function AdminAnalytics({ onNavigateBack = () => {} }) {
  const [queriesPerUser, setQueriesPerUser] = useState([]);
  const [frequentQueries, setFrequentQueries] = useState([]);

  const [limit, setLimit] = useState(10);

  const [loading, setLoading] = useState(true);
  const [loadingFrequent, setLoadingFrequent] = useState(false);

  const [error, setError] = useState('');

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError('');

      const [queriesData, frequentData] = await Promise.all([
        api.getQueriesPerUser(),
        api.getFrequentQueries(10),
      ]);

      setQueriesPerUser(Array.isArray(queriesData) ? queriesData : []);
      setFrequentQueries(Array.isArray(frequentData) ? frequentData : []);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError(err.message || 'Failed to load analytics.');
    } finally {
      setLoading(false);
    }
  };

  const loadFrequentQueries = async () => {
    try {
      setLoadingFrequent(true);
      setError('');

      const data = await api.getFrequentQueries(Number(limit));

      setFrequentQueries(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load frequent queries:', err);
      setError(err.message || 'Failed to load frequent queries.');
    } finally {
      setLoadingFrequent(false);
    }
  };

  const maxQueryCount =
    queriesPerUser.length > 0
      ? Math.max(...queriesPerUser.map((item) => item.query_count || 0))
      : 0;

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-loading">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>Analytics</h1>
          <p>View query usage and frequently asked questions.</p>
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
            onClick={loadAnalytics}
          >
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="admin-error">{error}</div>}

      {/* Queries Per User */}
      <section className="admin-section">
        <div className="admin-section-header">
          <div>
            <h2>Queries Per User</h2>
            <p>Number of queries submitted by each user.</p>
          </div>
        </div>

        {queriesPerUser.length === 0 ? (
          <div className="admin-empty">No query data available.</div>
        ) : (
          <div className="admin-chart">
            {queriesPerUser.map((item) => {
              const count = item.query_count || 0;

              const width =
                maxQueryCount > 0
                  ? `${(count / maxQueryCount) * 100}%`
                  : '0%';

              return (
                <div className="admin-chart-row" key={item.user_id}>
                  <div className="admin-chart-label" title={item.email}>
                    {item.email}
                  </div>

                  <div className="admin-chart-bar-container">
                    <div
                      className="admin-chart-bar"
                      style={{ width }}
                    >
                      {count}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Frequent Queries */}
      <section className="admin-section">
        <div className="admin-section-header">
          <div>
            <h2>Frequent Queries</h2>
            <p>Most commonly asked queries across the platform.</p>
          </div>

          <div className="admin-limit-control">
            <label htmlFor="query-limit">Limit:</label>

            <input
              id="query-limit"
              type="number"
              min="1"
              max="100"
              value={limit}
              onChange={(event) => setLimit(event.target.value)}
            />

            <button
              type="button"
              className="admin-refresh-btn"
              onClick={loadFrequentQueries}
              disabled={loadingFrequent}
            >
              {loadingFrequent ? 'Loading...' : 'Apply'}
            </button>
          </div>
        </div>

        {frequentQueries.length === 0 ? (
          <div className="admin-empty">No frequent queries available.</div>
        ) : (
          <div className="admin-table-wrapper">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Query</th>
                  <th>Occurrences</th>
                </tr>
              </thead>

              <tbody>
                {frequentQueries.map((item, index) => (
                  <tr key={`${item.query_text}-${index}`}>
                    <td>{index + 1}</td>
                    <td>{item.query_text}</td>
                    <td>{item.occurrence_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}