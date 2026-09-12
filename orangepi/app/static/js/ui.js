// Every DOM touch lives here. No API calls, no business logic.

import { t, getLang } from './i18n.js';

const el = {
  connPill: document.getElementById('conn-pill'),
  connText: document.getElementById('conn-text'),
  posX: document.getElementById('pos-x'),
  posY: document.getElementById('pos-y'),
  posZ: document.getElementById('pos-z'),
  summaryText: document.getElementById('summary-text'),
  selectedSlot: document.getElementById('selected-slot'),
  tray: document.getElementById('tray'),
  orderLine: document.getElementById('order-line'),
  trayHint: document.getElementById('tray-hint'),
  log: document.getElementById('log'),
  statecard: document.getElementById('statecard'),
  stateWhere: document.getElementById('state-where'),
  stateStage: document.getElementById('state-stage'),
  stateResult: document.getElementById('state-result'),
  stages: document.getElementById('stages'),
  alert: document.getElementById('alert'),
  syncBanner: document.getElementById('sync-banner'),
  derived: document.getElementById('derived'),
  problems: document.getElementById('problems'),
  geometryForm: document.getElementById('geometry-form'),
};

/** Buttons that only work once a slot is picked. */
const SLOT_ACTIONS = ['run', 'goto', 'tilt', 'teach'];

// FB_XY_Tray step -> which progress stage lights up. Matches CASE #StepNo in
// 04_FB_XY_Tray.scl. The step text itself comes from i18n ('step.<n>').
const STAGE_OF = {
  10: 0, 20: 1, 30: 2,
  100: 3, 170: 3, 175: 3, 180: 3, 190: 3,
  195: 4, 200: 4, 210: 4, 220: 4,
};

function stepText(step) {
  const key = `step.${step}`;
  const text = t(key);
  return text === key ? t('step.other', { step }) : text;
}

function resultText(result) {
  const key = `result.${result}`;
  const text = t(key);
  return text === key ? t('result.other', { code: result }) : text;
}

const POSITION_TOLERANCE = 3.0;   // mm, closer than this counts as "arrived"
let slotRows = [];

/* ------------------------------------------------------------------- tab */

export function showTab(name) {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.toggle('is-active', tab.dataset.tab === name);
  });
  document.querySelectorAll('[data-panel]').forEach((panel) => {
    panel.classList.toggle('is-hidden', panel.dataset.panel !== name);
  });
}

/* ------------------------------------------------------------ trang thai */

export function renderStatus(snapshot) {
  const { online, status, last_error: lastError } = snapshot;

  if (!online || !status) {
    setConnection('offline', lastError ? t('conn.offlineWhy', { err: lastError }) : t('conn.offline'));
    el.posX.textContent = el.posY.textContent = el.posZ.textContent = '—';
    el.stateWhere.textContent = '—';
    el.stateStage.textContent = t('conn.offline');
    el.statecard.dataset.state = 'error';
    // Mat ket noi thi khong con biet chan nao dang bat - xoa di, de so cu nam
    // lai la nguoi van hanh tuong cam bien van dang bao.
    renderSensors(null);
    markActiveSlot(null);
    return;
  }

  el.posX.textContent = status.x.toFixed(1);
  el.posY.textContent = status.y.toFixed(1);
  el.posZ.textContent = status.z.toFixed(1);

  if (status.error) {
    setConnection('error', t('conn.error', { code: status.error_id_hex }));
  } else if (status.busy) {
    setConnection('busy', t('conn.busy', { step: status.step }));
  } else if (!status.homed) {
    setConnection('online', t('conn.notHomed'));
  } else if (status.ready) {
    setConnection('online', t('conn.ready'));
  } else {
    setConnection('online', t('conn.noPower'));
  }

  el.stateWhere.textContent = describeWhere(status);
  el.stateStage.textContent = stepText(status.step);
  el.stateResult.textContent = resultText(status.result);
  el.statecard.dataset.state =
    status.error ? 'error' : status.busy ? 'busy' : status.homed ? 'ready' : 'idle';

  renderStages(status, STAGE_OF[status.step] ?? null);
  renderAlert(status);
  renderSensors(status.inputs);
  markActiveSlot(status.busy ? status.slot : null);
}

/**
 * Trang thai song cua cac chan cam bien.
 *
 * De doi chieu chan nao noi voi cai gi: che vat vao khe cam bien roi nhin chan
 * nao doi sang BAT. Truoc day phai mo TIA tao watch table moi biet.
 */
function renderSensors(inputs) {
  const o = document.getElementById('sensor-row');
  if (!o) return;
  if (!inputs) {
    o.textContent = t('sensor.waiting');
    return;
  }
  o.textContent = Object.entries(inputs)
    .map(([chan, bat]) => `${chan} ${bat ? t('sensor.on') : t('sensor.off')}`)
    .join(' · ');
}


function setConnection(state, text) {
  el.connPill.dataset.state = state;
  el.connText.textContent = text;
}

// Turn the X-Z numbers into a phrase: at which slot, at the park spot, or moving.
function describeWhere(status) {
  if (status.busy) {
    return status.slot > 0 ? t('where.runningTo', { slot: status.slot }) : t('where.moving');
  }
  const near = slotRows.find((row) =>
    Math.abs(row.x - status.x) <= POSITION_TOLERANCE &&
    Math.abs(row.z - status.z) <= POSITION_TOLERANCE);
  if (near) return t('where.atSlot', { slot: near.slot });
  if (Math.abs(status.x) <= POSITION_TOLERANCE && Math.abs(status.z) <= POSITION_TOLERANCE) {
    return t('where.park');
  }
  return t('where.freeXZ', { x: status.x.toFixed(0), z: status.z.toFixed(0) });
}

function renderStages(status, activeStage) {
  el.stages.querySelectorAll('li').forEach((item) => {
    const index = Number(item.dataset.stage);
    if (status.error) {
      item.dataset.state = 'error';
    } else if (activeStage === null) {
      item.dataset.state = (status.result === 2 && !status.busy) ? 'done' : 'todo';
    } else if (index < activeStage) {
      item.dataset.state = 'done';
    } else if (index === activeStage) {
      item.dataset.state = 'active';
    } else {
      item.dataset.state = 'todo';
    }
  });
}

/**
 * Ma loi Motion Control hay gap, dich sang cau noi duoc viec phai lam.
 *
 * 16#8402 la cai de dinh nhat: dat toc do cao hon Max velocity cua truc trong
 * TIA thi MC_MoveAbsolute tu choi ngay, FB nhay buoc 900 va may dung im - nhin
 * ma hex tran thi khong ai doan ra. Giu khop voi ERROR_HINTS trong Machine.kt
 * cua app Android.
 */
const ERROR_HINT_CODES = ['0x8400', '0x8402', '0x8403', '0x8404'];

function errorHint(hex) {
  const code = String(hex).toUpperCase().replace('0X', '0x');
  return ERROR_HINT_CODES.includes(code) ? t(`hint.${code}`) : '';
}

function renderAlert(status) {
  let message = '';
  if (status.error) {
    const hint = errorHint(status.error_id_hex);
    message = t('alert.faultHead', { code: status.error_id_hex })
            + (hint ? ` ${hint}` : '')
            + ` ${t('alert.faultTail')}`;
  } else if (status.result === 3) {
    message = t('alert.stoppedMidway');
  } else if (status.result === 6) {
    // Khong phai loi - truc cham vach gioi han va dung lai dung nhu phai the.
    // Van bao mot dong vi chu trinh chua chay het, nguoi van hanh can biet.
    message = t('alert.hitLimit');
  } else if (!status.homed) {
    message = t('alert.notHomed');
  }

  el.alert.textContent = message;
  el.alert.classList.toggle('is-hidden', !message);
  el.alert.dataset.level = status.error ? 'error' : 'warn';
}

/* --------------------------------------------------------------- ton kho */

/** Ve lai luoi khay: ma hang, so luong, thanh muc day. */
/** Mot nut khay. Dung rieng de renderSlots chi lo viec xep nhom. */
function buildSlotButton(row) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'slot';
  button.dataset.slot = row.slot;

  ['slot__number', 'slot__code', 'slot__count'].forEach((cls) => {
    const span = document.createElement('span');
    span.className = cls;
    button.append(span);
  });
  const bar = document.createElement('span');
  bar.className = 'slot__bar';
  bar.append(document.createElement('i'));
  button.append(bar);

  return button;
}

/** Gom cac ro thanh tung cum theo (hang, ben) - dung thu tu tren xuong. */
function groupSlots(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = `${row.row}|${row.side}`;
    if (!groups.has(key)) {
      groups.set(key, { row: row.row, side: row.side, rows: [] });
    }
    groups.get(key).rows.push(row);
  });
  return [...groups.values()];
}

/** Dung lai ca luoi khi so ro thay doi. Giu nguyen neu bo cuc van the. */
function rebuildTray(rows) {
  // Lang in the key too: switching VI/EN must redraw the row labels.
  const shape = `${rows.map((r) => r.slot).join(',')}|${getLang()}`;
  if (el.tray.dataset.shape === shape) return;
  el.tray.dataset.shape = shape;

  el.tray.replaceChildren(...groupSlots(rows).map((group) => {
    const box = document.createElement('div');
    box.className = 'tray__quadrant';
    box.dataset.side = group.side;

    const label = document.createElement('span');
    label.className = 'tray__label';
    label.textContent = t('tray.rowLabel', {
      side: group.side === 'phai' ? t('side.right') : t('side.left'),
      row: group.row + 1,
    });

    const slots = document.createElement('div');
    slots.className = 'tray__slots';
    slots.append(...group.rows.map(buildSlotButton));

    box.append(label, slots);
    return box;
  }));
}

export function renderSlots(rows, summary) {
  slotRows = rows;
  rebuildTray(rows);
  const byNumber = new Map(rows.map((r) => [r.slot, r]));

  el.tray.querySelectorAll('.slot').forEach((button) => {
    const row = byNumber.get(Number(button.dataset.slot));
    if (!row) return;

    const ratio = row.capacity ? row.count / row.capacity : 0;
    button.dataset.fill = ratio >= 1 ? 'full' : ratio >= 0.7 ? 'warn' : 'ok';
    button.querySelector('.slot__number').textContent = row.slot;
    button.querySelector('.slot__code').textContent = row.code || '';
    button.querySelector('.slot__count').textContent = `${row.count}/${row.capacity}`;
    button.querySelector('.slot__bar i').style.width = `${Math.min(ratio, 1) * 100}%`;
    const side = row.side === 'phai' ? t('side.right') : t('side.left');
    button.title = t('slot.title', { slot: row.slot, x: row.x, z: row.z, dir: side });
  });

  el.summaryText.textContent = t('tray.summary', {
    items: summary.total_items,
    cap: summary.total_capacity,
    full: summary.full_slots,
    empty: summary.empty_slots,
  });
}

/* ---------------------------------------------------------------- order line */

// The SKU checklist for the picked slot, like the app's OrderLine. Null / an
// empty order hides it and brings the generic hint back.
function el_(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

// "DH-3001 · 3/3 món · ĐỦ" — done count vs total, then complete / missing.
function orderStatusLine(order) {
  const tail = order.complete
    ? t('order.complete')
    : t('order.missing', { n: order.total - order.done });
  return `${t('order.progress', { done: order.done, total: order.total })} · ${tail}`;
}

function orderChips(order, into) {
  const box = into || el_('div', 'order-line__chips');
  order.items.forEach((item) => {
    const chip = el_('span', 'order-chip', `${item.scanned ? '✓' : '○'} ${item.sku}`);
    chip.dataset.scanned = item.scanned ? '1' : '0';
    box.append(chip);
  });
  return box;
}

export function renderOrder(order) {
  if (!order || !order.items || order.items.length === 0) {
    el.orderLine.classList.add('is-hidden');
    el.orderLine.replaceChildren();
    el.trayHint?.classList.remove('is-hidden');
    return;
  }

  el.trayHint?.classList.add('is-hidden');
  el.orderLine.classList.remove('is-hidden');

  // One flowing row: the status text and the SKU chips wrap together, with the
  // QR button held to the right — same as the app's OrderLine FlowRow.
  const flow = el_('div', 'order-line__flow');
  const label = el_('span', 'order-line__label',
    `${order.order} · ${orderStatusLine(order)}`);
  label.dataset.state = order.complete ? 'ok' : 'warn';
  flow.append(label);
  orderChips(order, flow);

  // FilledTonalButton with a QR icon then the label, like the app's OrderLine.
  const qrBtn = el_('button', 'btn order-qr-btn');
  qrBtn.type = 'button';
  qrBtn.innerHTML =
    '<svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden="true">'
    + '<path d="M3 3h8v8H3V3zm2 2v4h4V5H5zm-2 8h8v8H3v-8zm2 2v4h4v-4H5zM13 3h8v8h-8V3zm2 2v4h4V5h-4z'
    + 'M13 13h2v2h-2v-2zm4 0h2v2h-2v-2zm-4 4h2v2h-2v-2zm2 2h2v2h-2v-2zm2-2h2v2h-2v-2zm2 2h2v2h-2v-2zm0-4h2v2h-2v-2z"/>'
    + '</svg>';
  qrBtn.append(el_('span', null, t('order.qr')));
  qrBtn.addEventListener('click', () => openQr(order));

  const row = el_('div', 'order-line__row');
  row.append(flow, qrBtn);
  el.orderLine.replaceChildren(row);
}

// QR dialog, laid out like the app's OrderQrDialog: order code as the title, a
// big QR, the slot/progress line, the SKU checklist, then a hint and Close.
function openQr(order) {
  const overlay = el_('div', 'modal-overlay');
  const card = el_('div', 'modal-card qr-card');

  const img = el_('img', 'qr-img');
  img.alt = order.order;
  img.src = `/api/orders/${encodeURIComponent(order.order)}/qr`;
  const frame = el_('div', 'qr-frame');
  frame.append(img);

  const status = el_('div', 'qr-status',
    `${t('cycle.slotNo', { slot: order.slot })} · ${orderStatusLine(order)}`);
  status.dataset.state = order.complete ? 'ok' : 'warn';

  // Plain text button bottom-right, like the app's AlertDialog confirmButton.
  const close = el_('button', 'btn btn--link modal-close', t('order.close'));
  close.type = 'button';

  const dismiss = () => {
    overlay.remove();
    document.removeEventListener('keydown', onKey);
  };
  function onKey(event) { if (event.key === 'Escape') dismiss(); }

  close.addEventListener('click', dismiss);
  overlay.addEventListener('click', (event) => { if (event.target === overlay) dismiss(); });
  document.addEventListener('keydown', onKey);

  card.append(
    el_('h3', 'modal-title', order.order),
    frame,
    status,
    orderChips(order),
    el_('p', 'qr-hint', t('order.qrHint')),
    close,
  );
  overlay.append(card);
  document.body.append(overlay);
}

/* ---------------------------------------------------------------- chon khay */

export function markSelectedSlot(slot) {
  el.tray.querySelectorAll('.slot').forEach((button) => {
    button.classList.toggle('is-selected', Number(button.dataset.slot) === slot);
  });

  el.selectedSlot.textContent = slot ? t('cycle.slotNo', { slot }) : t('cycle.noSlot');

  const hint = document.getElementById('manual-slot-hint');
  if (hint) {
    hint.textContent = slot ? t('manual.slotHintOn', { slot }) : t('manual.slotHintNone');
  }

  SLOT_ACTIONS.forEach((action) => {
    document.querySelectorAll(`[data-action="${action}"]`)
      .forEach((button) => { button.disabled = !slot; });
  });
}

function markActiveSlot(slot) {
  el.tray.querySelectorAll('.slot').forEach((button) => {
    button.classList.toggle('is-active', slot > 0 && Number(button.dataset.slot) === slot);
  });
}

/* ---------------------------------------------------------------- cau hinh */

export function fillGeometryForm(geometry) {
  Object.entries(geometry).forEach(([key, value]) => {
    const input = el.geometryForm.elements.namedItem(key);
    if (input) input.value = value;
  });

  // The tilt hint carries the real software limit, filled here (not in HTML) so
  // it tracks y_max_angle and re-renders in the right language.
  const hint = document.getElementById('tilt-hint');
  if (hint) hint.innerHTML = t('cfg.tiltHint', { limit: geometry.y_max_angle });

  // Jog tay chay dung VelX / VelZ / TiltVel, khong co toc do rieng nua. Hien
  // len de nguoi van hanh biet minh dang thu o toc do nao.
  const jogNote = document.getElementById('jog-speed-note');
  if (jogNote) {
    jogNote.textContent = `X ${geometry.vel_x} mm/s · Z ${geometry.vel_z} mm/s`
                        + ` · ${t('jog.tiltWord')} ${geometry.tilt_vel} °/s`;
  }
}

export function readGeometryForm() {
  const out = {};
  new FormData(el.geometryForm).forEach((value, key) => { out[key] = Number(value); });
  return out;
}

export function renderDerived(derived) {
  el.derived.replaceChildren(...Object.entries(derived).map(([key, value]) => {
    const li = document.createElement('li');
    const name = document.createElement('span');
    const label = t(`derived.${key}`);
    name.textContent = label === `derived.${key}` ? key : label;
    const bold = document.createElement('b');
    bold.textContent = value;
    li.append(name, bold);
    return li;
  }));
}

/* ------------------------------------------------------------- sync banner */

// Result of the last Save, right next to the button. level: ok | warn | error.
export function showSyncBanner(text, level) {
  if (!el.syncBanner) return;
  el.syncBanner.textContent = text;
  el.syncBanner.dataset.level = level;
  el.syncBanner.classList.remove('is-hidden');
}

export function hideSyncBanner() {
  el.syncBanner?.classList.add('is-hidden');
}

// Hai loai, hai mau: problems la cau hinh tu mau thuan nen KHONG day xuong PLC
// duoc, con speed_warnings chi la toc do vuot tran driver - may van chay, nhung
// truc se bao 16#8402 roi dung im. Gop mot cho cho nguoi van hanh khoi phai
// nhin hai noi, tach bang data-level de nhin ra cai nao chan cai nao khong.
export function renderProblems(problems, speedWarnings = []) {
  if (!el.problems) return;
  const row = (text, level) => {
    const li = document.createElement('li');
    li.textContent = text;
    li.dataset.level = level;
    return li;
  };
  el.problems.replaceChildren(
    ...problems.map((t) => row(t, 'error')),
    ...speedWarnings.map((t) => row(t, 'warn')),
  );
}

/* ----------------------------------------------------------------- jog */

export function markJogHeld(button, held) {
  button.classList.toggle('is-held', held);
}

/* ---------------------------------------------------------------- nhat ky */

const LOG_LIMIT = 200;

export function log(message, level = 'info') {
  const item = document.createElement('li');
  item.dataset.level = level;

  const time = document.createElement('time');
  time.textContent = new Date().toLocaleTimeString(getLang() === 'en' ? 'en-GB' : 'vi-VN');

  const text = document.createElement('span');
  text.textContent = message;

  item.append(time, text);
  el.log.prepend(item);

  while (el.log.children.length > LOG_LIMIT) {
    el.log.lastElementChild.remove();
  }
}

