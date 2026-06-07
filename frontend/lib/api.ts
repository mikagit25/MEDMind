import axios from "axios";
import { clearMeCache } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
export { API_URL };

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Separate instance for refresh calls — does NOT trigger the 401 interceptor
export const refreshApi = axios.create({ baseURL: API_URL });

// BroadcastChannel: sync refreshed tokens across all open tabs
let _tokenChannel: BroadcastChannel | null = null;
function _getTokenChannel(): BroadcastChannel | null {
  if (typeof window === "undefined") return null;
  if (!_tokenChannel) {
    try {
      _tokenChannel = new BroadcastChannel("medmind_auth");
      _tokenChannel.onmessage = (e) => {
        if (e.data?.type === "tokens_refreshed") {
          // Another tab refreshed — update our localStorage silently
          const { access_token, refresh_token } = e.data;
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", refresh_token);
          try {
            const stored = localStorage.getItem("medmind-auth");
            if (stored) {
              const parsed = JSON.parse(stored);
              parsed.state = { ...parsed.state, accessToken: access_token, refreshToken: refresh_token };
              localStorage.setItem("medmind-auth", JSON.stringify(parsed));
            }
          } catch {}
        } else if (e.data?.type === "logout") {
          // Another tab logged out — sync
          _clearAuthData();
          window.location.href = "/login";
        }
      };
    } catch {}
  }
  return _tokenChannel;
}

// Attach JWT to every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let _isRefreshing = false;
let _refreshSubscribers: ((token: string) => void)[] = [];

function _subscribeRefresh(cb: (token: string) => void) {
  _refreshSubscribers.push(cb);
}
function _notifyRefreshed(token: string) {
  _refreshSubscribers.forEach((cb) => cb(token));
  _refreshSubscribers = [];
}

// Auto-refresh on 401 — deduplicates concurrent refreshes, syncs across tabs
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;

    // Only intercept 401 errors from the API (not auth endpoints — login/refresh handle their own 401)
    if (
      error.response?.status !== 401 ||
      original._retry ||
      original.url?.includes("/auth/")
    ) {
      return Promise.reject(error);
    }

    original._retry = true;

    // If another request is already refreshing, wait for it
    if (_isRefreshing) {
      return new Promise((resolve) => {
        _subscribeRefresh((newToken) => {
          original.headers.Authorization = `Bearer ${newToken}`;
          resolve(api(original));
        });
      });
    }

    _isRefreshing = true;
    const refreshToken = typeof window !== "undefined"
      ? localStorage.getItem("refresh_token")
      : null;

    if (!refreshToken) {
      _isRefreshing = false;
      _doLogout();
      return Promise.reject(error);
    }

    try {
      const res = await refreshApi.post("/auth/refresh", { refresh_token: refreshToken });
      const newAccess: string = res.data.access_token;
      const newRefresh: string = res.data.refresh_token;

      _storeTokens(newAccess, newRefresh);

      // Broadcast new tokens to all other open tabs
      try { _getTokenChannel()?.postMessage({ type: "tokens_refreshed", access_token: newAccess, refresh_token: newRefresh }); } catch {}

      _notifyRefreshed(newAccess);
      original.headers.Authorization = `Bearer ${newAccess}`;
      _isRefreshing = false;
      return api(original);
    } catch (refreshError: any) {
      _isRefreshing = false;
      _refreshSubscribers = [];

      const status = (refreshError as any)?.response?.status;
      if (status === 401 || status === 403) {
        // Before giving up, check if another tab already refreshed and we have new tokens
        const currentRefresh = localStorage.getItem("refresh_token");
        if (currentRefresh && currentRefresh !== refreshToken) {
          // Another tab refreshed — retry with new token
          original._retry = false;
          return api(original);
        }
        _doLogout();
      }
      // Network error → stay logged in, don't kick user out
      return Promise.reject(error);
    }
  }
);

function _storeTokens(access: string, refresh: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
  try {
    // Dynamic import to avoid circular dependency issues
    import("./store").then(({ useAuthStore }) => {
      const store = useAuthStore.getState();
      if (store.user) store.setAuth(store.user, access, refresh);
    }).catch(() => {});
  } catch {}
  try {
    const stored = localStorage.getItem("medmind-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      parsed.state = { ...parsed.state, accessToken: access, refreshToken: refresh };
      localStorage.setItem("medmind-auth", JSON.stringify(parsed));
    }
  } catch {}
}

function _clearAuthData() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  clearMeCache();
  try {
    const stored = localStorage.getItem("medmind-auth");
    if (stored) {
      const parsed = JSON.parse(stored);
      parsed.state = { ...parsed.state, user: null, accessToken: null, refreshToken: null, isAuthenticated: false };
      localStorage.setItem("medmind-auth", JSON.stringify(parsed));
    }
  } catch {}
}

function _doLogout() {
  if (typeof window === "undefined") return;
  _clearAuthData();
  try { _getTokenChannel()?.postMessage({ type: "logout" }); } catch {}
  window.location.href = "/login";
}

// Initialize BroadcastChannel early (on module load in browser)
if (typeof window !== "undefined") {
  _getTokenChannel();
}

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
  updateMe: (data: { first_name?: string; last_name?: string; role?: string; preferences?: Record<string, unknown> }) =>
    api.patch("/auth/me", data).then(r => r.data),
  onboarding: (data: object) => api.post("/auth/onboarding", data).then(r => r.data),
  updateVetSettings: (data: { vet_mode: boolean; species: string[] }) =>
    api.put("/auth/veterinary-settings", data).then(r => r.data),
};

export const contentApi = {
  getSpecialties: (vet = false) =>
    api.get(`/specialties${vet ? "?vet=true" : ""}`).then(r => r.data),
  getModules: (specialtyId: string) =>
    api.get(`/specialties/${specialtyId}/modules`).then(r => r.data),
  getAllModules: (params?: { search?: string; specialty_code?: string; vet?: boolean }) =>
    api.get("/modules", { params }).then(r => r.data),
  getModule: (id: string) => api.get(`/modules/${id}`).then(r => r.data),
  getLessons: (moduleId: string) => api.get(`/modules/${moduleId}/lessons`).then(r => r.data),
  getLesson: (id: string) => api.get(`/lessons/${id}`).then(r => r.data),
  getFlashcards: (moduleId: string, dueOnly = false) =>
    api.get(`/modules/${moduleId}/flashcards${dueOnly ? "?due_only=true" : ""}`).then(r => r.data),
  getMCQ: (moduleId: string) => api.get(`/modules/${moduleId}/mcq`).then(r => r.data),
  getAllCases: (params?: { locale?: string; specialty?: string; difficulty?: string; search?: string; limit?: number }) =>
    api.get("/cases", { params }).then(r => r.data),
  getCases: (moduleId: string, locale = "en") => api.get(`/modules/${moduleId}/cases`, { params: { locale } }).then(r => r.data),
  getCase: (caseId: string, locale = "en") => api.get(`/cases/${caseId}`, { params: { locale } }).then(r => r.data),
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
  downloadCMECertificate: (creditId: string) =>
    api.get(`/doctor/cme-credits/${creditId}/certificate`, { responseType: "blob" }).then(r => r.data),
};

export const drugsApi = {
  search: (q: string, lang = "en") => api.get(`/drugs?q=${encodeURIComponent(q)}&lang=${encodeURIComponent(lang)}`).then(r => r.data),
  browse: (page = 1, limit = 24, drug_class?: string, vet?: boolean, high_yield?: boolean, lang = "en") => {
    const params = new URLSearchParams({ page: String(page), limit: String(limit), lang });
    if (drug_class) params.set("drug_class", drug_class);
    if (vet !== undefined) params.set("vet", String(vet));
    if (high_yield !== undefined) params.set("high_yield", String(high_yield));
    return api.get(`/drugs/browse?${params}`).then(r => r.data);
  },
  getClasses: () => api.get("/drugs/classes").then(r => r.data),
  get: (id: string, lang = "en") => api.get(`/drugs/${id}?lang=${lang}`).then(r => r.data),
  getAlternatives: (id: string) => api.get(`/drugs/${id}/alternatives`).then(r => r.data),
  getDosing: (drugId: string, speciesId: string) =>
    api.get(`/veterinary/drugs/${drugId}/dosing/${speciesId}`).then(r => r.data),
  checkInteractions: (drug_ids: string[]) =>
    api.post("/drugs/check-interactions", { drug_ids }).then(r => r.data),
  calculateDose: (data: DoseCalcData) =>
    api.post("/drugs/calculate-dose", data).then(r => r.data),
  // RxImage NLM free API — official FDA drug pill images
  fetchRxImage: (name: string): Promise<string | null> =>
    fetch(`https://rximage.nlm.nih.gov/api/rximage/1/rxnav?name=${encodeURIComponent(name)}&resolution=600`)
      .then(r => r.json())
      .then(d => d?.replyList?.[0]?.imageUrl ?? null)
      .catch(() => null),
};

export const simulationApi = {
  // Virtual patient
  startVirtualPatient: (data: { specialty?: string; difficulty?: string; species?: string; patient_seed?: string; language?: string }) =>
    api.post("/ai/virtual-patient/start", data).then(r => r.data),
  chatVirtualPatient: (session_token: string, message: string, language?: string) =>
    api.post("/ai/virtual-patient/chat", { session_token, message, language }).then(r => r.data),
  evaluateVirtualPatient: (session_token: string, message: string, language?: string) =>
    api.post("/ai/virtual-patient/evaluate", { session_token, message, language }).then(r => r.data),
  // FSM cases
  startCase: (caseId: string) =>
    api.post(`/cases/${caseId}/sessions`).then(r => r.data),
  makeChoice: (sessionId: string, choice_id: string) =>
    api.post(`/cases/sessions/${sessionId}/choose`, null, { params: { choice_id } }).then(r => r.data),
  getSession: (sessionId: string) =>
    api.get(`/cases/sessions/${sessionId}`).then(r => r.data),
};

export const veterinaryApi = {
  getSpecies: () => api.get("/veterinary/species").then(r => r.data),
  getDrugDosing: (drugId: string, speciesId: string) =>
    api.get(`/veterinary/drugs/${drugId}/dosing/${speciesId}`).then(r => r.data),
  checkSafety: (drug_id: string, species_id: string) =>
    api.post("/veterinary/drugs/check-species-safety", { drug_id, species_id }).then(r => r.data),
  getZoonoses: () => api.get("/veterinary/zoonoses").then(r => r.data),
  getToxicityReference: () => api.get("/veterinary/toxicity-reference").then(r => r.data),
  getClinicalPearls: (species?: string) =>
    api.get("/veterinary/clinical-pearls", { params: species ? { species } : undefined }).then(r => r.data),
  // Species-adjusted dose scaling (requires vet_mode or works for any user in test mode)
  getScaledDosing: (drug: string, species: string) =>
    api.get("/drugs/dosing", { params: { drug, species } }).then(r => r.data),
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
  exportPDF: () =>
    api.get("/progress/export/pdf", { responseType: "blob" }).then(r => r.data),
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
  delete: (id: string) =>
    api.delete(`/notifications/${id}`).then(r => r.data),
};

export const imagingApi = {
  browse: (params?: { modality?: string; region?: string; specialty?: string; limit?: number; offset?: number }) =>
    api.get("/imaging", { params }).then(r => r.data),
  search: (q: string, modality?: string) =>
    api.get("/imaging/search", { params: { q, modality } }).then(r => r.data),
  get: (id: string) => api.get(`/imaging/${id}`).then(r => r.data),
  modalities: () => api.get("/imaging/modalities").then(r => r.data),
  regions: (modality?: string) => api.get("/imaging/regions", { params: modality ? { modality } : undefined }).then(r => r.data),
  searchOpenI: (q: string, m = 1, n = 10) =>
    api.get("/imaging/openi", { params: { q, m, n } }).then(r => r.data),
  listViewers: (system?: string) =>
    api.get("/imaging/anatomy/viewers", { params: system ? { system } : undefined }).then(r => r.data),
  analyzeImage: (data: { image_url: string; modality?: string; question?: string; image_id?: string }) =>
    api.post("/imaging/analyze", data).then(r => r.data),
  suggest: (topic: string, modality?: string, limit = 4) =>
    api.get("/imaging/suggest", { params: { topic, modality, limit } }).then(r => r.data),
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
  getTranslationStats: () =>
    api.get("/admin/translations/stats").then(r => r.data),
  retranslateAllFailed: (locale?: string) =>
    api.post("/admin/translations/retranslate-failed", null, { params: locale ? { locale } : {} }).then(r => r.data),
  getFeatureFlags: () =>
    api.get("/admin/feature-flags").then(r => r.data),
  setFeatureFlag: (flag: string, enabled: boolean, rollout?: number) =>
    api.patch(`/admin/feature-flags/${flag}`, null, { params: { enabled, rollout: rollout ?? 100 } }).then(r => r.data),
  getSystemHealth: () =>
    api.get("/admin/system/health").then(r => r.data),
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
  getLesson: (id: string, locale?: string) =>
    api.get(`/lessons/${id}`, { params: locale && locale !== "en" ? { locale } : undefined }).then(r => r.data),
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
  aiGenerateCourseOutline: (data: { title: string; description?: string; specialty: string; target_level?: string; num_modules?: number; lessons_per_module?: number; include_quiz?: boolean; include_clinical_case?: boolean; language?: string }) =>
    api.post("/lessons/generate-course-outline", data).then(r => r.data),

  // ── Analytics ──
  moduleAnalytics: (moduleId: string) =>
    api.get(`/lessons/modules/${moduleId}/analytics`).then(r => r.data),
  lessonAnalytics: (lessonId: string) =>
    api.get(`/lessons/${lessonId}/analytics`).then(r => r.data),

  // ── Export / Import ──
  exportModule: (moduleId: string) =>
    api.get(`/lessons/modules/${moduleId}/export`, { responseType: "blob" }).then(r => r.data),
  importModule: (specialtyId: string, data: object) =>
    api.post(`/lessons/modules/import?specialty_id=${specialtyId}`, data).then(r => r.data),

  // ── Translations ──
  getTranslationStatus: (lessonId: string) =>
    api.get(`/lessons/${lessonId}/translations`).then(r => r.data),
  getTranslation: (lessonId: string, locale: string) =>
    api.get(`/lessons/${lessonId}/translations/${locale}`).then(r => r.data),
  retranslate: (lessonId: string, locale: string) =>
    api.post(`/lessons/${lessonId}/translations/${locale}/retranslate`).then(r => r.data),
  updateTranslation: (lessonId: string, locale: string, data: { title?: string; content_json?: object }) =>
    api.patch(`/lessons/${lessonId}/translations/${locale}`, data).then(r => r.data),

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

  // Professor dashboard
  getProfessorDashboard: () =>
    api.get("/professor/dashboard").then(r => r.data),

  // At-risk students
  getAtRiskStudents: (courseId: string) =>
    api.get(`/professor/courses/${courseId}/at-risk`).then(r => r.data),

  // All students across all courses
  getAllStudents: (params?: { search?: string; course_id?: string; sort?: string }) =>
    api.get("/professor/students", { params }).then(r => r.data),

  // Content insights
  getContentInsights: (courseId: string) =>
    api.get(`/professor/courses/${courseId}/content-insights`).then(r => r.data),

  // Assignments
  createAssignment: (courseId: string, data: { module_id: string; title: string; due_date?: string; max_score?: number }) =>
    api.post(`/courses/${courseId}/assignments`, data).then(r => r.data),
  deleteAssignment: (courseId: string, assignmentId: string) =>
    api.delete(`/courses/${courseId}/assignments/${assignmentId}`).then(r => r.data),
  getCourseAssignments: (courseId: string) =>
    api.get(`/courses/${courseId}/assignments`).then(r => r.data),

  // Preview links
  createPreviewLink: (lessonId: string, ttlHours?: number) =>
    api.post(`/lessons/${lessonId}/preview-link`, { ttl_hours: ttlHours ?? 24 }).then(r => r.data),

  // Module reorder in course
  reorderModules: (courseId: string, moduleIds: string[]) =>
    api.patch(`/courses/${courseId}/modules/reorder`, { module_ids: moduleIds }).then(r => r.data),

  // Leaderboard
  getCourseLeaderboard: (courseId: string) =>
    api.get(`/courses/${courseId}/leaderboard`).then(r => r.data),

  // ── Teacher Articles ──
  listMyArticles: () =>
    api.get("/articles/my").then(r => r.data),
  getMyArticle: (id: string) =>
    api.get(`/articles/my/${id}`).then(r => r.data),
  createArticle: (data: { title: string; slug: string; excerpt: string; category: string; body: object[]; author_display_name?: string; author_bio?: string; keywords?: string[]; reading_time_minutes?: number; schema_type?: string }) =>
    api.post("/articles/my", data).then(r => r.data),
  updateArticle: (id: string, data: { title?: string; excerpt?: string; category?: string; body?: object[]; author_display_name?: string; author_bio?: string; keywords?: string[]; reading_time_minutes?: number; schema_type?: string }) =>
    api.patch(`/articles/my/${id}`, data).then(r => r.data),
  deleteMyArticle: (id: string) =>
    api.delete(`/articles/my/${id}`).then(r => r.data),
  submitArticleForReview: (id: string) =>
    api.post(`/articles/my/${id}/submit`).then(r => r.data),
  withdrawArticle: (id: string) =>
    api.post(`/articles/my/${id}/withdraw`).then(r => r.data),
  uploadArticleImage: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/articles/my/${id}/upload-image`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data);
  },
  getMyArticleStats: () =>
    api.get("/articles/my/stats").then(r => r.data),

  // AI article generation (credit-gated)
  generateArticleAI: (data: {
    topic: string;
    category: string;
    model: string;
    specialty?: string;
    author_display_name?: string;
    author_bio?: string;
  }) => api.post("/articles/my/generate-ai", data).then(r => r.data),

  // Grade tracking
  getAssignmentGrades: (courseId: string, assignmentId: string) =>
    api.get(`/courses/${courseId}/assignments/${assignmentId}/grades`).then(r => r.data),
  upsertGrade: (courseId: string, assignmentId: string, data: { student_id: string; score: number; feedback?: string }) =>
    api.post(`/courses/${courseId}/assignments/${assignmentId}/grades`, data).then(r => r.data),
};

// ============================================================
// CREDITS API
// ============================================================
export const creditsApi = {
  getBalance: () => api.get("/credits/balance").then(r => r.data),
  getPackages: () => api.get("/credits/packages").then(r => r.data),
  getPricing: () => api.get("/credits/pricing").then(r => r.data),
  getTransactions: () => api.get("/credits/transactions").then(r => r.data),
  createCheckout: (packageId: string) =>
    api.post("/credits/purchase/checkout", null, { params: { package_id: packageId } }).then(r => r.data),
};

export const commentsApi = {
  list: (contentType: "article" | "news", slug: string, limit = 50) =>
    api.get(`/comments/${contentType}/${encodeURIComponent(slug)}`, { params: { limit } }).then(r => r.data),
  post: (contentType: "article" | "news", slug: string, body: string) =>
    api.post(`/comments/${contentType}/${encodeURIComponent(slug)}`, { body }).then(r => r.data),
  delete: (id: string) =>
    api.delete(`/comments/${id}`).then(r => r.data),
  like: (id: string) =>
    api.post(`/comments/${id}/like`).then(r => r.data),
  report: (id: string) =>
    api.post(`/comments/${id}/report`).then(r => r.data),
};

// Fire-and-forget view tracking — never throws
export const trackArticleView = (slug: string): void => {
  fetch(`/api/v1/articles/${slug}/view`, { method: "POST" }).catch(() => {});
};

// ============================================================
// STUDENT COURSES API
// ============================================================
export const studentCoursesApi = {
  getEnrolled: () => api.get("/courses/enrolled").then(r => r.data),
  discover: (params?: { specialty?: string; difficulty?: string }) =>
    api.get("/courses/discover", { params }).then(r => r.data),
  join: (invite_code: string) => api.post("/courses/join", { invite_code }).then(r => r.data),
  joinById: (courseId: string) => api.post("/courses/join-open", { course_id: courseId }).then(r => r.data),
  requestAccess: (courseId: string, message?: string) =>
    api.post(`/courses/${courseId}/request-access`, { message: message ?? "" }).then(r => r.data),
  getRequestStatus: (courseId: string) =>
    api.get(`/courses/${courseId}/request-status`).then(r => r.data),
  getProgress: (courseId: string) => api.get(`/courses/${courseId}/my-progress`).then(r => r.data),
  getLeaderboard: (courseId: string) => api.get(`/courses/${courseId}/leaderboard`).then(r => r.data),
  leave: (courseId: string) => api.delete(`/courses/${courseId}/leave`).then(r => r.data),
  getCourse: (courseId: string) => api.get(`/courses/${courseId}`).then(r => r.data),
};

// ============================================================
// MEMORY / KNOWLEDGE BANK API
// ============================================================
export const memoryApi = {
  list: (params?: { specialty?: string; type?: string; limit?: number; offset?: number }) =>
    api.get("/memory/", { params }).then(r => r.data),
  stats: () => api.get("/memory/stats").then(r => r.data),
  remove: (id: string) => api.delete(`/memory/${id}`).then(r => r.data),
};

// ============================================================
// ADAPTIVE STUDY PLAN API
// ============================================================
export const adaptivePlanApi = {
  generate: () => api.post("/student/plan/adapt").then(r => r.data),
  getCurrent: () => api.get("/student/plan/current").then(r => r.data),
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

// ── TTS API ────────────────────────────────────────────────────────────────────
export const ttsApi = {
  /** Get available voices per locale. */
  voices: () => api.get("/tts/voices").then(r => r.data),

  /** Return a URL for streaming TTS audio — used as <audio src>. */
  speakUrl: (text: string, locale = "en", gender: "female" | "male" = "female", rate = "+0%") => {
    // We POST via fetch to get a blob URL (axios doesn't support blob streaming well)
    return { text, locale, gender, rate };
  },

  /** Fetch TTS audio as Blob (for playback). */
  speakBlob: async (text: string, locale = "en", gender: "female" | "male" = "female", rate = "+0%"): Promise<Blob> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const res = await fetch(`${API_URL}/tts/speak`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ text, locale, gender, rate }),
    });
    if (!res.ok) throw new Error(`TTS failed: ${res.status}`);
    return res.blob();
  },

  /** Stream article as audio blob. */
  articleBlob: async (articleId: string, locale = "en", gender: "female" | "male" = "female"): Promise<Blob> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const params = new URLSearchParams({ locale, gender });
    const res = await fetch(`${API_URL}/tts/article/${articleId}?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Article TTS failed: ${res.status}`);
    return res.blob();
  },
};

// ── Referral API ───────────────────────────────────────────────────────────────
export const referralApi = {
  getInfo: () => api.get("/referral").then(r => r.data),
  applyCode: (code: string) => api.post("/referral/apply", { code }).then(r => r.data),
};

// ── Team API ───────────────────────────────────────────────────────────────────
export const teamApi = {
  list: () => api.get("/team").then(r => r.data),
  invite: (email: string) => api.post("/team/invite", { email }).then(r => r.data),
  join: (token: string) => api.post(`/team/join/${token}`).then(r => r.data),
  removeMember: (memberId: string) => api.delete(`/team/members/${memberId}`).then(r => r.data),
  stats: () => api.get("/team/stats").then(r => r.data),
};

// ── Exam API ───────────────────────────────────────────────────────────────────
export const examApi = {
  getModes: () => api.get("/exam/modes").then(r => r.data),
  createSession: (mode_id: string, specialty_filter?: string) =>
    api.post("/exam/sessions", { mode_id, specialty_filter }).then(r => r.data),
  getSession: (sessionId: string) => api.get(`/exam/sessions/${sessionId}`).then(r => r.data),
  submitAnswer: (sessionId: string, question_index: number, selected_option: string) =>
    api.post(`/exam/sessions/${sessionId}/answer`, { question_index, selected_option }).then(r => r.data),
  finalizeSession: (sessionId: string) =>
    api.post(`/exam/sessions/${sessionId}/submit`).then(r => r.data),
  getResults: (sessionId: string) => api.get(`/exam/sessions/${sessionId}/results`).then(r => r.data),
  getHistory: () => api.get("/exam/history").then(r => r.data),
};
