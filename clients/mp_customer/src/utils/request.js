import axios from 'axios';
import { showToast } from 'vant';
import { v4 as uuidv4 } from 'uuid';

// Create instance
const service = axios.create({
  baseURL: '/api', // Vite proxy will handle this
  timeout: 10000,
});

// Request Interceptor
service.interceptors.request.use(
  (config) => {
    // 1. Inject Token
    const user = localStorage.getItem('drmoto_user');
    if (user) {
      // In real app, use a real JWT token
      config.headers['X-User-Id'] = JSON.parse(user).id;
    }

    // 2. Idempotency Key for mutation requests
    if (['post', 'put', 'delete'].includes(config.method)) {
      config.headers['Idempotency-Key'] = uuidv4();
    }

    // 3. Trace ID
    config.headers['X-Trace-Id'] = uuidv4();

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
service.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    // Handle 401
    if (error.response && error.response.status === 401) {
      showToast('Session expired, please login again');
      // Redirect to login or clear state
    }
    
    // Unified Error Toast
    const msg = error.response?.data?.detail || 'Network Error';
    showToast(msg);
    
    return Promise.reject(error);
  }
);

export default service;
