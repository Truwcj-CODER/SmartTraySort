// Giu trang thai giao dien, bat su kien, goi api.js, ve bang ui.js.

import * as api from './api.js';
import * as ui from './ui.js';
import * as viz from './viz.js';

const state = {
  selectedSlot: null,
  slots: [],
  geometry: null,
  showViz: false,
  jogBits: { x_pos: false, x_neg: false, y_pos: false, y_neg: false, z_pos: false, z_neg: false },
  running: false,
};

/* =============================================================== lenh may */

// Moi nut deu di qua day nen hanh vi giong nhau va khong cho nao quen bat loi
async function runCommand(label, action, { refresh = false } = {}) {
  if (state.running) {
    ui.log(`bỏ qua "${label}" — đang có lệnh chạy dở`, 'warn');
    return null;
  }

  state.running = true;
  ui.log(`${label}…`);

  try {
    const result = await action();
    ui.log(result?.message || `${label} xong`, 'ok');
    if (refresh) await refreshSlots();
    return result;
  } catch (error) {
    ui.log(`${label} thất bại: ${error.message}`, 'error');
    return null;
  } finally {
    state.running = false;
  }
}

const slot = () => state.selectedSlot;

/** Ban do nut -> lenh. Them lenh moi chi can them 1 dong o day. */
const ACTIONS = {
  run:   () => runCommand(`Chạy tự động khay ${slot()}`, () => api.runSlot(slot())),
  goto:  () => runCommand(`Tới khay ${slot()}`, () => api.gotoSlot(slot())),
  tilt:  () => runCommand(`Lật tại khay ${slot()}`, () => api.tiltSlot(slot())),
  teach: () => runCommand(`Teach khay ${slot()}`, () => api.teachSlot(slot()), { refresh: true }),
  home:  () => runCommand('Lấy gốc tọa độ', api.home),
  park:  () => runCommand('Về vị trí chờ', api.park),
  reset: () => runCommand('Xóa lỗi', api.reset),
  stop:  stopNow,

  'item-add':    () => runCommand(`Thêm 1 vật vào khay ${slot()}`,
                                  () => api.addItems(slot()), { refresh: true }),
  'item-remove': () => runCommand(`Bớt 1 vật khỏi khay ${slot()}`,
                                  () => api.removeItems(slot()), { refresh: true }),
  'item-clear':  () => clearSlot(),

  'push-table':  () => runCommand('Đẩy 20 tọa độ xuống PLC', api.pushTable),
  'reset-stock': () => resetStock(),
};

/** Dung khan di duong rieng: khong qua khoa, khong cho lenh dang chay. */
async function stopNow() {
  try {
    await api.stop();
    ui.log('ĐÃ GỬI LỆNH DỪNG', 'warn');
  } catch (error) {
    ui.log(`gửi lệnh dừng thất bại: ${error.message}`, 'error');
  }
}

async function clearSlot() {
  const target = slot();
  const row = state.slots.find((s) => s.slot === target);
  if (!row || row.count === 0) {
    ui.log(`khay ${target} đang trống`, 'warn');
    return;
  }
  await runCommand(`Đổ hết khay ${target}`,
                   () => api.removeItems(target, row.count), { refresh: true });
}

async function resetStock() {
  if (!window.confirm('Xóa toàn bộ số liệu tồn kho của 20 khay?')) return;
  await runCommand('Xóa toàn bộ tồn kho', api.resetInventory, { refresh: true });
}

/* ================================================================== quet ma */

async function handleScan(code) {
  ui.log(`Quét mã ${code}…`);
  try {
    const result = await api.scan(code);
    ui.log(result.message, 'ok');
    state.selectedSlot = result.slot;
    ui.markSelectedSlot(result.slot);
    await refreshSlots();
  } catch (error) {
    ui.log(`Quét ${code} thất bại: ${error.message}`, 'error');
  }
}

/* ================================================================== jog tay */

async function pushJog(direction, pressed) {
  if (state.jogBits[direction] === pressed) return;
  state.jogBits[direction] = pressed;

  try {
    await api.setJog(state.jogBits);
  } catch (error) {
    ui.log(`jog thất bại: ${error.message}`, 'error');
  }
}

/** Nha het moi huong. Goi khi chuot ra khoi nut, mat tieu diem, hoac roi trang. */
async function releaseAllJog() {
  if (!Object.values(state.jogBits).some(Boolean)) return;

  Object.keys(state.jogBits).forEach((key) => { state.jogBits[key] = false; });
  document.querySelectorAll('.jog').forEach((button) => ui.markJogHeld(button, false));

  try {
    await api.setJog(state.jogBits);
  } catch {
    /* nha nut ma loi thi PLC van tu cat jog sau JogMaxTime */
  }
}

/* ================================================================ tai du lieu */

async function refreshSlots() {
  try {
    const data = await api.getSlots();
    state.slots = data.slots;
    ui.renderSlots(data.slots, data.summary);
    if (state.showViz && state.geometry) {
      viz.initViz(document.getElementById('viz'), state.geometry, data.slots);
    }
  } catch (error) {
    ui.log(`không đọc được bảng khay: ${error.message}`, 'error');
  }
}

async function refreshGeometry() {
  try {
    const data = await api.getGeometry();
    state.geometry = data.geometry;
    ui.fillGeometryForm(data.geometry);
    ui.renderDerived(data.derived);
    ui.renderProblems(data.problems || []);
    if (state.showViz && state.slots.length) {
      viz.initViz(document.getElementById('viz'), data.geometry, state.slots);
    }
  } catch (error) {
    ui.log(`không đọc được cấu hình: ${error.message}`, 'error');
  }
}

/* ============================================================== gan su kien */

/** Bat tat so do may. Tat thi khong ve nua, do vua do man hinh vua do CPU. */
function setVizVisible(visible) {
  state.showViz = visible;
  localStorage.setItem('showViz', visible ? '1' : '0');

  document.getElementById('viz-panel').classList.toggle('is-hidden', !visible);
  document.getElementById('viz-toggle').setAttribute('aria-pressed', String(visible));

  if (visible && state.geometry && state.slots.length) {
    viz.initViz(document.getElementById('viz'), state.geometry, state.slots);
  }
}

function bindVizToggle() {
  const saved = localStorage.getItem('showViz') === '1';
  setVizVisible(saved);
  document.getElementById('viz-toggle')
    .addEventListener('click', () => setVizVisible(!state.showViz));
}

/* Theme dat san boi doan script trong <head>; o day chi lo doi icon va cu bam. */
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

function bindTabs() {
  document.getElementById('tabs').addEventListener('click', (event) => {
    const tab = event.target.closest('.tab');
    if (!tab) return;
    ui.showTab(tab.dataset.tab);
    if (tab.dataset.tab === 'config') refreshGeometry();
    if (tab.dataset.tab === 'operate') ui.focusScanInput();
  });
}

function bindSlotButtons() {
  document.getElementById('tray').addEventListener('click', (event) => {
    const button = event.target.closest('.slot');
    if (!button) return;
    state.selectedSlot = Number(button.dataset.slot);
    ui.markSelectedSlot(state.selectedSlot);
  });
}

function bindActionButtons() {
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-action]');
    if (!button || button.disabled) return;
    ACTIONS[button.dataset.action]?.();
  });
}

function bindScanForm() {
  const form = document.getElementById('scan-form');
  const input = document.getElementById('scan-input');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const code = input.value.trim();
    if (!code) return;
    input.value = '';
    await handleScan(code);
    input.focus();          // may quet ma ban lien tuc, giu tieu diem o o nhap
  });
}

function bindManualForms() {
  document.getElementById('move-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const data = new FormData(event.target);
    const x = Number(data.get('x'));
    const z = Number(data.get('z'));
    runCommand(`Đi tới ngang ${x} cao ${z}`, () => api.moveTo(x, z));
  });

  document.getElementById('tilt-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const angle = Number(new FormData(event.target).get('angle'));
    runCommand(`Lật tới ${angle}°`, () => api.tiltTo(angle));
  });

  document.getElementById('geometry-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const geometry = ui.readGeometryForm();
    const result = await runCommand('Lưu cấu hình', () => api.saveGeometry(geometry));
    if (result) {
      await refreshGeometry();
      await refreshSlots();

      const plan = result.layout;
      if (plan) ui.log(`bố cục mới: ${plan.slots} rổ — ${plan.rows} hàng × ${plan.columns} cột × 2 bên`);

      // Bo cuc co lai thi may ro cuoi bien mat - phai noi ro cai nao con vat ben trong.
      if (result.orphans?.length) {
        const list = result.orphans.map((o) => `${o.slot} (${o.count} vật)`).join(', ');
        ui.log(`bố cục nhỏ lại, rổ ${list} không còn trong bố cục — nhớ lấy vật ra`, 'warn');
      }
      // Luu xong la server day luon xuong PLC, bao ro ket qua cho khoi doan mo.
      if (result.pushed) {
        ui.log(result.pushed, result.pushed.startsWith('CHƯA') ? 'error' : 'ok');
      }
      if (result.problems?.length) {
        ui.log(`cấu hình có ${result.problems.length} chỗ chưa hợp lý, chưa đẩy xuống PLC`, 'warn');
      }
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

  // roi trang hoac chuyen tab khi dang giu nut -> nha ra cho chac
  window.addEventListener('blur', releaseAllJog);
  window.addEventListener('pagehide', releaseAllJog);
}

/* ==================================================================== khoi dong */

async function start() {
  bindVizToggle();
  bindTheme();
  bindTabs();
  bindSlotButtons();
  bindActionButtons();
  bindScanForm();
  bindManualForms();
  bindJogPad();
  ui.markSelectedSlot(null);

  api.openStatusStream(
    (snapshot) => {
      ui.renderStatus(snapshot);
      if (state.showViz && snapshot.status) {
        viz.updateViz(snapshot.status, snapshot.status.slot);
      }
    },
    (linked, mode) => {
      if (!linked && mode === 'websocket') {
        ui.log('WebSocket đứt, tạm chuyển sang hỏi vòng 0.5 giây/lần', 'warn');
      }
    },
  );

  await refreshGeometry();   // phai co hinh hoc truoc thi moi ve duoc so do
  await refreshSlots();
  ui.focusScanInput();
  ui.log('giao diện đã sẵn sàng');
}

start();
