import React, { useState, useRef, useEffect } from 'react';
import * as api from '../services/api';

export default function FileUploader({
  onUploadComplete,
}) {
  const [dragActive, setDragActive] = useState(false);
  const [uploadState, setUploadState] = useState('idle');
  const [fileName, setFileName] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const fileInputRef = useRef(null);
  const pollingRef = useRef(null);

  const allowedExtensions = [
    'pdf',
    'txt',
    'docx',
    'csv',
    'jpg',
    'jpeg',
    'png',

  ];


  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, []);


  const resetFileInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };


  const resetUploader = () => {
    setUploadState('idle');
    setFileName('');
    setUploadProgress(0);
    setProcessingProgress(0);
    setProcessingStatus(null);
    setErrorMessage('');

    resetFileInput();
  };


  const updateProcessingState = (status) => {
    setProcessingStatus(status);
    setProcessingProgress(
      status.progress || 0
    );

    if (status.status === 'completed') {
      setUploadState('success');
    }

    if (status.status === 'failed') {
      setUploadState('error');

      setErrorMessage(
        status.error ||
        status.message ||
        'Document processing failed.'
      );
    }
  };


  const pollUploadStatus = (jobId) => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }

    const checkStatus = async () => {
      try {
        const status =
          await api.getUploadStatus(jobId);

        updateProcessingState(status);

        if (
          status.status === 'completed' ||
          status.status === 'failed'
        ) {
          pollingRef.current = null;

          if (
            status.status === 'completed'
          ) {
            if (onUploadComplete) {
              try {
                await onUploadComplete();
              } catch (refreshError) {
                console.error(
                  'Document repository refresh failed:',
                  refreshError
                );
              }
            }
          }

          return;
        }

        pollingRef.current = setTimeout(
          checkStatus,
          1500
        );
      } catch (error) {
        console.error(
          'Could not retrieve upload status:',
          error
        );

        pollingRef.current = setTimeout(
          checkStatus,
          2000
        );
      }
    };

    checkStatus();
  };


  const validateAndUpload = async (file) => {
    if (!file) {
      return;
    }

    if (uploadState === 'uploading') {
      return;
    }

    const fileExtension = file.name
      .split('.')
      .pop()
      .toLowerCase();

    if (
      !allowedExtensions.includes(
        fileExtension
      )
    ) {
      setErrorMessage(
        'Unsupported file format. Please upload PDF, TXT, DOCX, CSV, JPG, JPEG, or PNG.'
      );

      setUploadState('error');

      return;
    }

    if (
      file.size >
      10 * 1024 * 1024
    ) {
      setErrorMessage(
        'File size exceeds the 10MB limit.'
      );

      setUploadState('error');

      return;
    }

    setFileName(file.name);
    setUploadState('uploading');
    setUploadProgress(0);
    setProcessingProgress(0);
    setProcessingStatus(null);
    setErrorMessage('');

    try {
      const uploadResult =
        await api.uploadDocument(
          file,
          (percent) => {
            setUploadProgress(percent);
          }
        );

      setUploadProgress(100);

      setProcessingStatus({
        status: 'processing',
        stage: 'uploaded',
        progress: 10,
        message:
          'File uploaded successfully.',
        chunksCount: 0,
        embeddingsCount: 0,
        vectorsStored: 0,
      });

      setProcessingProgress(10);

      pollUploadStatus(
        uploadResult.jobId
      );
    } catch (error) {
      console.error(
        'Document upload failed:',
        error
      );

      setErrorMessage(
        error.message ||
        'An error occurred during upload.'
      );

      setUploadState('error');
    }
  };


  const handleDrag = (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (
      event.type === 'dragenter' ||
      event.type === 'dragover'
    ) {
      setDragActive(true);
    } else if (
      event.type === 'dragleave'
    ) {
      setDragActive(false);
    }
  };


  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();

    setDragActive(false);

    if (
      uploadState === 'uploading'
    ) {
      return;
    }

    const files =
      event.dataTransfer.files;

    if (
      files &&
      files.length > 0
    ) {
      validateAndUpload(files[0]);
    }
  };


  const handleFileChange = (event) => {
    const files = event.target.files;

    if (
      files &&
      files.length > 0
    ) {
      validateAndUpload(files[0]);
    }
  };


  const onButtonClick = () => {
    if (
      uploadState !== 'uploading'
    ) {
      fileInputRef.current?.click();
    }
  };


  const getStageState = (stage) => {
    if (
      !processingStatus
    ) {
      return 'pending';
    }

    const currentStage =
      processingStatus.stage;

    const stageOrder = [
      'uploaded',
      'extracting',
      'chunking',
      'embedding',
      'storing',
      'completed',
    ];

    const currentIndex =
      stageOrder.indexOf(
        currentStage
      );

    const stageIndex =
      stageOrder.indexOf(stage);

    if (
      processingStatus.status ===
      'failed'
    ) {
      if (
        currentStage === stage
      ) {
        return 'error';
      }

      return stageIndex <
        currentIndex
        ? 'completed'
        : 'pending';
    }

    if (
      stageIndex < currentIndex
    ) {
      return 'completed';
    }

    if (
      stageIndex === currentIndex
    ) {
      if (
        currentStage ===
        'completed'
      ) {
        return 'completed';
      }

      return 'active';
    }

    return 'pending';
  };


  const getStageIcon = (state) => {
    if (state === 'completed') {
      return (
        <span
          style={{
            color:
              'var(--accent-emerald)',
            fontWeight: '700',
            fontSize: '18px',
          }}
        >
          ✓
        </span>
      );
    }

    if (state === 'error') {
      return (
        <span
          style={{
            color:
              'var(--accent-rose)',
            fontWeight: '700',
            fontSize: '18px',
          }}
        >
          ×
        </span>
      );
    }

    if (state === 'active') {
      return (
        <span
          style={{
            color:
              'var(--accent-blue)',
            fontWeight: '700',
            fontSize: '16px',
          }}
        >
          ⟳
        </span>
      );
    }

    return (
      <span
        style={{
          color:
            'var(--text-muted)',
          fontSize: '16px',
        }}
      >
        ○
      </span>
    );
  };


  const getStageLabel = (stage) => {
    const labels = {
      uploaded:
        'File uploaded',
      extracting:
        'Extracting text',
      chunking:
        'Creating document chunks',
      embedding:
        'Generating embeddings',
      storing:
        'Storing vectors in ChromaDB',
      completed:
        'Document processed successfully',
    };

    return labels[stage];
  };

  const getStageDetails = (stage) => {
    return '';
  };
  
  const renderProcessingStage = (
    stage
  ) => {
    const state =
      getStageState(stage);

    return (
      <div
        key={stage}
        style={{
          display: 'flex',
          alignItems:
            'flex-start',
          gap: '12px',
          padding:
            '9px 0',
          opacity:
            state === 'pending'
              ? 0.5
              : 1,
        }}
      >
        <div
          style={{
            width: '24px',
            height: '24px',
            display: 'flex',
            alignItems:
              'center',
            justifyContent:
              'center',
            flexShrink: 0,
          }}
        >
          {getStageIcon(
            state
          )}
        </div>

        <div
          style={{
            flex: 1,
            minWidth: 0,
          }}
        >
          <div
            style={{
              fontSize:
                '0.9rem',
              fontWeight:
                state === 'active'
                  ? '600'
                  : '500',
              color:
                state === 'error'
                  ? 'var(--accent-rose)'
                  : 'var(--text-primary)',
            }}
          >
            {getStageLabel(
              stage
            )}
          </div>

          {getStageDetails(
            stage
          ) && (
            <div
              style={{
                fontSize:
                  '0.75rem',
                color:
                  'var(--text-secondary)',
                marginTop:
                  '2px',
              }}
            >
              {getStageDetails(
                stage
              )}
            </div>
          )}
        </div>
      </div>
    );
  };


  const processingStages = [
    'uploaded',
    'extracting',
    'chunking',
    'embedding',
    'storing',
    'completed',
  ];


  return (
    <div
      className="glass-panel"
      style={{
        padding: '32px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        style={{
          display: 'none',
        }}
        multiple={false}
        onChange={
          handleFileChange
        }
        accept=".pdf,.txt,.docx,.csv,.jpg,.jpeg,.png"
      />

      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={
          uploadState !==
          'uploading'
            ? onButtonClick
            : null
        }
        style={{
          width: '100%',
          minHeight:
            uploadState ===
            'uploading'
              ? '390px'
              : '220px',
          border:
            dragActive
              ? '2px dashed var(--accent-purple)'
              : '2px dashed var(--border-color)',
          borderRadius: '12px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent:
            'center',
          padding: '24px',
          backgroundColor:
            dragActive
              ? 'hsla(263, 85%, 65%, 0.05)'
              : 'transparent',
          cursor:
            uploadState ===
            'uploading'
              ? 'not-allowed'
              : 'pointer',
          transition:
            'all 0.3s ease',
          outline: 'none',
        }}
      >
        {uploadState ===
          'idle' && (
          <div
            style={{
              textAlign:
                'center',
              display:
                'flex',
              flexDirection:
                'column',
              alignItems:
                'center',
            }}
          >
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius:
                  '50%',
                background:
                  'hsla(240, 20%, 30%, 0.2)',
                display:
                  'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                marginBottom:
                  '16px',
                color:
                  'var(--text-secondary)',
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line
                  x1="12"
                  y1="18"
                  x2="12"
                  y2="12"
                />
                <polyline points="9 15 12 12 15 15" />
              </svg>
            </div>

            <h3
              style={{
                fontSize:
                  '1.2rem',
                marginBottom:
                  '8px',
              }}
            >
              Drag & drop
              files here
            </h3>

            <p
              style={{
                fontSize:
                  '0.9rem',
                color:
                  'var(--text-secondary)',
                marginBottom:
                  '16px',
              }}
            >
              or{' '}
              <span
                style={{
                  color:
                    'var(--accent-purple)',
                  fontWeight:
                    '600',
                }}
              >
                browse your
                local files
              </span>
            </p>

            <span className="badge badge-blue">
              PDF, TXT, DOCX, CSV, Images
              (Max 10MB)
            </span>
          </div>
        )}

        {uploadState ===
          'uploading' && (
          <div
            style={{
              width: '100%',
              maxWidth:
                '520px',
            }}
          >
            <div
              style={{
                textAlign:
                  'center',
                marginBottom:
                  '20px',
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius:
                    '50%',
                  background:
                    'hsla(210, 100%, 60%, 0.1)',
                  color:
                    'var(--accent-blue)',
                  display:
                    'flex',
                  alignItems:
                    'center',
                  justifyContent:
                    'center',
                  margin:
                    '0 auto 12px',
                }}
              >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{
                    animation:
                      'spin 1.5s linear infinite',
                  }}
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    strokeDasharray="30 10"
                  />
                </svg>
              </div>

              <h4
                style={{
                  fontSize:
                    '1.1rem',
                  marginBottom:
                    '4px',
                }}
              >
                Processing
                knowledge file
              </h4>

              <p
                style={{
                  fontSize:
                    '0.85rem',
                  color:
                    'var(--text-muted)',
                  marginBottom:
                    '12px',
                  overflow:
                    'hidden',
                  textOverflow:
                    'ellipsis',
                  whiteSpace:
                    'nowrap',
                }}
              >
                {fileName}
              </p>

              <div
                style={{
                  width: '100%',
                  height: '6px',
                  background:
                    'var(--border-color)',
                  borderRadius:
                    '99px',
                  overflow:
                    'hidden',
                  marginBottom:
                    '6px',
                }}
              >
                <div
                  style={{
                    width: `${Math.max(
                      uploadProgress,
                      processingProgress
                    )}%`,
                    height: '100%',
                    background:
                      'linear-gradient(to right, var(--accent-blue), var(--accent-purple))',
                    borderRadius:
                      '99px',
                    transition:
                      'width 0.3s ease',
                  }}
                />
              </div>

              <span
                style={{
                  fontSize:
                    '0.75rem',
                  color:
                    'var(--text-secondary)',
                }}
              >
                {processingProgress > 0
                  ? `${processingProgress}% processed`
                  : `${uploadProgress}% uploaded`}
              </span>
            </div>

            <div
              style={{
                background:
                  'hsla(240, 20%, 20%, 0.25)',
                border:
                  '1px solid var(--border-color)',
                borderRadius:
                  '12px',
                padding:
                  '14px 18px',
              }}
            >
              {processingStages.map(
                renderProcessingStage
              )}
            </div>

            {processingStatus?.message && (
              <p
                style={{
                  textAlign:
                    'center',
                  fontSize:
                    '0.78rem',
                  color:
                    'var(--text-secondary)',
                  marginTop:
                    '12px',
                }}
              >
                {processingStatus.message}
              </p>
            )}
          </div>
        )}

        {uploadState ===
          'success' && (
          <div
            style={{
              textAlign:
                'center',
              width: '100%',
              maxWidth:
                '520px',
            }}
          >
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius:
                  '50%',
                background:
                  'hsla(142, 70%, 45%, 0.15)',
                color:
                  'var(--accent-emerald)',
                display:
                  'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                margin:
                  '0 auto 16px',
                boxShadow:
                  '0 0 16px hsla(142, 70%, 45%, 0.2)',
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>

            <h3
              style={{
                fontSize:
                  '1.25rem',
                marginBottom:
                  '6px',
                color:
                  'var(--accent-emerald)',
              }}
            >
              Document
              Processed
              Successfully
            </h3>

            <p
              style={{
                fontSize:
                  '0.9rem',
                color:
                  'var(--text-secondary)',
                marginBottom:
                  '16px',
              }}
            >
              {fileName}
            </p>

            <button
              type="button"
              className="btn btn-secondary"
              style={{
                marginTop:
                  '18px',
                fontSize:
                  '0.8rem',
                padding:
                  '7px 14px',
              }}
              onClick={(event) => {
                event.stopPropagation();
                resetUploader();
              }}
            >
              Upload Another
            </button>
          </div>
        )}

        {uploadState ===
          'error' && (
          <div
            style={{
              textAlign:
                'center',
            }}
          >
            <div
              style={{
                width: '60px',
                height: '60px',
                borderRadius:
                  '50%',
                background:
                  'hsla(350, 80%, 60%, 0.15)',
                color:
                  'var(--accent-rose)',
                display:
                  'flex',
                alignItems:
                  'center',
                justifyContent:
                  'center',
                margin:
                  '0 auto 16px',
                boxShadow:
                  '0 0 16px hsla(350, 80%, 60%, 0.2)',
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line
                  x1="18"
                  y1="6"
                  x2="6"
                  y2="18"
                />
                <line
                  x1="6"
                  y1="6"
                  x2="18"
                  y2="18"
                />
              </svg>
            </div>

            <h3
              style={{
                fontSize:
                  '1.25rem',
                marginBottom:
                  '6px',
                color:
                  'var(--accent-rose)',
              }}
            >
              Upload Failed
            </h3>

            <p
              style={{
                fontSize:
                  '0.9rem',
                color:
                  'var(--text-secondary)',
                marginBottom:
                  '16px',
              }}
            >
              {errorMessage}
            </p>

            <button
              type="button"
              className="btn btn-secondary"
              style={{
                fontSize:
                  '0.8rem',
                padding:
                  '6px 12px',
              }}
              onClick={(event) => {
                event.stopPropagation();
                resetUploader();
              }}
            >
              Try Again
            </button>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }

          100% {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}