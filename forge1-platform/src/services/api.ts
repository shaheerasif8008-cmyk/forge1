import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { toast } from 'react-hot-toast';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
export const tokenManager = {
  getToken: () => localStorage.getItem('access_token'),
  getRefreshToken: () => localStorage.getItem('refresh_token'),
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },
  clearTokens: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenManager.getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = tokenManager.getRefreshToken();
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          
          const { access_token, refresh_token } = response.data;
          tokenManager.setTokens(access_token, refresh_token);
          
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          
          return api(originalRequest);
        }
      } catch (refreshError) {
        tokenManager.clearTokens();
        window.location.href = '/login';
        toast.error('Session expired. Please login again.');
      }
    }

    // Handle other errors
    if (error.response?.status === 403) {
      toast.error('You do not have permission to perform this action.');
    } else if (error.response?.status === 404) {
      toast.error('Resource not found.');
    } else if (error.response?.status === 500) {
      toast.error('Server error. Please try again later.');
    }

    return Promise.reject(error);
  }
);

// API endpoints
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
  }) => api.post('/auth/register', data),
  
  logout: () => api.post('/auth/logout'),
  
  getCurrentUser: () => api.get('/auth/me'),
  
  updateProfile: (data: any) => api.put('/auth/profile', data),
};

export const employeeAPI = {
  list: (params?: any) => api.get('/employees', { params }),
  
  get: (id: string) => api.get(`/employees/${id}`),
  
  create: (data: any) => api.post('/employees', data),
  
  update: (id: string, data: any) => api.put(`/employees/${id}`, data),
  
  delete: (id: string) => api.delete(`/employees/${id}`),
  
  start: (id: string) => api.post(`/employees/${id}/start`),
  
  stop: (id: string) => api.post(`/employees/${id}/stop`),
  
  getLogs: (id: string, params?: any) => 
    api.get(`/employees/${id}/logs`, { params }),
  
  getMetrics: (id: string, params?: any) =>
    api.get(`/employees/${id}/metrics`, { params }),
};

export const billingAPI = {
  getSubscription: () => api.get('/billing/subscription'),
  
  getInvoices: (params?: any) => api.get('/billing/invoices', { params }),
  
  createCheckoutSession: (planId: string) =>
    api.post('/billing/checkout', { plan_id: planId }),
  
  cancelSubscription: () => api.post('/billing/cancel'),
  
  updatePaymentMethod: (paymentMethodId: string) =>
    api.post('/billing/payment-method', { payment_method_id: paymentMethodId }),
};

export const testingAPI = {
  getTestSuites: () => api.get('/testing/suites'),
  
  runTest: (suiteId: string, config: any) =>
    api.post(`/testing/suites/${suiteId}/run`, config),
  
  getTestResults: (testId: string) =>
    api.get(`/testing/results/${testId}`),
  
  getTestLogs: (testId: string) =>
    api.get(`/testing/results/${testId}/logs`),
  
  stopTest: (testId: string) =>
    api.post(`/testing/results/${testId}/stop`),
};

export default api;
