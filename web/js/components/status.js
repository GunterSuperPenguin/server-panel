import { control } from '../api.js';
import { $ } from '../dom.js';
import { onChange } from '../state.js';

const LABELS = {
  stopped: 'Остановлен',
  starting: 'Запускается…',
  running: 'Работает',
  stopping: 'Останавливается…',
};

function render({ server, state }) {
  const none = server === null;
  const busy = state === 'stopped' || state === 'stopping';
  $('#status').dataset.s = state;
  $('#status-text').textContent = LABELS[state];
  $('#b-start').disabled = none || state !== 'stopped';
  $('#b-stop').disabled = none || busy;
  $('#b-restart').disabled = none || busy;
}

export function initStatus() {
  $('#b-start').onclick = () => control('start');
  $('#b-stop').onclick = () => control('stop');
  $('#b-restart').onclick = () => confirm('Перезапустить сервер?') && control('restart');
  onChange(render);
}
