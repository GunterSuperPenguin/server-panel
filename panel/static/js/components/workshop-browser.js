import { searchWorkshop, getWorkshopDetails } from '../api.js';
import { $ } from '../dom.js';
import { t } from '../i18n.js';
import { onChange, store } from '../state.js';

const tags = ['Addon', 'Gamemode', 'Map', 'Weapon', 'Vehicle', 'NPC', 'Tool', 'Effects', 'Model', 'ServerContent'];
const selected = new Set();
let pageSize = 30;
let items = [], page = 1, total = 0, requestVersion = 0, detailVersion = 0;
let notice = '', noticeBusy = false;
let presets = null, saving = false, loading = false, started = false, preview = null, addItem;
const grid = $('#workshop-grid'), status = $('#browser-message'), dialog = $('#workshop-preview');
const node = (tag, cls, text) => {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
};
const number = value => new Intl.NumberFormat(store.lang).format(value);
const size = value => `${number(Math.round(value / 1048576 * 10) / 10)} ${t('browser-mb')}`;
const tagTitle = tag => tags.some(value => value.toLowerCase() === tag.toLowerCase()) ? t('browser-tag-' + tag.toLowerCase()) : tag;
const active = () => presets?.collections.find(c => c.id === presets.active);

function addButton(item) {
  const added = active()?.addons.some(a => a.wsid === item.wsid);
  const button = node('button', 'btn' + (added ? '' : ' primary'), t(added ? 'browser-added' : 'browser-add'));
  button.disabled = !!added || !active() || saving;
  button.onclick = () => addItem(item);
  return button;
}

function image(url, title) {
  const img = node('img', 'workshop-image');
  img.alt = title;
  img.loading = 'lazy';
  // Steam URLs are untrusted data; never accept script/data URLs.
  if (url?.startsWith('https://')) img.src = url;
  img.onerror = () => { img.removeAttribute('src'); img.onerror = null; };
  return img;
}

function stats(item) {
  const rating = item.rating == null ? t('browser-unrated') : `${number(Math.round(item.rating * 50) / 10)} / 5 ★`;
  return `${rating} · ${number(item.subscriptions)} ${t('browser-subscribers')} · ${size(item.size)}`;
}

function renderCards() {
  if (loading) return;
  grid.replaceChildren();
  for (const item of items) {
    const card = node('article', 'workshop-card');
    const open = node('button', 'workshop-card-open');
    const copy = node('span', 'workshop-card-copy');
    copy.append(node('span', 'workshop-card-title', item.title),
      node('span', 'workshop-meta', `${t('browser-author')}: ${item.author || t('browser-unknown')}`),
      node('span', 'workshop-meta', stats(item)));
    open.append(image(item.image, item.title), copy);
    open.onclick = () => openPreview(item);
    card.append(open, addButton(item));
    grid.append(card);
  }
  $('#workshop-prev').disabled = page <= 1 || loading;
  $('#workshop-next').disabled = page * pageSize >= total || page >= 1000 || loading;
  $('#workshop-page').textContent = `${number(page)} / ${number(Math.max(1, Math.ceil(total / pageSize)))}`;
}

function renderPreview() {
  if (!dialog.open || !preview) return;
  $('#preview-title').textContent = preview.title;
  const content = $('#preview-content');
  content.replaceChildren();
  const images = node('div', 'preview-images');
  for (const url of [...new Set([preview.image, ...(preview.previews || [])])].filter(Boolean)) images.append(image(url, preview.title));
  const actions = node('div', 'preview-actions');
  const link = node('a', '', t('browser-steam'));
  link.href = `https://steamcommunity.com/sharedfiles/filedetails/?id=${encodeURIComponent(preview.wsid)}`;
  link.target = '_blank'; link.rel = 'noopener noreferrer';
  actions.append(addButton(preview), link);
  const updated = preview.updated ? new Date(preview.updated * 1000).toLocaleDateString(store.lang) : t('browser-unknown');
  content.append(images, node('p', 'workshop-meta', `${t('browser-author')}: ${preview.author || t('browser-unknown')} · WSID ${preview.wsid} · ${t('browser-updated')}: ${updated}`),
    node('p', 'workshop-meta', stats(preview)), node('p', 'workshop-meta', preview.tags.map(tagTitle).join(' · ')), actions,
    node('div', 'preview-description', preview.description || t('browser-no-description')));
  if (preview.required_items?.length) content.append(node('p', 'workshop-meta', `${t('dependencies-required')}: ${preview.required_items.join(', ')}`));
  if (notice) {
    const status = node('p', 'msg' + (noticeBusy ? ' resolving' : ''), notice);
    status.setAttribute('role', 'status');
    content.prepend(status);
  }
}

async function openPreview(item) {
  const current = ++detailVersion;
  preview = item;
  dialog.showModal();
  renderPreview();
  const note = node('p', 'msg', t('browser-loading'));
  $('#preview-content').append(note);
  try {
    const result = await getWorkshopDetails(item.wsid);
    if (current !== detailVersion || !dialog.open) return;
    if (result.error) note.textContent = result.error;
    else {
      // Preserve search previews when the public detail page has none.
      preview = { ...item, ...result, previews: result.previews?.length ? result.previews : item.previews, rating: result.rating ?? item.rating, subscriptions: result.subscriptions || item.subscriptions };
      renderPreview();
    }
  } catch { if (current === detailVersion) note.textContent = t('workshop-network'); }
}

async function search() {
  const current = ++requestVersion;
  loading = true;
  status.textContent = t('browser-loading');
  $('#browser-retry').hidden = true;
  grid.setAttribute('aria-busy', 'true');
  grid.replaceChildren();
  for (let i = 0; i < 6; i++) grid.append(node('div', 'workshop-skeleton'));
  $('#workshop-prev').disabled = $('#workshop-next').disabled = true;
  try {
    const result = await searchWorkshop({ q: $('#workshop-query').value.trim(), tags: [...selected].join(','), sort: $('#workshop-sort').value, page });
    if (current !== requestVersion) return;
    pageSize = result.page_size || 30;
    items = result.items || []; total = result.total || 0; page = result.page || page;
    status.textContent = result.error || (items.length ? `${number(total)} ${t('browser-results')}` : t('browser-empty'));
    $('#browser-retry').hidden = !result.error;
  } catch {
    if (current !== requestVersion) return;
    items = []; total = 0;
    status.textContent = t('workshop-network');
    $('#browser-retry').hidden = false;
  } finally {
    if (current === requestVersion) { loading = false; grid.setAttribute('aria-busy', 'false'); renderCards(); }
  }
}

function renderTags() {
  const container = $('#workshop-tags');
  container.replaceChildren();
  for (const tag of tags) {
    const button = node('button', 'btn workshop-tag', tagTitle(tag));
    button.setAttribute('aria-pressed', selected.has(tag));
    button.onclick = () => { if (selected.has(tag)) selected.delete(tag); else selected.add(tag); renderTags(); page = 1; search(); };
    container.append(button);
  }
}

export function refreshBrowserPresets(state, busy) {
  presets = state; saving = busy;
  renderCards(); renderPreview();
}

export function initBrowser({ add }) {
  addItem = add;
  renderTags(); renderCards();
  $('#workshop-search').onsubmit = event => { event.preventDefault(); page = 1; search(); };
  $('#workshop-sort').onchange = () => { page = 1; search(); };
  $('#browser-retry').onclick = search;
  $('#workshop-prev').onclick = () => { page--; search(); };
  $('#workshop-next').onclick = () => { page++; search(); };
  $('#preview-close').onclick = () => dialog.close();
  dialog.onclose = () => { detailVersion++; preview = null; };
  document.querySelector('[data-tab="workshop"]').addEventListener('click', () => { if (!started) { started = true; search(); } });
  let lang = store.lang;
  onChange(() => {
    if (lang !== store.lang) { lang = store.lang; renderTags(); renderCards(); renderPreview(); if (started) search(); }
  });
}

export function setBrowserNotice(text, busy = false) {
  notice = text;
  noticeBusy = busy;
  renderPreview();
}
