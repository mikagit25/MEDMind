import { useEffect, useRef } from 'react';
import { Stack, router } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import * as Notifications from 'expo-notifications';
import { useAuthStore } from '@/store/authStore';
import { pushPendingReviews } from '@/lib/database';
import {
  registerForPushNotifications,
  scheduleFlashcardReminder,
  setupNotificationResponseHandler,
} from '@/lib/notifications';
import { progressApi } from '@/lib/api';

export default function RootLayout() {
  const { isAuthenticated, isLoading, loadUser } = useAuthStore();
  const notifCleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    loadUser();
  }, []);

  useEffect(() => {
    if (isLoading) return;
    if (isAuthenticated) {
      pushPendingReviews().catch(() => {});
      router.replace('/(tabs)/dashboard');

      // Register for push notifications and schedule flashcard reminder
      registerForPushNotifications().catch(() => {});

      // Schedule daily reminder based on due card count
      progressApi.getDueFlashcards()
        .then((res) => {
          const count: number = (res.data as any[])?.length ?? 0;
          return scheduleFlashcardReminder(count);
        })
        .catch(() => {});

      // Handle notification taps — navigate to the relevant screen
      notifCleanupRef.current = setupNotificationResponseHandler((screen) => {
        router.push(`/(tabs)/${screen}` as any);
      });
    } else {
      // Cancel cleanup when logged out
      notifCleanupRef.current?.();
      router.replace('/auth/login');
    }

    return () => { notifCleanupRef.current?.(); };
  }, [isAuthenticated, isLoading]);

  return (
    <>
      <StatusBar style="dark" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  );
}
