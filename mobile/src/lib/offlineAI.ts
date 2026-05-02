/**
 * F2: Offline AI stub — returns a helpful fallback when the device is offline.
 *
 * When `route_ai_request` fails due to network error, the mobile app calls
 * `getOfflineAIResponse()` instead of crashing or showing a raw error.
 *
 * Strategy:
 *  - Check a small set of keyword-matched offline answers stored locally.
 *  - If no keyword matches, return a generic "you're offline" message.
 *  - Queue the original question for retry when connectivity returns.
 */
import NetInfo from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';

const OFFLINE_QUEUE_KEY = 'medmind_offline_ai_queue';

interface OfflineAIMessage {
  message: string;
  specialty: string;
  mode: string;
  timestamp: number;
}

// ── Offline keyword → canned answer map ────────────────────────────────────
// Keep this small — it's just a fallback, not a replacement for the API.
const CANNED_RESPONSES: Array<{ keywords: RegExp; answer: string }> = [
  {
    keywords: /\b(mi|myocardial infarction|heart attack|chest pain|stemi|nstemi)\b/i,
    answer:
      'Myocardial infarction (MI) is caused by sudden blockage of a coronary artery (usually atherosclerotic plaque rupture + thrombus). Key: MONA mnemonic (Morphine, Oxygen, Nitrates, Aspirin); call STEMI → primary PCI within 90 min. ⚠️ You are currently offline — connect to get a full AI response.',
  },
  {
    keywords: /\b(hypertension|high blood pressure|antihypertensive)\b/i,
    answer:
      'Hypertension thresholds: ≥130/80 mmHg (ACC/AHA 2017). First-line: ACE inhibitors/ARBs (especially in CKD/diabetes), CCBs, thiazide diuretics. Avoid beta-blockers as first-line unless heart failure or angina. ⚠️ You are offline — connect for a detailed AI response.',
  },
  {
    keywords: /\b(sepsis|septic shock|qsofa|sofa)\b/i,
    answer:
      'Sepsis-3 definition: life-threatening organ dysfunction caused by dysregulated host response to infection. qSOFA: ≥2 of (RR≥22, altered mentation, SBP≤100). Management: "1-hour bundle" — blood cultures → broad-spectrum antibiotics → 30 mL/kg IV crystalloid → vasopressors if needed. ⚠️ You are offline.',
  },
  {
    keywords: /\b(diabetes|insulin|hba1c|metformin|t2dm|t1dm)\b/i,
    answer:
      'Type 2 DM first-line: Metformin (if eGFR >30). Add SGLT2i (cardioprotective, renoprotective) or GLP-1 RA if ASCVD risk. Target HbA1c <7% for most patients. ⚠️ You are offline — connect for personalised AI guidance.',
  },
  {
    keywords: /\b(antibiotic|penicillin|amoxicillin|cephalosporin|vancomycin)\b/i,
    answer:
      'Antibiotic choice depends on suspected organism, site, local resistance patterns, and allergy history. Consult your local antibiogram. Empirical community pneumonia: Amoxicillin ± macrolide. MRSA: Vancomycin or linezolid. ⚠️ You are offline — connect for full AI guidance.',
  },
];

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Returns true when there is no network connection.
 */
export async function isOffline(): Promise<boolean> {
  const state = await NetInfo.fetch();
  return !state.isConnected;
}

/**
 * Returns an offline AI response for the given message.
 * Saves the original question to the offline queue for later retry.
 */
export async function getOfflineAIResponse(
  message: string,
  specialty: string,
  mode: string
): Promise<{ reply: string; fromCache: boolean }> {
  // Queue for retry
  await _enqueueOfflineMessage({ message, specialty, mode, timestamp: Date.now() });

  // Try keyword match
  for (const entry of CANNED_RESPONSES) {
    if (entry.keywords.test(message)) {
      return { reply: entry.answer, fromCache: false };
    }
  }

  // Generic fallback
  return {
    reply:
      `You appear to be offline. Your question about "${message.slice(0, 60)}${message.length > 60 ? '…' : ''}" has been saved and will be answered when you reconnect. In the meantime, you can review your flashcards offline.`,
    fromCache: false,
  };
}

/**
 * Returns all queued offline messages (to re-send when online).
 */
export async function getOfflineQueue(): Promise<OfflineAIMessage[]> {
  try {
    const raw = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
    return raw ? (JSON.parse(raw) as OfflineAIMessage[]) : [];
  } catch {
    return [];
  }
}

/**
 * Clears the offline queue (call after successfully re-sending).
 */
export async function clearOfflineQueue(): Promise<void> {
  await AsyncStorage.removeItem(OFFLINE_QUEUE_KEY);
}

// ── Internal helpers ──────────────────────────────────────────────────────────

async function _enqueueOfflineMessage(msg: OfflineAIMessage): Promise<void> {
  try {
    const queue = await getOfflineQueue();
    // Avoid duplicate consecutive messages
    const last = queue[queue.length - 1];
    if (last && last.message === msg.message) return;
    queue.push(msg);
    // Keep at most 50 messages
    const trimmed = queue.slice(-50);
    await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(trimmed));
  } catch {
    // Non-fatal
  }
}
