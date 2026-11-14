import { initBrowser, refreshBrowserPresets, setBrowserNotice } from './workshop-browser.js';
import { getWorkshop, updateWorkshop } from '../api.js';
import { $ } from '../dom.js';
import { t } from '../i18n.js';
import { store, onChange } from '../state.js';

let state = null;
let busy = false;
let version = 0;
const editor = $('#workshop-editor');
const select = $('#workshop-collections');
const message = $('#workshop-message');

function render() {
  select.replaceChildren();
  const list = $('#workshop-addons');
  list.replaceChildren();
  refreshBrowserPresets(state, busy);
  if (!state) return;
  for (const c of state.collections) {
    const option = new Option(c.name || t('workshop-default'), c.id);
    option.selected = c.id === state.active;
    select.add(option);
  }
  const active = state.collections.find(c => c.id === state.active);
  $('#workshop-delete').disabled = busy || state.collections.length === 1;
  if (!active.addons.length) list.textContent = t('workshop-empty');
  for (const addon of active.addons) {
    const row = document.createElement('div');
    row.className = 'row workshop-addon';
    const label = document.createElement('label');
    label.className = 'check';
    const toggle = document.createElement('input');
    toggle.type = 'checkbox';
    toggle.setAttribute('role', 'switch');
    toggle.setAttribute('aria-label', `${t('workshop-enabled')} ${addon.wsid}`);
    toggle.checked = addon.enabled;
    toggle.onchange = () => mutate({ action: 'toggle', wsid: addon.wsid, enabled: toggle.checked });
    const text = document.createElement('span');
    text.textContent = `${addon.label || addon.wsid} — ${t(addon.enabled ? 'workshop-enabled' : 'workshop-disabled')}`;
    label.append(toggle, text);
    const remove = document.createElement('button');
    remove.className = 'btn';
    remove.textContent = t('workshop-remove');
    remove.onclick = () => mutate({ action: 'remove', wsid: addon.wsid });
    row.append(label, remove);
    list.append(row);
  }
}

export async function loadWorkshop() {
  const requestVersion = ++version;
  state = null;
  render();
  message.textContent = '';
  setBrowserNotice('');
  if (store.server === null) { message.textContent = t('browser-no-server'); return; }
  try {
    const result = await getWorkshop();
    if (requestVersion !== version) return;
    if (result.error) message.textContent = result.error;
    else { state = result; render(); }
  } catch { if (requestVersion === version) message.textContent = t('workshop-network'); }
}

async function mutate(data) {
  if (busy || !state || store.server === null) return;
  if (data.action === 'delete' && !confirm(t('workshop-confirm-delete'))) { render(); return; }
  busy = true;
  if (data.action === 'add') {
    message.className = 'msg resolving';
    message.textContent = t('dependencies-resolving');
    setBrowserNotice(message.textContent, true);
  }
  editor.setAttribute('aria-busy', 'true');
  refreshBrowserPresets(state, busy);
  const requestVersion = version;
  editor.querySelectorAll('button,input,select,textarea').forEach(el => el.disabled = true);
  try {
    const result = await updateWorkshop({ collection: state.active, ...data });
    if (requestVersion !== version) return;
    message.className = 'msg' + (result.error ? ' error' : '');
    message.textContent = result.error || t('workshop-saved');
    if (result.addition) {
      const { roots, dependencies, warnings } = result.addition;
      const names = roots.map(a => a.label || a.wsid).join(', ');
      message.textContent = `${t('dependencies-added')}: ${names || t('dependencies-none')} + ${dependencies.length} ${t('dependencies-count')}`;
      if (dependencies.length) message.textContent += ` (${dependencies.map(a => a.label || a.wsid).join(', ')})`;
      if (warnings.length) {
        message.className = 'msg error';
        message.textContent += '\n' + warnings.map(w => `${w.wsid}: ${t(w.key)}`).join('\n');
      }
    }
    setBrowserNotice(message.textContent);
    if (!result.error) {
      state = result;
      if (data.action === 'add') $('#workshop-ids').value = '';
      if (['create', 'rename'].includes(data.action)) $('#workshop-name').value = '';
    }
  } catch {
    if (requestVersion === version) {
      message.className = 'msg error';
      message.textContent = t('workshop-network');
      setBrowserNotice(message.textContent);
    }
  }
  finally {
    busy = false;
    editor.setAttribute('aria-busy', 'false');
    message.classList.remove('resolving');
    editor.querySelectorAll('button,input,select,textarea').forEach(el => el.disabled = false);
    render();
  }
}

export function initWorkshop() {
  select.onchange = () => mutate({ action: 'activate', collection: select.value });
  for (const action of ['create', 'rename', 'delete']) {
    $('#workshop-' + action).onclick = () => mutate({ action, name: $('#workshop-name').value });
  }
  $('#workshop-add').onsubmit = event => {
    event.preventDefault();
    mutate({ action: 'add', ids: $('#workshop-ids').value });
  };
  initBrowser({ add: item => mutate({ action: 'add', ids: item.wsid }) });
  let server = undefined;
  let language = store.lang;
  onChange(() => {
    if (server !== store.server) { server = store.server; loadWorkshop(); }
    if (language !== store.lang) { language = store.lang; message.textContent = ''; render(); }
  });
}
