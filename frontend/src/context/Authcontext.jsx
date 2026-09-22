/*
 * IS Procurement AI Authentication Context
 *
 * Central source of truth for:
 * - Current user
 * - Authentication token
 * - Login
 * - Registration
 * - Logout
 * - Session restoration
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
} from 'react';

import * as api from '../services/api';


const AuthContext = createContext(null);


/* ------------------------------------------------------------------ */
/* Storage helpers                                                     */
/* ------------------------------------------------------------------ */

const TOKEN_KEY = 'qn_auth_token';
const USER_KEY = 'qn_auth_user';


function clearStoredSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);

  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}


function storeSession(
  authToken,
  userProfile,
  rememberMe = true,
) {
  clearStoredSession();

  const storage = rememberMe
    ? localStorage
    : sessionStorage;

  storage.setItem(
    TOKEN_KEY,
    authToken,
  );

  storage.setItem(
    USER_KEY,
    JSON.stringify(userProfile),
  );
}


function getStoredToken() {
  return (
    localStorage.getItem(TOKEN_KEY) ||
    sessionStorage.getItem(TOKEN_KEY)
  );
}


/* ------------------------------------------------------------------ */
/* Provider                                                            */
/* ------------------------------------------------------------------ */

export const AuthProvider = ({
  children,
}) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);


  /*
   * Save authentication information locally.
   */
  const saveAuthSession = (
    authToken,
    userProfile,
    rememberMe = true,
  ) => {
    setToken(authToken);
    setUser(userProfile);

    storeSession(
      authToken,
      userProfile,
      rememberMe,
    );
  };


  /*
   * Clear all client-side authentication data.
   */
  const clearAuthSession = () => {
    setToken(null);
    setUser(null);

    clearStoredSession();
  };


  /*
   * Restore the session after page refresh.
   *
   * The stored JWT is validated by the FastAPI backend.
   */
  useEffect(() => {
    let cancelled = false;

    const restoreSession = async () => {
      const storedToken = getStoredToken();

      if (!storedToken) {
        if (!cancelled) {
          setLoading(false);
        }

        return;
      }

      try {
        /*
         * api.getCurrentUser() reads the token from either
         * localStorage or sessionStorage and calls /auth/me.
         */
        const currentUser =
          await api.getCurrentUser();

        if (cancelled) {
          return;
        }

        setToken(storedToken);
        setUser(currentUser);

      } catch (error) {
        console.warn(
          'Stored authentication session is invalid:',
          error,
        );

        if (!cancelled) {
          clearAuthSession();
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    restoreSession();

    return () => {
      cancelled = true;
    };
  }, []);


  /*
   * Log in through the FastAPI backend.
   */
  const login = async (
    email,
    password,
    rememberMe = true,
  ) => {
    const data = await api.loginUser(
      email.trim(),
      password,
    );

    if (!data?.token || !data?.user) {
      throw new Error(
        'Authentication response is incomplete.',
      );
    }

    saveAuthSession(
      data.token,
      data.user,
      rememberMe,
    );

    return data;
  };


  /*
   * Register through the FastAPI backend.
   */
  const register = async (
    fullName,
    email,
    password,
    rememberMe = true,
  ) => {
    setLoading(true);

    try {
      const data =
        await api.registerUser(
          fullName.trim(),
          email.trim(),
          password,
        );

      if (!data?.token || !data?.user) {
        throw new Error(
          'Registration response is incomplete.',
        );
      }

      saveAuthSession(
        data.token,
        data.user,
        rememberMe,
      );

      return data;

    } finally {
      setLoading(false);
    }
  };


  /*
   * Logout from backend and frontend.
   */
  const logout = async () => {
    const currentToken =
      token || getStoredToken();

    try {
      await api.logoutUser(
        currentToken,
      );

    } catch (error) {
      /*
       * Even if backend logout fails,
       * remove the local session.
       */
      console.warn(
        'Backend logout failed:',
        error,
      );

    } finally {
      clearAuthSession();
    }
  };


  return (
    <AuthContext.Provider
      value={{
        user,
        token,

        isLoggedIn:
          Boolean(user && token),

        loading,

        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};


/*
 * Access authentication state from any child component.
 */
export const useAuth = () => {
  const context =
    useContext(AuthContext);

  if (!context) {
    throw new Error(
      'useAuth must be used within an AuthProvider',
    );
  }

  return context;
};