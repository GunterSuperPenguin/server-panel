import { getConfig, getOptions, getServerCfg, openFolder, saveConfig, saveServerCfg } from '../api.js';
import { $ } from '../dom.js';
import { t } from '../i18n.js';
import { onChange, store } from '../state.js';
import { createCombobox } from './combobox.js';

const form = $('#cfg');
const msg = $('#msg');
const cfgBox = $('#server-cfg');
const gamemodes = createCombobox($('#combo-gamemode'));
const maps = createCombobox($('#combo-map'));

const fields = () => [...form.elements].filter(el => el.name);

function report(res, okKey) {
  msg.className = 'msg' + (res.error ? ' error' : '');
  msg.textContent = res.error || t(okKey);
}

export async function refreshOptions() {
  if (store.server === null) return;
  const res = await getOptions();
  if (res.error) return;
  gamemodes.setOptions(res.gamemodes);
  maps.setOptions(res.maps);
}

export async function loadSettings() {
  if (store.server === null) return;
  const [cfg, serverCfg] = await Promise.all([getConfig(), getServerCfg()]);
  if (cfg.error || serverCfg.error) return;
  msg.textContent = '';
  $('#path').textContent = `servers/${store.server}/`;
  for (const el of fields()) {
    if (el.type === 'checkbox') el.checked = !!cfg[el.name];
    else el.value = cfg[el.name] ?? '';
  }
  cfgBox.value = serverCfg.content;
  refreshOptions();
}

export function initSettings() {
  let lang = store.lang;

  form.onsubmit = async e => {
    e.preventDefault();
    if (store.server === null) return;
    const data = {};
    for (const el of fields()) data[el.name] = el.type === 'checkbox' ? el.checked : el.value;
    const res = await saveConfig(data);
    if (res.error) return report(res);
    report(await saveServerCfg(cfgBox.value), 'settings-saved');
  };

  $('#b-open-folder').onclick = async () => {
    if (store.server === null) return;
    const res = await openFolder();
    if (res.error) report(res);
  };

  onChange(({ lang: next }) => {
    if (next === lang) return;
    lang = next;
    msg.textContent = '';
  });
}
