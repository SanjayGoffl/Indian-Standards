import React, { useState } from 'react';
import robotLogo from '../assets/hero.jpg';
import './AuthPage.css';

import { useAuth } from '../context/Authcontext';


export default function AuthPage({
  onLoginSuccess,
  onNavigateToWorkspace,
}) {
  const {
    user,
    loading: authLoading,
    login,
    register,
    logout,
  } = useAuth();


  const [activeTab, setActiveTab] = useState('login');

  /* Login form state */
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  /* Signup form state */
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirmPassword, setSignupConfirmPassword] = useState('');
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [agreeTerms, setAgreeTerms] = useState(false);

  /* UI state */
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState(null);
  const [showForgotModal, setShowForgotModal] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');


  /* ---------------------------------------------------------------- */
  /* Toast                                                             */
  /* ---------------------------------------------------------------- */

  const triggerToast = (type, message) => {
    setToast({
      type,
      message,
    });

    setTimeout(() => {
      setToast(null);
    }, 4500);
  };


  /* ---------------------------------------------------------------- */
  /* Password strength                                                 */
  /* ---------------------------------------------------------------- */

  const getPasswordStrength = (pass) => {
    if (!pass) {
      return {
        score: 0,
        label: '',
        color: 'transparent',
      };
    }

    let score = 0;

    if (pass.length >= 6) {
      score += 1;
    }

    if (pass.length >= 10) {
      score += 1;
    }

    if (/[A-Z]/.test(pass)) {
      score += 1;
    }

    if (/[0-9]/.test(pass)) {
      score += 1;
    }

    if (/[^A-Za-z0-9]/.test(pass)) {
      score += 1;
    }

    if (score <= 2) {
      return {
        score: 33,
        label: 'Weak',
        color: '#ff4d4d',
      };
    }

    if (score <= 4) {
      return {
        score: 66,
        label: 'Medium',
        color: '#ffb84d',
      };
    }

    return {
      score: 100,
      label: 'Strong',
      color: '#00e699',
    };
  };


  const strength =
    getPasswordStrength(signupPassword);


  /* ---------------------------------------------------------------- */
  /* Backend login                                                     */
  /* ---------------------------------------------------------------- */

  const handleLoginSubmit = async (e) => {
    e.preventDefault();

    if (
      !loginEmail.trim() ||
      !loginPassword
    ) {
      triggerToast(
        'error',
        'Please fill in both email and password.',
      );

      return;
    }

    setSubmitting(true);

    try {
      const data = await login(
        loginEmail.trim(),
        loginPassword,
        rememberMe,
      );

      triggerToast(
        'success',
        data?.message ||
          'Logged in successfully!',
      );

      if (onLoginSuccess) {
        onLoginSuccess(data.user);
      }

      if (onNavigateToWorkspace) {
        setTimeout(
          onNavigateToWorkspace,
          500,
        );
      }

    } catch (error) {
      triggerToast(
        'error',
        error?.message ||
          'Unable to sign in. Please check your credentials.',
      );

    } finally {
      setSubmitting(false);
    }
  };


  /* ---------------------------------------------------------------- */
  /* Backend registration                                              */
  /* ---------------------------------------------------------------- */

  const handleSignupSubmit = async (e) => {
    e.preventDefault();

    if (!signupName.trim()) {
      triggerToast(
        'error',
        'Please enter your full name.',
      );

      return;
    }

    if (
      !signupEmail.trim() ||
      !signupEmail.includes('@')
    ) {
      triggerToast(
        'error',
        'Please enter a valid email address.',
      );

      return;
    }

    if (signupPassword.length < 6) {
      triggerToast(
        'error',
        'Password must be at least 6 characters long.',
      );

      return;
    }

    if (signupPassword !== signupConfirmPassword) {
      triggerToast(
        'error',
        'Passwords do not match.',
      );

      return;
    }

    if (!agreeTerms) {
      triggerToast(
        'error',
        'You must agree to the Terms of Service to create an account.',
      );

      return;
    }

    setSubmitting(true);

    try {
      const data = await register(
        signupName.trim(),
        signupEmail.trim(),
        signupPassword,
        true,
      );

      triggerToast(
        'success',
        data?.message ||
          'Account created successfully!',
      );

      if (onLoginSuccess) {
        onLoginSuccess(data.user);
      }

      if (onNavigateToWorkspace) {
        setTimeout(
          onNavigateToWorkspace,
          500,
        );
      }

    } catch (error) {
      triggerToast(
        'error',
        error?.message ||
          'Unable to create your account.',
      );

    } finally {
      setSubmitting(false);
    }
  };


  /* ---------------------------------------------------------------- */
  /* Logout                                                            */
  /* ---------------------------------------------------------------- */

  const handleLogout = async () => {
    setSubmitting(true);

    try {
      await logout();

      triggerToast(
        'success',
        'Signed out successfully.',
      );

    } finally {
      setSubmitting(false);
    }
  };


  /* ---------------------------------------------------------------- */
  /* Forgot password                                                   */
  /* ---------------------------------------------------------------- */

  const handleForgotPassword = (e) => {
    e.preventDefault();

    if (!forgotEmail.trim()) {
      triggerToast(
        'error',
        'Please provide an email address.',
      );

      return;
    }

    /*
     * There is currently no password-reset endpoint
     * in the backend authentication API.
     *
     * Therefore this remains a UI placeholder.
     */
    triggerToast(
      'success',
      'Password reset is not yet enabled on the backend.',
    );

    setShowForgotModal(false);
    setForgotEmail('');
  };


  /* ---------------------------------------------------------------- */
  /* Logged-in view                                                    */
  /* ---------------------------------------------------------------- */

  if (user) {
    return (
      <div className="auth-page-container">

        {toast && (
          <div
            className={`auth-toast auth-toast-${toast.type}`}
          >
            <span
              style={{
                fontSize: '1.2rem',
                marginRight: '8px',
              }}
            >
              {toast.type === 'success'
                ? '✓'
                : '⚠️'}
            </span>

            <span
              style={{
                flex: 1,
                fontSize: '0.9rem',
                fontWeight: 500,
              }}
            >
              {toast.message}
            </span>

            <button
              onClick={() => setToast(null)}
              className="toast-close-btn"
            >
              &times;
            </button>
          </div>
        )}

        <div className="auth-card">

          <div className="auth-header">

            <div className="auth-logo-badge">
              <img
                src={robotLogo}
                alt="IS Procurement AI Logo"
                className="auth-logo-img"
              />
            </div>

            <h1 className="auth-title">
              IS Procurement AI
            </h1>

            <p className="auth-subtitle">
              AI-Powered Indian Standards Recommendation and Validation Platform for procurement requirements, BIS standards discovery, standards applicability analysis, and compliance guidance.
            </p>

          </div>


          <div className="auth-logged-in-box">

            <div className="user-profile-hero">

              <img
                src={
                  user.avatar ||
                  `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(
                    user.email,
                  )}`
                }
                alt={user.full_name}
                className="profile-hero-avatar"
              />

              <div className="profile-hero-info">

                <h3>
                  {user.full_name}
                </h3>

                <p className="user-email">
                  {user.email}
                </p>

                <span
                  style={{
                    display: 'inline-block',
                    marginTop: '6px',
                    padding: '4px 10px',
                    borderRadius: '99px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background:
                      'hsla(174, 100%, 41%, 0.1)',
                    color:
                      'hsl(174, 100%, 41%)',
                    border:
                      '1px solid hsla(174, 100%, 41%, 0.25)',
                  }}
                >
                  {user.role || 'User'}
                </span>

              </div>

            </div>


            <div className="auth-actions-group">

              {onNavigateToWorkspace && (
                <button
                  onClick={onNavigateToWorkspace}
                  className="auth-submit-btn"
                  disabled={submitting}
                >
                  Enter Knowledge Console →
                </button>
              )}

              <button
                onClick={handleLogout}
                className="preset-btn"
                disabled={submitting}
                style={{
                  width: '100%',
                  padding: '12px',
                  justifyContent: 'center',
                }}
              >
                {submitting
                  ? 'Signing out...'
                  : 'Sign Out of Account'}
              </button>

            </div>

          </div>

        </div>
      </div>
    );
  }


  /* ---------------------------------------------------------------- */
  /* Authentication forms                                             */
  /* ---------------------------------------------------------------- */

  return (
    <div className="auth-page-container">

      {toast && (
        <div
          className={`auth-toast auth-toast-${toast.type}`}
        >
          <span
            style={{
              fontSize: '1.2rem',
              marginRight: '8px',
            }}
          >
            {toast.type === 'success'
              ? '✓'
              : '⚠️'}
          </span>

          <span
            style={{
              flex: 1,
              fontSize: '0.9rem',
              fontWeight: 500,
            }}
          >
            {toast.message}
          </span>

          <button
            onClick={() => setToast(null)}
            className="toast-close-btn"
          >
            &times;
          </button>
        </div>
      )}


      <div className="auth-card">

        {/* Header */}
        <div className="auth-header">

          <div className="auth-logo-badge">
            <img
              src={robotLogo}
              alt="IS Procurement AI Logo"
              className="auth-logo-img"
            />
          </div>

          <h1 className="auth-title">
            IS Procurement AI
          </h1>

          <p className="auth-subtitle">
            AI-Powered Indian Standards Recommendation and Validation Platform for procurement requirements, BIS standards discovery, standards applicability analysis, and compliance guidance.
          </p>

        </div>


        {/* Tabs */}
        <div className="auth-tab-switch">

          <button
            type="button"
            className={`auth-tab-btn ${
              activeTab === 'login'
                ? 'active'
                : ''
            }`}
            onClick={() =>
              setActiveTab('login')
            }
          >
            Sign In
          </button>

          <button
            type="button"
            className={`auth-tab-btn ${
              activeTab === 'signup'
                ? 'active'
                : ''
            }`}
            onClick={() =>
              setActiveTab('signup')
            }
          >
            Create Account
          </button>

        </div>


        {/* ---------------------------------------------------------- */}
        {/* LOGIN                                                        */}
        {/* ---------------------------------------------------------- */}

        {activeTab === 'login' && (
          <form
            onSubmit={handleLoginSubmit}
            className="auth-form"
          >

            <div className="form-group">

              <label className="input-label">
                Email Address
              </label>

              <div className="input-wrapper">

                <svg
                  className="input-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>

                <input
                  type="email"
                  className="input-text with-icon"
                  placeholder="name@company.com"
                  value={loginEmail}
                  onChange={(e) =>
                    setLoginEmail(
                      e.target.value,
                    )
                  }
                  required
                />

              </div>

            </div>


            <div className="form-group">

              <div className="label-row">

                <label className="input-label">
                  Password
                </label>

                <button
                  type="button"
                  className="forgot-link"
                  onClick={() =>
                    setShowForgotModal(true)
                  }
                >
                  Forgot password?
                </button>

              </div>


              <div className="input-wrapper">

                <svg
                  className="input-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect
                    x="3"
                    y="11"
                    width="18"
                    height="11"
                    rx="2"
                    ry="2"
                  />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>

                <input
                  type={
                    showLoginPassword
                      ? 'text'
                      : 'password'
                  }
                  className="input-text with-icon with-end-icon"
                  placeholder="••••••••••••"
                  value={loginPassword}
                  onChange={(e) =>
                    setLoginPassword(
                      e.target.value,
                    )
                  }
                  required
                />

                <button
                  type="button"
                  className="end-icon-btn"
                  onClick={() =>
                    setShowLoginPassword(
                      !showLoginPassword,
                    )
                  }
                >
                  {showLoginPassword
                    ? '👁️'
                    : '🔒'}
                </button>

              </div>

            </div>


            <div className="form-checkbox-row">

              <label className="checkbox-label">

                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) =>
                    setRememberMe(
                      e.target.checked,
                    )
                  }
                />

                <span>
                  Keep me signed in
                </span>

              </label>

            </div>


            <button
              type="submit"
              disabled={
                submitting ||
                authLoading
              }
              className="auth-submit-btn"
            >
              {submitting
                ? 'Signing in...'
                : 'Sign In to Dashboard'}
            </button>

          </form>
        )}


        {/* ---------------------------------------------------------- */}
        {/* SIGNUP                                                       */}
        {/* ---------------------------------------------------------- */}

        {activeTab === 'signup' && (
          <form
            onSubmit={handleSignupSubmit}
            className="auth-form"
          >

            <div className="form-group">

              <label className="input-label">
                Full Name
              </label>

              <div className="input-wrapper">

                <svg
                  className="input-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle
                    cx="12"
                    cy="7"
                    r="4"
                  />
                </svg>

                <input
                  type="text"
                  className="input-text with-icon"
                  placeholder="Alex Mercer"
                  value={signupName}
                  onChange={(e) =>
                    setSignupName(
                      e.target.value,
                    )
                  }
                  required
                />

              </div>

            </div>


            <div className="form-group">

              <label className="input-label">
                Work Email
              </label>

              <div className="input-wrapper">

                <svg
                  className="input-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                  <polyline points="22,6 12,13 2,6" />
                </svg>

                <input
                  type="email"
                  className="input-text with-icon"
                  placeholder="alex@company.com"
                  value={signupEmail}
                  onChange={(e) =>
                    setSignupEmail(
                      e.target.value,
                    )
                  }
                  required
                />

              </div>

            </div>


            <div className="form-group">

              <label className="input-label">
                Create Password
              </label>

              <div className="input-wrapper">

                <svg
                  className="input-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect
                    x="3"
                    y="11"
                    width="18"
                    height="11"
                    rx="2"
                    ry="2"
                  />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>

                <input
                  type={
                    showSignupPassword
                      ? 'text'
                      : 'password'
                  }
                  className="input-text with-icon with-end-icon"
                  placeholder="At least 6 characters"
                  value={signupPassword}
                  onChange={(e) =>
                    setSignupPassword(
                      e.target.value,
                    )
                  }
                  required
                />

                <button
                  type="button"
                  className="end-icon-btn"
                  onClick={() =>
                    setShowSignupPassword(
                      !showSignupPassword,
                    )
                  }
                >
                  {showSignupPassword
                    ? '👁️'
                    : '🔒'}
                </button>

              </div>


              {signupPassword && (
                <div className="strength-meter">

                  <div className="strength-bar-bg">

                    <div
                      className="strength-bar-fill"
                      style={{
                        width: `${strength.score}%`,
                        backgroundColor:
                          strength.color,
                      }}
                    />

                  </div>

                  <span
                    className="strength-label"
                    style={{
                      color: strength.color,
                    }}
                  >
                    {strength.label} Password
                  </span>

                </div>
              )}

            </div>


            <div className="form-group">

              <label className="input-label">
                Confirm Password
              </label>

              <div className="input-wrapper">

                <svg
                  className="input-icon"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>

                <input
                  type="password"
                  className="input-text with-icon"
                  placeholder="Re-enter password"
                  value={signupConfirmPassword}
                  onChange={(e) =>
                    setSignupConfirmPassword(
                      e.target.value,
                    )
                  }
                  required
                />

              </div>


              {signupConfirmPassword && (
                <div
                  style={{
                    fontSize: '0.75rem',
                    marginTop: '4px',
                  }}
                >
                  {signupPassword ===
                  signupConfirmPassword ? (
                    <span
                      style={{
                        color:
                          'hsl(145, 80%, 42%)',
                      }}
                    >
                      ✓ Passwords match
                    </span>
                  ) : (
                    <span
                      style={{
                        color:
                          'hsl(0, 85%, 60%)',
                      }}
                    >
                      ✗ Passwords do not match
                    </span>
                  )}
                </div>
              )}

            </div>


            <div className="form-checkbox-row">

              <label className="checkbox-label">

                <input
                  type="checkbox"
                  checked={agreeTerms}
                  onChange={(e) =>
                    setAgreeTerms(
                      e.target.checked,
                    )
                  }
                />

                <span>
                  I accept the Terms of Service & Privacy Policy
                </span>

              </label>

            </div>


            <button
              type="submit"
              disabled={
                submitting ||
                authLoading
              }
              className="auth-submit-btn"
            >
              {submitting
                ? 'Creating Account...'
                : 'Create Free Account'}
            </button>

          </form>
        )}


      </div>


      {/* ------------------------------------------------------------ */}
      {/* Forgot password modal                                         */}
      {/* ------------------------------------------------------------ */}

      {showForgotModal && (
        <div className="modal-backdrop">

          <div
            className="modal-content"
            style={{
              maxWidth: '400px',
              width: '90%',
            }}
          >

            <h3
              style={{
                marginBottom: '8px',
              }}
            >
              Reset Your Password
            </h3>

            <p
              style={{
                fontSize: '0.85rem',
                marginBottom: '20px',
                color:
                  'hsl(185, 8%, 58%)',
              }}
            >
              Password reset is not currently
              enabled by the IS Procurement AI backend.
            </p>


            <form
              onSubmit={
                handleForgotPassword
              }
            >

              <input
                type="email"
                className="input-text"
                placeholder="name@company.com"
                value={forgotEmail}
                onChange={(e) =>
                  setForgotEmail(
                    e.target.value,
                  )
                }
                required
                style={{
                  marginBottom: '16px',
                }}
              />


              <div
                style={{
                  display: 'flex',
                  gap: '10px',
                  justifyContent: 'flex-end',
                }}
              >

                <button
                  type="button"
                  className="preset-btn"
                  onClick={() =>
                    setShowForgotModal(
                      false,
                    )
                  }
                >
                  Cancel
                </button>


                <button
                  type="submit"
                  className="auth-submit-btn"
                  style={{
                    width: 'auto',
                    padding: '10px 16px',
                  }}
                >
                  Close
                </button>

              </div>

            </form>

          </div>

        </div>
      )}

    </div>
  );
}