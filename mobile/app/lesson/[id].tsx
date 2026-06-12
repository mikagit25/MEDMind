/**
 * Lesson reader screen — renders lesson content blocks and marks completion.
 */
import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { contentApi, progressApi } from '@/lib/api';

// ── Content block types ─────────────────────────────────────────────────────

interface Block {
  type: string;
  content?: string;
  items?: string[];
  level?: number;
  src?: string;
  caption?: string;
  data?: unknown;
}

interface LessonData {
  id: string;
  title: string;
  estimated_minutes: number;
  content: Block[];
  clinical_risk_level: string;
  requires_clinical_supervision: boolean;
  lay_summary?: string;
}

const C = {
  bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B',
  surface: '#FFFFFF', border: '#E8E3D9', blue: '#3B82F6',
  amber: '#D97706', green: '#16A34A', red: '#DC2626',
};

// ── Block renderers ──────────────────────────────────────────────────────────

function renderBlock(block: Block, index: number) {
  switch (block.type) {
    case 'h1':
      return <Text key={index} style={r.h1}>{block.content}</Text>;
    case 'h2':
      return <Text key={index} style={r.h2}>{block.content}</Text>;
    case 'h3':
      return <Text key={index} style={r.h3}>{block.content}</Text>;
    case 'p':
    case 'paragraph':
      return <Text key={index} style={r.p}>{block.content}</Text>;
    case 'ul':
    case 'list':
      return (
        <View key={index} style={r.list}>
          {(block.items ?? []).map((item, i) => (
            <View key={i} style={r.listItem}>
              <Text style={r.bullet}>•</Text>
              <Text style={r.listText}>{item}</Text>
            </View>
          ))}
        </View>
      );
    case 'ol':
      return (
        <View key={index} style={r.list}>
          {(block.items ?? []).map((item, i) => (
            <View key={i} style={r.listItem}>
              <Text style={r.bullet}>{i + 1}.</Text>
              <Text style={r.listText}>{item}</Text>
            </View>
          ))}
        </View>
      );
    case 'callout':
    case 'tip':
      return (
        <View key={index} style={r.callout}>
          <Text style={r.calloutIcon}>💡</Text>
          <Text style={r.calloutText}>{block.content}</Text>
        </View>
      );
    case 'warning':
      return (
        <View key={index} style={[r.callout, r.calloutWarn]}>
          <Text style={r.calloutIcon}>⚠️</Text>
          <Text style={r.calloutText}>{block.content}</Text>
        </View>
      );
    case 'table':
      return (
        <View key={index} style={r.tableNote}>
          <Text style={r.tableNoteText}>📊 Table — open on desktop for best view</Text>
        </View>
      );
    default:
      if (block.content) {
        return <Text key={index} style={r.p}>{block.content}</Text>;
      }
      return null;
  }
}

// ── Screen ───────────────────────────────────────────────────────────────────

export default function LessonReaderScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [lesson, setLesson] = useState<LessonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    if (!id) return;
    contentApi.getLesson(id)
      .then((res) => setLesson(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const handleComplete = useCallback(async () => {
    if (!id || completed) return;
    setCompleting(true);
    try {
      await progressApi.completeLesson(id);
      setCompleted(true);
    } catch {
      Alert.alert('Error', 'Could not mark lesson as complete. Check your connection.');
    } finally {
      setCompleting(false);
    }
  }, [id, completed]);

  if (loading) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <ActivityIndicator color={C.ink} />
      </SafeAreaView>
    );
  }

  if (!lesson) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <Text style={s.errorText}>Lesson not found.</Text>
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Text style={s.backText}>← Go back</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={s.container}>
      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
        {/* Nav */}
        <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
          <Text style={s.backText}>← Back</Text>
        </TouchableOpacity>

        {/* Lesson header */}
        <View style={s.lessonHeader}>
          <Text style={s.lessonTitle}>{lesson.title}</Text>
          <View style={s.headerMeta}>
            {lesson.estimated_minutes > 0 && (
              <Text style={s.metaChip}>⏱ {lesson.estimated_minutes} min</Text>
            )}
            {lesson.clinical_risk_level === 'high' && (
              <View style={s.riskBadge}>
                <Text style={s.riskText}>⚠️ HIGH RISK</Text>
              </View>
            )}
            {lesson.requires_clinical_supervision && (
              <View style={s.supervBadge}>
                <Text style={s.supervText}>👨‍⚕️ Supervision required</Text>
              </View>
            )}
          </View>
        </View>

        {/* Medical disclaimer */}
        <View style={s.disclaimer}>
          <Text style={s.disclaimerText}>
            This content is for educational purposes only and does not constitute medical advice.
            Always consult a qualified healthcare professional for clinical decisions.
          </Text>
        </View>

        {/* Content blocks */}
        <View style={s.content}>
          {(lesson.content ?? []).map((block, i) => renderBlock(block, i))}
        </View>

        {/* Lay summary (if available) */}
        {lesson.lay_summary && (
          <View style={s.laySummary}>
            <Text style={s.laySummaryTitle}>Plain-language summary</Text>
            <Text style={s.laySummaryText}>{lesson.lay_summary}</Text>
          </View>
        )}

        {/* Complete button */}
        <TouchableOpacity
          style={[s.completeBtn, completed && s.completeBtnDone]}
          onPress={handleComplete}
          disabled={completed || completing}
          activeOpacity={0.8}
        >
          {completing ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={s.completeBtnText}>
              {completed ? '✓ Completed' : 'Mark as complete'}
            </Text>
          )}
        </TouchableOpacity>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  center: { justifyContent: 'center', alignItems: 'center' },
  scroll: { padding: 16 },
  backBtn: { marginBottom: 12 },
  backText: { fontSize: 14, color: C.blue, fontWeight: '600' },
  errorText: { fontSize: 16, color: C.ink2, marginBottom: 16 },
  lessonHeader: { marginBottom: 12 },
  lessonTitle: { fontSize: 22, fontWeight: '800', color: C.ink, lineHeight: 28, marginBottom: 8 },
  headerMeta: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  metaChip: { fontSize: 12, color: C.ink2 },
  riskBadge: { backgroundColor: '#FEF2F2', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  riskText: { fontSize: 11, fontWeight: '700', color: C.red },
  supervBadge: { backgroundColor: '#FFFBEB', borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },
  supervText: { fontSize: 11, color: C.amber },
  disclaimer: {
    backgroundColor: '#FFF9E6', borderLeftWidth: 3, borderLeftColor: C.amber,
    borderRadius: 8, padding: 12, marginBottom: 20,
  },
  disclaimerText: { fontSize: 11, color: C.amber, lineHeight: 16 },
  content: { gap: 12, marginBottom: 24 },
  laySummary: {
    backgroundColor: C.surface, borderRadius: 12, padding: 16,
    borderWidth: 1, borderColor: C.border, marginBottom: 20,
  },
  laySummaryTitle: { fontSize: 13, fontWeight: '700', color: C.ink, marginBottom: 6 },
  laySummaryText: { fontSize: 13, color: C.ink2, lineHeight: 20 },
  completeBtn: {
    backgroundColor: C.blue, borderRadius: 12, padding: 16,
    alignItems: 'center', marginTop: 8,
  },
  completeBtnDone: { backgroundColor: C.green },
  completeBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});

// Block-level styles separated for clarity
const r = StyleSheet.create({
  h1: { fontSize: 20, fontWeight: '800', color: C.ink, marginBottom: 4, marginTop: 8 },
  h2: { fontSize: 17, fontWeight: '700', color: C.ink, marginBottom: 4, marginTop: 6 },
  h3: { fontSize: 15, fontWeight: '700', color: C.ink, marginBottom: 2, marginTop: 4 },
  p: { fontSize: 14, color: C.ink, lineHeight: 22 },
  list: { gap: 6 },
  listItem: { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  bullet: { fontSize: 14, color: C.ink2, minWidth: 16 },
  listText: { flex: 1, fontSize: 14, color: C.ink, lineHeight: 20 },
  callout: {
    backgroundColor: '#EFF6FF', borderRadius: 8, padding: 12,
    flexDirection: 'row', gap: 8, alignItems: 'flex-start',
  },
  calloutWarn: { backgroundColor: '#FFFBEB' },
  calloutIcon: { fontSize: 16 },
  calloutText: { flex: 1, fontSize: 13, color: C.ink, lineHeight: 19 },
  tableNote: {
    backgroundColor: C.surface, borderRadius: 8, padding: 12,
    borderWidth: 1, borderColor: C.border, alignItems: 'center',
  },
  tableNoteText: { fontSize: 12, color: C.ink2 },
});
