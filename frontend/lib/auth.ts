/**
 * Client-side JWT utilities — decode without library, no network call.
 * Used to check token expiry before deciding whether to validate with server.
 */

export interface JWTPayload {
  sub: string;
  exp: number;
  iat: number;
}

/** Decode JWT payload without verifying signature (client-side only). */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload as JWTPayload;
  } catch {
    return null;
  }
}

/** Returns true if the access token is valid AND not expiring within the next 5 minutes. */
export function isTokenFresh(token: string | null): boolean {
  if (!token) return false;
  const payload = decodeJWT(token);
  if (!payload?.exp) return false;
  const nowSec = Math.floor(Date.now() / 1000);
  return payload.exp > nowSec + 300; // 5-min buffer
}

/** Returns true if the token is expired (or missing). */
export function isTokenExpired(token: string | null): boolean {
  if (!token) return true;
  const payload = decodeJWT(token);
  if (!payload?.exp) return true;
  return payload.exp <= Math.floor(Date.now() / 1000);
}

/** Key for storing the last /auth/me validation timestamp. */
const LAST_ME_KEY = "mm_last_me_check";

/** Store the timestamp when /auth/me was last called successfully. */
export function markMeChecked() {
  try { sessionStorage.setItem(LAST_ME_KEY, Date.now().toString()); } catch {}
}

/** Returns true if /auth/me was successfully called within the last 10 minutes. */
export function wasMeCheckedRecently(): boolean {
  try {
    const ts = sessionStorage.getItem(LAST_ME_KEY);
    if (!ts) return false;
    return Date.now() - parseInt(ts) < 10 * 60 * 1000; // 10 minutes
  } catch { return false; }
}

/** Clear the me-check cache (on logout). */
export function clearMeCache() {
  try { sessionStorage.removeItem(LAST_ME_KEY); } catch {}
}
