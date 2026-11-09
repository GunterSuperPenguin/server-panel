import { createServer } from '../api.js';
import { $ } from '../dom.js';

const dlg = $('#dlg');
const input = $('#newname');
const msg = $('#newmsg');

export function openNewServerDialog() {
  msg.textContent = '';
  input.value = '';
  dlg.showModal();
  input.focus();
}

export function initNewServerDialog({ onCreated }) {
  $('#newcancel').onclick = () => dlg.close();
  $('#newform').onsubmit = async e => {
    e.preventDefault();
    const res = await createServer(input.value);
    if (res.error) {
      msg.className = 'msg error';
      msg.textContent = res.error;
      return;
    }
    dlg.close();
    await onCreated(res.name);
  };
}
