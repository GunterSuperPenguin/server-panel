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
export const getOptions = () => request('/api/options' + serverQuery());
export const getServerCfg = () => request('/api/server-cfg' + serverQuery());
export const saveServerCfg = content => post('/api/server-cfg' + serverQuery(), { content });
export const openFolder = () => post('/api/open-folder' + serverQuery());
export const getWorkshop = () => request('/api/workshop' + serverQuery());
export const updateWorkshop = data => post('/api/workshop' + serverQuery(), data);
export const searchWorkshop = params => request('/api/workshop/search' + query(params));
export const getWorkshopDetails = id => request('/api/workshop/details' + query({ id }));
