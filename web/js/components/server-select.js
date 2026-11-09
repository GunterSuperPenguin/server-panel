import { getServers } from '../api.js';
import { $ } from '../dom.js';
import { onChange, store } from '../state.js';

const NEW = '__new__';
const DOT = { stopped: '○', starting: '◐', stopping: '◐', running: '●' };
const sel = $('#server');
let names = [];

const label = s => `${DOT[s.state]} ${s.name}`;

export async function refreshServers() {
  const list = await getServers();
  const same = list.length === names.length && list.every((s, i) => s.name === names[i]);
  if (same) {
    list.forEach((s, i) => { sel.options[i].textContent = label(s); });
  } else {
    names = list.map(s => s.name);
    const options = list.map(s => new Option(label(s), s.name));
    if (!list.length) options.push(Object.assign(new Option('Нет серверов', ''), { disabled: true }));
    options.push(new Option('+ Создать новый…', NEW));
    sel.replaceChildren(...options);
  }
  sel.value = store.server ?? '';
  return list;
}

export function initServerSelect({ onSelect, onCreate }) {
  sel.onchange = () => {
    if (sel.value === NEW) {
      sel.value = store.server ?? '';
      onCreate();
    } else {
      onSelect(sel.value);
    }
  };
  onChange(({ server }) => { sel.value = server ?? ''; });
}
