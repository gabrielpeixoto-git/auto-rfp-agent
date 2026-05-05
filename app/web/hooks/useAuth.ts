"use client";

import { useState, useEffect, useCallback } from "react";
import { authApi } from "@/lib/api/client";
import type { User } from "@/types/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isInitialized: boolean; // Indica se a verificação inicial de auth terminou
}

/**
 * Clear access token from storage
 * Note: Refresh token is stored in httpOnly cookie (not accessible to JS)
 */
function clearAccessToken(): void {
  // Only clear access token - refresh token is httpOnly cookie
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  sessionStorage.removeItem("token");
  sessionStorage.removeItem("user");
  // Note: Cannot clear httpOnly cookies from JavaScript
  // Server must clear them via Set-Cookie header
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isLoading: false,
    error: null,
    isInitialized: false,
  });

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      setState((prev) => ({ ...prev, token, isLoading: false, isInitialized: true }));
    } else {
      setState((prev) => ({ ...prev, isLoading: false, isInitialized: true }));
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      console.log("Tentando login com:", email);
      const response = await authApi.login(email, password);
      console.log("Login response:", response);
      localStorage.setItem("token", response.access_token);
      setState({
        user: response.user || null,
        token: response.access_token,
        isLoading: false,
        error: null,
        isInitialized: true,
      });
      return true;
    } catch (error: any) {
      console.error("Login error:", error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error.message || "Login failed",
      }));
      return false;
    }
  }, []);

  const logout = useCallback(async (redirectTo: string = "/login") => {
    // Call logout endpoint to clear httpOnly cookie server-side
    try {
      await authApi.logout();
    } catch (e) {
      // Ignore errors - we'll clear local state anyway
      console.warn("Logout API call failed", e);
    }
    
    // Clear local access token
    clearAccessToken();
    
    // Reset state
    setState({
      user: null,
      token: null,
      isLoading: false,
      error: null,
      isInitialized: true,
    });
    
    // Redirect to login page
    if (typeof window !== "undefined") {
      window.location.href = redirectTo;
    }
  }, []);

  /**
   * Refresh access token using httpOnly cookie
   * This is called automatically when access token expires
   */
  const refreshToken = useCallback(async (): Promise<boolean> => {
    try {
      const response = await authApi.refresh();
      
      // Store new access token
      localStorage.setItem("token", response.access_token);
      setState((prev) => ({
        ...prev,
        token: response.access_token,
        user: response.user,
        error: null,
      }));
      return true;
    } catch (error: any) {
      console.error("Token refresh failed:", error);
      // Refresh failed - user needs to login again
      clearAccessToken();
      setState((prev) => ({
        ...prev,
        token: null,
        user: null,
        error: "Session expired. Please login again.",
      }));
      return false;
    }
  }, []);

  const isAuthenticated = !!state.token;

  return {
    ...state,
    isAuthenticated,
    login,
    logout,
    refreshToken,
  };
}
