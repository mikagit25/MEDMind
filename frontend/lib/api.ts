import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("refresh_token");
      if (refresh) {
        try {
          const res = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refresh,
          });
          localStorage.setItem("access_token", res.data.access_token);
          localStorage.setItem("refresh_token", res.data.refresh_token);
          original.headers.Authorization = `Bearer ${res.data.access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ============================================================
// API FUNCTIONS
// ============================================================

export const authApi = {
  register: (data: RegisterData) => api.post("/auth/register", data),
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  refresh: (refresh_token: string) =>
    api.post("/auth/refresh", { refresh_token }),
  me: () => api.get("/auth/me"),
  updateMe: (data: { first_name?: string; last_name?: string; preferences?: Record<string, unknown> }) =>
    api.patch("/auth/me", data),
  onboarding: (data: object) => api.post("/auth/onboarding", data),
  updateVetSettings: (vet_mode: boolean, species: string[]) =>
    api.put("/auth/veterinary-settings", { vet_mode, species }),
};

export const contentApi = {
  getSpecialties: (vet = false) =>
    api.get(`/specialties${vet ? "?vet=true" : ""}`),
  getModules: (specialtyId: string) =>
    api.get(`/specialties/${specialtyId}/modules`),
  getModule: (id: string) => api.get(`/modules/${id}`),
  getLessons: (moduleId: string) => api.get(`/modules/${moduleId}/lessons`),
  getLesson: (id: string) => api.get(`/lessons/${id}`),
  getFlashcards: (moduleId: string, dueOnly = false) =>
    api.get(`/modules/${moduleId}/flashcards${dueOnly ? "?due_only=true" : ""}`),
  getMCQ: (moduleId: string) => api.get(`/modules/${moduleId}/mcq`),
  getCases: (moduleId: string) => api.get(`/modules/${moduleId}/cases`),
  getCase: (caseId: string) => api.get(`/cases/${caseId}`),
  searchDrugs: (q: string) => api.get(`/drugs?q=${encodeURIComponent(q)}`),
  getDrugDosing: (drug: string, species: string) =>
    api.get(`/drugs/dosing?drug=${encodeURIComponent(drug)}&species=${encodeURIComponent(species)}`),
  search: (q: string, limit = 20) => api.get(`/search?q=${encodeURIComponent(q)}&limit=${limit}`),
};

export const progressApi = {
  completeLesson: (lessonId: string) =>
    api.post(`/progress/lesson/${lessonId}/complete`),
  reviewFlashcard: (flashcardId: string, quality: number) =>
    api.post("/progress/flashcard/review", { flashcard_id: flashcardId, quality }),
  answerMCQ: (questionId: string, selectedOption: string) =>
    api.post(`/progress/mcq/${questionId}/answer`, {
      question_id: questionId,
      selected_option: selectedOption,
    }),
  completeCase: (caseId: string, answer: string) =>
    api.post(`/progress/cases/${caseId}/complete`, { answer }),
  getStats: () => api.get("/progress/stats"),
  getHistory: () => api.get("/progress/history"),
  getWeaknesses: () => api.get("/progress/weaknesses"),
  getModulesProgress: () => api.get("/progress/modules"),
};

export const aiApi = {
  ask: (data: AIAskData) => api.post("/ai/ask", data),
  getConversations: () => api.get("/ai/conversations"),
  getMessages: (conversationId: string) =>
    api.get(`/ai/conversations/${conversationId}/messages`),
  feedback: (messageId: string, rating: number) =>
    api.post("/ai/feedback", null, {
      params: { message_id: messageId, rating },
    }),
};

export const notesApi = {
  list: (params?: { lesson_id?: string; module_id?: string }) =>
    api.get("/notes", { params }),
  create: (data: { content: string; lesson_id?: string; module_id?: string }) =>
    api.post("/notes", data),
  update: (id: string, content: string) =>
    api.patch(`/notes/${id}`, { content }),
  remove: (id: string) => api.delete(`/notes/${id}`),
};

export const bookmarksApi = {
  list: (content_type?: string) =>
    api.get("/bookmarks", { params: content_type ? { content_type } : undefined }),
  add: (content_type: string, content_id: string) =>
    api.post(`/bookmarks/${content_type}/${content_id}`),
  remove: (content_type: string, content_id: string) =>
    api.delete(`/bookmarks/${content_type}/${content_id}`),
  check: (content_type: string, content_id: string) =>
    api.get(`/bookmarks/check/${content_type}/${content_id}`),
};

export const achievementsApi = {
  list: () => api.get("/achievements"),
  check: () => api.post("/achievements/check"),
};

export const adminApi = {
  getStats: () => api.get("/admin/stats"),
  getUsers: (params?: { search?: string; tier?: string; page?: number; limit?: number }) =>
    api.get("/admin/users", { params }),
  patchUser: (id: string, data: { subscription_tier?: string; role?: string; is_active?: boolean }) =>
    api.patch(`/admin/users/${id}`, data),
  getModules: (params?: { search?: string; specialty?: string; published?: boolean; limit?: number }) =>
    api.get("/admin/modules", { params }),
  patchModule: (id: string, data: { is_published?: boolean; is_fundamental?: boolean; title?: string }) =>
    api.patch(`/admin/modules/${id}`, data),
  bulkPublish: (ids: string[], publish: boolean) =>
    api.post("/admin/modules/bulk-publish", { ids, publish }),
};

// Types
interface RegisterData {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: string;
  consent_terms: boolean;
  consent_data_processing: boolean;
  consent_marketing?: boolean;
}

interface AIAskData {
  message: string;
  conversation_id?: string;
  specialty?: string;
  mode?: string;
  search_pubmed?: boolean;
}
