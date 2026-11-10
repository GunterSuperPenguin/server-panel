import { store } from './state.js';

const query = params => '?' + new URLSearchParams({ lang: store.lang, ...params });
const serverQuery = () => query({ server: store.server ?? '' });

const request = (url, options) => fetch(url, options).then(r => r.json());

const post = (url, body = {}) => request(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export const getServers = () => request('/api/servers' + query({}));
export const createServer = name => post('/api/servers' + query({}), { name });
export const getConfig = () => request('/api/config' + serverQuery());
export const saveConfig = data => post('/api/config' + serverQuery(), data);
export const control = action => post(`/api/${action}${serverQuery()}`);
export const sendCommand = command => post('/api/command' + serverQuery(), { command });
export const eventsUrl = name => '/api/events' + query({ server: name });
