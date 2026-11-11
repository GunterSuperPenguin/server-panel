import { clear } from './components/console.js';
import { loadSettings } from './components/settings.js';
import { onChange, update } from './state.js';
import { connect } from './stream.js';

export function savedServer() {
  try { return localStorage.getItem('server'); } catch { return null; }
}

export function switchServer(name) {
  try { localStorage.setItem('server', name); } catch {}
  update({ server: name, state: 'stopped', p2p: null });
  clear();
  connect(name);
  loadSettings();
}

export function initSession() {
  let lang = null;
  onChange(({ lang: next, server }) => {
    if (next === lang) return;
    const first = lang === null;
    lang = next;
    if (!first && server !== null) connect(server);
  });
}
