/**
 * Lesson reader screen — renders lesson content blocks, marks completion, and inline MCQ quiz.
 */
import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { contentApi, progressApi } from '@/lib/api';

// ── MCQ types ────────────────────────────────────────────────────────────────

interface MCQOption { label: string; text: string; }
interface MCQQuestion {
  id: string;
  question: string;
  options: MCQOption[];
  explanation?: string;
  correct_option?: string;
  module_id: string;
}

// ── Inline Quiz Component ────────────────────────────────────────────────────

function InlineQuiz({ moduleId }: { moduleId: string }) {
  const [question, setQuestion] = useState<MCQQuestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<{ correct: boolean; explanation: string; correct_option: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [revealed, setRevealed] = useState(false);

  const fetchQuestion = async () => {
    setLoading(true);
    setSelected(null);
    setResult(null);
    setRevealed(false);
    try {
      const res = await contentApi.getMCQ(moduleId);
      const questions: MCQQuestion[] = res.data ?? [];
      if (questions.length > 0) {
        setQuestion(questions[Math.floor(Math.random() * questions.length)]);
      }
    } catch {}
    finally { setLoading(false); }
  };

  const handleSubmit = async () => {
    if (!selected || !question) return;
    setSubmitting(true);
    try {
      const res = await progressApi.answerMcq(question.id, selected);
      setResult({
        correct: res.data.correct,
        explanation: res.data.explanation ?? question.explanation ?? '',
        correct_option: res.data.correct_option ?? question.correct_option ?? '',
      });
      setRevealed(true);
    } catch {
      setRevealed(true);
    } finally {
      setSubmitting(false);
    }
  };

  if (!question && !loading) {
    return (
      <TouchableOpacity style={q.startBtn} onPress={fetchQuestion} activeOpacity={0.8}>
        <Text style={q.startBtnText}>📝 Practice Quiz</Text>
      </TouchableOpacity>
    );
  }

  if (loading) {
    return <ActivityIndicator style={{ marginVertical: 16 }} color={C.blue} />;
  }

  if (!question) return null;

  const optionStyle = (label: string) => {
    if (!revealed) {
      return selected === label ? q.optionSelected : q.option;
    }
    if (result?.correct_option === label) return q.optionCorrect;
    if (selected === label && !result?.correct) return q.optionWrong;
    return q.option;
  };

  return (
    <View style={q.container}>
      <Text style={q.title}>Practice Question</Text>
      <Text style={q.questionText}>{question.question}</Text>

      <View style={q.options}>
        {question.options.map((opt) => (
          <TouchableOpacity
            key={opt.label}
            style={optionStyle(opt.label)}
            onPress={() => !revealed && setSelected(opt.label)}
            activeOpacity={0.75}
            disabled={revealed}
          >
            <Text style={q.optionLabel}>{opt.label}.</Text>
            <Text style={q.optionText}>{opt.text}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {!revealed ? (
        <TouchableOpacity
          style={[q.submitBtn, !selected && q.submitDisabled]}
          onPress={handleSubmit}
          disabled={!selected || submitting}
          activeOpacity={0.8}
        >
          {submitting ? <ActivityIndicator color="#fff" /> : <Text style={q.submitText}>Submit Answer</Text>}
        </TouchableOpacity>
      ) : (
        <View>
          <View style={[q.feedback, result?.correct ? q.feedbackCorrect : q.feedbackWrong]}>
            <Text style={q.feedbackIcon}>{result?.correct ? '✓' : '✗'}</Text>
            <Text style={q.feedbackText}>{result?.correct ? 'Correct!' : 'Incorrect'}</Text>
          </View>
          {!!result?.explanation && (
            <Text style={q.explanation}>{result.explanation}</Text>
          )}
          <TouchableOpacity style={q.nextBtn} onPress={fetchQuestion} activeOpacity={0.8}>
            <Text style={q.nextBtnText}>Next Question →</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

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
  module_id?: string;
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

        {/* Inline quiz */}
        {lesson.module_id && (
          <InlineQuiz moduleId={lesson.module_id} />
        )}

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

// Quiz styles
const q = StyleSheet.create({
  container: { marginTop: 24, backgroundColor: C.surface, borderRadius: 12, padding: 16, borderWidth: 1, borderColor: C.border },
  title: { fontSize: 13, fontWeight: '700', color: C.ink2, marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 },
  questionText: { fontSize: 15, fontWeight: '600', color: C.ink, lineHeight: 22, marginBottom: 16 },
  options: { gap: 8, marginBottom: 16 },
  option: { flexDirection: 'row', gap: 10, borderWidth: 1, borderColor: C.border, borderRadius: 10, padding: 12, backgroundColor: '#FAFAF9' },
  optionSelected: { flexDirection: 'row', gap: 10, borderWidth: 2, borderColor: C.blue, borderRadius: 10, padding: 12, backgroundColor: '#EFF6FF' },
  optionCorrect: { flexDirection: 'row', gap: 10, borderWidth: 2, borderColor: C.green, borderRadius: 10, padding: 12, backgroundColor: '#F0FFF4' },
  optionWrong: { flexDirection: 'row', gap: 10, borderWidth: 2, borderColor: '#EF4444', borderRadius: 10, padding: 12, backgroundColor: '#FFF5F5' },
  optionLabel: { fontSize: 14, fontWeight: '700', color: C.ink2, minWidth: 18 },
  optionText: { flex: 1, fontSize: 14, color: C.ink, lineHeight: 20 },
  submitBtn: { backgroundColor: C.blue, borderRadius: 10, padding: 14, alignItems: 'center' },
  submitDisabled: { backgroundColor: C.ink2, opacity: 0.5 },
  submitText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  feedback: { flexDirection: 'row', gap: 8, alignItems: 'center', padding: 12, borderRadius: 10, marginBottom: 10 },
  feedbackCorrect: { backgroundColor: '#F0FFF4' },
  feedbackWrong: { backgroundColor: '#FFF5F5' },
  feedbackIcon: { fontSize: 18, fontWeight: '800' },
  feedbackText: { fontSize: 15, fontWeight: '700', color: C.ink },
  explanation: { fontSize: 13, color: C.ink2, lineHeight: 20, marginBottom: 14 },
  nextBtn: { borderWidth: 1, borderColor: C.border, borderRadius: 10, padding: 12, alignItems: 'center' },
  nextBtnText: { fontSize: 14, fontWeight: '600', color: C.blue },
  startBtn: { marginTop: 24, borderWidth: 1, borderColor: C.blue, borderRadius: 12, padding: 14, alignItems: 'center' },
  startBtnText: { fontSize: 14, fontWeight: '700', color: C.blue },
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
