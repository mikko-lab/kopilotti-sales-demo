import { getCsrfToken, captureCsrfToken } from './csrf.js';

// See negotiation-api.js for why this moved off onrender.com (2026-08-02
// same-registrable-domain migration).
const DEFAULT_BACKEND_URL = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
  ? 'http://localhost:3001'
  : 'https://api.kopilotti.online';

// See negotiation-api.js's own DEFAULT_BASE_PATH comment — a Magic Link
// page passes `/api/n/{token}` instead, no fallback between the two.
const DEFAULT_BASE_PATH = '/api/digital-salesperson';

export class EmailVerificationApi {
  constructor({ backendUrl = DEFAULT_BACKEND_URL, basePath = DEFAULT_BASE_PATH, fetchImpl = globalThis.fetch.bind(globalThis) } = {}) {
    this.backendUrl = backendUrl;
    this.basePath = basePath;
    this.fetchImpl = fetchImpl;
  }

  requestCode(email) {
    return this.request(`${this.basePath}/email/request-code`, { method: 'POST', body: JSON.stringify({ email }) });
  }

  verifyCode(email, code) {
    return this.request(`${this.basePath}/email/verify-code`, { method: 'POST', body: JSON.stringify({ email, code }) });
  }

  async request(path, options) {
    const csrfToken = getCsrfToken();
    const response = await this.fetchImpl(`${this.backendUrl}${path}`, {
      ...options,
      // See the matching comment in negotiation-api.js: the device-identity
      // cookie is cross-site (Render backend vs. Vercel frontend) and needs
      // this to be sent/stored at all.
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}) },
    });
    captureCsrfToken(response);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(body.error?.message || 'Palvelu ei ole juuri nyt käytettävissä');
      Object.assign(error, body.error, { code: body.error?.code || 'SERVICE_UNAVAILABLE' });
      throw error;
    }
    return body;
  }
}
