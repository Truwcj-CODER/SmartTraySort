// Moi thao tac cham vao DOM nam o day. Khong goi API, khong giu logic nghiep vu.

const el = {
  connPill: document.getElementById('conn-pill'),
  connText: document.getElementById('conn-text'),
  posX: document.getElementById('pos-x'),
  posY: document.getElementById('pos-y'),
  posZ: document.getElementById('pos-z'),
  stockTotal: document.getElementById('stock-total'),
  summaryText: document.getElementById('summary-text'),
  selectedSlot: document.getElementById('selected-slot'),
  tray: document.getElementById('tray'),
  log: document.getElementById('log'),
  statecard: document.getElementById('statecard'),
  stateWhere: document.getElementById('state-where'),
  stateStage: document.getElementById('state-stage'),
  stateResult: document.getElementById('state-result'),
  stages: document.getElementById('stages'),
  alert: document.getElementById('alert'),
  derived: document.getElementById('derived'),
  problems: document.getElementById('problems'),
  geometryForm: document.getElementById('geometry-form'),
};

/** Cac nut chi bam duoc khi da chon khay. */
const SLOT_ACTIONS = ['run', 'goto', 'tilt', 'teach', 'item-add', 'item-remove', 'item-clear'];

// Buoc trong FB_XY_Tray -> chu tieng Viet + giai doan tren thanh tien trinh.
// Khop voi CASE #StepNo trong 04_FB_XY_Tray.scl
const STEPS = {
  0:   { text: 'chờ lệnh', stage: null },
  5:   { text: 'đang lấy gốc tọa độ', stage: null },
  10:  { text: 'chạy ngang tới khay', stage: 0 },
  20:  { text: 'lên xuống tới khay', stage: 1 },
  30:  { text: 'dừng ổn định tại khay', stage: 2 },
  100: { text: 'chuẩn bị lật', stage: 3 },
  170: { text: 'đang lật ra', stage: 3 },
  175: { text: 'giữ ở góc lật', stage: 3 },
  180: { text: 'lật về giữa', stage: 3 },
  190: { text: 'lật xong', stage: 3 },
  195: { text: 'đưa trục lật về giữa', stage: 4 },
  200: { text: 'nâng hạ về chỗ chờ', stage: 4 },
  210: { text: 'chạy ngang về chỗ chờ', stage: 4 },
  220: { text: 'hoàn tất chu trình', stage: 4 },
  300: { text: 'lật tay tới góc đặt', stage: null },
  900: { text: 'DỪNG VÌ LỖI', stage: null },
  950: { text: 'đang xóa lỗi…', stage: null },
};

const RESULT_TEXT = {
  0: 'chưa chạy lệnh nào',
  1: 'đang chạy',
  2: 'hoàn thành',
  3: 'bị dừng giữa chừng',
  4: 'lỗi',
  5: 'lệnh không hợp lệ',
};

const POSITION_TOLERANCE = 3.0;   // mm, sai lech nho hon nay coi nhu da toi noi
let slotRows = [];

const DERIVED_LABELS = {
  so_ro: 'Số rổ máy xếp được',
  buoc_ngang_mm: 'Bước ngang giữa 2 rổ (mm)',
  khe_ho_that_mm: 'Khe hở thật sau khi trải đều (mm)',
  buoc_hang_mm: 'Bước giữa 2 hàng (mm)',
  x_pulses_per_mm: 'X — xung mỗi mm',
  z_pulses_per_mm: 'Z — xung mỗi mm',
  y_pulses_per_degree: 'Y — xung mỗi độ',
  x_pulses_full_travel: 'X — xung hết hành trình',
  z_pulses_full_travel: 'Z — xung hết hành trình',
  y_pulses_full_range: 'Y — xung hết góc lật',
  x_max_velocity_mm_s: 'X — tốc độ trần (mm/s)',
  z_max_velocity_mm_s: 'Z — tốc độ trần (mm/s)',
  y_max_velocity_deg_s: 'Y — tốc độ trần (°/s)',
};

/**
 * Ma loi Motion Control hay gap, dich sang cau noi duoc viec phai lam.
 *
 * 16#8402 la cai de dinh nhat: dat toc do cao hon Max velocity cua truc trong
 * TIA thi MC_MoveAbsolute tu choi ngay, FB nhay buoc 900 va may dung im - nhin
 * ma hex tran thi khong ai doan ra.
 */
const ERROR_HINTS = {
  '0x8400': 'sai tham so lenh chay - kiem tra lai toa do gui xuong.',
  '0x8402': 'tốc độ vượt trần Max velocity của trục trong TIA. Giảm tốc độ ở trang '
          + 'Cài đặt, hoặc nâng Dynamics → Max velocity trong TIA rồi nạp lại.',
  '0x8403': 'gia tốc vượt trần Max acceleration của trục trong TIA.',
  '0x8404': 'giật (jerk) vượt trần khai báo trong TIA.',
};

function errorHint(hex) {
  return ERROR_HINTS[String(hex).toUpperCase().replace('0X', '0x')] ?? '';
}

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
    setConnection('offline', lastError ? `mất kết nối — ${lastError}` : 'mất kết nối PLC');
    el.posX.textContent = el.posY.textContent = el.posZ.textContent = '—';
    el.stateWhere.textContent = '—';
    el.stateStage.textContent = 'mất kết nối';
    el.statecard.dataset.state = 'error';
    markActiveSlot(null);
    return;
  }

  el.posX.textContent = status.x.toFixed(1);
  el.posY.textContent = status.y.toFixed(1);
  el.posZ.textContent = status.z.toFixed(1);

  if (status.error) {
    setConnection('error', `lỗi — ${status.error_id_hex}`);
  } else if (status.busy) {
    setConnection('busy', `đang chạy — bước ${status.step}`);
  } else if (!status.homed) {
    setConnection('online', 'chưa lấy gốc tọa độ');
  } else if (status.ready) {
    setConnection('online', 'sẵn sàng');
  } else {
    setConnection('online', 'chưa cấp điện trục');
  }

  renderStateCard(status);
  markActiveSlot(status.busy ? status.slot : null);
}

function setConnection(state, text) {
  el.connPill.dataset.state = state;
  el.connText.textContent = text;
}

/** Bang trang thai: dang o dau, dang lam gi, lenh cuoi ra sao. */
function renderStateCard(status) {
  const step = STEPS[status.step] ?? { text: `bước ${status.step}`, stage: null };

  el.stateWhere.textContent = describeWhere(status);
  el.stateStage.textContent = step.text;
  el.stateResult.textContent = RESULT_TEXT[status.result] ?? `mã ${status.result}`;

  el.statecard.dataset.state =
    status.error ? 'error' : status.busy ? 'busy' : status.homed ? 'ready' : 'idle';

  renderStages(status, step.stage);
  renderAlert(status);
}

/** Doi tri so X-Z thanh cau chu: dang o khay nao, o cho cho, hay dang chay. */
function describeWhere(status) {
  if (status.busy) {
    return status.slot > 0 ? `đang chạy → khay ${status.slot}` : 'đang di chuyển';
  }

  const near = slotRows.find((row) =>
    Math.abs(row.x - status.x) <= POSITION_TOLERANCE &&
    Math.abs(row.z - status.z) <= POSITION_TOLERANCE);
  if (near) return `khay ${near.slot}`;

  if (Math.abs(status.x) <= POSITION_TOLERANCE && Math.abs(status.z) <= POSITION_TOLERANCE) {
    return 'vị trí chờ (home)';
  }
  return `ngang ${status.x.toFixed(0)} · cao ${status.z.toFixed(0)}`;
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

function renderAlert(status) {
  let message = '';
  if (status.error) {
    const hint = errorHint(status.error_id_hex);
    message = `MÁY DỪNG VÌ LỖI — mã ${status.error_id_hex}. `
            + (hint ? `${hint} ` : '')
            + 'Kiểm tra cơ cấu rồi bấm Xóa lỗi, sau đó Lấy gốc tọa độ.';
  } else if (status.result === 3) {
    message = 'Chu trình trước bị dừng giữa chừng. Kiểm tra vị trí rồi chạy lại.';
  } else if (!status.homed) {
    message = 'Chưa lấy gốc tọa độ — bấm "Lấy gốc tọa độ" trước khi chạy.';
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
  const shape = rows.map((r) => r.slot).join(',');
  if (el.tray.dataset.shape === shape) return;
  el.tray.dataset.shape = shape;

  el.tray.replaceChildren(...groupSlots(rows).map((group) => {
    const box = document.createElement('div');
    box.className = 'tray__quadrant';
    box.dataset.side = group.side;

    const label = document.createElement('span');
    label.className = 'tray__label';
    label.textContent = `${group.side === 'phai' ? 'Phải' : 'Trái'} — hàng ${group.row + 1}`;

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
    button.title = `Khay ${row.slot} — X ${row.x} mm, Z ${row.z} mm, lật ${row.side}`;
  });

  el.stockTotal.textContent = `${summary.total_items}/${summary.total_capacity}`;
  el.summaryText.textContent =
    `${summary.total_items}/${summary.total_capacity} vật · ${summary.full_slots} khay đầy · ` +
    `${summary.empty_slots} khay trống`;

}

/* ---------------------------------------------------------------- chon khay */

export function markSelectedSlot(slot) {
  el.tray.querySelectorAll('.slot').forEach((button) => {
    button.classList.toggle('is-selected', Number(button.dataset.slot) === slot);
  });

  el.selectedSlot.textContent = slot ? `khay số ${slot}` : 'chưa chọn khay';

  const hint = document.getElementById('manual-slot-hint');
  if (hint) {
    hint.textContent = slot
      ? `Đang thao tác trên khay ${slot}.`
      : 'Chọn khay bên tab Vận hành trước.';
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
    if (!input) return;
    if (input.type === 'checkbox') input.checked = Boolean(value);
    else input.value = value;
  });

  // Ghi chu duoi o goc lat phai bam theo gioi han that, khong viet cung trong HTML.
  const note = document.getElementById('y-limit-note');
  if (note) note.textContent = `±${geometry.y_max_angle}°`;
}

export function readGeometryForm() {
  const out = {};
  Array.from(el.geometryForm.elements).forEach((input) => {
    if (!input.name) return;
    if (input.type === 'checkbox') out[input.name] = input.checked;
    else out[input.name] = Number(input.value);
  });
  return out;
}

export function renderDerived(derived) {
  el.derived.replaceChildren(...Object.entries(derived).map(([key, value]) => {
    const li = document.createElement('li');
    const name = document.createElement('span');
    name.textContent = DERIVED_LABELS[key] ?? key;
    const bold = document.createElement('b');
    bold.textContent = value;
    li.append(name, bold);
    return li;
  }));

  applyVelocityLimits(derived);
}

/**
 * Dan tran toc do len chinh o nhap, de nguoi dung biet truoc khi bam Luu.
 *
 * Tran nay do co khi quyet dinh nen khong viet cung trong HTML duoc - server
 * tinh ra trong 'derived' moi lan doc cau hinh. Giong cach y-limit-note bam
 * theo y_max_angle o fillGeometryForm.
 */
function applyVelocityLimits(derived) {
  const caps = [
    ['vel_x', derived.x_max_velocity_mm_s, 'X', 'mm/s'],
    ['vel_z', derived.z_max_velocity_mm_s, 'Z', 'mm/s'],
    ['tilt_vel', derived.y_max_velocity_deg_s, 'Y', '°/s'],
  ];

  const parts = [];
  caps.forEach(([name, cap, truc, donVi]) => {
    if (!Number.isFinite(cap)) return;
    const input = el.geometryForm?.elements.namedItem(name);
    if (input) input.max = cap;
    parts.push(`${truc} ${cap} ${donVi}`);
  });

  const note = document.getElementById('vel-limit-note');
  if (note) note.textContent = parts.length ? parts.join(' · ') : '—';
}

export function renderProblems(problems) {
  if (!el.problems) return;
  el.problems.replaceChildren(...problems.map((text) => {
    const li = document.createElement('li');
    li.textContent = text;
    return li;
  }));
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
  time.textContent = new Date().toLocaleTimeString('vi-VN');

  const text = document.createElement('span');
  text.textContent = message;

  item.append(time, text);
  el.log.prepend(item);

  while (el.log.children.length > LOG_LIMIT) {
    el.log.lastElementChild.remove();
  }
}

export function focusScanInput() {
  document.getElementById('scan-input')?.focus();
}
