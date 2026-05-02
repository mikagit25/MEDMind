import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuthStore } from '@/store/authStore';

const COLORS = { bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B', surface: '#FFFFFF', border: '#E8E3D9', red: '#EF4444' };

export default function LoginScreen() {
  const { login } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!email || !password) { setError('Please fill in all fields'); return; }
    setLoading(true); setError('');
    try {
      await login(email.trim().toLowerCase(), password);
      router.replace('/(tabs)/dashboard');
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={s.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.flex}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <View style={s.logo}>
            <Text style={s.logoIcon}>🏥</Text>
            <Text style={s.logoTitle}>MedMind AI</Text>
            <Text style={s.logoSub}>Medical education, reimagined</Text>
          </View>

          <View style={s.card}>
            <Text style={s.cardTitle}>Sign in</Text>

            {error ? <Text style={s.error}>{error}</Text> : null}

            <View style={s.field}>
              <Text style={s.label}>Email</Text>
              <TextInput
                style={s.input}
                value={email}
                onChangeText={setEmail}
                placeholder="you@example.com"
                placeholderTextColor={COLORS.ink2}
                autoCapitalize="none"
                keyboardType="email-address"
                autoComplete="email"
              />
            </View>

            <View style={s.field}>
              <Text style={s.label}>Password</Text>
              <TextInput
                style={s.input}
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                placeholderTextColor={COLORS.ink2}
                secureTextEntry
                autoComplete="password"
              />
            </View>

            <TouchableOpacity
              style={[s.btn, loading && s.btnDisabled]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#FFF" />
              ) : (
                <Text style={s.btnText}>Sign In</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity style={s.linkRow} onPress={() => router.push('/auth/register')}>
              <Text style={s.linkText}>Don't have an account? <Text style={s.link}>Sign up</Text></Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, padding: 24, justifyContent: 'center' },
  logo: { alignItems: 'center', marginBottom: 32 },
  logoIcon: { fontSize: 56, marginBottom: 8 },
  logoTitle: { fontSize: 28, fontWeight: '800', color: COLORS.ink },
  logoSub: { fontSize: 14, color: COLORS.ink2, marginTop: 4 },
  card: { backgroundColor: COLORS.surface, borderRadius: 20, padding: 24, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 16, elevation: 3 },
  cardTitle: { fontSize: 22, fontWeight: '800', color: COLORS.ink, marginBottom: 20 },
  error: { color: COLORS.red, fontSize: 13, marginBottom: 12, fontWeight: '500' },
  field: { marginBottom: 16 },
  label: { fontSize: 12, fontWeight: '700', color: COLORS.ink2, marginBottom: 6, letterSpacing: 0.5 },
  input: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, fontSize: 15, color: COLORS.ink, backgroundColor: COLORS.bg },
  btn: { backgroundColor: COLORS.ink, borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#FFF', fontWeight: '800', fontSize: 15 },
  linkRow: { marginTop: 16, alignItems: 'center' },
  linkText: { fontSize: 13, color: COLORS.ink2 },
  link: { color: COLORS.ink, fontWeight: '700', textDecorationLine: 'underline' },
});
