import { $ } from '../dom.js';
import { scrollToEnd } from './console.js';

export function initTabs() {
  const tabs = document.querySelectorAll('.tab');
  tabs.forEach(tab => {
    tab.onclick = () => {
      tabs.forEach(t => t.setAttribute('aria-selected', t === tab));
      document.querySelectorAll('main > section').forEach(s => s.classList.remove('active'));
      $('#view-' + tab.dataset.tab).classList.add('active');
      if (tab.dataset.tab === 'console') scrollToEnd();
    };
  });
}
