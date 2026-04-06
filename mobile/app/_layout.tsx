import { useEffect } from 'react';
import { Stack, router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useAuthStore } from '@/store/authStore';
import { pushPendingReviews } from '@/lib/database';

export default function RootLayout() {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      pushPendingReviews().catch(() => {});
      router.replace('/(tabs)/dashboard');
    } else {
      router.replace('/auth/login');
    }
  }, [isAuthenticated, isLoading]);

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
