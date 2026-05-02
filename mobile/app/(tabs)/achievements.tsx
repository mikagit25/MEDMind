/**
 * F4: Achievements screen — badge grid with locked/unlocked state
 */
import { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet,
  ActivityIndicator, RefreshControl, TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { progressApi } from '@/lib/api';

interface Achievement {
  code: string;
  title: string;
  description: string;
  icon: string;
  xp: number;
  unlocked: boolean;
  earned_at?: string;
}

const COLORS = {
  bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B',
  surface: '#FFFFFF', border: '#E8E3D9',
  gold: '#F59E0B', locked: '#D1D5DB', blue: '#3B82F6',
};

// Local catalog — mirrors backend ACHIEVEMENT_META
const ACHIEVEMENT_CATALOG: Omit<Achievement, 'unlocked' | 'earned_at'>[] = [
  { code: 'first_lesson',       title: 'First Step',         description: 'Complete your first lesson',          icon: '🎯', xp: 50 },
  { code: 'streak_7',           title: 'Week Warrior',        description: '7-day study streak',                  icon: '🔥', xp: 100 },
  { code: 'streak_30',          title: 'Monthly Master',      description: '30-day study streak',                 icon: '🏅', xp: 500 },
  { code: 'flashcard_100',      title: 'Card Shark',          description: 'Review 100 flashcards',              icon: '🃏', xp: 200 },
  { code: 'flashcard_1000',     title: 'Memory Palace',       description: 'Review 1000 flashcards',             icon: '🧠', xp: 1000 },
  { code: 'mcq_perfect',        title: 'Perfect Score',       description: 'Answer 10 MCQs correctly in a row',  icon: '💯', xp: 150 },
  { code: 'level_5',            title: 'Rising Star',         description: 'Reach level 5',                      icon: '⭐', xp: 250 },
  { code: 'level_10',           title: 'Senior Resident',     description: 'Reach level 10',                     icon: '🌟', xp: 500 },
  { code: 'ai_conversations_10', title: 'AI Explorer',        description: 'Have 10 AI conversations',           icon: '🤖', xp: 100 },
  { code: 'module_complete',    title: 'Module Champion',     description: 'Complete a full module',             icon: '🏆', xp: 300 },
  { code: 'case_solved',        title: 'Case Closed',         description: 'Successfully discuss a clinical case', icon: '🔍', xp: 100 },
  { code: 'early_bird',         title: 'Early Bird',          description: 'Study before 7 AM',                  icon: '🌅', xp: 75 },
];

export default function AchievementsScreen() {
  const [unlocked, setUnlocked] = useState<Set<string>>(new Set());
  const [earnedDates, setEarnedDates] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const load = async () => {
    try {
      const res = await progressApi.getAchievements();
      const items: Array<{ achievement_code: string; earned_at: string }> = res.data ?? [];
      const codes = new Set(items.map((a) => a.achievement_code));
      const dates: Record<string, string> = {};
      items.forEach((a) => { dates[a.achievement_code] = a.earned_at; });
      setUnlocked(codes);
      setEarnedDates(dates);
    } catch (e) {
      console.warn('[Achievements] fetch error', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const onRefresh = () => { setRefreshing(true); load(); };

  const achievements: Achievement[] = ACHIEVEMENT_CATALOG.map((a) => ({
    ...a,
    unlocked: unlocked.has(a.code),
    earned_at: earnedDates[a.code],
  }));

  const unlockedCount = achievements.filter((a) => a.unlocked).length;

  if (loading) {
    return (
      <SafeAreaView style={[s.container, s.center]}>
        <ActivityIndicator color={COLORS.ink} />
      </SafeAreaView>
    );
  }

  const selectedAch = selected ? achievements.find((a) => a.code === selected) : null;

  return (
    <SafeAreaView style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.title}>🏅 Achievements</Text>
        <Text style={s.count}>{unlockedCount} / {achievements.length}</Text>
      </View>

      {/* Progress bar */}
      <View style={s.progressBar}>
        <View style={[s.progressFill, { width: `${(unlockedCount / achievements.length) * 100}%` as any }]} />
      </View>

      <ScrollView
        contentContainerStyle={s.grid}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {achievements.map((ach) => (
          <TouchableOpacity
            key={ach.code}
            style={[s.badge, ach.unlocked ? s.badgeUnlocked : s.badgeLocked]}
            onPress={() => setSelected(selected === ach.code ? null : ach.code)}
            activeOpacity={0.75}
          >
            <Text style={[s.badgeIcon, !ach.unlocked && s.iconLocked]}>
              {ach.unlocked ? ach.icon : '🔒'}
            </Text>
            <Text style={[s.badgeTitle, !ach.unlocked && s.textLocked]} numberOfLines={2}>
              {ach.unlocked ? ach.title : '???'}
            </Text>
            {ach.unlocked && (
              <Text style={s.badgeXP}>+{ach.xp} XP</Text>
            )}
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Detail panel — shows on tap */}
      {selectedAch && (
        <View style={s.detail}>
          <Text style={s.detailIcon}>{selectedAch.unlocked ? selectedAch.icon : '🔒'}</Text>
          <View style={s.detailText}>
            <Text style={s.detailTitle}>{selectedAch.title}</Text>
            <Text style={s.detailDesc}>{selectedAch.description}</Text>
            {selectedAch.unlocked && selectedAch.earned_at ? (
              <Text style={s.detailDate}>
                Earned {new Date(selectedAch.earned_at).toLocaleDateString()}
              </Text>
            ) : !selectedAch.unlocked ? (
              <Text style={s.detailLocked}>Not yet unlocked • +{selectedAch.xp} XP</Text>
            ) : null}
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  center: { justifyContent: 'center', alignItems: 'center' },
  header: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: COLORS.border },
  title: { fontSize: 20, fontWeight: '800', color: COLORS.ink },
  count: { fontSize: 13, fontWeight: '700', color: COLORS.ink2 },
  progressBar: { height: 4, backgroundColor: COLORS.border, marginHorizontal: 20, marginBottom: 16, borderRadius: 2 },
  progressFill: { height: 4, backgroundColor: COLORS.gold, borderRadius: 2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', padding: 12, gap: 10, paddingBottom: 40 },
  badge: { width: '30%', borderRadius: 14, padding: 12, alignItems: 'center', gap: 6, borderWidth: 1 },
  badgeUnlocked: { backgroundColor: COLORS.surface, borderColor: COLORS.gold },
  badgeLocked: { backgroundColor: '#F9FAFB', borderColor: COLORS.border },
  badgeIcon: { fontSize: 32 },
  iconLocked: { opacity: 0.4 },
  badgeTitle: { fontSize: 11, fontWeight: '700', color: COLORS.ink, textAlign: 'center' },
  textLocked: { color: COLORS.locked },
  badgeXP: { fontSize: 10, color: COLORS.gold, fontWeight: '700' },
  detail: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16, backgroundColor: COLORS.surface, borderTopWidth: 1, borderTopColor: COLORS.border },
  detailIcon: { fontSize: 36 },
  detailText: { flex: 1 },
  detailTitle: { fontSize: 15, fontWeight: '800', color: COLORS.ink },
  detailDesc: { fontSize: 13, color: COLORS.ink2, marginTop: 2 },
  detailDate: { fontSize: 11, color: COLORS.gold, marginTop: 4, fontWeight: '600' },
  detailLocked: { fontSize: 11, color: COLORS.locked, marginTop: 4, fontWeight: '600' },
});
