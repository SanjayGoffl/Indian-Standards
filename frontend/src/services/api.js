/*
 * IS Procurement AI Service
 *
 * Centralized communication layer for the FastAPI backend.
 *
 * Responsibilities:
 * - Authentication
 * - Documents
 * - Conversations
 * - RAG queries
 * - Milestone 3 clarification/memory support
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '');

let useMock = false;

const mockDocuments = [];


/* ------------------------------------------------------------------ */
/* Mock mode                                                          */
/* ------------------------------------------------------------------ */

export const setMockMode = (enable) => {
  useMock = Boolean(enable);
};

export const getMockMode = () => useMock;


/* ------------------------------------------------------------------ */
/* Authentication helpers                                             */
/* ------------------------------------------------------------------ */

/*
 * Return the currently stored authentication token.
 *
 * localStorage is checked first because that is the normal
 * authenticated session storage used by QueryNest.
 */
export const getAuthToken = () => {
  return (
    localStorage.getItem('qn_auth_token') ||
    sessionStorage.getItem('qn_auth_token')
  );
};


/*
 * Build common authenticated headers.
 *
 * The backend expects:
 * Authorization: Bearer <token>
 */
export function getAuthHeaders(includeJsonContentType = false) {
  const headers = {};

  if (includeJsonContentType) {
    headers['Content-Type'] = 'application/json';
  }

  headers.Accept = 'application/json';
  headers['ngrok-skip-browser-warning'] = 'true';

  const token = getAuthToken();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  return headers;
};


/* ------------------------------------------------------------------ */
/* Response handling                                                   */
/* ------------------------------------------------------------------ */

async function parseResponse(response) {
  let data = {};

  try {
    data = await response.json();
  } catch {
    // Some responses may not contain JSON.
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;

    if (typeof data?.detail === 'string') {
      message = data.detail;
    } else if (typeof data?.message === 'string') {
      message = data.message;
    } else if (Array.isArray(data?.detail)) {
      message = data.detail
        .map((item) => item?.msg || 'Invalid request.')
        .join(', ');
    }

    /*
     * Hide provider-specific rate-limit information from the user.
     *
     * The original backend response is still preserved in error.data
     * for debugging, so this does not remove useful diagnostic data.
     */
    const normalizedMessage = String(message).toLowerCase();

    const isRateLimitError =
      response.status === 429 ||
      normalizedMessage.includes('rate limit reached') ||
      normalizedMessage.includes('rate limit') ||
      normalizedMessage.includes('too many requests') ||
      normalizedMessage.includes('error code: 429');

    if (isRateLimitError) {
      message =
        'The AI service is temporarily busy. Please try again in a few minutes.';
    }

    const error = new Error(message);

    error.status = response.status;
    error.data = data;

    throw error;
  }

  return data;
}


/*
 * Handle authentication failures consistently.
 */
export const isUnauthorizedError = (error) => {
  return error?.status === 401;
};


/* ------------------------------------------------------------------ */
/* Authentication APIs                                                 */
/* ------------------------------------------------------------------ */


/*
 * Log in an existing user.
 */
export async function loginUser(email, password) {
  const response = await fetch(
    `${API_BASE_URL}/auth/login`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
      body: JSON.stringify({
        email: email.trim(),
        password,
      }),
    },
  );

  return parseResponse(response);
}


/*
 * Register a new user.
 */
export async function registerUser(
  fullName,
  email,
  password,
) {
  const response = await fetch(
    `${API_BASE_URL}/auth/register`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        'ngrok-skip-browser-warning': 'true',
      },
      body: JSON.stringify({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
      }),
    },
  );

  return parseResponse(response);
}


/*
 * Validate the saved token and retrieve the current user.
 */
export async function getCurrentUser() {
  const token = getAuthToken();

  if (!token) {
    throw new Error('Authentication token not found.');
  }

  const response = await fetch(
    `${API_BASE_URL}/auth/me`,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
        'ngrok-skip-browser-warning': 'true',
      },
    },
  );

  return parseResponse(response);
}


/*
 * Log out the current user on the backend.
 *
 * JWT is currently stateless, so local session data is also
 * cleared by AuthContext after this request.
 */
export async function logoutUser(token = null) {
  const authToken = token || getAuthToken();

  if (!authToken) {
    return {
      success: true,
      message: 'Already signed out.',
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/auth/logout`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${authToken}`,
        'ngrok-skip-browser-warning': 'true',
      },
    },
  );

  return parseResponse(response);
}


/* ------------------------------------------------------------------ */
/* Document APIs                                                       */
/* ------------------------------------------------------------------ */


/*
 * Fetch indexed documents.
 */
export async function getDocuments() {
  if (useMock) {
    return [...mockDocuments];
  }

  const response = await fetch(
    `${API_BASE_URL}/documents`,
    {
      headers: getAuthHeaders(),
    },
  );

  const data = await parseResponse(response);

  return Array.isArray(data)
    ? data
    : (data.documents || []);
}


/*
 * Upload and index a document.
 */
export async function uploadDocument(
  file,
  onProgress = () => {},
) {
  if (useMock) {
    onProgress(100);

    const doc = {
      id: crypto.randomUUID(),
      name: file.name,
      size: file.size,
      status: 'indexed',
      stage: 'completed',
      progress: 100,
      message: 'Document processed successfully.',
      uploadedAt: new Date().toISOString(),
      chunksCount: 0,
      embeddingsCount: 0,
      vectorsStored: 0,
    };

    mockDocuments.unshift(doc);

    return {
      accepted: true,
      jobId: doc.id,
      documentId: doc.id,
      filename: file.name,
    };
  }

  const formData = new FormData();

  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.open(
      'POST',
      `${API_BASE_URL}/upload`,
    );

    const token = getAuthToken();

    if (token) {
      xhr.setRequestHeader(
        'Authorization',
        `Bearer ${token}`,
      );
    }

    xhr.setRequestHeader(
      'Accept',
      'application/json',
    );

    xhr.setRequestHeader(
      'ngrok-skip-browser-warning',
      'true',
);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round(
          (event.loaded / event.total) * 100,
        );

        onProgress(percent);
      }
    };

    xhr.onload = () => {
      let data = {};

      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        reject(
          new Error(
            'The backend returned an invalid response.',
          ),
        );

        return;
      }

      if (
        xhr.status >= 200 &&
        xhr.status < 300 &&
        data.status === 'accepted' &&
        data.jobId
      ) {
        onProgress(100);

        resolve({
          accepted: true,
          jobId: data.jobId,
          documentId: data.documentId,
          filename: data.filename || file.name,
          message: data.message,
        });

        return;
      }

      const message =
        data.message ||
        data.detail ||
        `Upload failed (${xhr.status})`;

      const error = new Error(message);
      error.status = xhr.status;
      error.data = data;

      reject(error);
    };

    xhr.onerror = () => {
      reject(
        new Error(
          'Could not connect to the FastAPI backend.',
        ),
      );
    };

    xhr.onabort = () => {
      reject(
        new Error(
          'The upload was cancelled.',
        ),
      );
    };

    xhr.send(formData);
  });
}


/*
 * Check document-processing status.
 */
export async function getUploadStatus(jobId) {
  if (useMock) {
    return {
      jobId,
      documentId: jobId,
      filename: 'Mock document',
      status: 'completed',
      stage: 'completed',
      progress: 100,
      message: 'Document processed successfully.',
      chunksCount: 0,
      embeddingsCount: 0,
      vectorsStored: 0,
      error: null,
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/upload/status/${encodeURIComponent(jobId)}`,
    {
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/*
 * Delete an indexed document.
 */
export async function deleteDocument(id) {
  if (useMock) {
    const index = mockDocuments.findIndex(
      (doc) => doc.id === id,
    );

    if (index >= 0) {
      mockDocuments.splice(index, 1);
    }

    return {
      status: 'success',
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(id)}`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/* ------------------------------------------------------------------ */
/* Conversation APIs                                                   */
/* ------------------------------------------------------------------ */


/*
 * Create a new persistent conversation.
 *
 * IMPORTANT:
 * The backend now generates the conversation UUID.
 * The frontend does not send a conversation_id.
 */
export async function createConversation() {
  if (useMock) {
    return {
      success: true,
      conversation_id: crypto.randomUUID(),
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations`,
    {
      method: 'POST',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/*
 * Fetch all conversations belonging to the logged-in user.
 */
export async function getConversations() {
  if (useMock) {
    return {
      success: true,
      count: 0,
      conversations: [],
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations`,
    {
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/*
 * Fetch one conversation with its messages.
 */
export async function getConversation(
  conversationId,
) {
  if (!conversationId) {
    throw new Error(
      'conversationId is required.',
    );
  }

  if (useMock) {
    return {
      success: true,
      conversation_id: conversationId,
      messages: [],
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations/${encodeURIComponent(
      conversationId,
    )}`,
    {
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/*
 * Fetch structured memory context for a conversation.
 */
export async function getConversationContext(
  conversationId,
) {
  if (!conversationId) {
    throw new Error(
      'conversationId is required.',
    );
  }

  if (useMock) {
    return {
      success: true,
      conversation_id: conversationId,
      context: [],
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations/${encodeURIComponent(
      conversationId,
    )}/context`,
    {
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/*
 * Delete a saved conversation.
 */
export async function deleteConversation(
  conversationId,
) {
  if (!conversationId) {
    throw new Error(
      'conversationId is required.',
    );
  }

  if (useMock) {
    return {
      success: true,
      conversation_id: conversationId,
      message: 'Conversation deleted successfully.',
    };
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations/${encodeURIComponent(
      conversationId,
    )}`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


/*
 * Save a conversation turn manually.
 */
export async function saveConversationTurn(
  conversationId,
  userQuery,
  aiResponse = null,
) {
  if (!conversationId) {
    throw new Error(
      'conversationId is required.',
    );
  }

  const response = await fetch(
    `${API_BASE_URL}/conversations/${encodeURIComponent(
      conversationId,
    )}/turns`,
    {
      method: 'POST',
      headers: getAuthHeaders(true),
      body: JSON.stringify({
        user_query: userQuery,
        ai_response: aiResponse,
      }),
    },
  );

  return parseResponse(response);
}


/* ------------------------------------------------------------------ */
/* RAG / Milestone 3 Query API                                        */
/* ------------------------------------------------------------------ */


/*
 * Send a text or voice-transcribed query.
 *
 * conversationId enables persistent memory.
 * clarification fields continue a clarification flow.
 */
export async function sendChatMessage(
  message,
  _history = [],
  conversationId = null,
  clarificationAnswer = null,
  clarificationQuestion = null,
  originalQuery = null,
) {
  if (!message || !message.trim()) {
    throw new Error('Message cannot be empty.');
  }

  if (useMock) {
    return {
      success: true,
      query: message,
      conversation_id: conversationId || null,
      query_understanding: null,
      route: 'retrieval',
      route_reason: 'Mock response',
      clarification_required: false,
      clarification_question: null,
      retrieval: {
        results: [],
        retrieval: {
          semantic_candidates: 0,
          exact_candidates: 0,
          merged_candidates: 0,
          returned_results: 0,
          completeness_query: false,
        },
      },
      response: {
        answer:
          'Mock mode is enabled. Connect the FastAPI backend to retrieve real document context.',
        sources: [],
        confidence: 0,
      },
    };
  }

  const requestBody = {
    query: message,
    k: 3,
  };

  if (conversationId) {
    requestBody.conversation_id = conversationId;
  }

  if (clarificationAnswer) {
    requestBody.clarification_answer =
      clarificationAnswer;
  }

  if (clarificationQuestion) {
    requestBody.clarification_question =
      clarificationQuestion;
  }

  if (originalQuery) {
    requestBody.original_query =
      originalQuery;
  }

  console.log("[CHAT] Request payload:", requestBody);

  const response = await fetch(
    `${API_BASE_URL}/query`,
    {
      method: 'POST',
      headers: getAuthHeaders(true),
      body: JSON.stringify(requestBody),
    },
  );

  const data = await parseResponse(response);

  if (!data.success) {
    throw new Error(
      data.detail ||
      data.message ||
      'Query failed.',
    );
  }

  return data;
}

/* ------------------------------------------------------------------ */
/* Admin APIs                                                         */
/* ------------------------------------------------------------------ */

export async function getAdminOverview() {
  const response = await fetch(
    `${API_BASE_URL}/admin/overview`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}

export async function getAdminUsers() {
  const response = await fetch(
    `${API_BASE_URL}/admin/users`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}

/* ------------------------------------------------------------------ */
/* Procurement & Indian Standards Recommendation APIs                */
/* ------------------------------------------------------------------ */

export async function analyzeProcurementSpecification(formData) {
  const response = await fetch(`${API_BASE_URL}/api/procurement/analyze`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });

  return parseResponse(response);
}

export async function getUserProcurementRequests() {
  const response = await fetch(`${API_BASE_URL}/api/procurement/requests`, {
    headers: getAuthHeaders(),
  });
  return parseResponse(response);
}

export async function getProcurementRequestDetail(requestId) {
  const response = await fetch(`${API_BASE_URL}/api/procurement/requests/${encodeURIComponent(requestId)}`, {
    headers: getAuthHeaders(),
  });
  return parseResponse(response);
}

export async function deleteProcurementRequest(requestId) {
  const response = await fetch(`${API_BASE_URL}/api/procurement/requests/${encodeURIComponent(requestId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return parseResponse(response);
}

export async function getIndianStandards(search = '', category = '') {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (category) params.append('category', category);

  const response = await fetch(`${API_BASE_URL}/api/standards?${params.toString()}`, {
    headers: getAuthHeaders(),
  });
  return parseResponse(response);
}

export async function getIndianStandardDetail(standardNumber) {
  const response = await fetch(`${API_BASE_URL}/api/standards/${encodeURIComponent(standardNumber)}`, {
    headers: getAuthHeaders(),
  });
  return parseResponse(response);
}

export async function getProcurementAnalyticsSummary() {
  const response = await fetch(`${API_BASE_URL}/api/analytics/summary`, {
    headers: getAuthHeaders(),
  });
  return parseResponse(response);
}


export async function getAdminUser(userId) {
  const response = await fetch(
    `${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}

export async function updateAdminUserStatus(userId, isActive) {
  const response = await fetch(
    `${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}/status`,
    {
      method: 'PATCH',
      headers: getAuthHeaders(true),
      body: JSON.stringify({ is_active: Boolean(isActive) }),
    },
  );

  return parseResponse(response);
}


export async function updateAdminUserRole(userId, role) {
  const response = await fetch(
    `${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}/role`,
    {
      method: 'PATCH',
      headers: getAuthHeaders(true),
      body: JSON.stringify({ role }),
    },
  );

  return parseResponse(response);
}

// Backward-compatible helper for callers that only need promotion.
export async function promoteAdminUser(userId) {
  return updateAdminUserRole(userId, 'Admin');
}

export async function demoteAdminUser(userId) {
  return updateAdminUserRole(userId, 'User');
}


export async function deleteAdminUser(userId) {
  const response = await fetch(
    `${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}


export async function getAdminDocuments() {
  const response = await fetch(
    `${API_BASE_URL}/admin/documents`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}

export async function deleteAdminDocument(documentId) {
  const response = await fetch(
    `${API_BASE_URL}/admin/documents/${encodeURIComponent(documentId)}`,
    {
      method: 'DELETE',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}

export async function getQueriesPerUser() {
  const response = await fetch(
    `${API_BASE_URL}/admin/analytics/queries-per-user`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}

export async function getFrequentQueries(limit = 10) {
  const response = await fetch(
    `${API_BASE_URL}/admin/analytics/frequent-queries?limit=${encodeURIComponent(limit)}`,
    {
      method: 'GET',
      headers: getAuthHeaders(),
    },
  );

  return parseResponse(response);
}
