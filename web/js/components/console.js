import { sendCommand } from '../api.js';
import { $ } from '../dom.js';
import { store } from '../state.js';

const MAX_LINES = 3000;
const el = $('#console');

function lineEl(text) {
  const div = document.createElement('div');
  div.textContent = text;
  if (text.startsWith('[panel]')) div.className = 'panel';
  else if (text.startsWith('> ')) div.className = 'cmd';
  else if (/error|exception|failed/i.test(text)) div.className = 'err';
  else if (/warning/i.test(text)) div.className = 'warn';
  return div;
}

function render(lines, replace) {
  const stick = replace || el.scrollTop + el.clientHeight >= el.scrollHeight - 40;
  const frag = document.createDocumentFragment();
  lines.forEach(line => frag.append(lineEl(line)));
  if (replace) el.replaceChildren();
  el.append(frag);
  while (el.childElementCount > MAX_LINES) el.firstChild.remove();
  if (stick) scrollToEnd();
}

export const addLines = lines => render(lines, false);
export const setLines = lines => render(lines, true);
export const clear = () => el.replaceChildren();

export function scrollToEnd() {
  el.scrollTop = el.scrollHeight;
}

export function showMessage(text) {
  const div = document.createElement('div');
  div.className = 'empty';
  div.textContent = text;
  el.replaceChildren(div);
}

export function initConsole() {
  $('#cmdform').onsubmit = async e => {
    e.preventDefault();
    const input = $('#cmd');
    const command = input.value.trim();
    if (!command || store.server === null) return;
    input.value = '';
    const res = await sendCommand(command);
    if (res.error) addLines(['[panel] ' + res.error]);
  };
}
