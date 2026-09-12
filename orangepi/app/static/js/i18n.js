// VI / EN strings for the web UI. Mirrors Strings.kt in the Android app.
// The strings live in /static/lang/{vi,en}.json — one flat file per language.
// Placeholders are named: "khay số {slot}" filled by t(key, { slot: 3 }).

const BUNDLES = { vi: {}, en: {} };
let loaded = false;

let lang = 'vi';
try { lang = localStorage.getItem('lang') === 'en' ? 'en' : 'vi'; } catch { /* private mode */ }

export function getLang() { return lang; }

// Load both language files once, up front. Call and await before first render.
export async function initI18n() {
  if (loaded) return;
  const [vi, en] = await Promise.all([
    fetch('/static/lang/vi.json').then((r) => r.json()),
    fetch('/static/lang/en.json').then((r) => r.json()),
  ]);
  BUNDLES.vi = vi;
  BUNDLES.en = en;
  loaded = true;
}

// t('cycle.slotNo', { slot: 3 }) -> named {slot} placeholders get filled in.
export function t(key, params) {
  let out = BUNDLES[lang]?.[key] ?? BUNDLES.vi?.[key] ?? key;
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      out = out.split(`{${name}}`).join(value);
    }
  }
  return out;
}

// Redraw every static string. Dynamic panels (status, slots, derived) re-render
// on their own poll; app.js also forces one after a switch.
export function applyStatic() {
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-html]').forEach((el) => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll('[data-i18n-title]').forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
}

export function setLang(next, onChange) {
  lang = next === 'en' ? 'en' : 'vi';
  try { localStorage.setItem('lang', lang); } catch { /* ignore */ }
  applyStatic();
  onChange?.();
}
