import { store } from './state.js';

const query = () => '?server=' + encodeURIComponent(store.server ?? '');

const request = (url, options) => fetch(url, options).then(r => r.json());

const post = (url, body = {}) => request(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const getServers = () => request('/api/servers');
export const createServer = name => post('/api/servers', { name });
export const getConfig = () => request('/api/config' + query());
export const saveConfig = data => post('/api/config' + query(), data);
export const control = action => post(`/api/${action}${query()}`);
export const sendCommand = command => post('/api/command' + query(), { command });
export const eventsUrl = name => '/api/events?server=' + encodeURIComponent(name);
