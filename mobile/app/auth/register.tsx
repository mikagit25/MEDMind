import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { useAuthStore } from '@/store/authStore';
import { authApi, storeTokens } from '@/lib/api';

const COLORS = { bg: '#F5F0E8', ink: '#1A1A1A', ink2: '#6B6B6B', surface: '#FFFFFF', border: '#E8E3D9', red: '#EF4444', green: '#22C55E' };

const ROLES = [
  { value: 'doctor', label: 'Doctor / Physician' },
  { value: 'student', label: 'Medical Student' },
  { value: 'nurse', label: 'Nurse' },
  { value: 'vet', label: 'Veterinarian' },
  { value: 'vet_student', label: 'Vet Student' },
  { value: 'paramedic', label: 'Paramedic / EMT' },
  { value: 'other', label: 'Other Healthcare' },
];

export default function RegisterScreen() {
  const { loadUser } = useAuthStore();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [consentTerms, setConsentTerms] = useState(false);
  const [consentData, setConsentData] = useState(false);
  const [showRolePicker, setShowRolePicker] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRegister = async () => {
    if (!firstName || !lastName || !email || !password) {
      setError('Please fill in all fields');
      return;
    }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    if (!consentTerms || !consentData) {
      setError('You must accept the required consents to proceed');
      return;
    }
    setLoading(true); setError('');
    try {
      const res = await authApi.register(
        email.trim().toLowerCase(),
        password,
        firstName.trim(),
        lastName.trim(),
        role,
        consentTerms,
        consentData,
      );
      await storeTokens(res.data.access_token, res.data.refresh_token);
      await loadUser();
      router.replace('/(tabs)/dashboard');
    } catch (e: any) {
      setError(e.response?.data?.detail ?? 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const selectedRole = ROLES.find((r) => r.value === role);

  return (
    <SafeAreaView style={s.container}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={s.flex}>
        <ScrollView contentContainerStyle={s.scroll} keyboardShouldPersistTaps="handled">
          <View style={s.logo}>
            <Text style={s.logoIcon}>🏥</Text>
            <Text style={s.logoTitle}>MedMind AI</Text>
          </View>

          <View style={s.card}>
            <Text style={s.cardTitle}>Create account</Text>

            {error ? <Text style={s.error}>{error}</Text> : null}

            <View style={s.row}>
              <View style={[s.field, s.flex]}>
                <Text style={s.label}>First Name</Text>
                <TextInput style={s.input} value={firstName} onChangeText={setFirstName} placeholder="Jane" placeholderTextColor={COLORS.ink2} autoCapitalize="words" />
              </View>
              <View style={[s.field, s.flex]}>
                <Text style={s.label}>Last Name</Text>
                <TextInput style={s.input} value={lastName} onChangeText={setLastName} placeholder="Smith" placeholderTextColor={COLORS.ink2} autoCapitalize="words" />
              </View>
            </View>

            <View style={s.field}>
              <Text style={s.label}>Email</Text>
              <TextInput style={s.input} value={email} onChangeText={setEmail} placeholder="you@example.com" placeholderTextColor={COLORS.ink2} autoCapitalize="none" keyboardType="email-address" />
            </View>

            <View style={s.field}>
              <Text style={s.label}>Password</Text>
              <TextInput style={s.input} value={password} onChangeText={setPassword} placeholder="Min. 8 characters" placeholderTextColor={COLORS.ink2} secureTextEntry />
            </View>

            <View style={s.field}>
              <Text style={s.label}>Role</Text>
              <TouchableOpacity style={s.roleBtn} onPress={() => setShowRolePicker((v) => !v)}>
                <Text style={s.roleBtnText}>{selectedRole?.label ?? 'Select role'}</Text>
                <Text style={s.roleChevron}>{showRolePicker ? '▲' : '▼'}</Text>
              </TouchableOpacity>
              {showRolePicker && (
                <View style={s.rolePicker}>
                  {ROLES.map((r) => (
                    <TouchableOpacity
                      key={r.value}
                      style={[s.roleOption, r.value === role && s.roleOptionSelected]}
                      onPress={() => { setRole(r.value); setShowRolePicker(false); }}
                    >
                      <Text style={[s.roleOptionText, r.value === role && s.roleOptionTextSelected]}>{r.label}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>

            <View style={s.consentsBox}>
              <TouchableOpacity style={s.checkRow} onPress={() => setConsentTerms((v) => !v)}>
                <View style={[s.checkbox, consentTerms && s.checkboxChecked]}>
                  {consentTerms && <Text style={s.checkmark}>✓</Text>}
                </View>
                <Text style={s.checkLabel}>
                  I accept the <Text style={s.bold}>Terms of Service</Text> and <Text style={s.bold}>Privacy Policy</Text>{' '}
                  <Text style={s.required}>*</Text>
                </Text>
              </TouchableOpacity>
              <TouchableOpacity style={s.checkRow} onPress={() => setConsentData((v) => !v)}>
                <View style={[s.checkbox, consentData && s.checkboxChecked]}>
                  {consentData && <Text style={s.checkmark}>✓</Text>}
                </View>
                <Text style={s.checkLabel}>
                  I consent to processing of personal data (GDPR) <Text style={s.required}>*</Text>
                </Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={[s.btn, loading && s.btnDisabled]} onPress={handleRegister} disabled={loading}>
              {loading ? <ActivityIndicator color="#FFF" /> : <Text style={s.btnText}>Create Account</Text>}
            </TouchableOpacity>

            <TouchableOpacity style={s.linkRow} onPress={() => router.push('/auth/login')}>
              <Text style={s.linkText}>Already have an account? <Text style={s.link}>Sign in</Text></Text>
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
  logo: { alignItems: 'center', marginBottom: 28 },
  logoIcon: { fontSize: 48, marginBottom: 6 },
  logoTitle: { fontSize: 24, fontWeight: '800', color: '#1A1A1A' },
  card: { backgroundColor: COLORS.surface, borderRadius: 20, padding: 24, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 16, elevation: 3 },
  cardTitle: { fontSize: 22, fontWeight: '800', color: COLORS.ink, marginBottom: 20 },
  error: { color: COLORS.red, fontSize: 13, marginBottom: 12, fontWeight: '500' },
  row: { flexDirection: 'row', gap: 10 },
  field: { marginBottom: 14 },
  label: { fontSize: 12, fontWeight: '700', color: COLORS.ink2, marginBottom: 6, letterSpacing: 0.5 },
  input: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, fontSize: 15, color: COLORS.ink, backgroundColor: COLORS.bg },
  roleBtn: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 11, backgroundColor: COLORS.bg },
  roleBtnText: { fontSize: 15, color: COLORS.ink },
  roleChevron: { fontSize: 12, color: COLORS.ink2 },
  rolePicker: { borderWidth: 1, borderColor: COLORS.border, borderRadius: 10, marginTop: 4, backgroundColor: COLORS.surface, overflow: 'hidden' },
  roleOption: { paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  roleOptionSelected: { backgroundColor: '#F0F0F0' },
  roleOptionText: { fontSize: 14, color: COLORS.ink },
  roleOptionTextSelected: { fontWeight: '700' },
  consentsBox: { marginBottom: 16, gap: 10 },
  checkRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  checkbox: { width: 20, height: 20, borderWidth: 1.5, borderColor: COLORS.border, borderRadius: 5, marginTop: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.bg },
  checkboxChecked: { backgroundColor: COLORS.ink, borderColor: COLORS.ink },
  checkmark: { color: '#FFF', fontSize: 12, fontWeight: '800' },
  checkLabel: { flex: 1, fontSize: 12, color: COLORS.ink2, lineHeight: 18 },
  bold: { fontWeight: '700', color: COLORS.ink },
  required: { color: COLORS.red },
  btn: { backgroundColor: COLORS.ink, borderRadius: 12, paddingVertical: 14, alignItems: 'center', marginTop: 8 },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: '#FFF', fontWeight: '800', fontSize: 15 },
  linkRow: { marginTop: 16, alignItems: 'center' },
  linkText: { fontSize: 13, color: COLORS.ink2 },
  link: { color: COLORS.ink, fontWeight: '700', textDecorationLine: 'underline' },
});
