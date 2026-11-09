import { getConfig, saveConfig } from '../api.js';
import { $ } from '../dom.js';
import { store } from '../state.js';

const form = $('#cfg');
const msg = $('#msg');

const fields = () => [...form.elements].filter(el => el.name);

export async function loadSettings() {
  if (store.server === null) return;
  const cfg = await getConfig();
  if (cfg.error) return;
  msg.textContent = '';
  $('#path').textContent = `servers/${store.server}/`;
  for (const el of fields()) {
    if (el.type === 'checkbox') el.checked = !!cfg[el.name];
    else el.value = cfg[el.name] ?? '';
  }
}

export function initSettings() {
  form.onsubmit = async e => {
    e.preventDefault();
    if (store.server === null) return;
    const data = {};
    for (const el of fields()) data[el.name] = el.type === 'checkbox' ? el.checked : el.value;
    const res = await saveConfig(data);
    msg.className = 'msg' + (res.error ? ' error' : '');
    msg.textContent = res.error || 'Сохранено';
  };
}
