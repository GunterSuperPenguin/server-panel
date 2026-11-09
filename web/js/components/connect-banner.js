import { copyText } from '../clipboard.js';
import { $ } from '../dom.js';
import { onChange } from '../state.js';

const HINT = 'Нажмите, чтобы скопировать';

export function initConnectBanner() {
  const banner = $('#connect');
  const text = $('#connect-text');
  const hint = banner.querySelector('small');
  let timer;

  banner.onclick = async () => {
    await copyText(text.textContent);
    banner.classList.add('copied');
    hint.textContent = 'Скопировано ✓';
    clearTimeout(timer);
    timer = setTimeout(() => {
      banner.classList.remove('copied');
      hint.textContent = HINT;
    }, 1800);
  };

  onChange(({ state, p2p }) => {
    const show = state === 'running' && p2p;
    banner.classList.toggle('show', !!show);
    if (show) text.textContent = 'connect ' + p2p;
  });
}
