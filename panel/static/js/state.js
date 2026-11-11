export const store = { server: null, state: 'stopped', p2p: null, lang: 'en' };

const listeners = new Set();

export function update(patch) {
  Object.assign(store, patch);
  listeners.forEach(fn => fn(store));
}

export function onChange(fn) {
  listeners.add(fn);
  fn(store);
}
