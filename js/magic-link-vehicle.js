// Reads the Magic Link token straight from location.pathname — never a
// query string, so a wrong/copied link with the token stripped can't be
// confused with the demo path, and the token never round-trips through a
// visible `?` parameter a user might strip or share incompletely.
// vercel.json rewrites /n/:token to this same page without changing the
// visible URL, so this always sees the real /n/{token} path in production.
const MAGIC_LINK_PATH_PATTERN = /^\/n\/([A-Za-z0-9_-]+)$/;

export const magicLinkToken = MAGIC_LINK_PATH_PATTERN.exec(window.location.pathname)?.[1] ?? null;

// No real per-vehicle photo exists for an arbitrary DMS-imported vehicle —
// this is a best-effort cosmetic match against the existing stock photo
// set (assets/cars/), by make, falling back to a neutral generic image.
// Never derived from anything the server considers internal.
const MAKE_IMAGE_MAP = {
  audi: '/assets/cars/audi-a4.jpg',
  bmw: '/assets/cars/bmw-320.jpg',
  citroën: '/assets/cars/citroen-berlingo.jpg',
  citroen: '/assets/cars/citroen-berlingo.jpg',
  ford: '/assets/cars/ford-focus.jpg',
  hyundai: '/assets/cars/hyundai-i30.jpg',
  kia: '/assets/cars/kia-niro.jpg',
  mazda: '/assets/cars/mazda-3.jpg',
  'mercedes-benz': '/assets/cars/mercedes-benz-c-class.jpg',
  mercedes: '/assets/cars/mercedes-benz-c-class.jpg',
  nissan: '/assets/cars/nissan-qashqai.jpg',
  peugeot: '/assets/cars/peugeot-208.jpg',
  skoda: '/assets/cars/skoda-octavia.jpg',
  škoda: '/assets/cars/skoda-octavia.jpg',
  toyota: '/assets/cars/toyota-corolla.jpg',
  volkswagen: '/assets/cars/volkswagen-golf.jpg',
  volvo: '/assets/cars/volvo-v60.jpg',
};
const GENERIC_VEHICLE_IMAGE = '/assets/cars/volkswagen-golf.jpg';

function imageForMake(make) {
  const key = (make || '').trim().toLowerCase();
  return MAKE_IMAGE_MAP[key] || GENERIC_VEHICLE_IMAGE;
}

// Fetches the PUBLIC vehicle view only (see kopilotti-sales'
// PostgresVehicleNegotiationCatalog.getPublicView, and the router that
// exposes it at GET /api/n/{token} — that query never selects floor/
// target/counter-step at all). Returns null for every failure case (wrong,
// expired, revoked token, inactive/out-of-window policy, or a network
// error) — the caller must show one generic "not available" view and must
// never fall back to the static demo vehicle.
export async function loadMagicLinkVehicle(token, backendUrl) {
  try {
    const response = await fetch(`${backendUrl}/api/n/${encodeURIComponent(token)}`, { credentials: 'include' });
    if (!response.ok) return null;
    const view = await response.json();
    if (typeof view.listPrice !== 'number') return null;
    return {
      // Client-side-only key: used purely for sessionStorage naming and the
      // local "does this offer belong to the current vehicle" check (see
      // negotiation-api.js) — never sent anywhere as a claim about the real
      // internal vehicleId, and never itself internal: it's the same token
      // already visible in the page's own URL.
      id: token,
      makeModel: [view.make, view.model].filter(Boolean).join(' ') || 'Ajoneuvo',
      registration: view.registrationNumber || '',
      listPrice: view.listPrice,
      // Illustrative-only: feeds the separate "Konseptidemo" post-purchase
      // journey animation (see the journeyDemo* elements in vehicle.html),
      // never the real negotiation — no real agreed price exists before a
      // customer has actually negotiated one.
      agreedPrice: view.listPrice,
      image: imageForMake(view.make),
      imageAlt: `Esimerkkikuva ajoneuvosta: ${[view.make, view.model].filter(Boolean).join(' ') || 'ajoneuvo'}`,
      campaignLabel: view.campaignLabel || null,
    };
  } catch {
    return null;
  }
}
