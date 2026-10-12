import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('insurewise_user');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('insurewise_token') || null);
  const [loading, setLoading] = useState(false);

  const persistSession = (userData, tokenString) => {
    setUser(userData);
    setToken(tokenString);
    if (userData) {
      localStorage.setItem('insurewise_user', JSON.stringify(userData));
      localStorage.setItem('insurewise_user_id', userData.id);
    } else {
      localStorage.removeItem('insurewise_user');
      localStorage.removeItem('insurewise_user_id');
    }
    if (tokenString) {
      localStorage.setItem('insurewise_token', tokenString);
    } else {
      localStorage.removeItem('insurewise_token');
    }
  };

  const login = async (email, password) => {
    setLoading(true);
    try {
      const res = await api.login({ email, password });
      persistSession(res.user, res.token);
      return res.user;
    } finally {
      setLoading(false);
    }
  };

  const signup = async (name, email, password) => {
    setLoading(true);
    try {
      const res = await api.signup({ name, email, password });
      persistSession(res.user, res.token);
      return res.user;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    persistSession(null, null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        loading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
