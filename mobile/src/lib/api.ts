/**
 * MedMind AI — Mobile API Client
 * Mirrors frontend/lib/api.ts but uses SecureStore for token persistence.
 */
import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';

// ── Config ─────────────────────────────────────────────────────────────────
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'medmind_access_token';
const REFRESH_KEY = 'medmind_refresh_token';

// ── Axios instance ──────────────────────────────────────────────────────────
const api: AxiosInstance = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
      if (refresh) {
        try {
          const res = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refresh,
          });
          const newAccess: string = res.data.access_token;
          await SecureStore.setItemAsync(TOKEN_KEY, newAccess);
          error.config.headers.Authorization = `Bearer ${newAccess}`;
          return api.request(error.config);
        } catch {
          await SecureStore.deleteItemAsync(TOKEN_KEY);
          await SecureStore.deleteItemAsync(REFRESH_KEY);
        }
      }
    }
    return Promise.reject(error);
  }
);

// ── Token helpers ───────────────────────────────────────────────────────────
export const storeTokens = async (access: string, refresh: string) => {
  await SecureStore.setItemAsync(TOKEN_KEY, access);
  await SecureStore.setItemAsync(REFRESH_KEY, refresh);
};

export const clearTokens = async () => {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
};

// ── Auth API ────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (
    email: string,
    password: string,
    first_name: string,
    last_name: string,
    role: string,
    consent_terms: boolean,
    consent_data_processing: boolean,
  ) =>
    api.post('/auth/register', {
      email,
      password,
      first_name,
      last_name,
      role,
      consent_terms,
      consent_data_processing,
      consent_marketing: false,
    }),
  me: () => api.get('/auth/me'),
  logout: async () => {
    const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
    return api.post('/auth/logout', { refresh_token: refresh ?? '' });
  },
};

// ── Content API ─────────────────────────────────────────────────────────────
export const contentApi = {
  getSpecialties: () => api.get('/specialties'),
  getModules: (specialtyId: string) =>
    api.get(`/specialties/${specialtyId}/modules`),
  getModule: (id: string) => api.get(`/modules/${id}`),
  getLessons: (moduleId: string) => api.get(`/modules/${moduleId}/lessons`),
  getLesson: (id: string) => api.get(`/lessons/${id}`),
  getFlashcards: (moduleId: string, dueOnly = false) =>
    api.get(`/modules/${moduleId}/flashcards${dueOnly ? '?due_only=true' : ''}`),
  getMCQ: (moduleId: string) => api.get(`/modules/${moduleId}/mcq`),
  getCases: (moduleId: string) => api.get(`/modules/${moduleId}/cases`),
  searchDrugs: (q: string) => api.get(`/drugs?q=${encodeURIComponent(q)}`),
  search: (q: string) => api.get(`/search?q=${encodeURIComponent(q)}&limit=20`),
};

// ── Progress API ────────────────────────────────────────────────────────────
export const progressApi = {
  completeLesson: (lessonId: string) =>
    api.post(`/progress/lesson/${lessonId}/complete`),
  reviewFlashcard: (flashcardId: string, quality: number) =>
    api.post('/progress/flashcard/review', { flashcard_id: flashcardId, quality }),
  answerMCQ: (questionId: string, selectedOption: string) =>
    api.post(`/progress/mcq/${questionId}/answer`, { selected_option: selectedOption }),
  getStats: () => api.get('/progress/stats'),
  getHistory: (days = 30) => api.get(`/progress/history?days=${days}`),
  getDueFlashcards: () => api.get('/progress/flashcards/due'),
};

// ── AI API ──────────────────────────────────────────────────────────────────
export const aiApi = {
  ask: (message: string, conversationId?: string, specialty = 'General Medicine', mode = 'tutor') =>
    api.post('/ai/ask', {
      message,
      conversation_id: conversationId,
      specialty,
      mode,
      search_pubmed: false,
    }),
  getConversations: () => api.get('/ai/conversations'),
  getMessages: (conversationId: string) =>
    api.get(`/ai/conversations/${conversationId}/messages`),
};

export default api;
