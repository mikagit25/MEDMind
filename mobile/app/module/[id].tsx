/**
 * Module detail screen — shows lessons list for a given module.
 */
import { useEffect, useState } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { contentApi } from '@/lib/api';

interface Lesson {
  id: string;
  title: string;
  lesson_order: number;
  estimated_minutes: number;
  status: string;
}

interface ModuleDetail {
  id: string;
  title: string;
  description: string;
  is_fundamental: boolean;
  lesson_count: number;
  flashcard_count: number;
}

const C = {
  bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B',
  surface: '#FFFFFF', border: '#E8E3D9', blue: '#3B82F6', green: '#16A34A',
};

export default function ModuleDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [mod, setMod] = useState<ModuleDetail | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const [modRes, lessonsRes] = await Promise.all([
          contentApi.getModule(id),
          contentApi.getLessons(id),
        ]);
        setMod(modRes.data);
        const all: Lesson[] = lessonsRes.data ?? [];
        setLessons(all.sort((a, b) => a.lesson_order - b.lesson_order));
      } catch {}
      finally { setLoading(false); }
    })();
  }, [id]);

  if (loading) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <ActivityIndicator color={C.ink} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Text style={s.backText}>← Back</Text>
        </TouchableOpacity>
        <Text style={s.title}>{mod?.title ?? 'Module'}</Text>
        {mod?.description ? (
          <Text style={s.desc}>{mod.description}</Text>
        ) : null}
        <View style={s.metaRow}>
          <Text style={s.metaChip}>📖 {mod?.lesson_count ?? lessons.length} lessons</Text>
          <Text style={s.metaChip}>⚡ {mod?.flashcard_count ?? 0} cards</Text>
          {mod?.is_fundamental && (
            <View style={s.freeBadge}><Text style={s.freeText}>FREE</Text></View>
          )}
        </View>
      </View>

      {/* Lessons list */}
      <FlatList
        data={lessons}
        keyExtractor={(item) => item.id}
        contentContainerStyle={s.list}
        ListEmptyComponent={
          <Text style={s.empty}>No lessons available yet.</Text>
        }
        renderItem={({ item, index }) => (
          <TouchableOpacity
            style={s.lessonCard}
            onPress={() => router.push(`/lesson/${item.id}` as any)}
            activeOpacity={0.75}
          >
            <View style={s.lessonNum}>
              <Text style={s.lessonNumText}>{index + 1}</Text>
            </View>
            <View style={s.lessonInfo}>
              <Text style={s.lessonTitle}>{item.title}</Text>
              {item.estimated_minutes > 0 && (
                <Text style={s.lessonMeta}>⏱ {item.estimated_minutes} min</Text>
              )}
            </View>
            <Text style={s.chevron}>›</Text>
          </TouchableOpacity>
        )}
      />
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  center: { justifyContent: 'center', alignItems: 'center' },
  header: { padding: 16, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: C.border, backgroundColor: C.surface },
  backBtn: { marginBottom: 10 },
  backText: { fontSize: 14, color: C.blue, fontWeight: '600' },
  title: { fontSize: 20, fontWeight: '800', color: C.ink, marginBottom: 6 },
  desc: { fontSize: 13, color: C.ink2, lineHeight: 19, marginBottom: 10 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  metaChip: { fontSize: 12, color: C.ink2, fontWeight: '500' },
  freeBadge: { backgroundColor: '#F0FFF4', borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2 },
  freeText: { fontSize: 10, fontWeight: '800', color: C.green },
  list: { padding: 16, gap: 10 },
  empty: { textAlign: 'center', color: C.ink2, marginTop: 40, fontSize: 14 },
  lessonCard: {
    backgroundColor: C.surface, borderRadius: 12, padding: 14,
    flexDirection: 'row', alignItems: 'center', gap: 12,
    shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 6, elevation: 2,
  },
  lessonNum: {
    width: 32, height: 32, borderRadius: 16, backgroundColor: C.blue,
    alignItems: 'center', justifyContent: 'center',
  },
  lessonNumText: { color: '#fff', fontWeight: '700', fontSize: 13 },
  lessonInfo: { flex: 1 },
  lessonTitle: { fontSize: 14, fontWeight: '600', color: C.ink },
  lessonMeta: { fontSize: 12, color: C.ink2, marginTop: 2 },
  chevron: { fontSize: 18, color: C.ink2 },
});
