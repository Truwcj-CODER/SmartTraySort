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

/* ------------------------------------------------------------ lenh theo khay */
export const runSlot = (slot) => request(`/api/slots/${slot}/run`, { method: 'POST' });
export const gotoSlot = (slot) => request(`/api/slots/${slot}/goto`, { method: 'POST' });
export const teachSlot = (slot) => request(`/api/slots/${slot}/teach`, { method: 'POST' });

/* ------------------------------------------------------------- lenh chung */
export const home = () => request('/api/home', { method: 'POST' });
export const park = () => request('/api/park', { method: 'POST' });
export const parkHere = () => request('/api/park/here', { method: 'POST' });
export const stop = () => request('/api/stop', { method: 'POST' });
export const reset = () => request('/api/reset', { method: 'POST' });
export const moveTo = (x, z) => request('/api/move', { method: 'POST', body: { x, z } });
export const tiltTo = (angle) => request('/api/tilt', { method: 'POST', body: { angle } });

/* --------------------------------------------------------------- khay + ton kho */
export const getSlots = () => request('/api/slots');
export const tiltSlot = (slot) => request(`/api/slots/${slot}/tilt`, { method: 'POST' });
export const getOrderAtSlot = (slot) => request(`/api/orders/${slot}`);


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

// Status / inventory / layout, pushed over Server-Sent Events - same /api/events
// stream the Android app uses. EventSource reconnects on its own, and the server
// sends all three event types once on connect, so no separate initial fetch.
//
// handlers: { status, inventory, layout, linkChange }
export function openEventStream(handlers) {
  const source = new EventSource('/api/events');

  for (const type of ['status', 'inventory', 'layout']) {
    if (handlers[type]) {
      source.addEventListener(type, (event) => handlers[type](JSON.parse(event.data)));
    }
  }

  source.onopen = () => handlers.linkChange?.(true);
  source.onerror = () => handlers.linkChange?.(false);   // EventSource retries itself

  return () => source.close();
}
