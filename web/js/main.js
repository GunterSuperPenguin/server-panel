import { initConnectBanner } from './components/connect-banner.js';
import { initConsole, showMessage } from './components/console.js';
import { initNewServerDialog, openNewServerDialog } from './components/new-server-dialog.js';
import { initServerSelect, refreshServers } from './components/server-select.js';
import { initSettings } from './components/settings.js';
import { initStatus } from './components/status.js';
import { initTabs } from './components/tabs.js';
import { savedServer, switchServer } from './session.js';

initTabs();
initConnectBanner();
initStatus();
initConsole();
initSettings();
initNewServerDialog({
  onCreated: async name => {
    await refreshServers();
    switchServer(name);
  },
});
initServerSelect({ onSelect: switchServer, onCreate: openNewServerDialog });

async function start() {
  const servers = await refreshServers();
  const saved = savedServer();
  const first = servers.some(s => s.name === saved) ? saved : servers[0]?.name ?? null;
  if (first) {
    switchServer(first);
  } else {
    showMessage('Серверов пока нет. Создайте первый.');
    openNewServerDialog();
  }
  setInterval(refreshServers, 4000);
}

start();
