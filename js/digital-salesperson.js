import { CustomerNegotiationApi } from './negotiation-api.js';
import { PurchaseFlowApi } from './purchase-flow-api.js';
import { EmailVerificationApi } from './email-verification-api.js';
import { DEMO_VEHICLE } from './demo-vehicle.js';
import { magicLinkToken, loadMagicLinkVehicle } from './magic-link-vehicle.js';
import { calculateDealSummary, formatSignedEuro, formatSignedPercent, parseEuroInput } from './deal-summary.js';
import { formatLockExpiry } from './lock-expiry-format.js';

// Magic Link pages are served at /n/{token} (see vercel.json's rewrite) —
// the token never becomes a query string, it's read straight from
// location.pathname (see magic-link-vehicle.js). Its presence is the ONE
// branch point between the two entirely separate code paths this file
// supports: the always-on canned demo (DEMO_VEHICLE, /api/digital-salesperson)
// and a real per-dealer Magic Link negotiation
// (/api/n/{token}, kopilotti-admin's actual pricing rules). There is no
// fallback from the Magic Link path back to the demo path on any failure —
// see loadVehicle() below.
const api = new CustomerNegotiationApi(magicLinkToken ? { basePath: `/api/n/${magicLinkToken}` } : {});
const purchaseApi = new PurchaseFlowApi();
const emailApi = new EmailVerificationApi(magicLinkToken ? { basePath: `/api/n/${magicLinkToken}` } : {});
const state = { vehicle: null, negotiationStarted: false, preNegotiationReportOpened: false, conditionReturnFocus: null, purchasePath: null, latestCounterOffer: null, latestAgreedPrice: null, demoRun: 0, pendingOffer: null, pendingEmail: null };
const PURCHASE_PATH = { DIRECT: 'DIRECT_LIST_PRICE', NEGOTIATED: 'NEGOTIATED_PRICE' };
const DEMO_STEP_DELAY_MS = 1_500;
const REDUCED_MOTION_DEMO_STEP_DELAY_MS = 120;

async function loadVehicle() {
  if (magicLinkToken) {
    const vehicle = await loadMagicLinkVehicle(magicLinkToken, api.backendUrl);
    if (!vehicle) {
      renderVehicleUnavailable();
      return;
    }
    state.vehicle = vehicle;
    renderVehicle(state.vehicle);
    return;
  }
  state.vehicle = DEMO_VEHICLE;
  renderVehicle(state.vehicle);
}

// Same generic, safe wording regardless of why the vehicle view failed
// (wrong/expired/revoked token, inactive policy, network error) — never
// reveals which, matching the backend's own "one failure shape" convention
// (see src/http/magic-link-negotiation-routes.js).
function renderVehicleUnavailable() {
  document.title = 'Neuvottelulinkki ei ole käytössä – Kopilotti Sales';
  setText('vehicleTitle', 'Tämä neuvottelulinkki ei ole käytössä');
  setText('vehicleSubtitle', 'Linkki voi olla vanhentunut, mitätöity tai virheellinen.');
  setText('vehiclePrice', '');
  setText('vehicleAvailability', '');
  document.getElementById('digitalSalespersonCard')?.classList.add('hidden');
  document.getElementById('digitalSalespersonFlow')?.classList.add('hidden');
}

function renderVehicle(vehicle) {
  document.title = `${vehicle.makeModel} · ${vehicle.registration} – Kopilotti Sales`;
  setText('breadcrumbVehicle', vehicle.makeModel);
  setText('vehicleTitle', vehicle.makeModel);
  setText('vehicleSubtitle', vehicle.registration);
  setText('vehiclePrice', formatEuro(vehicle.listPrice));
  setText('vehicleMonthly', '');
  setText('vehicleAvailability', magicLinkToken ? 'Myynnissä' : 'Demoajoneuvo');
  const image = document.getElementById('vehicleImage');
  image.src = vehicle.image;
  image.alt = vehicle.imageAlt;
  const campaignEl = document.getElementById('vehicleCampaignLabel');
  if (campaignEl) {
    if (vehicle.campaignLabel) {
      campaignEl.textContent = vehicle.campaignLabel;
      campaignEl.classList.remove('hidden');
    } else {
      campaignEl.textContent = '';
      campaignEl.classList.add('hidden');
    }
  }

  setText('specMakeModel', vehicle.makeModel);
  setText('specRegistration', vehicle.registration);
  setText('specListPrice', formatEuro(vehicle.listPrice));
  setText('flowVehicle', vehicleIdentity(vehicle));
  setText('journeyDemoAgreedPrice', `Hinnasta sovittu · ${formatEuro(vehicle.agreedPrice)}`);
  setText('journeyDemoVehicle', vehicleIdentity(vehicle));
  setText('dealSummaryVehicle', vehicle.makeModel);
  setText('dealSummaryRegistration', vehicle.registration);
  setText('dealSummaryListPrice', formatEuro(vehicle.listPrice));
  const summaryImage = document.getElementById('dealSummaryImage');
  summaryImage.src = vehicle.image;
  summaryImage.alt = 'Esimerkkikuva demoautosta';
}

function updateDealSummary() {
  const summary = calculateDealSummary(state.vehicle.listPrice, parseEuroInput(document.getElementById('priceInput').value));
  const offer = document.getElementById('dealSummaryOffer');
  offer.textContent = summary ? formatEuro(summary.offerPrice) : 'Ei vielä annettu';
  offer.classList.toggle('has-value', Boolean(summary));
  setText('dealSummaryDifference', summary ? `${formatSignedEuro(summary.difference)} · ${formatSignedPercent(summary.percentageDifference)}` : '—');
}

function showAcceptedDealSummary(approvedAmount) {
  const summary = calculateDealSummary(state.vehicle.listPrice, approvedAmount);
  setText('dealSummaryOfferLabel', 'Sovittu kauppahinta');
  setText('dealSummaryOffer', formatEuro(approvedAmount));
  document.getElementById('dealSummaryOffer').classList.add('has-value');
  setText('dealSummaryDifference', `${formatSignedEuro(summary.difference)} · ${formatSignedPercent(summary.percentageDifference)}`);
  document.getElementById('priceInput').disabled = true;
}

function openFlow() {
  if (!state.preNegotiationReportOpened) {
    setText('negotiationGateStatus', '☐ Kuntoraportti avattava ennen hintaneuvottelua');
    document.getElementById('btnOpenPreNegotiationReport').focus();
    return;
  }
  const flow = document.getElementById('digitalSalespersonFlow');
  flow.classList.remove('hidden');
  document.getElementById('btnStartDigitalSalesperson').setAttribute('aria-expanded', 'true');
  flow.focus();
  startNegotiation();
}

function markPreNegotiationReportOpened() {
  state.preNegotiationReportOpened = true;
  setText('conditionReportAvailability', '✓ Avattu');
  setText('negotiationGateStatus', '✓ Kuntoraporttiin tutustuttu');
  document.getElementById('negotiationGateStatus').classList.add('complete');
  const startButton = document.getElementById('btnStartDigitalSalesperson');
  startButton.disabled = false;
  const reportButton = document.getElementById('btnOpenPreNegotiationReport');
  reportButton.textContent = 'Avaa uudelleen';
  reportButton.setAttribute('aria-label', 'Avaa kuntoraportti uudelleen');
}

function openPreNegotiationConditionReport() {
  markPreNegotiationReportOpened();
  const dialog = document.getElementById('preNegotiationConditionReport');
  dialog.showModal();
  document.getElementById('btnClosePreNegotiationReport').focus();
}

function closePreNegotiationConditionReport() {
  document.getElementById('preNegotiationConditionReport').close();
}

function restoreFocusAfterPreNegotiationReport() {
  document.getElementById('btnStartDigitalSalesperson').focus();
}

function closeFlow() {
  document.getElementById('digitalSalespersonFlow').classList.add('hidden');
  document.getElementById('btnStartDigitalSalesperson').setAttribute('aria-expanded', 'false');
  document.getElementById('btnStartDigitalSalesperson').focus();
}

// Opens (or restores) the negotiation session as soon as the customer
// starts the flow, before ever showing the price form - previously this
// only happened lazily on the first "Ehdota hintaa" submit, so a customer
// who needed email verification (or hit a NEGOTIATION_LOCKED vehicle) typed
// a price first and only then got redirected, having already invested the
// effort. Checking eagerly means they see exactly the panel they need
// (verification, lock, or the price form) on the very first screen, never
// a form they can't actually use yet.
async function startNegotiation() {
  if (state.negotiationStarted) return;
  state.negotiationStarted = true;
  document.getElementById('conversation').classList.remove('hidden');
  document.getElementById('priceForm').classList.add('hidden');
  const waitingMessage = addMessage('salesperson pending', 'Tarkistetaan, voidaanko hintaneuvottelu aloittaa.');
  document.getElementById('messageList').focus();
  try {
    await api.ensureSession(state.vehicle.id);
    waitingMessage.remove();
    document.getElementById('priceForm').classList.remove('hidden');
  } catch (error) {
    waitingMessage.remove();
    if (error.code === 'EMAIL_VERIFICATION_REQUIRED') {
      showEmailVerificationRequired(Boolean(error.recoveryContext));
    } else if (error.code === 'NEGOTIATION_LOCKED') {
      showNegotiationLocked(error.message, error.expiresAt);
    } else {
      document.getElementById('priceForm').classList.remove('hidden');
      addMessage('salesperson decision', offerErrorMessage(error));
      renderDecisionActions('unavailable');
    }
  }
}

const OFFER_ERROR_MESSAGES = {
  VEHICLE_ALREADY_RESERVED: 'Tämä auto on juuri varattu toiselle asiakkaalle. Yritä hetken kuluttua uudelleen.',
  VERSION_CONFLICT: 'Neuvottelutilanne ehti muuttua sillä välin. Päivitä sivu ja yritä uudelleen.',
  VEHICLE_MISMATCH: 'Tarjous ei täsmännyt valittuun autoon. Päivitä sivu ja yritä uudelleen.',
  POLICY_UNAVAILABLE: 'Hinnoittelutietoja päivitetään juuri nyt. Ota yhteys myyjään tai yritä hetken kuluttua uudelleen.',
  VEHICLE_NOT_FOUND: 'Ajoneuvon tietoja ei löytynyt. Päivitä sivu ja yritä uudelleen.',
  INVALID_REQUEST: 'Pyyntöä ei voitu käsitellä. Päivitä sivu ja yritä uudelleen.',
};

function offerErrorMessage(error) {
  return OFFER_ERROR_MESSAGES[error?.code]
    ?? 'Hinnan tarkistaminen ei onnistunut juuri nyt. Kaupan tietoja ei muutettu. Yritä hetken kuluttua uudelleen.';
}

async function submitPrice(event) {
  event.preventDefault();
  const input = document.getElementById('priceInput');
  const errorElement = document.getElementById('priceError');
  const offerAmount = parseEuroInput(input.value);
  errorElement.textContent = '';
  if (!Number.isSafeInteger(offerAmount) || offerAmount <= 0) {
    errorElement.textContent = 'Kirjoita ehdottamasi kauppahinta kokonaisina euroina, esimerkiksi 90 000.';
    input.focus();
    return;
  }

  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  addMessage('customer', formatEuro(offerAmount), 'Sinä');
  const waitingMessage = addMessage('salesperson pending', 'Tarkistan, voimmeko tehdä kaupat tällä hinnalla.');
  // Disabling the currently-focused button removes it from the a11y tree,
  // which drops focus to <body> for as long as the request is in flight -
  // move it to the (already aria-live) message list instead, so a keyboard/
  // screen-reader user stays anchored right where the messages are. Must
  // happen after the addMessage() calls above: #messageList is
  // "display: none" while empty (.message-list:empty in vehicle.css), so
  // focusing it before it has content is a silent no-op.
  document.getElementById('messageList').focus();
  const evidence = `Asiakkaan hintaehdotus on ${offerAmount} EUR.`;
  try {
    const decision = await api.discussPrice({ vehicleId: state.vehicle.id, offerAmount, evidence });
    waitingMessage.remove();
    renderDecision(decision);
    form.classList.add('hidden');
  } catch (error) {
    waitingMessage.remove();
    // These three codes get their own dedicated UI (email verification,
    // lock, offer-limit) instead of the generic offer-error message below -
    // see the matching backend checks in negotiation-service.js's create()
    // (Step 4/5) and submitOffer() (Step 5).
    if (error.code === 'EMAIL_VERIFICATION_REQUIRED') {
      state.pendingOffer = { offerAmount, evidence };
      form.classList.add('hidden');
      showEmailVerificationRequired(Boolean(error.recoveryContext));
    } else if (error.code === 'SESSION_NOT_FOUND') {
      // Only reachable for a session that already existed (see
      // negotiation-api.js's discussPrice retry) - always framed as
      // recovery, never as a first-time verification.
      state.pendingOffer = { offerAmount, evidence };
      form.classList.add('hidden');
      showEmailVerificationRequired(true);
    } else if (error.code === 'NEGOTIATION_LOCKED') {
      form.classList.add('hidden');
      showNegotiationLocked(error.message, error.expiresAt);
    } else if (error.code === 'OFFER_LIMIT_REACHED') {
      form.classList.add('hidden');
      showOfferLimitReached(error.message, error.cooldownUntil);
    } else {
      addMessage('salesperson decision', offerErrorMessage(error));
      renderDecisionActions('unavailable');
    }
  } finally {
    submitButton.disabled = false;
  }
}

// --- Step 6: email verification, negotiation lock, and offer-limit UI ---

const EMAIL_VERIFICATION_INTRO = {
  firstTime: 'Vahvista sähköpostiosoitteesi ennen hintaneuvottelun aloittamista.',
  // Shown only when a previously-working session just failed to re-validate
  // (lost device cookie, see resolve-device.js's KNOWN LIMITATION) - never
  // for a genuine first-time visitor. Framed as continuing, not restarting.
  recovery: 'Vahvista sähköpostisi, jotta voimme palauttaa aiemman neuvottelusi.',
};

function showEmailVerificationRequired(recovery = false) {
  const panel = document.getElementById('emailVerificationPanel');
  setText('emailVerificationIntro', recovery ? EMAIL_VERIFICATION_INTRO.recovery : EMAIL_VERIFICATION_INTRO.firstTime);
  document.getElementById('emailRequestForm').classList.remove('hidden');
  document.getElementById('emailVerifyForm').classList.add('hidden');
  panel.classList.remove('hidden');
  panel.focus();
}

async function requestVerificationCode(event) {
  event.preventDefault();
  const input = document.getElementById('emailInput');
  const errorElement = document.getElementById('emailRequestError');
  const button = event.currentTarget.querySelector('button[type="submit"]');
  errorElement.textContent = '';
  const email = input.value.trim();
  if (!email) {
    errorElement.textContent = 'Kirjoita sähköpostiosoitteesi.';
    input.focus();
    return;
  }
  button.disabled = true;
  try {
    await emailApi.requestCode(email);
    state.pendingEmail = email;
    document.getElementById('emailRequestForm').classList.add('hidden');
    const verifyForm = document.getElementById('emailVerifyForm');
    verifyForm.classList.remove('hidden');
    setText('emailVerifySentNotice', `Lähetimme vahvistuskoodin osoitteeseen ${email}. Koodi on voimassa vain vähän aikaa.`);
    document.getElementById('codeInput').focus();
  } catch (_error) {
    errorElement.textContent = 'Koodin lähetys ei onnistunut juuri nyt. Yritä hetken kuluttua uudelleen.';
    input.focus();
  } finally {
    button.disabled = false;
  }
}

const EMAIL_VERIFY_ERROR_MESSAGES = {
  CODE_MISMATCH: 'Koodi ei täsmää, tarkista ja yritä uudelleen.',
  CODE_EXPIRED: 'Koodi on vanhentunut, pyydä uusi.',
  TOO_MANY_ATTEMPTS: 'Liian monta yritystä. Pyydä uusi koodi.',
};

function emailVerifyErrorMessage(error) {
  return EMAIL_VERIFY_ERROR_MESSAGES[error?.code] ?? 'Vahvistus ei onnistunut juuri nyt. Tarkista koodi ja yritä uudelleen.';
}

async function verifyEmailCode(event) {
  event.preventDefault();
  const input = document.getElementById('codeInput');
  const errorElement = document.getElementById('emailVerifyError');
  const button = event.currentTarget.querySelector('button[type="submit"]');
  errorElement.textContent = '';
  const code = input.value.trim();
  if (!/^\d{6}$/.test(code)) {
    errorElement.textContent = 'Koodi on kuusi numeroa.';
    input.focus();
    return;
  }
  button.disabled = true;
  try {
    await emailApi.verifyCode(state.pendingEmail, code);
    document.getElementById('emailVerificationPanel').classList.add('hidden');
    await retryPendingOffer();
  } catch (error) {
    errorElement.textContent = emailVerifyErrorMessage(error);
    input.value = '';
    input.focus();
  } finally {
    button.disabled = false;
  }
}

// Runs the exact offer the customer already typed before verification
// interrupted them - they should never have to re-type or re-click
// "Ehdota hintaa" a second time. If verification instead happened eagerly,
// right when the negotiation opened (startNegotiation), there is no typed
// offer yet - just reveal the price form so the customer can make their
// first offer now that they're verified.
async function retryPendingOffer() {
  const pending = state.pendingOffer;
  state.pendingOffer = null;
  const form = document.getElementById('priceForm');
  if (!pending) {
    form.classList.remove('hidden');
    document.getElementById('priceInput').focus();
    return;
  }
  form.classList.remove('hidden');
  const waitingMessage = addMessage('salesperson pending', 'Tarkistan, voimmeko tehdä kaupat tällä hinnalla.');
  document.getElementById('messageList').focus();
  try {
    const decision = await api.discussPrice({ vehicleId: state.vehicle.id, ...pending });
    waitingMessage.remove();
    renderDecision(decision);
    form.classList.add('hidden');
  } catch (error) {
    waitingMessage.remove();
    if (error.code === 'NEGOTIATION_LOCKED') {
      form.classList.add('hidden');
      showNegotiationLocked(error.message, error.expiresAt);
    } else if (error.code === 'OFFER_LIMIT_REACHED') {
      form.classList.add('hidden');
      showOfferLimitReached(error.message, error.cooldownUntil);
    } else {
      addMessage('salesperson decision', offerErrorMessage(error));
      renderDecisionActions('unavailable');
    }
  }
}

// Matches the existing btnContactSeller convention (see below): this demo
// has no real backend endpoint to send a human-salesperson contact
// request to, so leaving contact details is a UI gesture that ends in the
// same honest, non-technical notice already used elsewhere in this file.
function renderContactPrompt(container) {
  container.replaceChildren();
  container.append(createAction('Jätä yhteystiedot myyjälle', () => {
    const note = document.createElement('p');
    note.className = 'purchase-fineprint';
    note.textContent = 'Tämä konseptidemo ei lähetä oikeaa yhteydenottopyyntöä. Myyjä voi auttaa poikkeustilanteissa ja lisäkysymyksissä.';
    container.replaceChildren(note);
  }, false));
}

// message is always the backend's own text (§12 of the feature spec) -
// expiresAt is the only thing formatted client-side, from structured data,
// never computed or guessed here (see lock-expiry-format.js).
function showNegotiationLocked(message, expiresAt) {
  const panel = document.getElementById('negotiationLockedPanel');
  const fullMessage = expiresAt
    ? `${message} Voit jatkaa neuvottelua aikaisintaan ${formatLockExpiry(expiresAt)}, ellei autoliike ota sinuun yhteyttä aiemmin.`
    : message;
  setText('negotiationLockedMessage', fullMessage);
  renderContactPrompt(document.getElementById('negotiationLockedContact'));
  panel.classList.remove('hidden');
  panel.focus();
}

// COOLDOWN, not a real handoff to a human (2026-08-05 fix): message is the
// backend's own honest text - it never claims the negotiation has already
// been handed to the dealer, only that automated negotiation is paused.
// cooldownUntil (structured data, same convention as showNegotiationLocked's
// expiresAt) tells the customer exactly when a genuinely new negotiation
// can start - reloading the page (or just trying again) after that time
// gets a fresh session automatically, see negotiation-service.js's create().
function showOfferLimitReached(message, cooldownUntil) {
  const panel = document.getElementById('offerLimitPanel');
  const fullMessage = cooldownUntil
    ? `${message} Voit aloittaa uuden neuvottelun aikaisintaan ${formatLockExpiry(cooldownUntil)}.`
    : message;
  setText('offerLimitMessage', fullMessage);
  renderContactPrompt(document.getElementById('offerLimitContact'));
  panel.classList.remove('hidden');
  panel.focus();
}

function renderDecision(decision) {
  if (decision.status === 'ACCEPT') {
    state.latestCounterOffer = null;
    state.latestAgreedPrice = decision.approvedAmount;
    showAcceptedDealSummary(decision.approvedAmount);
    addMessage('salesperson decision', `Voimme tehdä kaupat hinnalla ${formatEuro(decision.approvedAmount)}. Jatketaan maksutavan valintaan.`);
    renderDecisionActions('reserve');
  } else if (decision.status === 'COUNTER') {
    state.latestCounterOffer = decision.counterOffer;
    addMessage('salesperson decision', counterMessage(decision));
    renderDecisionActions('counter', decision);
  } else if (decision.status === 'REJECT') {
    addMessage('salesperson decision', 'Emme voi tehdä kauppoja ehdottamallasi hinnalla. Voit jatkaa neuvottelua tai edetä listahinnalla.');
    renderDecisionActions('rejected');
  } else {
    addMessage('salesperson decision', 'En voi vahvistaa kauppaa tällä hinnalla suoraan. Tarkistutan vielä, voimmeko tulla hinnassa vastaan. Neuvottelua ei tarvitse aloittaa alusta.');
    renderDecisionActions('escalate');
  }
}

const FINAL_ROUND_APPEAL = 'Myymme auton sinulle oikein mielellämme, mutta ehdotuksesi ei vielä riitä kauppaan asti. Ole ystävällinen ja tee viimeinen korkein ehdotuksesi.';

function counterMessage(decision) {
  const price = formatEuro(decision.counterOffer);
  let message;
  if (decision.messageCode === 'COUNTER_ROUND_1') {
    message = `Kiitos ehdotuksestasi. Tällä hinnalla emme vielä voi tehdä kauppaa. Voimme tulla vastaan hintaan ${price}. Haluatko hyväksyä hinnan vai tehdä uuden ehdotuksen?`;
  } else if (decision.messageCode === 'COUNTER_ROUND_2') {
    message = `Olemme jo lähempänä. Voimme tarkistaa hinnan ${price.replace(' €', ' euroon')}. Haluatko hyväksyä hinnan vai jatkaa neuvottelua?`;
  } else {
    message = `Voimme tehdä vielä viimeisen tarkistuksen hintaan ${price}. Jos hyväksyt tämän hinnan, voimme jatkaa ostoprosessiin.`;
  }
  if (decision.isFinalAutomatedRound) {
    message += ` ${FINAL_ROUND_APPEAL}`;
  }
  return message;
}

function renderDecisionActions(mode, decision = null) {
  const container = document.getElementById('decisionActions');
  container.classList.remove('hidden');
  container.replaceChildren();
  if (mode === 'reserve') {
    // 2026-08-05 follow-up to the purchase-flow handoff fix: this button no
    // longer starts an "ostoprosessi" (purchase process) at all in the
    // Magic Link context - beginPurchaseFlow() shows the handoff view
    // directly, without ever calling the demo-only purchase-flow API (see
    // its own comment). "Jatka ostoprosessiin" would be actively misleading
    // there. The old internal demo (no magicLinkToken) really does continue
    // into its own purchase process, so its label is unchanged.
    const reserveLabel = magicLinkToken ? 'Viimeistele neuvottelu' : 'Jatka ostoprosessiin';
    container.append(createAction(reserveLabel, (event) => beginPurchaseFlow(PURCHASE_PATH.NEGOTIATED, event.currentTarget), true));
  }
  if (mode === 'counter') {
    container.append(createAction(`Hyväksy ${formatEuro(decision.counterOffer)}`, acceptCounterOffer, true));
    if (decision.canSubmitNewOffer) container.append(createAction('Tee uusi ehdotus', prepareNewOffer, false));
  }
  if (mode === 'rejected') {
    container.append(createAction('Jatka listahinnalla', (event) => beginPurchaseFlow(PURCHASE_PATH.DIRECT, event.currentTarget), true));
  }
  if (mode === 'escalate') {
    const note = document.createElement('p');
    note.className = 'purchase-fineprint';
    note.textContent = 'Tämä konseptidemo ei lähetä oikeaa yhteydenottopyyntöä.';
    container.append(note);
  }
  if (mode === 'unavailable') {
    const note = document.createElement('p');
    note.className = 'purchase-fineprint';
    note.textContent = 'Voit lähettää saman hinnan uudelleen, kun palveluyhteys toimii.';
    container.append(note);
  }
  container.append(createAction('Palaa auton tietoihin', closeFlow, false));
  // Without this, focus is left on the (now-hidden) price form's submit
  // button and the browser drops it to <body> - a keyboard/screen-reader
  // user loses their place the instant the bot responds and has no
  // indication where the new action buttons are.
  container.querySelector('button')?.focus();
}

function prepareNewOffer() {
  const form = document.getElementById('priceForm');
  const input = document.getElementById('priceInput');
  document.getElementById('decisionActions').classList.add('hidden');
  form.classList.remove('hidden');
  input.disabled = false;
  input.value = '';
  updateDealSummary();
  input.focus();
}

function acceptCounterOffer(event) {
  const amount = state.latestCounterOffer;
  if (!Number.isSafeInteger(amount)) return;
  state.latestAgreedPrice = amount;
  showAcceptedDealSummary(amount);
  document.getElementById('priceForm').classList.add('hidden');
  document.getElementById('decisionActions').classList.add('hidden');
  addMessage('salesperson decision', `Hinnasta sovittu ${formatEuro(amount)}. Jatketaan ostoprosessiin.`);
  beginPurchaseFlow(PURCHASE_PATH.NEGOTIATED, event.currentTarget);
}

function createAction(label, handler, primary) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `btn ${primary ? 'btn-primary' : 'btn-outline'} purchase-button`;
  button.textContent = label;
  button.addEventListener('click', handler);
  return button;
}

function addMessage(className, text, speaker) {
  const message = document.createElement('div');
  message.className = `message ${className}`;
  const name = document.createElement('strong');
  name.textContent = speaker;
  const content = document.createElement('span');
  content.textContent = text;
  if (speaker) message.append(name);
  message.append(content);
  const list = document.getElementById('messageList');
  list.append(message);
  list.scrollTop = list.scrollHeight;
  return message;
}

async function beginPurchaseFlow(purchasePath, trigger) {
  state.conditionReturnFocus = trigger || document.activeElement;
  state.purchasePath = purchasePath;
  // 2026-08-05 hotfix (found during the first production Magic Link test,
  // right after this PR's own vehicle-identity fix let a real negotiation
  // reach ACCEPT for the first time): PurchaseFlowService's own vehicle
  // lookup (purchase-flow-service.js's `this.inventory`, wired in
  // bootstrap.js) only ever reads the static file-based demo catalog - it
  // has no knowledge of kopilotti-admin's Postgres
  // vehicle catalog that Magic Link vehicles actually live in. Every
  // Magic Link vehicle id therefore fails this call with
  // VEHICLE_NOT_AVAILABLE (409), shown to the customer as a generic
  // "Ostoprosessia ei voitu aloittaa" error - regardless of purchasePath.
  // For Kopilotti's own scope, a Magic Link ACCEPT (or an agreed list
  // price) already IS the successful end state: the payment boundary
  // (README's "Maksut pysyvät aina myyjäliikkeellä") means the dealership
  // takes the deal from here in its own systems, not this page. Building a
  // real Postgres-aware purchase/condition-report/payment path for Magic
  // Link vehicles is a separate, larger piece of work - this fix only
  // stops calling an API this path was never built to support, and shows
  // the customer an accurate handoff message instead of a false error. The
  // pre-existing internal demo (no magicLinkToken) is completely
  // untouched - it still calls the real purchase-flow API exactly as
  // before.
  if (magicLinkToken) {
    showMagicLinkPurchaseHandoff(purchasePath);
    return;
  }
  try {
    await purchaseApi.start({
      vehicleId: state.vehicle.id,
      purchasePath,
      negotiationSessionId: purchasePath === PURCHASE_PATH.NEGOTIATED ? api.getSessionId() : null,
    });
    showDealAgreement(purchasePath);
  } catch (error) {
    const journey = document.getElementById('purchaseJourney');
    document.getElementById('paymentMethods').classList.add('hidden');
    document.getElementById('dealAgreement').classList.add('hidden');
    document.getElementById('demoConfirmation').classList.add('hidden');
    journey.classList.remove('hidden');
    setPurchaseStatus('Ostoprosessia ei voitu aloittaa', 'Kaupan tietoja ei muutettu. Yritä uudelleen tai ota yhteys myyjään.');
    journey.focus();
  }
}

// Magic Link vehicles have no purchase/condition-report/payment session on
// the backend (see the comment in beginPurchaseFlow above) - this never
// calls purchaseApi or touches PurchaseFlowService at all. It only renders
// the same "Kaupan eteneminen" panel the internal demo uses, showing the
// price the customer and dealer just agreed on (or the list price, for the
// DIRECT/"Jatka listahinnalla" path) and a clear handoff to the dealer's
// own systems - never the demo's condition-report/payment-method/provider
// steps, since none of those exist for this session.
function showMagicLinkPurchaseHandoff(purchasePath) {
  document.getElementById('digitalSalespersonFlow').classList.add('hidden');
  document.querySelectorAll('.purchase-card').forEach((card) => card.classList.add('hidden'));
  document.getElementById('conditionReportStep').classList.add('hidden');
  document.getElementById('paymentMethods').classList.add('hidden');
  document.getElementById('demoConfirmation').classList.add('hidden');
  document.getElementById('dealAgreement').classList.add('hidden');
  document.querySelector('.purchase-progress')?.classList.add('hidden');
  const journey = document.getElementById('purchaseJourney');
  journey.classList.remove('hidden');
  const negotiated = purchasePath === PURCHASE_PATH.NEGOTIATED;
  const price = negotiated ? state.latestAgreedPrice : state.vehicle.listPrice;
  setText('purchaseJourneyTitle', negotiated ? 'Hinnasta sovittu' : 'Ostopolku jatkuu listahinnalla');
  setPurchaseStatus(
    `Hinnasta sovittu: ${formatEuro(price)}`,
    'Myyjäliike viimeistelee kaupan kanssasi. Maksut, rahoitus ja ajoneuvon luovutus hoidetaan myyjäliikkeen omissa järjestelmissä.',
  );
  journey.focus();
}

function showDealAgreement(purchasePath) {
  document.getElementById('digitalSalespersonFlow').classList.add('hidden');
  document.querySelectorAll('.purchase-card').forEach((card) => card.classList.add('hidden'));
  document.getElementById('conditionReportStep').classList.add('hidden');
  document.getElementById('paymentMethods').classList.add('hidden');
  document.getElementById('demoConfirmation').classList.add('hidden');
  const journey = document.getElementById('purchaseJourney');
  const agreement = document.getElementById('dealAgreement');
  journey.classList.remove('hidden');
  agreement.classList.remove('hidden');
  const negotiated = purchasePath === PURCHASE_PATH.NEGOTIATED;
  setText('purchaseJourneyTitle', negotiated ? `Hinnasta sovittu · ${formatEuro(purchaseApi.session.agreedPrice)}` : 'Ostopolku aloitettu');
  setText('dealAgreementTitle', negotiated ? 'Hinnasta sovittu' : 'Listahinta valittu');
  setText('agreementPrice', formatEuro(purchaseApi.session.agreedPrice));
  setText('agreementVehicle', vehicleIdentity(state.vehicle));
  setPurchaseStatus(
    negotiated ? 'Hinnasta sovittu' : 'Suora ostopolku',
    `${vehicleIdentity(state.vehicle)}. Kuntoraportti on saattanut päivittyä sen jälkeen kun tutustuit siihen — vahvista se vielä kertaalleen ennen maksua.`,
  );
  renderPurchaseProgress('price');
  journey.focus();
}

async function continueToConditionReport() {
  const button = document.getElementById('btnReviewCondition');
  button.disabled = true;
  document.getElementById('dealAgreement').classList.add('hidden');
  document.getElementById('purchaseJourney').classList.add('hidden');
  const step = document.getElementById('conditionReportStep');
  resetConditionReportView();
  step.classList.remove('hidden');
  step.focus();
  setConditionStatus('Kuntoraporttia ladataan…');
  try { await loadConditionReport(); }
  catch (error) { showConditionFailure(error); }
  finally { button.disabled = false; }
}

async function loadConditionReport() {
  setConditionStatus('Kuntoraporttia ladataan…');
  const report = await purchaseApi.openReport();
  renderConditionReport(report);
  await afterNextPaint();
  await purchaseApi.markDisplayed();
  setConditionStatus(`Kuntoraportti ${report.version} on avattu. Tutustu kaikkiin raportin osioihin ennen kuittausta.`);
  const form = document.getElementById('conditionAcknowledgementForm');
  form.classList.remove('hidden');
  document.getElementById('conditionAcknowledgement').focus();
}

function renderConditionReport(report) {
  setText('conditionReportMeta', `Raportti ${report.id} · versio ${report.version} · tarkastettu ${formatDate(report.inspectedAt)}`);
  const sections = document.getElementById('conditionReportSections');
  sections.replaceChildren(...report.sections.map((section) => {
    const wrapper = document.createElement('section');
    wrapper.className = 'condition-section';
    const heading = document.createElement('h3');
    heading.textContent = section.title;
    const content = document.createElement('p');
    content.textContent = section.content;
    wrapper.append(heading, content);
    return wrapper;
  }));

  const photographSection = document.getElementById('conditionPhotographs');
  const grid = document.getElementById('conditionPhotoGrid');
  grid.replaceChildren(...report.photographs.map((photo) => {
    const figure = document.createElement('figure');
    figure.className = 'condition-photo';
    const image = document.createElement('img');
    image.src = purchaseApi.assetUrl(photo.url);
    image.alt = photo.alt;
    const caption = document.createElement('figcaption');
    caption.textContent = photo.caption || photo.alt;
    figure.append(image, caption);
    return figure;
  }));
  photographSection.classList.toggle('hidden', report.photographs.length === 0);

  const source = document.getElementById('conditionReportSource');
  if (report.sourceDocumentUrl) {
    source.href = purchaseApi.assetUrl(report.sourceDocumentUrl);
    source.classList.remove('hidden');
  } else {
    source.removeAttribute('href');
    source.classList.add('hidden');
  }
  document.getElementById('conditionReportContent').classList.remove('hidden');
}

async function submitConditionAcknowledgement(event) {
  event.preventDefault();
  const checkbox = document.getElementById('conditionAcknowledgement');
  const button = document.getElementById('btnProceedAfterCondition');
  if (!checkbox.checked || button.disabled) return;
  button.disabled = true;
  setText('conditionReportError', '');
  try {
    await purchaseApi.acknowledge();
    showPaymentSelection();
  } catch (error) {
    if (error.code === 'CONDITION_REPORT_CHANGED') {
      setConditionStatus('Auton kuntoraportti on päivittynyt. Tutustu uuteen versioon ennen kuin jatkat.', 'review');
      resetAcknowledgement();
      try { await loadConditionReport(); } catch (loadError) { showConditionFailure(loadError); }
    } else {
      setText('conditionReportError', 'Kuittausta ei voitu tallentaa. Emme siirry rahoitukseen tai maksamiseen ennen kuin palvelinyhteys toimii.');
    }
  }
}

function showPaymentSelection() {
  document.getElementById('conditionReportStep').classList.add('hidden');
  const journey = document.getElementById('purchaseJourney');
  journey.classList.remove('hidden');
  document.getElementById('paymentMethods').classList.remove('hidden');
  document.getElementById('demoConfirmation').classList.add('hidden');
  document.getElementById('dealAgreement').classList.add('hidden');
  setText('purchaseJourneyTitle', 'Hinnasta sovittu');
  setPurchaseStatus('Kuntoraportti kuitattu', 'Valitse, haluatko jatkaa maksamiseen vai hakea rahoitusta.');
  renderPurchaseProgress('provider');
  journey.focus();
}

async function selectPayment(event) {
  const button = event.target.closest('button[data-payment-method]');
  if (!button) return;
  const method = button.dataset.paymentMethod;
  document.querySelectorAll('[data-payment-method]').forEach((control) => { control.disabled = true; });
  setPurchaseStatus(method === 'PAYMENT' ? 'Maksua käynnistetään' : 'Rahoitushakemusta käynnistetään', 'Odotetaan palveluyhteyttä…');
  try {
    await purchaseApi.selectPaymentMethod(method);
    const pending = await purchaseApi.startProvider();
    document.getElementById('paymentMethods').classList.add('hidden');
    renderProviderStatus(pending);
  } catch (error) {
    // AVAILABILITY_CHECK_UNAVAILABLE has a known, proven cause (no dealer
    // has an external availability integration configured yet — see
    // src/adapters/disabled-availability-provider.js) — name it instead of
    // showing the generic "connection failed" text, which reads like an
    // unrelated technical fault.
    if (error.code === 'AVAILABILITY_CHECK_UNAVAILABLE') {
      setPurchaseStatus('Saatavuutta ei voitu vahvistaa', 'Tämä auto vaatii dealer-kohtaisen saatavuusintegraation ennen kuin täysi ostoprosessi maksuun asti voi valmistua. Yritä hetken kuluttua uudelleen tai ota yhteys myyjään.');
    } else if (error.code === 'PROVIDER_UNAVAILABLE') {
      // Same reasoning as AVAILABILITY_CHECK_UNAVAILABLE above: this demo has
      // no real payment/financing integration configured (see
      // src/adapters/disabled-payment-provider.js and
      // disabled-financing-provider.js - every attempt fails this same way,
      // it is not a transient technical fault) - name the demo limitation
      // instead of showing a generic "connection failed" text.
      setPurchaseStatus(
        method === 'PAYMENT' ? 'Demo ei sisällä oikeaa maksupalvelua' : 'Demo ei sisällä oikeaa rahoitusintegraatiota',
        method === 'PAYMENT'
          ? 'Tämä on ei-sitova esitys ostopolusta. Oikea maksu vaatii myyjäliikkeen maksupalveluintegraation, jota ei ole kytketty tähän demoon.'
          : 'Tämä on ei-sitova esitys ostopolusta. Oikea rahoitushakemus vaatii myyjäliikkeen rahoitusyhtiöintegraation, jota ei ole kytketty tähän demoon.',
        'notice',
      );
    } else {
      const message = method === 'PAYMENT'
        ? 'Maksupalveluun ei saatu yhteyttä. Maksua ei ole vahvistettu.'
        : 'Rahoituspalveluun ei saatu yhteyttä. Rahoitusta ei ole vahvistettu.';
      setPurchaseStatus('Yhteys ei onnistunut', message);
    }
    document.querySelectorAll('[data-payment-method]').forEach((control) => { control.disabled = false; });
  }
}

function renderProviderStatus(session) {
  const payment = session.paymentMethod === 'PAYMENT';
  setText('purchaseJourneyTitle', 'Maksu odottaa vahvistusta');
  setPurchaseStatus(
    'Auto on varattu. Maksua odotetaan.',
    payment
      ? 'Jatkamme heti, kun maksupalvelu on vahvistanut maksun.'
      : 'Rahoitushakemuksesi on käsittelyssä. Rahoituksen vahvistaa erillinen rahoitusyhtiö.',
  );
  renderPurchaseProgress('provider');
  if (session.simulated) showDemoConfirmation(session.paymentMethod);
}

function showDemoConfirmation(method) {
  const container = document.getElementById('demoConfirmation');
  const note = document.createElement('p');
  note.className = 'purchase-fineprint';
  note.textContent = 'Simuloitu vahvistus on käytettävissä vain tässä konseptidemossa.';
  const button = createAction(method === 'PAYMENT' ? 'Demon maksuvahvistus' : 'Demon rahoitusvahvistus', () => confirmDemo(method), true);
  container.replaceChildren(note, button);
  container.classList.remove('hidden');
  button.focus();
}

async function confirmDemo(method) {
  const container = document.getElementById('demoConfirmation');
  const button = container.querySelector('button');
  button.disabled = true;
  try {
    const session = await purchaseApi.confirmDemo(method);
    container.classList.add('hidden');
    renderConfirmedStatus(session);
  } catch (_error) {
    setPurchaseStatus('Vahvistus ei onnistunut', method === 'PAYMENT' ? 'Maksua ei ole vahvistettu.' : 'Rahoitusta ei ole vahvistettu.');
    button.disabled = false;
    button.focus();
  }
}

function renderConfirmedStatus(session) {
  if (session.status === 'READY_FOR_HANDOVER') {
    setText('purchaseJourneyTitle', 'Valmis noudettavaksi');
    setPurchaseStatus('Valmis noudettavaksi', `${vehicleIdentity(state.vehicle)}. Auton luovutuksen edellytykset ovat kunnossa. Saat seuraavaksi nouto- tai toimitusohjeet.`);
    renderPurchaseProgress('handover');
    return;
  }
  const payment = session.status === 'PAYMENT_CONFIRMED';
  setText('purchaseJourneyTitle', payment ? 'Maksu vahvistettu' : 'Rahoitus vahvistettu');
  setPurchaseStatus(
    payment ? 'Maksu vahvistettu' : 'Rahoitus vahvistettu',
    payment
      ? 'Maksu on vahvistettu. Tarkistamme seuraavaksi auton luovutuksen edellytykset.'
      : 'Rahoitus on vahvistettu. Tarkistamme seuraavaksi auton luovutuksen edellytykset.',
  );
}

function setPurchaseStatus(title, message, tone) {
  const panel = document.getElementById('purchaseStatus');
  const heading = document.createElement('strong');
  const text = document.createElement('span');
  heading.textContent = title;
  text.textContent = message;
  panel.replaceChildren(heading, text);
  panel.classList.toggle('notice', tone === 'notice');
  if (!document.getElementById('purchaseJourney').classList.contains('hidden')) panel.focus();
}

function renderPurchaseProgress(current) {
  const order = ['price', 'condition', 'provider', 'handover'];
  const index = order.indexOf(current);
  document.querySelectorAll('[data-progress]').forEach((item) => {
    const itemIndex = order.indexOf(item.dataset.progress);
    item.classList.toggle('complete', itemIndex < index);
    item.classList.toggle('current', itemIndex === index);
    if (itemIndex === index) item.setAttribute('aria-current', 'step'); else item.removeAttribute('aria-current');
  });
}

function showConditionFailure(error) {
  document.getElementById('conditionReportContent').classList.add('hidden');
  document.getElementById('conditionAcknowledgementForm').classList.add('hidden');
  if (error.code === 'CONDITION_REPORT_REVIEW_REQUIRED') {
    setConditionStatus('Auton kuntotiedot vaativat myyjän tarkistuksen. Pyyntö on välitetty eteenpäin.', 'review');
  } else {
    setConditionStatus('Auton kuntoraporttia ei saatu avattua. Emme siirry rahoitukseen tai maksamiseen ennen kuin raportti on saatavilla.', 'error');
  }
}

function resetConditionReportView() {
  document.getElementById('conditionReportContent').classList.add('hidden');
  document.getElementById('conditionAcknowledgementForm').classList.add('hidden');
  document.getElementById('conditionReportSections').replaceChildren();
  document.getElementById('conditionPhotoGrid').replaceChildren();
  setText('conditionReportError', '');
  resetAcknowledgement();
}

function resetAcknowledgement() {
  const checkbox = document.getElementById('conditionAcknowledgement');
  checkbox.checked = false;
  document.getElementById('btnProceedAfterCondition').disabled = true;
}

function closeConditionReport() {
  document.getElementById('conditionReportStep').classList.add('hidden');
  if (purchaseApi.session) {
    const journey = document.getElementById('purchaseJourney');
    document.getElementById('dealAgreement').classList.remove('hidden');
    journey.classList.remove('hidden');
    journey.focus();
  } else if (state.conditionReturnFocus?.isConnected) state.conditionReturnFocus.focus();
}

function setConditionStatus(text, variant = '') {
  const status = document.getElementById('conditionReportStatus');
  status.textContent = text;
  status.className = `condition-status ${variant}`.trim();
}

function afterNextPaint() {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

function formatEuro(value) { return `${formatNumber(value)} €`; }
function formatNumber(value) { return Number(value).toLocaleString('fi-FI'); }
function formatDate(value) { return new Date(value).toLocaleString('fi-FI', { dateStyle: 'medium', timeStyle: 'short' }); }
function setText(id, value) { document.getElementById(id).textContent = value; }
function vehicleIdentity(vehicle) { return `${vehicle.makeModel} · ${vehicle.registration}`; }

const DEMO_STEPS = [
  ['condition', 'Kuntoraportti avattu'],
  ['offer', 'Asiakas ehdottaa 86 400 €'],
  ['counter-one', 'Digitaalinen automyyjä ehdottaa 93 100 €'],
  ['offer-two', 'Asiakas ehdottaa 89 800 €'],
  ['counter-two', 'Digitaalinen automyyjä ehdottaa 92 700 €'],
  ['agreement', `Hinnasta sovittu: ${formatEuro(DEMO_VEHICLE.agreedPrice)}`],
  ['payment', 'Maksutavaksi valittu käteinen / tilisiirto'],
  ['waiting', 'Auto on varattu. Maksua odotetaan. Varaus voimassa 22.7.2026 klo 18.00 asti.'],
  ['confirmed', 'Maksu vahvistettu. Auto valmistellaan luovutukseen.'],
  ['ready', 'Valmis noudettavaksi'],
];

async function runDemo() {
  const run = ++state.demoRun;
  markPreNegotiationReportOpened();
  const button = document.getElementById('btnRunDemo');
  const timeline = document.getElementById('journeyDemoTimeline');
  button.disabled = true;
  timeline.classList.remove('hidden');
  document.querySelectorAll('[data-demo-step]').forEach((item) => item.classList.remove('current', 'complete'));
  // Give the browser one paint before the first status change: some screen
  // readers only start watching an aria-live region for changes once it has
  // actually rendered, so un-hiding the region and updating its text in the
  // same tick risks the very first step going unannounced.
  await new Promise(requestAnimationFrame);
  const delay = matchMedia('(prefers-reduced-motion: reduce)').matches
    ? REDUCED_MOTION_DEMO_STEP_DELAY_MS
    : DEMO_STEP_DELAY_MS;
  for (let index = 0; index < DEMO_STEPS.length; index += 1) {
    if (run !== state.demoRun) return;
    const [key, message] = DEMO_STEPS[index];
    document.querySelectorAll('[data-demo-step]').forEach((item, itemIndex) => {
      item.classList.toggle('complete', itemIndex < index);
      item.classList.toggle('current', item.dataset.demoStep === key);
    });
    setText('journeyDemoStatus', message);
    await new Promise((resolve) => setTimeout(resolve, delay));
  }
  document.querySelectorAll('[data-demo-step]').forEach((item) => { item.classList.remove('current'); item.classList.add('complete'); });
  setText('journeyDemoStatus', 'Valmis noudettavaksi');
  button.disabled = false;
  button.textContent = 'Katso demopolku uudelleen';
  button.focus();
}

document.getElementById('btnStartDigitalSalesperson').addEventListener('click', openFlow);
document.getElementById('btnOpenPreNegotiationReport').addEventListener('click', openPreNegotiationConditionReport);
document.getElementById('btnClosePreNegotiationReport').addEventListener('click', closePreNegotiationConditionReport);
document.getElementById('preNegotiationConditionReport').addEventListener('close', restoreFocusAfterPreNegotiationReport);
document.getElementById('btnCloseFlow').addEventListener('click', closeFlow);
document.getElementById('btnRunDemo').addEventListener('click', runDemo);
document.getElementById('btnReviewCondition').addEventListener('click', continueToConditionReport);
document.getElementById('priceForm').addEventListener('submit', submitPrice);
document.getElementById('priceInput').addEventListener('input', updateDealSummary);
document.getElementById('emailRequestForm').addEventListener('submit', requestVerificationCode);
document.getElementById('emailVerifyForm').addEventListener('submit', verifyEmailCode);
document.getElementById('conditionAcknowledgement').addEventListener('change', (event) => {
  document.getElementById('btnProceedAfterCondition').disabled = !event.currentTarget.checked;
});
document.getElementById('conditionAcknowledgementForm').addEventListener('submit', submitConditionAcknowledgement);
document.getElementById('btnBackFromCondition').addEventListener('click', closeConditionReport);
document.getElementById('paymentMethods').addEventListener('click', selectPayment);
document.getElementById('btnContactSeller').addEventListener('click', () => {
  setPurchaseStatus('Ota yhteys myyjään', 'Tämä konseptidemo ei lähetä oikeaa yhteydenottopyyntöä. Myyjä voi auttaa poikkeustilanteissa ja lisäkysymyksissä.');
});
loadVehicle().catch(() => {
  setText('vehicleTitle', 'Ajoneuvotietoja ei voitu ladata');
  setText('vehicleSubtitle', 'Palaa takaisin autoihin ja yritä uudelleen.');
});
