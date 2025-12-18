import axios from 'axios';
import { ElMessage } from 'element-plus';
import { v4 as uuidv4 } from 'uuid';

const service = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

service.interceptors.request.use(
  (config) => {
    config.headers['X-User-Role'] = 'admin'; // Mock Admin
    if (['post', 'put', 'delete'].includes(config.method)) {
      config.headers['Idempotency-Key'] = uuidv4();
    }
    return config;
  },
  (error) => Promise.reject(error)
);

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || 'Network Error';
    ElMessage.error(msg);
    return Promise.reject(error);
  }
);

export default service;
