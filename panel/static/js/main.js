import { initConnectBanner } from './components/connect-banner.js';
import { initConsole, showMessage } from './components/console.js';
import { initLanguageSelect } from './components/language-select.js';
import { initNewServerDialog, openNewServerDialog } from './components/new-server-dialog.js';
import { initServerSelect, refreshServers } from './components/server-select.js';
import { initSettings } from './components/settings.js';
import { initStatus } from './components/status.js';
import { initTabs } from './components/tabs.js';
import { initI18n } from './i18n.js';
import { initSession, savedServer, switchServer } from './session.js';

async function start() {
  const languages = await initI18n();
  initLanguageSelect(languages);
  initTabs();
  initConnectBanner();
  initStatus();
  initConsole();
  initSettings();
  initSession();
  initNewServerDialog({
    onCreated: async name => {
      await refreshServers();
      switchServer(name);
    },
  });
  initServerSelect({ onSelect: switchServer, onCreate: openNewServerDialog });
  document.body.classList.remove('pending');

  const servers = await refreshServers();
  const saved = savedServer();
  const first = servers.some(s => s.name === saved) ? saved : servers[0]?.name ?? null;
  if (first) {
    switchServer(first);
  } else {
    showMessage('console-no-servers');
    openNewServerDialog();
  }
  setInterval(refreshServers, 4000);
}

start();
