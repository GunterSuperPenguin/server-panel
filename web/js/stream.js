import { eventsUrl } from './api.js';
import { addLines, setLines } from './components/console.js';
import { update } from './state.js';

let source = null;

export function connect(name) {
  disconnect();
  source = new EventSource(eventsUrl(name));
  source.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'line') addLines([msg.text]);
    else if (msg.type === 'history') setLines(msg.lines);
    else if (msg.type === 'state') update({ state: msg.state, p2p: msg.p2p });
  };
}

export function disconnect() {
  source?.close();
  source = null;
}
