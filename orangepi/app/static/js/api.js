// Lop goi REST duy nhat cua giao dien. Khong dung toi DOM.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// Moi ham ben duoi deu di qua day nen them endpoint moi khong phai viet lai xu ly loi
async function request(path, { method = 'GET', body } = {}) {
  const options = { method, headers: {} };

  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch (cause) {
    throw new ApiError('khong goi duoc server', 0);
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = payload?.detail ?? `loi HTTP ${response.status}`;
    throw new ApiError(detail, response.status);
  }
  return payload;
}

/* ------------------------------------------------------------- trang thai */
export const getStatus = () => request('/api/status');

/* ------------------------------------------------------------ lenh theo khay */
export const runSlot = (slot) => request(`/api/slots/${slot}/run`, { method: 'POST' });
export const gotoSlot = (slot) => request(`/api/slots/${slot}/goto`, { method: 'POST' });
export const teachSlot = (slot) => request(`/api/slots/${slot}/teach`, { method: 'POST' });

/* ------------------------------------------------------------- lenh chung */
export const home = () => request('/api/home', { method: 'POST' });
export const park = () => request('/api/park', { method: 'POST' });
export const stop = () => request('/api/stop', { method: 'POST' });
export const reset = () => request('/api/reset', { method: 'POST' });
export const moveTo = (x, z) => request('/api/move', { method: 'POST', body: { x, z } });
export const tiltTo = (angle) => request('/api/tilt', { method: 'POST', body: { angle } });

/* --------------------------------------------------------------- khay + ton kho */
export const getSlots = () => request('/api/slots');
export const tiltSlot = (slot) => request(`/api/slots/${slot}/tilt`, { method: 'POST' });


export const addItems = (slot, amount = 1) =>
  request(`/api/slots/${slot}/items`, { method: 'POST', body: { amount } });

export const removeItems = (slot, amount = 1) =>
  request(`/api/slots/${slot}/items?amount=${amount}`, { method: 'DELETE' });

export const resetInventory = () => request('/api/inventory/reset', { method: 'POST' });

/* ------------------------------------------------------------------- quet ma */
export const scan = (code, run = true) =>
  request('/api/scan', { method: 'POST', body: { code, run } });

/* ------------------------------------------------------------------- cau hinh */
export const getGeometry = () => request('/api/config/geometry');
export const saveGeometry = (geometry) =>
  request('/api/config/geometry', { method: 'PUT', body: geometry });
export const pushTable = () => request('/api/config/push', { method: 'POST' });

export const setJog = (bits) => request('/api/jog', { method: 'POST', body: bits });

// Mo duong nhan trang thai. Uu tien WebSocket, hong thi tu chuyen sang hoi vong.
// Nho vay thieu thu vien websocket tren may chu thi giao dien van song.
export function openStatusStream(onSnapshot, onLinkChange) {
  const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/status`;
  let socket = null;
  let poller = null;
  let retryDelay = 1000;
  let stopped = false;

  const startPolling = () => {
    if (poller) return;
    poller = setInterval(async () => {
      try {
        onSnapshot(await getStatus());
        onLinkChange?.(true, 'polling');
      } catch {
        onLinkChange?.(false, 'polling');
      }
    }, 500);
  };

  const stopPolling = () => {
    clearInterval(poller);
    poller = null;
  };

  const connect = () => {
    if (stopped) return;
    socket = new WebSocket(url);

    socket.onopen = () => {
      retryDelay = 1000;
      stopPolling();
      onLinkChange?.(true, 'websocket');
    };

    socket.onmessage = (event) => onSnapshot(JSON.parse(event.data));

    socket.onclose = () => {
      onLinkChange?.(false, 'websocket');
      startPolling();               // khong de giao dien chet trong luc cho ket noi lai
      setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 10000);
    };

    socket.onerror = () => socket.close();
  };

  connect();
  return () => { stopped = true; stopPolling(); socket?.close(); };
}
