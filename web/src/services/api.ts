import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Download endpoints
export const submitDownload = async (data: {
  url: string;
  profile?: string;
  options?: any;
}) => {
  // Transform single URL to array format expected by backend
  const payload = {
    urls: [data.url],
    profile: data.profile,
    ...data.options
  };
  const response = await api.post('/download', payload);
  return response.data;
};

export const getVideoInfo = async (url: string) => {
  const response = await api.post('/video-info', { url });
  return response.data;
};

export const fetchRecentDownloads = async () => {
  const response = await api.get('/downloads/recent');
  return response.data;
};

export const fetchDownloads = async (params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) => {
  const response = await api.get('/downloads', { params });
  return response.data;
};

// Queue endpoints
export const fetchQueue = async () => {
  const response = await api.get('/queue');
  return response.data;
};

export const pauseDownload = async (downloadId: string) => {
  const response = await api.post(`/downloads/${downloadId}/pause`);
  return response.data;
};

export const resumeDownload = async (downloadId: string) => {
  const response = await api.post(`/downloads/${downloadId}/resume`);
  return response.data;
};

export const cancelDownload = async (downloadId: string) => {
  const response = await api.post(`/downloads/${downloadId}/cancel`);
  return response.data;
};

// Stats endpoints
export const fetchStats = async () => {
  const response = await api.get('/stats');
  return response.data;
};

// History endpoints
export const fetchHistory = async (params?: {
  limit?: number;
  offset?: number;
  search?: string;
}) => {
  const response = await api.get('/history', { params });
  return response.data;
};

// Settings endpoints
export const fetchSettings = async () => {
  const response = await api.get('/settings');
  return response.data;
};

export const updateSettings = async (settings: any) => {
  const response = await api.put('/settings', settings);
  return response.data;
};

// Profiles endpoints
export const fetchProfiles = async () => {
  const response = await api.get('/profiles');
  return response.data;
};

export const createProfile = async (profile: any) => {
  const response = await api.post('/profiles', profile);
  return response.data;
};

export const updateProfile = async (profileId: string, profile: any) => {
  const response = await api.put(`/profiles/${profileId}`, profile);
  return response.data;
};

export const deleteProfile = async (profileId: string) => {
  const response = await api.delete(`/profiles/${profileId}`);
  return response.data;
};

// File access endpoints
export const downloadFile = (downloadId: string) => {
  const url = `${API_BASE_URL}/downloads/${downloadId}/file`;
  window.open(url, '_blank');
};

export const openFolder = async (downloadId: string) => {
  const response = await api.post(`/downloads/${downloadId}/open-folder`);
  return response.data;
};
