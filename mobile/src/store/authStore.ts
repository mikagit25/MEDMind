import { create } from 'zustand';
import { authApi, storeTokens, clearTokens } from '@/lib/api';

interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  subscription_tier: string;
  xp: number;
  level: number;
  streak_days: number;
  preferences?: Record<string, unknown>;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  updateUser: (data: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isAuthenticated: false,

  loadUser: async () => {
    set({ isLoading: true });
    try {
      const res = await authApi.me();
      set({ user: res.data, isAuthenticated: true });
    } catch {
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  login: async (email, password) => {
    const res = await authApi.login(email, password);
    await storeTokens(res.data.access_token, res.data.refresh_token);
    const me = await authApi.me();
    set({ user: me.data, isAuthenticated: true });
  },

  logout: async () => {
    try { await authApi.logout(); } catch {}
    await clearTokens();
    set({ user: null, isAuthenticated: false });
  },

  updateUser: (data) =>
    set((state) => ({ user: state.user ? { ...state.user, ...data } : null })),
}));
