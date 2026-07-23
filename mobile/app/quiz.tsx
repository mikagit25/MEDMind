/**
 * Mobile Quiz screen — pick a specialty, then answer MCQs with immediate feedback.
 * Accessed via the dashboard quick actions grid.
 */
import { useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  ActivityIndicator, SafeAreaView as RNSafeArea,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { contentApi, progressApi } from '@/lib/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Specialty { id: string; name: string; icon: string; }
interface Module { id: string; title: string; }
interface MCQOption { label: string; text: string; }
interface Question {
  id: string;
  question: string;
  options: MCQOption[];
  explanation?: string;
  correct_option?: string;
}
interface AnswerResult {
  correct: boolean;
  explanation: string;
  correct_option: string;
}

type Phase = 'pick_specialty' | 'loading' | 'quiz' | 'done';

const C = {
  bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B',
  surface: '#FFFFFF', border: '#E8E3D9',
  blue: '#3B82F6', green: '#16A34A', red: '#DC2626', amber: '#D97706',
};

// ── Main screen ───────────────────────────────────────────────────────────────

export default function QuizScreen() {
  const [phase, setPhase] = useState<Phase>('pick_specialty');
  const [specialties, setSpecialties] = useState<Specialty[]>([]);
  const [specialtyName, setSpecialtyName] = useState('');
  const [questions, setQuestions] = useState<Question[]>([]);
  const [idx, setIdx] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [score, setScore] = useState(0);
  const [loadingSpecialties, setLoadingSpecialties] = useState(false);

  // Load specialties on first render
  const loadSpecialties = useCallback(async () => {
    if (specialties.length > 0) return;
    setLoadingSpecialties(true);
    try {
      const res = await contentApi.getSpecialties();
      setSpecialties(res.data ?? []);
    } catch {}
    finally { setLoadingSpecialties(false); }
  }, [specialties.length]);

  useState(() => { loadSpecialties(); });

  const pickSpecialty = async (spec: Specialty) => {
    setSpecialtyName(spec.name);
    setPhase('loading');
    try {
      // Load modules for this specialty, then grab MCQs from first available
      const modsRes = await contentApi.getModules(spec.id);
      const mods: Module[] = modsRes.data ?? [];
      const allQs: Question[] = [];
      for (const mod of mods.slice(0, 5)) {
        try {
          const qRes = await contentApi.getMCQ(mod.id);
          const qs: Question[] = qRes.data ?? [];
          allQs.push(...qs);
          if (allQs.length >= 10) break;
        } catch {}
      }
      // Shuffle and take up to 10
      const shuffled = allQs.sort(() => Math.random() - 0.5).slice(0, 10);
      if (shuffled.length === 0) {
        setPhase('pick_specialty');
        return;
      }
      setQuestions(shuffled);
      setIdx(0);
      setScore(0);
      setSelected(null);
      setResult(null);
      setRevealed(false);
      setPhase('quiz');
    } catch {
      setPhase('pick_specialty');
    }
  };

  const handleSubmit = async () => {
    const q = questions[idx];
    if (!selected || !q) return;
    setSubmitting(true);
    try {
      const res = await progressApi.answerMCQ(q.id, selected);
      const correct = res.data.correct as boolean;
      if (correct) setScore((s) => s + 1);
      setResult({
        correct,
        explanation: res.data.explanation ?? q.explanation ?? '',
        correct_option: res.data.correct_option ?? q.correct_option ?? '',
      });
      setRevealed(true);
    } catch {
      setRevealed(true);
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => {
    if (idx + 1 >= questions.length) {
      setPhase('done');
    } else {
      setIdx((i) => i + 1);
      setSelected(null);
      setResult(null);
      setRevealed(false);
    }
  };

  // ── Phase: pick specialty ────────────────────────────────────────────────────
  if (phase === 'pick_specialty') {
    return (
      <SafeAreaView style={s.container}>
        <View style={s.header}>
          <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
            <Text style={s.backText}>← Back</Text>
          </TouchableOpacity>
          <Text style={s.title}>📝 Quick Quiz</Text>
          <Text style={s.subtitle}>Pick a specialty to test your knowledge</Text>
        </View>
        <ScrollView contentContainerStyle={s.list}>
          {loadingSpecialties ? (
            <ActivityIndicator color={C.blue} style={{ marginTop: 40 }} />
          ) : (
            specialties.map((spec) => (
              <TouchableOpacity
                key={spec.id}
                style={s.specCard}
                onPress={() => pickSpecialty(spec)}
                activeOpacity={0.75}
              >
                <Text style={s.specIcon}>{spec.icon || '📚'}</Text>
                <Text style={s.specName}>{spec.name}</Text>
                <Text style={s.specArrow}>›</Text>
              </TouchableOpacity>
            ))
          )}
        </ScrollView>
      </SafeAreaView>
    );
  }

  // ── Phase: loading ────────────────────────────────────────────────────────────
  if (phase === 'loading') {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <ActivityIndicator color={C.blue} size="large" />
        <Text style={[s.subtitle, { marginTop: 16 }]}>Loading questions…</Text>
      </SafeAreaView>
    );
  }

  // ── Phase: done ───────────────────────────────────────────────────────────────
  if (phase === 'done') {
    const pct = Math.round((score / questions.length) * 100);
    const colour = pct >= 75 ? C.green : pct >= 50 ? C.amber : C.red;
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <Text style={{ fontSize: 56, marginBottom: 12 }}>
          {pct >= 75 ? '🏆' : pct >= 50 ? '👍' : '📚'}
        </Text>
        <Text style={[s.score, { color: colour }]}>{pct}%</Text>
        <Text style={s.scoreLabel}>{score} / {questions.length} correct</Text>
        <Text style={s.subtitle}>{specialtyName}</Text>
        <TouchableOpacity
          style={[s.submitBtn, { marginTop: 32 }]}
          onPress={() => setPhase('pick_specialty')}
          activeOpacity={0.8}
        >
          <Text style={s.submitText}>Try another specialty</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[s.backBtn, { marginTop: 16 }]}
          onPress={() => router.back()}
        >
          <Text style={s.backText}>← Back to dashboard</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // ── Phase: quiz ───────────────────────────────────────────────────────────────
  const q = questions[idx];
  if (!q) return null;

  const optionStyle = (label: string) => {
    if (!revealed) return selected === label ? s.optionSelected : s.option;
    if (result?.correct_option === label) return s.optionCorrect;
    if (selected === label && !result?.correct) return s.optionWrong;
    return s.option;
  };

  return (
    <SafeAreaView style={s.container}>
      {/* Progress */}
      <View style={s.progressBar}>
        <View
          style={[
            s.progressFill,
            { width: `${((idx + 1) / questions.length) * 100}%` as any },
          ]}
        />
      </View>

      <ScrollView contentContainerStyle={s.quizScroll}>
        <View style={s.quizHeader}>
          <TouchableOpacity onPress={() => router.back()} style={s.backBtn}>
            <Text style={s.backText}>← Quit</Text>
          </TouchableOpacity>
          <Text style={s.counter}>{idx + 1} / {questions.length} • {specialtyName}</Text>
        </View>

        <Text style={s.questionText}>{q.question}</Text>

        <View style={s.options}>
          {q.options.map((opt) => (
            <TouchableOpacity
              key={opt.label}
              style={optionStyle(opt.label)}
              onPress={() => !revealed && setSelected(opt.label)}
              activeOpacity={0.75}
              disabled={revealed}
            >
              <Text style={s.optionLabel}>{opt.label}.</Text>
              <Text style={s.optionText}>{opt.text}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {!revealed ? (
          <TouchableOpacity
            style={[s.submitBtn, !selected && s.submitDisabled]}
            onPress={handleSubmit}
            disabled={!selected || submitting}
            activeOpacity={0.8}
          >
            {submitting ? <ActivityIndicator color="#fff" /> : <Text style={s.submitText}>Submit</Text>}
          </TouchableOpacity>
        ) : (
          <View>
            <View style={[s.feedback, result?.correct ? s.feedbackOk : s.feedbackErr]}>
              <Text style={s.feedbackIcon}>{result?.correct ? '✓' : '✗'}</Text>
              <Text style={s.feedbackText}>{result?.correct ? 'Correct!' : 'Incorrect'}</Text>
            </View>
            {!!result?.explanation && (
              <Text style={s.explanation}>{result.explanation}</Text>
            )}
            <TouchableOpacity style={s.nextBtn} onPress={next} activeOpacity={0.8}>
              <Text style={s.nextText}>
                {idx + 1 >= questions.length ? 'See results →' : 'Next →'}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  center: { justifyContent: 'center', alignItems: 'center', padding: 24 },
  header: { padding: 20, paddingBottom: 12 },
  backBtn: { marginBottom: 8 },
  backText: { fontSize: 14, color: C.blue, fontWeight: '600' },
  title: { fontSize: 24, fontWeight: '800', color: C.ink, marginBottom: 4 },
  subtitle: { fontSize: 13, color: C.ink2 },
  list: { padding: 16, gap: 10 },
  specCard: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: C.surface, borderRadius: 12,
    padding: 16, borderWidth: 1, borderColor: C.border,
  },
  specIcon: { fontSize: 22, marginRight: 12 },
  specName: { flex: 1, fontSize: 15, fontWeight: '600', color: C.ink },
  specArrow: { fontSize: 20, color: C.ink2 },
  progressBar: { height: 3, backgroundColor: C.border },
  progressFill: { height: 3, backgroundColor: C.blue },
  quizScroll: { padding: 20 },
  quizHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  counter: { fontSize: 12, color: C.ink2, fontWeight: '600' },
  questionText: { fontSize: 16, fontWeight: '600', color: C.ink, lineHeight: 24, marginBottom: 20 },
  options: { gap: 10, marginBottom: 20 },
  option: { flexDirection: 'row', gap: 10, borderWidth: 1, borderColor: C.border, borderRadius: 10, padding: 14, backgroundColor: '#FAFAF9' },
  optionSelected: { flexDirection: 'row', gap: 10, borderWidth: 2, borderColor: C.blue, borderRadius: 10, padding: 14, backgroundColor: '#EFF6FF' },
  optionCorrect: { flexDirection: 'row', gap: 10, borderWidth: 2, borderColor: C.green, borderRadius: 10, padding: 14, backgroundColor: '#F0FFF4' },
  optionWrong: { flexDirection: 'row', gap: 10, borderWidth: 2, borderColor: C.red, borderRadius: 10, padding: 14, backgroundColor: '#FFF5F5' },
  optionLabel: { fontSize: 14, fontWeight: '700', color: C.ink2, minWidth: 20 },
  optionText: { flex: 1, fontSize: 14, color: C.ink, lineHeight: 20 },
  submitBtn: { backgroundColor: C.blue, borderRadius: 12, padding: 16, alignItems: 'center' },
  submitDisabled: { backgroundColor: C.ink2, opacity: 0.4 },
  submitText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  feedback: { flexDirection: 'row', gap: 8, alignItems: 'center', padding: 14, borderRadius: 10, marginBottom: 12 },
  feedbackOk: { backgroundColor: '#F0FFF4' },
  feedbackErr: { backgroundColor: '#FFF5F5' },
  feedbackIcon: { fontSize: 20, fontWeight: '800' },
  feedbackText: { fontSize: 16, fontWeight: '700', color: C.ink },
  explanation: { fontSize: 13, color: C.ink2, lineHeight: 20, marginBottom: 16 },
  nextBtn: { borderWidth: 1, borderColor: C.blue, borderRadius: 12, padding: 14, alignItems: 'center' },
  nextText: { fontSize: 15, fontWeight: '700', color: C.blue },
  score: { fontSize: 64, fontWeight: '900', marginBottom: 4 },
  scoreLabel: { fontSize: 18, fontWeight: '600', color: C.ink, marginBottom: 4 },
});
