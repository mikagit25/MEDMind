import { create } from "zustand";
import { persist } from "zustand/middleware";
import { clearMeCache } from "./auth";

interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  role: string;
  subscription_tier: string;
  xp: number;
  level: number;
  streak_days: number;
  longest_streak?: number;
  onboarding_completed: boolean;
  preferences: Record<string, unknown>;
  created_at?: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  _hasHydrated: boolean;
  setAuth: (user: User, access: string, refresh: string) => void;
  updateUser: (data: Partial<User>) => void;
  logout: () => void;
  setHasHydrated: (v: boolean) => void;
}

interface UIState {
  darkMode: boolean;
  toggleDarkMode: () => void;
  setDarkMode: (val: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      _hasHydrated: false,

      setAuth: (user, access, refresh) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", access);
          localStorage.setItem("refresh_token", refresh);
        }
        set({ user, accessToken: access, refreshToken: refresh, isAuthenticated: true });
      },

      updateUser: (data) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...data } : null,
        })),

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          clearMeCache();
        }
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },

      setHasHydrated: (v) => set({ _hasHydrated: v }),
    }),
    {
      name: "medmind-auth",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        // _hasHydrated is NOT persisted — it's always false on fresh load
      }),
      onRehydrateStorage: () => (state) => {
        // Called when Zustand finishes loading from localStorage
        state?.setHasHydrated(true);
        // Also sync tokens to localStorage keys used by the API interceptor
        if (state?.accessToken && typeof window !== "undefined") {
          localStorage.setItem("access_token", state.accessToken);
        }
        if (state?.refreshToken && typeof window !== "undefined") {
          localStorage.setItem("refresh_token", state.refreshToken);
        }
      },
    }
  )
);

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      darkMode: false,
      toggleDarkMode: () =>
        set((state) => {
          const next = !state.darkMode;
          if (typeof document !== "undefined") {
            document.documentElement.classList.toggle("dark", next);
          }
          return { darkMode: next };
        }),
      setDarkMode: (val) => {
        if (typeof document !== "undefined") {
          document.documentElement.classList.toggle("dark", val);
        }
        set({ darkMode: val });
      },
    }),
    { name: "medmind-ui" }
  )
);
