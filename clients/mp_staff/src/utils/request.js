import axios from 'axios';
import { showToast } from 'vant';
import { v4 as uuidv4 } from 'uuid';

const service = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

service.interceptors.request.use(
  (config) => {
    // Inject Staff ID (Mock for now, normally from JWT)
    config.headers['X-User-Role'] = 'staff'; 
    const staff = localStorage.getItem('drmoto_staff');
    if (staff) {
        config.headers['X-User-Id'] = JSON.parse(staff).id;
    }
    
    if (['post', 'put', 'delete'].includes(config.method)) {
      config.headers['Idempotency-Key'] = uuidv4();
    }
    config.headers['X-Trace-Id'] = uuidv4();
    return config;
  },
  (error) => Promise.reject(error)
);

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || 'Network Error';
    showToast(msg);
    return Promise.reject(error);
  }
);

export default service;
