// CSRF token handling for the double-submit cookie scheme (see
// src/security/csrf.js). The backend still sets a kopilotti_csrf cookie,
// but this frontend runs on a different domain (Vercel) than the backend
// (Render) - document.cookie can never read a cookie set for a different
// domain, no matter its httpOnly/SameSite/Secure attributes. That's a
// same-origin restriction on *reading* cookies via JS, unrelated to
// SameSite's control over whether a cookie is *sent*. Found 2026-07-31: the
// original document.cookie-based implementation always returned null in
// production, so no request ever carried a valid X-CSRF-Token header once a
// device cookie already existed, and every such request was rejected.
//
// Fixed by capturing the token from a response header instead (see
// captureCsrfToken) - the backend echoes the current token on every
// response via CSRF_RESPONSE_HEADER_NAME, exposed cross-origin through
// Access-Control-Expose-Headers (server.js).
//
// A second bug found the same day, in this fix's own first version: state
// was kept in a plain module-level variable only, which resets to null on
// every page load - but the device cookie the CSRF check gates on persists
// for 365 days, so any returning visitor's very first request on a fresh
// page load still had no captured token and was rejected. localStorage (the
// frontend's OWN origin, no cross-origin restriction at all here) persists
// the token across page loads the same way the cookie was always meant to.
const STORAGE_KEY = 'kopilotti_csrf_token';

function readStoredToken() {
  try {
    return globalThis.localStorage?.getItem(STORAGE_KEY) ?? null;
  } catch (_error) {
    // Storage disabled/unavailable (e.g. Safari private mode edge cases) -
    // fall back to in-memory-only for this page load rather than throwing.
    return null;
  }
}

function writeStoredToken(token) {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, token);
  } catch (_error) {
    // Same fallback as above - the in-memory value below still works for
    // the rest of this page load even if persistence itself fails.
  }
}

let currentToken = readStoredToken();

export function getCsrfToken() {
  return currentToken;
}

export function captureCsrfToken(response) {
  const token = response.headers?.get?.('x-csrf-token-value');
  if (!token) return;
  currentToken = token;
  writeStoredToken(token);
}
