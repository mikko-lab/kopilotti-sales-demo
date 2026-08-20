// Pure display formatting only - never computes or estimates a lock's
// expiry itself. expiresAt always comes from the backend (see
// src/domain/negotiation-lock-expiry.js); this only turns that ISO string
// into the Finnish, Europe/Helsinki phrasing customers see (§12 of the
// feature spec: "Voit jatkaa neuvottelua aikaisintaan maanantaina klo
// 10.00...").
const WEEKDAY_ESSIVE_FI = {
  Sunday: 'sunnuntaina',
  Monday: 'maanantaina',
  Tuesday: 'tiistaina',
  Wednesday: 'keskiviikkona',
  Thursday: 'torstaina',
  Friday: 'perjantaina',
  Saturday: 'lauantaina',
};

export function formatLockExpiry(isoString) {
  const date = new Date(isoString);
  // Weekday is read via the en-US locale purely to get a stable English
  // name to key WEEKDAY_ESSIVE_FI with - the timeZone is what actually
  // matters here (Europe/Helsinki, regardless of the customer's own device
  // timezone).
  const englishWeekday = new Intl.DateTimeFormat('en-US', { timeZone: 'Europe/Helsinki', weekday: 'long' }).format(date);
  const time = new Intl.DateTimeFormat('fi-FI', { timeZone: 'Europe/Helsinki', hour: '2-digit', minute: '2-digit' }).format(date);
  const weekday = WEEKDAY_ESSIVE_FI[englishWeekday] ?? englishWeekday;
  return `${weekday} klo ${time}`;
}
