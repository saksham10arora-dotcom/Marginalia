// extension/background.js
// Clicking the toolbar icon toggles the panel without needing a page reload
// — content-script.js only ever injects it once automatically on page load;
// this is the only way to bring it back after closing it, or show it on a
// tab where it hasn't run yet.
chrome.action.onClicked.addListener((tab) => {
  if (!tab.id || !tab.url?.includes('youtube.com/watch')) return;
  chrome.tabs.sendMessage(tab.id, { type: 'hn:toggle-panel' }).catch(() => {
    // Content script isn't loaded yet on this tab (e.g. extension was just
    // installed/reloaded) — nothing to toggle.
  });
});
