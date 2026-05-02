/**
 * F3: Leaderboard screen — weekly/monthly/all-time rankings
 */
import { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { progressApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

type Period = 'week' | 'month' | 'all';

interface LeaderboardEntry {
  rank: number;
  user_id: string;
  display_name: string;
  xp: number;
  level: number;
  is_me: boolean;
}

interface LeaderboardData {
  period: Period;
  entries: LeaderboardEntry[];
  my_rank: number | null;
}

const COLORS = {
  bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B',
  surface: '#FFFFFF', border: '#E8E3D9',
  gold: '#F59E0B', silver: '#94A3B8', bronze: '#B45309',
  blue: '#3B82F6', meHighlight: '#EFF6FF',
};

const PERIOD_LABELS: Record<Period, string> = {
  week: 'This Week',
  month: 'This Month',
  all: 'All Time',
};

const RANK_MEDALS: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' };

export default function LeaderboardScreen() {
  const { user } = useAuthStore();
  const [period, setPeriod] = useState<Period>('week');
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (p: Period) => {
    try {
      const res = await progressApi.getLeaderboard(p, 50);
      setData(res.data);
    } catch (e) {
      console.warn('[Leaderboard] fetch error', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    load(period);
  }, [period, load]);

  const onRefresh = () => {
    setRefreshing(true);
    load(period);
  };

  const switchPeriod = (p: Period) => {
    if (p === period) return;
    setData(null);
    setLoading(true);
    setPeriod(p);
  };

  return (
    <SafeAreaView style={s.container}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.title}>🏆 Leaderboard</Text>
        {data?.my_rank != null && (
          <Text style={s.myRank}>Your rank: #{data.my_rank}</Text>
        )}
      </View>

      {/* Period selector */}
      <View style={s.periodRow}>
        {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
          <TouchableOpacity
            key={p}
            style={[s.periodBtn, period === p && s.periodBtnActive]}
            onPress={() => switchPeriod(p)}
          >
            <Text style={[s.periodLabel, period === p && s.periodLabelActive]}>
              {PERIOD_LABELS[p]}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={s.center}>
          <ActivityIndicator color={COLORS.ink} />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={s.list}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
          {(data?.entries ?? []).length === 0 ? (
            <View style={s.empty}>
              <Text style={s.emptyIcon}>📊</Text>
              <Text style={s.emptyText}>No data for this period yet.</Text>
            </View>
          ) : (
            (data?.entries ?? []).map((entry) => (
              <LeaderboardRow key={entry.user_id} entry={entry} />
            ))
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}

function LeaderboardRow({ entry }: { entry: LeaderboardEntry }) {
  const medal = RANK_MEDALS[entry.rank];
  const rankColor =
    entry.rank === 1 ? COLORS.gold :
    entry.rank === 2 ? COLORS.silver :
    entry.rank === 3 ? COLORS.bronze : COLORS.ink2;

  return (
    <View style={[s.row, entry.is_me && s.rowMe]}>
      {/* Rank */}
      <View style={s.rankBox}>
        {medal ? (
          <Text style={s.medal}>{medal}</Text>
        ) : (
          <Text style={[s.rankNum, { color: rankColor }]}>#{entry.rank}</Text>
        )}
      </View>

      {/* Avatar placeholder */}
      <View style={[s.avatar, entry.is_me && s.avatarMe]}>
        <Text style={s.avatarText}>
          {(entry.display_name?.[0] ?? '?').toUpperCase()}
        </Text>
      </View>

      {/* Name + level */}
      <View style={s.nameBox}>
        <Text style={[s.name, entry.is_me && s.nameMe]} numberOfLines={1}>
          {entry.display_name}{entry.is_me ? ' (You)' : ''}
        </Text>
        <Text style={s.level}>Level {entry.level}</Text>
      </View>

      {/* XP */}
      <Text style={s.xp}>{fmtXP(entry.xp)} XP</Text>
    </View>
  );
}

function fmtXP(xp: number): string {
  if (xp >= 1000) return `${(xp / 1000).toFixed(1)}k`;
  return String(xp);
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: COLORS.border },
  title: { fontSize: 20, fontWeight: '800', color: COLORS.ink },
  myRank: { fontSize: 13, fontWeight: '700', color: COLORS.blue },
  periodRow: { flexDirection: 'row', padding: 12, gap: 8 },
  periodBtn: { flex: 1, paddingVertical: 8, borderRadius: 20, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, alignItems: 'center' },
  periodBtnActive: { backgroundColor: COLORS.ink, borderColor: COLORS.ink },
  periodLabel: { fontSize: 12, fontWeight: '600', color: COLORS.ink2 },
  periodLabelActive: { color: '#FFF' },
  list: { paddingHorizontal: 16, paddingBottom: 40 },
  row: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.surface, borderRadius: 12, marginBottom: 8, padding: 12, gap: 10, borderWidth: 1, borderColor: COLORS.border },
  rowMe: { backgroundColor: COLORS.meHighlight, borderColor: COLORS.blue },
  rankBox: { width: 36, alignItems: 'center' },
  medal: { fontSize: 22 },
  rankNum: { fontSize: 14, fontWeight: '700' },
  avatar: { width: 40, height: 40, borderRadius: 20, backgroundColor: COLORS.ink, justifyContent: 'center', alignItems: 'center' },
  avatarMe: { backgroundColor: COLORS.blue },
  avatarText: { color: '#FFF', fontWeight: '800', fontSize: 16 },
  nameBox: { flex: 1 },
  name: { fontSize: 14, fontWeight: '700', color: COLORS.ink },
  nameMe: { color: COLORS.blue },
  level: { fontSize: 11, color: COLORS.ink2, marginTop: 1 },
  xp: { fontSize: 13, fontWeight: '700', color: COLORS.ink },
  empty: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 14, color: COLORS.ink2 },
});
