/**
 * F1: Push notifications — Expo Notifications setup + flashcard reminder scheduling.
 *
 * Flow:
 *  1. On app start, call `registerForPushNotifications()` to get an Expo push token
 *     and send it to the backend (PATCH /auth/push-token).
 *  2. Schedule a local daily reminder if the user has due flashcards.
 *  3. Handle foreground notification display.
 */
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import api from './api';

// ── Notification handler (shown while app is in foreground) ─────────────────
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

// ── Request permission + get Expo push token ────────────────────────────────
export async function registerForPushNotifications(): Promise<string | null> {
  if (!Device.isDevice) {
    // Simulators can't receive push notifications
    console.log('[Push] Physical device required for push notifications');
    return null;
  }

  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== 'granted') {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== 'granted') {
    console.log('[Push] Permission not granted');
    return null;
  }

  // Android requires a notification channel
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'MedMind',
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#1A1A1A',
    });
  }

  try {
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: process.env.EXPO_PUBLIC_PROJECT_ID,
    });
    const token = tokenData.data;
    console.log('[Push] Expo push token:', token);

    // Register with backend
    await api.patch('/auth/push-token', { push_token: token }).catch(() => {
      // Non-fatal — backend might not have this endpoint yet
    });

    return token;
  } catch (e) {
    console.warn('[Push] Failed to get push token:', e);
    return null;
  }
}

// ── Schedule a local daily flashcard reminder ────────────────────────────────
const REMINDER_ID = 'medmind_flashcard_reminder';

export async function scheduleFlashcardReminder(dueCount: number): Promise<void> {
  // Cancel any existing reminder first
  await cancelFlashcardReminder();

  if (dueCount <= 0) return;

  // Schedule for 9:00 AM local time daily
  await Notifications.scheduleNotificationAsync({
    identifier: REMINDER_ID,
    content: {
      title: 'Time to review! 🧠',
      body: `You have ${dueCount} flashcard${dueCount === 1 ? '' : 's'} due for review.`,
      sound: true,
      badge: dueCount,
      data: { screen: 'flashcards' },
    },
    trigger: {
      type: Notifications.SchedulableTriggerInputTypes.DAILY,
      hour: 9,
      minute: 0,
    },
  });

  console.log(`[Push] Scheduled daily reminder for ${dueCount} due cards`);
}

export async function cancelFlashcardReminder(): Promise<void> {
  await Notifications.cancelScheduledNotificationAsync(REMINDER_ID).catch(() => {});
}

// ── Show an immediate local notification ─────────────────────────────────────
export async function showLocalNotification(title: string, body: string): Promise<void> {
  await Notifications.scheduleNotificationAsync({
    content: { title, body, sound: true },
    trigger: null, // immediate
  });
}

// ── Notification response handler — navigate to relevant screen ──────────────
export function setupNotificationResponseHandler(
  navigate: (screen: string) => void
): () => void {
  const subscription = Notifications.addNotificationResponseReceivedListener((response) => {
    const screen = response.notification.request.content.data?.screen as string | undefined;
    if (screen) navigate(screen);
  });

  return () => subscription.remove();
}
