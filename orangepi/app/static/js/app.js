// Holds the UI state, binds events, calls api.js, draws through ui.js.

import * as api from './api.js';
import * as ui from './ui.js';
import * as viz from './viz.js';
import { t, getLang, setLang, applyStatic, initI18n } from './i18n.js';

const state = {
  selectedSlot: null,
  order: null,
  slots: [],
  geometry: null,
  showViz: false,
  jogBits: { x_pos: false, x_neg: false, y_pos: false, y_neg: false, z_pos: false, z_neg: false },
  running: false,
};

/* =============================================================== machine commands */

// Every button goes through here so behaviour matches and no path forgets error
// handling. The SSE stream pushes any table/layout change that follows.
async function runCommand(label, action) {
  if (state.running) {
    ui.log(t('cmd.busy', { label }), 'warn');
    return null;
  }

  state.running = true;
  ui.log(`${label}…`);

  try {
    const result = await action();
    ui.log(result?.message || t('cmd.doneSuffix', { label }), 'ok');
    return result;
  } catch (error) {
    ui.log(t('cmd.failed', { label, err: error.message }), 'error');
    return null;
  } finally {
    state.running = false;
  }
}

const slot = () => state.selectedSlot;

/** Button -> command map. A new command is one line here. */
const ACTIONS = {
  run:   () => runCommand(t('cmd.runSlot', { slot: slot() }), () => api.runSlot(slot())),
  goto:  () => runCommand(t('cmd.gotoSlot', { slot: slot() }), () => api.gotoSlot(slot())),
  tilt:  () => runCommand(t('cmd.tiltSlot', { slot: slot() }), () => api.tiltSlot(slot())),
  teach: () => runCommand(t('cmd.teachSlot', { slot: slot() }), () => api.teachSlot(slot())),
  // LIMIT = diem cam bien, co dinh theo co khi. HOME = cho may dung nghi,
  // nguoi van hanh tu dat. Truoc day hai nut nay cung ve mot cho nen bam cai
  // nao cung nhu nhau - xem ghi chu o MC_Home trong 04_FB_XY_Tray.scl.
  home:  () => runCommand(t('cmd.home'), api.home),
  park:  () => runCommand(t('cmd.park'), api.park),
  'park-here': () => runCommand(t('cmd.parkHere'), api.parkHere),
  reset: () => runCommand(t('cmd.reset'), api.reset),
  stop:  stopNow,

  'push-table':  () => runCommand(t('cmd.pushTable'), api.pushTable),
  'reset-stock': () => resetStock(),
};

/** Emergency stop takes its own path: no lock, does not wait for a running command. */
async function stopNow() {
  try {
    await api.stop();
    ui.log(t('cmd.stopSent'), 'warn');
  } catch (error) {
    ui.log(t('cmd.stopFailed', { err: error.message }), 'error');
  }
}

async function resetStock() {
  if (!window.confirm(t('cmd.wipeAsk'))) return;
  await runCommand(t('cmd.wipeStock'), api.resetInventory, { refresh: true });
}

/* ================================================================== scan */

async function handleScan(code) {
  ui.log(t('scan.scanning', { code }));
  try {
    const result = await api.scan(code);
    ui.log(result.message, 'ok');
    state.selectedSlot = result.slot;
    ui.markSelectedSlot(result.slot);
    await loadOrder(result.slot);   // the slot table redraws via the SSE stream
  } catch (error) {
    ui.log(t('scan.failed', { code, err: error.message }), 'error');
  }
}

/** Fetch the order sitting in a slot; 404 = the slot has none. */
async function loadOrder(slot) {
  if (!slot) {
    state.order = null;
    ui.renderOrder(null);
    return;
  }
  try {
    const data = await api.getOrderAtSlot(slot);
    state.order = data.order;
  } catch {
    state.order = null;
  }
  ui.renderOrder(state.order);
}

/* ================================================================== manual jog */

async function pushJog(direction, pressed) {
  if (state.jogBits[direction] === pressed) return;
  state.jogBits[direction] = pressed;

  try {
    await api.setJog(state.jogBits);
  } catch (error) {
    ui.log(t('cmd.jogFailed', { err: error.message }), 'error');
  }
}

/** Release every direction. Called on pointer leave, blur, or page unload. */
async function releaseAllJog() {
  if (!Object.values(state.jogBits).some(Boolean)) return;

  Object.keys(state.jogBits).forEach((key) => { state.jogBits[key] = false; });
  document.querySelectorAll('.jog').forEach((button) => ui.markJogHeld(button, false));

  try {
    await api.setJog(state.jogBits);
  } catch {
    /* release failed -> the PLC still cuts jog off after JogMaxTime */
  }
}

/* ============================================ data (pushed over the SSE stream) */

// Draw a slots_payload ({slots, summary}) - from the SSE "inventory" event or a
// one-shot GET. state keeps a copy so the 3D view and a language switch can
// redraw without re-fetching.
function applyInventory({ slots, summary }) {
  state.slots = slots;
  ui.renderSlots(slots, summary);
  redrawViz();
  if (state.selectedSlot) loadOrder(state.selectedSlot);
}

// Draw a geometry_payload - from the SSE "layout" event or a one-shot GET.
function applyLayout({ geometry, derived, problems, speed_warnings: speedWarnings }) {
  state.geometry = geometry;
  ui.fillGeometryForm(geometry);
  ui.renderDerived(derived);
  ui.renderProblems(problems || [], speedWarnings || []);
  redrawViz();
}

function redrawViz() {
  if (state.showViz && state.geometry && state.slots.length) {
    viz.initViz(document.getElementById('viz'), state.geometry, state.slots);
    // initViz dung lai ca cay DOM - to sang lai cho khoi mat danh dau.
    viz.markPickedSlot(state.selectedSlot);
  }
}

// One-shot pulls. Only used to repaint in the other language after a switch -
// the SSE stream does not re-send on its own.
async function pullSlots() {
  try { applyInventory(await api.getSlots()); }
  catch (error) { ui.log(t('slots.readFail', { err: error.message }), 'error'); }
}
async function pullLayout() {
  try { applyLayout(await api.getGeometry()); }
  catch (error) { ui.log(t('cfg.readFail', { err: error.message }), 'error'); }
}

/* ============================================================== event binding */

/** Toggle the machine diagram. Off means it stops drawing, saving screen and CPU. */
function setVizVisible(visible) {
  state.showViz = visible;
  localStorage.setItem('showViz', visible ? '1' : '0');

  document.getElementById('viz-panel').classList.toggle('is-hidden', !visible);
  document.getElementById('viz-toggle').setAttribute('aria-pressed', String(visible));
  // 3D off -> Chu trinh panel stretches across the whole bottom row (see CSS).
  document.querySelector('[data-panel="operate"]').classList.toggle('is-3d-off', !visible);

  if (visible && state.geometry && state.slots.length) {
    viz.initViz(document.getElementById('viz'), state.geometry, state.slots);
    // initViz dung lai ca cay DOM - to sang lai cho khoi mat danh dau.
    viz.markPickedSlot(state.selectedSlot);
  }
}

function bindVizToggle() {
  const saved = localStorage.getItem('showViz') === '1';
  setVizVisible(saved);
  document.getElementById('viz-toggle')
    .addEventListener('click', () => setVizVisible(!state.showViz));
}

/* Theme is set by the inline <head> script; here we only swap the icon and keep the click. */
function currentTheme() {
  return document.documentElement.getAttribute('data-theme')
    || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

function paintThemeIcon() {
  const dark = currentTheme() === 'dark';
  document.getElementById('ico-sun').classList.toggle('is-hidden', dark);
  document.getElementById('ico-moon').classList.toggle('is-hidden', !dark);
}

function bindTheme() {
  paintThemeIcon();
  document.getElementById('theme-btn').addEventListener('click', () => {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    paintThemeIcon();
  });
}

/* VI / EN toggle, next to the theme button. Static strings redraw at once; the
   status panel picks the new language up on the SSE stream's next tick. */
function bindLang() {
  const label = document.getElementById('lang-label');
  const paint = () => { label.textContent = getLang() === 'en' ? 'EN' : 'VI'; };
  applyStatic();
  paint();

  document.getElementById('lang-btn').addEventListener('click', () => {
    setLang(getLang() === 'en' ? 'vi' : 'en', () => {
      paint();
      ui.markSelectedSlot(state.selectedSlot);
      ui.renderOrder(state.order);
      pullLayout();
      pullSlots();
    });
  });
}

function bindTabs() {
  document.getElementById('tabs').addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (!tab) return;
    ui.showTab(tab.dataset.tab);
  });
}

function bindSlotButtons() {
  document.getElementById('tray').addEventListener('click', (event) => {
    const button = event.target.closest('.slot');
    if (!button) return;
    const picked = Number(button.dataset.slot);
    // Click the picked slot again -> deselect, like the app.
    state.selectedSlot = state.selectedSlot === picked ? null : picked;
    ui.markSelectedSlot(state.selectedSlot);
    viz.markPickedSlot(state.selectedSlot);
    loadOrder(state.selectedSlot);
  });
}

function bindActionButtons() {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button || button.disabled) return;
    ACTIONS[button.dataset.action]?.();
  });
}

/** Take the code from a scan gun with NO input field on the page.
 *
 *  A scan gun is a keyboard: it types each character then Enter. We used to keep
 *  a hidden input focused to catch it, and one stray click lost the code. Now we
 *  listen on the document: scan from anywhere.
 *
 *  We tell a gun from a human by RHYTHM: a gun fires the whole code in tens of
 *  milliseconds, a human does not. Past GAP_MS with no Enter it counts as typing
 *  and we drop it, so shortcuts and stray keys never become a scan.
 */
/** Vong loang ra tu dung cho ngon tay vua cham vao nut.
 *
 *  Bat o pointerdown chu khong phai click: phan hoi phai den NGAY luc ngon tay
 *  cham, khong doi nha ra. Nghe o document nen nut nao them sau nay cung co,
 *  khong phai mac day tung cai.
 *
 *  Don bang ca animationend lan hen gio: neu tab bi an di giua chung thi
 *  animation khong bao gio ket thuc, khong don la ripple nam lai mai.
 */
function bindRipple() {
  const SELECTOR = '.btn, .jog, .tab, .icon-btn, .toggle';

  document.addEventListener('pointerdown', (event) => {
    const target = event.target.closest(SELECTOR);
    if (!target || target.disabled) return;

    const rect = target.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;
    ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${event.clientY - rect.top - size / 2}px`;

    const drop = () => ripple.remove();
    ripple.addEventListener('animationend', drop, { once: true });
    setTimeout(drop, 900);
    target.appendChild(ripple);
  });
}


function bindScanGun() {
  const GAP_MS = 60;
  let buffer = '';
  let last = 0;

  document.addEventListener('keydown', async (event) => {
    // Typing in a real input (config, manual) -> leave it alone.
    const tag = event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || event.target.isContentEditable) return;

    const now = event.timeStamp;
    if (now - last > GAP_MS) buffer = '';
    last = now;

    if (event.key === 'Enter') {
      const code = buffer.trim();
      buffer = '';
      if (code.length >= 3) await handleScan(code);
      return;
    }
    if (event.key.length === 1) buffer += event.key;
  });
}

function bindManualForms() {
  document.getElementById('move-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const data = new FormData(event.target);
    const x = Number(data.get('x'));
    const z = Number(data.get('z'));
    runCommand(t('cmd.moveTo', { x, z }), () => api.moveTo(x, z));
  });

  document.getElementById('tilt-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const angle = Number(new FormData(event.target).get('angle'));
    runCommand(t('cmd.tiltTo', { angle }), () => api.tiltTo(angle));
  });

  document.getElementById('geometry-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const geometry = ui.readGeometryForm();

    ui.showSyncBanner(t('sync.saving'), 'warn');
    const result = await runCommand(t('cmd.saveConfig'), () => api.saveGeometry(geometry));

    if (!result) {
      ui.showSyncBanner(t('sync.saveFailed'), 'error');
      return;
    }

    // The SSE stream repaints the form, derived table and slot grid from the
    // bumped revisions; here we only handle the one-off messages.
    const plan = result.layout;
    if (plan) ui.log(t('cfg.newLayout', { slots: plan.slots, rows: plan.rows, cols: plan.columns }));

    // Layout shrank -> the last slots vanish; say which ones still hold items.
    if (result.orphans?.length) {
      const list = result.orphans
        .map((o) => t('cfg.orphanItem', { slot: o.slot, count: o.count }))
        .join(', ');
      ui.log(t('cfg.orphans', { list }), 'warn');
    }
    if (result.pushed) ui.log(result.pushed, result.push_ok ? 'ok' : 'error');

    // push_ok is a real boolean from the server, no more "CHUA" string test.
    if (result.push_ok) {
      ui.showSyncBanner(t('sync.done'), 'ok');
      setTimeout(ui.hideSyncBanner, 4000);
    } else {
      ui.showSyncBanner(t('sync.failed', { reason: result.pushed || t('sync.badConfig') }), 'error');
    }
  });
}

function bindJogPad() {
  document.querySelectorAll('.jog').forEach((button) => {
    const direction = button.dataset.jog;

    const press = (event) => {
      event.preventDefault();
      ui.markJogHeld(button, true);
      pushJog(direction, true);
    };

    const release = () => {
      ui.markJogHeld(button, false);
      pushJog(direction, false);
    };

    button.addEventListener('pointerdown', press);
    button.addEventListener('pointerup', release);
    button.addEventListener('pointerleave', release);
    button.addEventListener('pointercancel', release);
  });

  // Leaving the page or switching tabs mid-hold -> release to be safe.
  window.addEventListener('blur', releaseAllJog);
  window.addEventListener('pagehide', releaseAllJog);
}

/* ==================================================================== startup */

async function start() {
  await initI18n();   // language files must be in before the first render

  bindLang();
  bindVizToggle();
  bindTheme();
  bindTabs();
  bindSlotButtons();
  bindActionButtons();
  bindRipple();
  bindScanGun();
  bindManualForms();
  bindJogPad();
  ui.markSelectedSlot(null);
  ui.renderOrder(null);

  // One SSE stream: status + inventory + layout, all pushed. The server sends
  // all three once on connect, so there is nothing to fetch up front.
  let wasDown = false;
  api.openEventStream({
    status: (snapshot) => {
      ui.renderStatus(snapshot);
      if (state.showViz && snapshot.status) {
        viz.updateViz(snapshot.status, snapshot.status.slot);
      }
    },
    inventory: applyInventory,
    layout: applyLayout,
    linkChange: (up) => {
      if (!up && !wasDown) ui.log(t('log.sseDropped'), 'warn');
      wasDown = !up;
    },
  });

  ui.log(t('log.ready'));
}

start();
