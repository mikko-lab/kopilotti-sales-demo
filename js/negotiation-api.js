import { getCsrfToken, captureCsrfToken } from './csrf.js';

// Same registrable domain as the frontend (api.kopilotti.online /
// app.kopilotti.online) as of 2026-08-02 -- the kopilotti_device cookie
// (see resolve-device.js) is now same-site instead of cross-site, which is
// what actually fixes the third-party-cookie blocking (Safari ITP, Chrome +
// certain extensions, and the Storage Access API flakiness documented
// there) rather than anything about the cookie's own attributes.
const DEFAULT_BACKEND_URL = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
  ? 'http://localhost:3001'
  : 'https://api.kopilotti.online';

// basePath defaults to the always-on demo BFF; a Magic Link page passes
// `/api/n/{token}` instead (see src/http/magic-link-negotiation-routes.js) —
// same request shape, tenantId/vehicleId resolved server-side from the
// token rather than a hardcoded demo tenant. No fallback exists between the
// two: a page either constructs this class with a real token's basePath or
// doesn't, there is no code path here that silently switches to the demo
// basePath on failure.
const DEFAULT_BASE_PATH = '/api/digital-salesperson';

export class CustomerNegotiationApi {
  constructor({ backendUrl = DEFAULT_BACKEND_URL, basePath = DEFAULT_BASE_PATH, fetchImpl = globalThis.fetch.bind(globalThis), storage = globalThis.sessionStorage ?? null } = {}) {
    this.backendUrl = backendUrl;
    this.basePath = basePath;
    this.fetchImpl = fetchImpl;
    this.storage = storage;
    this.session = null;
  }

  getSessionId() { return this.session?.id || null; }

  async ensureSession(vehicleId) {
    if (this.session?.vehicleId === vehicleId && this.session.status === 'OPEN') return this.session;
    const storedSessionId = this.storage?.getItem(this.storageKey(vehicleId));
    let recovering = false;
    if (storedSessionId) {
      try {
        const restored = await this.request(`${this.basePath}/sessions/${encodeURIComponent(storedSessionId)}`, { method: 'GET' });
        if (restored.vehicleId === vehicleId && restored.status === 'OPEN') {
          this.session = restored;
          return restored;
        }
      } catch (_error) {
        // A stored session id existed but the restore-GET failed - reaching
        // this point at all means there WAS a previously-working session for
        // this browser, distinct from a genuine first-time visitor. Marked
        // purely from this client-side bookkeeping (never sent to the
        // server, never customerIdentityId) so the UI can frame the next
        // failure as "let's recover your negotiation" rather than "let's
        // start one".
        recovering = true;
        this.storage?.removeItem(this.storageKey(vehicleId));
      }
    }
    try {
      this.session = await this.request(`${this.basePath}/sessions`, {
        method: 'POST',
        body: JSON.stringify({ vehicleId }),
      });
    } catch (error) {
      if (recovering) error.recoveryContext = true;
      throw error;
    }
    this.storage?.setItem(this.storageKey(vehicleId), this.session.id);
    return this.session;
  }

  async discussPrice({ vehicleId, offerAmount, evidence }) {
    const session = await this.ensureSession(vehicleId);
    try {
      return await this.submitOffer(session, { offerAmount, evidence });
    } catch (error) {
      // The backend keeps in-flight negotiation sessions in process memory, so a
      // backend restart between opening the negotiation and submitting an offer
      // invalidates the session this tab already holds. Rather than surface that
      // as a customer-facing error, start a fresh session once and retry silently
      // — from the customer's side this restart is invisible.
      if (error.code !== 'SESSION_NOT_FOUND') throw error;
      this.clearSession(vehicleId);
      try {
        const freshSession = await this.ensureSession(vehicleId);
        return await this.submitOffer(freshSession, { offerAmount, evidence });
      } catch (retryError) {
        // Reaching this retry branch at all means a session that previously
        // worked just got rejected - always frame the resulting failure as
        // a recovery, not a first-time verification.
        retryError.recoveryContext = true;
        throw retryError;
      }
    }
  }

  async submitOffer(session, { offerAmount, evidence }) {
    const decision = await this.request(`${this.basePath}/sessions/${encodeURIComponent(session.id)}/offers`, {
      method: 'POST',
      body: JSON.stringify({
        offerAmount,
        currency: 'EUR',
        evidence,
        expectedVersion: session.version,
        commandId: crypto.randomUUID(),
      }),
    });
    this.session = { ...session, version: decision.sessionVersion, status: decision.sessionStatus };
    return decision;
  }

  clearSession(vehicleId) {
    this.session = null;
    this.storage?.removeItem(this.storageKey(vehicleId));
  }

  storageKey(vehicleId) { return `kopilotti.negotiation.${vehicleId}`; }

  async request(path, options) {
    const csrfToken = getCsrfToken();
    const response = await this.fetchImpl(`${this.backendUrl}${path}`, {
      ...options,
      // The device-identity cookie (see resolve-device.js) is set by a
      // different site (Render backend vs. Vercel frontend) - without
      // credentials: 'include', the browser neither sends this cookie nor
      // stores the backend's Set-Cookie response for it at all.
      credentials: 'include',
      // Absent on this browser's very first-ever request this page load (no
      // token captured yet, see csrf.js) - the backend's own check
      // (src/security/csrf.js) exempts exactly that bootstrap case, so
      // omitting the header here is correct, not a bug.
      headers: { 'Content-Type': 'application/json', ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}) },
    });
    captureCsrfToken(response);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body.error?.message || 'Palvelu ei ole juuri nyt käytettävissä');
      // Object.assign after code/message carries any structured extra
      // fields (e.g. NEGOTIATION_LOCKED's expiresAt) through onto the
      // thrown error without hardcoding each one here - the caller decides
      // what to do with them, this transport layer stays generic.
      Object.assign(error, body.error, { code: body.error?.code || 'SERVICE_UNAVAILABLE' });
      throw error;
    }
    return body;
  }
}
