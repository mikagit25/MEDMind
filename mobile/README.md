# MedMind AI — Mobile App

React Native (Expo) companion app for MedMind AI.

## Stack
- **Expo** ~52 with **expo-router** (file-based navigation)
- **WatermelonDB** for offline-first flashcard storage
- **Zustand** for auth state
- **expo-secure-store** for JWT token persistence
- **SSE streaming** via `event-source-polyfill` for AI tutor

## Project Structure
```
mobile/
  app/
    _layout.tsx           # Root layout, auth guard
    (tabs)/
      _layout.tsx         # Bottom tab navigator
      dashboard.tsx       # XP, streak, activity chart, quick actions
      flashcards.tsx      # SM-2 review with offline queue
      ai.tsx              # AI Tutor (streaming SSE to Claude)
      modules.tsx         # Module library browser
    auth/
      login.tsx
      register.tsx
  src/
    lib/
      api.ts              # Axios client + token refresh interceptor
      schema.ts           # WatermelonDB schema
      models.ts           # WatermelonDB model classes
      database.ts         # DB instance + sync helpers
    store/
      authStore.ts        # Zustand auth store
```

## Setup
```bash
cd mobile
npm install

# Set API URL (defaults to http://localhost:8000/api/v1)
echo 'EXPO_PUBLIC_API_URL=http://YOUR_BACKEND_IP:8000/api/v1' > .env

# Start dev server
npx expo start

# Run on iOS simulator
npx expo start --ios

# Run on Android emulator
npx expo start --android
```

## Offline Support
Flashcards are synced to SQLite via WatermelonDB:
- `syncModules()` — downloads module list on app launch
- `syncFlashcards(moduleId)` — downloads cards for a module
- Reviews while offline are queued as `pending_review = true`
- `pushPendingReviews()` — called on app resume to sync to backend

## EAS Build (Production)
```bash
npm install -g eas-cli
eas login
eas build --platform ios --profile production
eas build --platform android --profile production
```
