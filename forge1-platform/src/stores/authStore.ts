import { create } from 'zustand';
import { authAPI, tokenManager } from '../services/api';
import { toast } from 'react-hot-toast';

interface User {
  id: string;
  email: string;
  full_name: string;
  company_name?: string;
  role: string;
  created_at: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    try {
      const response = await authAPI.login(email, password);
      const { access_token, refresh_token, user } = response.data;
      
      tokenManager.setTokens(access_token, refresh_token);
      set({ user, isAuthenticated: true });
      
      toast.success('Welcome back!');
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed';
      toast.error(message);
      throw error;
    }
  },

  register: async (data) => {
    try {
      const response = await authAPI.register(data);
      const { access_token, refresh_token, user } = response.data;
      
      tokenManager.setTokens(access_token, refresh_token);
      set({ user, isAuthenticated: true });
      
      toast.success('Account created successfully!');
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Registration failed';
      toast.error(message);
      throw error;
    }
  },

  logout: async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      // Ignore logout errors
    } finally {
      tokenManager.clearTokens();
      set({ user: null, isAuthenticated: false });
      toast.success('Logged out successfully');
    }
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const token = tokenManager.getToken();
      if (!token) {
        set({ user: null, isAuthenticated: false, isLoading: false });
        return;
      }

      const response = await authAPI.getCurrentUser();
      set({ user: response.data, isAuthenticated: true, isLoading: false });
    } catch (error) {
      tokenManager.clearTokens();
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  updateProfile: async (data) => {
    try {
      const response = await authAPI.updateProfile(data);
      set({ user: response.data });
      toast.success('Profile updated successfully');
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to update profile';
      toast.error(message);
      throw error;
    }
  },
}));
