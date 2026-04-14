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
  register: (data: RegisterData) => api.post("/auth/register", data).then(r => r.data),
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }).then(r => r.data),
  refresh: (refresh_token: string) =>
    api.post("/auth/refresh", { refresh_token }).then(r => r.data),
  me: () => api.get("/auth/me").then(r => r.data),
  updateMe: (data: { first_name?: string; last_name?: string; preferences?: Record<string, unknown> }) =>
    api.patch("/auth/me", data).then(r => r.data),
  onboarding: (data: object) => api.post("/auth/onboarding", data).then(r => r.data),
  updateVetSettings: (data: { vet_mode?: boolean; species?: string[] }) =>
    api.put("/veterinary/user/veterinary-settings", data).then(r => r.data),
};

export const contentApi = {
  getSpecialties: (vet = false) =>
    api.get(`/specialties${vet ? "?vet=true" : ""}`).then(r => r.data),
  getModules: (specialtyId: string) =>
    api.get(`/specialties/${specialtyId}/modules`).then(r => r.data),
  getModule: (id: string) => api.get(`/modules/${id}`).then(r => r.data),
  getLessons: (moduleId: string) => api.get(`/modules/${moduleId}/lessons`).then(r => r.data),
  getLesson: (id: string) => api.get(`/lessons/${id}`).then(r => r.data),
  getFlashcards: (moduleId: string, dueOnly = false) =>
    api.get(`/modules/${moduleId}/flashcards${dueOnly ? "?due_only=true" : ""}`).then(r => r.data),
  getMCQ: (moduleId: string) => api.get(`/modules/${moduleId}/mcq`).then(r => r.data),
  getCases: (moduleId: string) => api.get(`/modules/${moduleId}/cases`).then(r => r.data),
  getCase: (caseId: string) => api.get(`/cases/${caseId}`).then(r => r.data),
  search: (q: string, limit = 20) => api.get(`/search?q=${encodeURIComponent(q)}&limit=${limit}`).then(r => r.data),
  searchPubMed: (query: string, max_results = 5) =>
    api.get(`/search/pubmed?query=${encodeURIComponent(query)}&max_results=${max_results}`).then(r => r.data),
  getRecommendations: () => api.get("/recommendations").then(r => r.data),
  getDailyPlan: () => api.get("/recommendations/daily").then(r => r.data),
  getDashboard: () => api.get("/dashboard/overview").then(r => r.data),
  getStudentDashboard: () => api.get("/student/dashboard").then(r => r.data),
  getDoctorDashboard: () => api.get("/doctor/dashboard").then(r => r.data),
  getProfessorDashboard: () => api.get("/professor/dashboard").then(r => r.data),
  getCMECredits: (year?: number) =>
    api.get("/doctor/cme-credits", { params: year ? { year } : undefined }).then(r => r.data),
};

export const drugsApi = {
  search: (q: string) => api.get(`/drugs?q=${encodeURIComponent(q)}`).then(r => r.data),
  get: (id: string) => api.get(`/drugs/${id}`).then(r => r.data),
  getDosing: (drugId: string, speciesId: string) =>
    api.get(`/veterinary/drugs/${drugId}/dosing/${speciesId}`).then(r => r.data),
  checkInteractions: (drug_ids: string[]) =>
    api.post("/drugs/check-interactions", { drug_ids }).then(r => r.data),
  calculateDose: (data: DoseCalcData) =>
    api.post("/drugs/calculate-dose", data).then(r => r.data),
};

export const progressApi = {
  completeLesson: (lessonId: string) =>
    api.post(`/progress/lesson/${lessonId}/complete`).then(r => r.data),
  recordLessonCompletion: (lessonId: string, data: { time_spent_seconds?: number; quiz_score?: number; quiz_attempts?: number }) =>
    api.post(`/lessons/${lessonId}/complete`, data).then(r => r.data).catch(() => null), // non-fatal
  reviewFlashcard: (flashcardId: string, quality: number) =>
    api.post("/progress/flashcard/review", { flashcard_id: flashcardId, quality }).then(r => r.data),
  answerMCQ: (questionId: string, selectedOption: string) =>
    api.post(`/progress/mcq/${questionId}/answer`, {
      question_id: questionId,
      selected_option: selectedOption,
    }).then(r => r.data),
  completeCase: (caseId: string, answer: string) =>
    api.post(`/progress/cases/${caseId}/complete`, { answer }).then(r => r.data),
  getStats: () => api.get("/progress/stats").then(r => r.data),
  getHistory: (days?: number) => api.get("/progress/history", { params: days ? { days } : undefined }).then(r => r.data),
  getWeaknesses: () => api.get("/progress/weaknesses").then(r => r.data),
  getModulesProgress: () => api.get("/progress/modules").then(r => r.data),
  getStreak: () => api.get("/progress/streak").then(r => r.data),
  getAchievements: () => api.get("/achievements").then(r => r.data),
  getLeaderboard: (period: string = "week", limit: number = 50) =>
    api.get("/progress/leaderboard", { params: { period, limit } }).then(r => r.data),
  getSpecialtyLeaderboard: (specialtyId: string) =>
    api.get(`/progress/leaderboard/specialty/${specialtyId}`).then(r => r.data),
};

export const aiApi = {
  ask: (data: AIAskData) => api.post("/ai/ask", data).then(r => r.data),
  getConversations: () => api.get("/ai/conversations").then(r => r.data),
  getMessages: (conversationId: string) =>
    api.get(`/ai/conversations/${conversationId}/messages`).then(r => r.data),
  feedback: (messageId: string, rating: number) =>
    api.post("/ai/feedback", null, { params: { message_id: messageId, rating } }).then(r => r.data),
  explain: (concept: string, mode?: string) =>
    api.post(`/ai/explain/${encodeURIComponent(concept)}`, { mode }).then(r => r.data),
  quiz: (topic: string) =>
    api.post(`/ai/quiz/${encodeURIComponent(topic)}`).then(r => r.data),
  discussCase: (caseId: string, decision?: string) =>
    api.post(`/ai/case-discuss/${caseId}`, { decision }).then(r => r.data),
};

export const notesApi = {
  list: (params?: { lesson_id?: string; module_id?: string }) =>
    api.get("/notes", { params }).then(r => r.data),
  create: (data: { content: string; lesson_id?: string; module_id?: string }) =>
    api.post("/notes", data).then(r => r.data),
  update: (id: string, content: string) =>
    api.patch(`/notes/${id}`, { content }).then(r => r.data),
  remove: (id: string) => api.delete(`/notes/${id}`).then(r => r.data),
};

export const bookmarksApi = {
  list: (resource_type?: string) =>
    api.get("/bookmarks", { params: resource_type ? { resource_type } : undefined }).then(r => r.data),
  add: (resource_type: string, resource_id: string) =>
    api.post(`/bookmarks/${resource_type}/${resource_id}`).then(r => r.data),
  remove: (resource_type: string, resource_id: string) =>
    api.delete(`/bookmarks/${resource_type}/${resource_id}`).then(r => r.data),
  check: (resource_type: string, resource_id: string) =>
    api.get(`/bookmarks/check/${resource_type}/${resource_id}`).then(r => r.data),
};

export const achievementsApi = {
  list: () => api.get("/achievements").then(r => r.data),
  check: () => api.post("/achievements/check").then(r => r.data),
};

export const notificationsApi = {
  list: (params?: { unread_only?: boolean; page?: number; limit?: number }) =>
    api.get("/notifications", { params }).then(r => r.data),
  markRead: (id: string) =>
    api.post(`/notifications/${id}/read`).then(r => r.data),
  markAllRead: () =>
    api.post("/notifications/read-all").then(r => r.data),
};

export const complianceApi = {
  exportData: () => api.get("/compliance/export-data").then(r => r.data),
  deleteAccount: () => api.post("/compliance/delete-account").then(r => r.data),
  getConsents: () => api.get("/compliance/consents").then(r => r.data),
  updateConsent: (consent_type: string, given: boolean) =>
    api.post("/compliance/consents", { consent_type, given }).then(r => r.data),
};

export const adminApi = {
  getStats: () => api.get("/admin/stats").then(r => r.data),
  getUsers: (params?: { search?: string; tier?: string; page?: number; limit?: number }) =>
    api.get("/admin/users", { params }).then(r => r.data),
  patchUser: (id: string, data: { subscription_tier?: string; role?: string; is_active?: boolean }) =>
    api.patch(`/admin/users/${id}`, data).then(r => r.data),
  getModules: (params?: { search?: string; specialty?: string; published?: boolean; limit?: number }) =>
    api.get("/admin/modules", { params }).then(r => r.data),
  patchModule: (id: string, data: { is_published?: boolean; is_fundamental?: boolean; title?: string }) =>
    api.patch(`/admin/modules/${id}`, data).then(r => r.data),
  bulkPublish: (ids: string[], publish: boolean) =>
    api.post("/admin/modules/bulk-publish", { ids, publish }).then(r => r.data),
  generateModule: (data: { specialty: string; topic: string; level: number; auto_publish?: boolean }) =>
    api.post("/admin/modules/generate", data).then(r => r.data),
  importModule: (file: File, auto_publish = false) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/admin/modules/import?auto_publish=${auto_publish}`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data);
  },
  getAuditLogs: (params?: { user_id?: string; action?: string; page?: number; limit?: number }) =>
    api.get("/admin/audit-logs", { params }).then(r => r.data),
};

// ============================================================
// TEACHER AUTHORING API
// ============================================================
export const teacherApi = {
  // ── Modules ──
  listMyModules: () =>
    api.get("/lessons/my-modules").then(r => r.data),
  createModule: (data: { title: string; description?: string; specialty_code?: string; level_label?: string; is_veterinary?: boolean }) =>
    api.post("/lessons/modules", data).then(r => r.data),
  updateModule: (id: string, data: { title?: string; description?: string; level_label?: string }) =>
    api.patch(`/lessons/modules/${id}`, data).then(r => r.data),
  publishModule: (id: string) =>
    api.patch(`/lessons/modules/${id}/publish`).then(r => r.data),
  deleteModule: (id: string) =>
    api.delete(`/lessons/modules/${id}`).then(r => r.data),

  // ── Lessons ──
  listLessons: (moduleId: string, includeDrafts = true) =>
    api.get(`/lessons/modules/${moduleId}/lessons`, { params: { include_drafts: includeDrafts } }).then(r => r.data),
  getLesson: (id: string) =>
    api.get(`/lessons/${id}`).then(r => r.data),
  createLesson: (moduleId: string, data: { title: string; content: object; estimated_minutes?: number; lesson_order?: number }) =>
    api.post(`/lessons/modules/${moduleId}/lessons`, data).then(r => r.data),
  updateLesson: (id: string, data: { title?: string; content?: object; estimated_minutes?: number; lesson_order?: number; review_notes?: string }) =>
    api.patch(`/lessons/${id}`, data).then(r => r.data),
  archiveLesson: (id: string) =>
    api.delete(`/lessons/${id}`).then(r => r.data),

  // ── Workflow ──
  submitForReview: (id: string) =>
    api.patch(`/lessons/${id}/submit-review`).then(r => r.data),
  publishLesson: (id: string) =>
    api.patch(`/lessons/${id}/publish`).then(r => r.data),
  unpublishLesson: (id: string) =>
    api.patch(`/lessons/${id}/unpublish`).then(r => r.data),
  previewLesson: (id: string) =>
    api.get(`/lessons/${id}/preview`).then(r => r.data),

  // ── AI ──
  aiImprove: (id: string, data: { task: string; specialty: string; target_level?: string }) =>
    api.post(`/lessons/${id}/ai-improve`, data).then(r => r.data),
  aiGenerate: (moduleId: string, data: { title: string; specialty: string; key_concepts?: string[]; target_level?: string; estimated_minutes?: number; include_quiz?: boolean; include_clinical_case?: boolean }) =>
    api.post(`/lessons/generate?module_id=${moduleId}`, data).then(r => r.data),

  // ── Analytics ──
  moduleAnalytics: (moduleId: string) =>
    api.get(`/lessons/modules/${moduleId}/analytics`).then(r => r.data),
  lessonAnalytics: (lessonId: string) =>
    api.get(`/lessons/${lessonId}/analytics`).then(r => r.data),

  // ── Version history ──
  listVersions: (lessonId: string) =>
    api.get(`/lessons/${lessonId}/versions`).then(r => r.data),
  getVersion: (lessonId: string, versionNumber: number) =>
    api.get(`/lessons/${lessonId}/versions/${versionNumber}`).then(r => r.data),
  restoreVersion: (lessonId: string, versionNumber: number) =>
    api.post(`/lessons/${lessonId}/versions/${versionNumber}/restore`).then(r => r.data),

  // ── Courses (teacher) ──
  listMyCourses: () =>
    api.get("/courses/my").then(r => r.data),
  createCourse: (data: { title: string; description?: string; specialty?: string; level?: string }) =>
    api.post("/courses", data).then(r => r.data),
  getCourse: (id: string) =>
    api.get(`/courses/${id}`).then(r => r.data),
  updateCourse: (id: string, data: object) =>
    api.patch(`/courses/${id}`, data).then(r => r.data),
  addModuleToCourse: (courseId: string, moduleId: string) =>
    api.post(`/courses/${courseId}/modules`, null, { params: { module_id: moduleId } }).then(r => r.data),
  removeModuleFromCourse: (courseId: string, moduleId: string) =>
    api.delete(`/courses/${courseId}/modules/${moduleId}`).then(r => r.data),
  getCourseStudents: (courseId: string) =>
    api.get(`/courses/${courseId}/students`).then(r => r.data),
  removeStudentFromCourse: (courseId: string, studentId: string) =>
    api.delete(`/courses/${courseId}/students/${studentId}`).then(r => r.data),
};

// Types
interface DoseCalcData {
  drug_id: string;
  species_id: string;
  weight_kg: number;
  age_years?: number;
  renal_gfr?: number;
}

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
