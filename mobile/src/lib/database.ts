/**
 * WatermelonDB database instance + offline sync helpers
 */
import { Database } from '@nozbe/watermelondb';
import SQLiteAdapter from '@nozbe/watermelondb/adapters/sqlite';
import schema from './schema';
import { ModuleModel, LessonModel, FlashcardModel, AIMessageModel } from './models';
import { contentApi, progressApi } from './api';

const adapter = new SQLiteAdapter({
  schema,
  dbName: 'medmind_offline',
  jsi: true,
  onSetUpError: (error) => {
    console.error('WatermelonDB setup error:', error);
  },
});

export const db = new Database({
  adapter,
  modelClasses: [ModuleModel, LessonModel, FlashcardModel, AIMessageModel],
});

// ── Sync helpers ──────────────────────────────────────────────────────────────

/** Download all modules from server → upsert into local DB */
export async function syncModules(): Promise<void> {
  try {
    const specialties = await contentApi.getSpecialties();
    const modulesCollection = db.get<ModuleModel>('modules');

    await db.write(async () => {
      for (const spec of specialties.data) {
        const mods = await contentApi.getModules(spec.id);
        for (const mod of mods.data) {
          const existing = await modulesCollection
            .query()
            .fetch()
            .then((all) => all.find((m) => m.remoteId === mod.id));

          if (existing) {
            await existing.update((m) => {
              m.title = mod.title;
              m.description = mod.description ?? '';
              m.specialtyName = spec.name;
              m.isFundamental = mod.is_fundamental ?? false;
            });
          } else {
            await modulesCollection.create((m) => {
              m.remoteId = mod.id;
              m.title = mod.title;
              m.description = mod.description ?? '';
              m.specialtyName = spec.name;
              m.isFundamental = mod.is_fundamental ?? false;
            });
          }
        }
      }
    });
  } catch (e) {
    console.warn('syncModules failed (offline?):', e);
  }
}

/** Download flashcards for a module → upsert into local DB */
export async function syncFlashcards(moduleId: string, remoteModuleId: string): Promise<void> {
  try {
    const res = await contentApi.getFlashcards(remoteModuleId);
    const col = db.get<FlashcardModel>('flashcards');

    await db.write(async () => {
      for (const fc of res.data) {
        const existing = await col
          .query()
          .fetch()
          .then((all) => all.find((f) => f.remoteId === fc.id));

        if (existing) {
          await existing.update((f) => {
            f.front = fc.question;
            f.back = fc.answer;
            f.dueDate = new Date(fc.due_date ?? Date.now());
            f.interval = fc.interval ?? 1;
            f.easeFactor = fc.ease_factor ?? 2.5;
            f.repetitions = fc.repetitions ?? 0;
          });
        } else {
          await col.create((f) => {
            f.remoteId = fc.id;
            f.moduleId = moduleId;
            f.front = fc.question;
            f.back = fc.answer;
            f.dueDate = new Date(fc.due_date ?? Date.now());
            f.interval = fc.interval ?? 1;
            f.easeFactor = fc.ease_factor ?? 2.5;
            f.repetitions = fc.repetitions ?? 0;
            f.pendingReview = false;
            f.pendingQuality = null;
          });
        }
      }
    });
  } catch (e) {
    console.warn('syncFlashcards failed (offline?):', e);
  }
}

/** Push any pending offline flashcard reviews to the server */
export async function pushPendingReviews(): Promise<void> {
  const col = db.get<FlashcardModel>('flashcards');
  const pending = await col.query().fetch().then((all) =>
    all.filter((f) => f.pendingReview && f.pendingQuality != null)
  );
  for (const fc of pending) {
    try {
      await progressApi.reviewFlashcard(fc.remoteId, fc.pendingQuality!);
      await db.write(async () => {
        await fc.update((f) => {
          f.pendingReview = false;
          f.pendingQuality = null;
        });
      });
    } catch {
      break; // stop on first network error — retry next time
    }
  }
}
