import { update } from './state.js';

let messages = {};

export const t = key => messages[key] ?? key;

function preferred() {
  try {
    const saved = localStorage.getItem('lang');
    if (saved) return saved;
  } catch {}
  return (navigator.language ?? '').slice(0, 2);
}

export function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-attr]').forEach(el => {
    for (const pair of el.dataset.i18nAttr.split(',')) {
      const [attr, key] = pair.split(':').map(s => s.trim());
      el.setAttribute(attr, t(key));
    }
  });
}

async function activate(code) {
  const data = await fetch('/api/locale?lang=' + encodeURIComponent(code)).then(r => r.json());
  messages = data.messages;
  document.documentElement.lang = data.lang;
  try { localStorage.setItem('lang', data.lang); } catch {}
  applyTranslations();
  update({ lang: data.lang });
  return data.languages;
}

export const initI18n = () => activate(preferred());
export const setLanguage = code => activate(code);
