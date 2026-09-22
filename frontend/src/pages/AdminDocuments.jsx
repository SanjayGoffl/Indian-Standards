import React, { useEffect, useState } from 'react';
import * as api from '../services/api';
import './AdminDashboard.css';

export default function AdminDocuments({ onNavigateBack = () => {} }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notification, setNotification] = useState('');

  const loadDocuments = async () => {
    setLoading(true);
    setError('');

    try {
      const data = await api.getAdminDocuments();

      setDocuments(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(
        'Failed to load admin documents:',
        err
      );

      setError(
        err?.message ||
          'Unable to load documents. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const formatDate = (date) => {
    if (!date) return '—';

    return new Date(date).toLocaleString();
  };

  const formatFileType = (fileType, filename = '') => {
    if (fileType) {
      const normalized = String(fileType).trim().replace(/^\.+/, '');
      if (normalized) {
        return normalized.toUpperCase();
      }
    }

    const match = String(filename).match(/\.([^.]+)$/);
    return match ? match[1].toUpperCase() : '—';
  };

  const formatFileSize = (bytes) => {
    if (
      bytes === null ||
      bytes === undefined ||
      bytes === 0
    ) {
      return '0 B';
    }

    const units = [
      'B',
      'KB',
      'MB',
      'GB',
    ];

    const index = Math.floor(
      Math.log(bytes) / Math.log(1024)
    );

    const size = bytes / Math.pow(1024, index);

    return `${size.toFixed(index === 0 ? 0 : 2)} ${
      units[index] || 'B'
    }`;
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="admin-page-header">
          <div>
            <h1>Documents</h1>
            <p>
              Manage all documents uploaded to the system.
            </p>
          </div>
        </div>

        <div className="admin-loading">
          Loading documents...
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">

      {/* ==========================================================
          Header
          ========================================================== */}
      <div className="admin-page-header">
        <div>
          <h1>Documents</h1>

          <p>
            View and manage all documents in the system.
          </p>
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
            onClick={loadDocuments}
          >
            Refresh
          </button>
        </div>
      </div>

      {/* ==========================================================
          Notifications
          ========================================================== */}
      {notification && (
        <div className="admin-success">
          {notification}
        </div>
      )}

      {error && (
        <div className="admin-error">
          {error}
        </div>
      )}

      {/* ==========================================================
          Documents Table
          ========================================================== */}
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Type</th>
              <th>Size</th>
              <th>Status</th>
              <th>Owner</th>
              <th>Created</th>
            </tr>
          </thead>

          <tbody>
            {documents.length === 0 ? (
              <tr>
                <td
                  colSpan="6"
                  className="admin-empty"
                >
                  No documents found.
                </td>
              </tr>
            ) : (
              documents.map((document) => (
                <tr key={document.id}>

                  {/* Filename */}
                  <td>
                    <div>
                      {document.filename ||
                        document.original_filename ||
                        '—'}
                    </div>

                    {document.original_filename &&
                      document.filename !==
                        document.original_filename && (
                        <small>
                          {document.original_filename}
                        </small>
                      )}
                  </td>

                  {/* Type */}
                  <td>
                    {formatFileType(
                      document.file_type,
                      document.filename ||
                        document.original_filename ||
                        ''
                    )}
                  </td>

                  {/* Size */}
                  <td>
                    {formatFileSize(
                      document.file_size
                    )}
                  </td>

                  {/* Status */}
                  <td>
                    <span className="admin-status">
                      {document.status || '—'}
                    </span>
                  </td>

                  {/* Owner */}
                  <td>
                    {document.owner_email || '—'}
                  </td>

                  {/* Created */}
                  <td>
                    {formatDate(
                      document.created_at
                    )}
                  </td>


                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
}