// extension/content-script.js
const SIDECAR_URL = 'http://localhost:8765';
const PANEL_WIDTH = '420px'; // must match #margin-panel's width in panel.css
let statusPollIntervalId = null;

// YouTube's player sizes itself off window.innerWidth via JS, not CSS, so
// just adding margin-right doesn't shrink it — it stays full-width behind
// the fixed panel. Reserving the space with margin AND firing a resize
// event (the same trick reader-mode/sidebar extensions use) makes YouTube's
// own resize observer recompute the player size against the new layout.
function reserveSpaceForPanel() {
  document.documentElement.style.marginRight = PANEL_WIDTH;
  window.dispatchEvent(new Event('resize'));
}

function releaseSpaceForPanel() {
  document.documentElement.style.marginRight = '';
  window.dispatchEvent(new Event('resize'));
}

// Real, functional connection indicator — not decorative. Pings the sidecar's
// own /health route so the dot reflects whether note-chunk requests will
// actually succeed, not just whether the extension loaded.
async function pollSidecarStatus() {
  const statusEl = document.getElementById('hn-status');
  const labelEl = document.getElementById('hn-status-label');
  if (!statusEl) return;
  try {
    const response = await fetch(`${SIDECAR_URL}/health`);
    statusEl.dataset.state = response.ok ? 'online' : 'offline';
    labelEl.textContent = response.ok ? 'Sidecar' : 'Sidecar offline';
  } catch {
    statusEl.dataset.state = 'offline';
    labelEl.textContent = 'Sidecar offline';
  }
}

function startStatusPolling() {
  if (statusPollIntervalId) clearInterval(statusPollIntervalId);
  pollSidecarStatus();
  statusPollIntervalId = setInterval(pollSidecarStatus, 15000);
}

function injectPanel() {
  if (document.getElementById('margin-panel')) return;

  const panel = document.createElement('div');
  panel.id = 'margin-panel';
  panel.innerHTML = `
    <div class="hn-header">
      <div class="hn-brand">
        <span class="hn-brand-dot"></span>
        Margin
      </div>
      <div class="hn-header-actions">
        <span class="hn-status" id="hn-status" data-state="unknown">
          <span class="hn-status-dot"></span>
          <span id="hn-status-label">Sidecar</span>
        </span>
        <button class="hn-icon-btn" id="hn-close" aria-label="Close panel" title="Close">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
    </div>
    <div class="hn-recording" id="hn-recording">
      <span class="hn-recording-dot"></span>
      <span class="hn-recording-label">Recording to</span>
      <span class="hn-recording-name" id="hn-recording-name"></span>
    </div>
    <div class="hn-actionbar">
      <button class="hn-icon-btn" id="hn-action-video" title="Open source video">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 4 5.5 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.5-4-9s1.5-6.5 4-9Z"/></svg>
      </button>
      <button class="hn-icon-btn" id="hn-action-copy" title="Copy note as markdown">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>
      </button>
      <button class="hn-icon-btn" id="hn-action-download" title="Download note as .md">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>
      </button>
      <button class="hn-icon-btn" id="hn-action-history" title="Browse all notes">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>
      </button>
      <button class="hn-icon-btn" id="hn-action-flashcards" title="Export Anki flashcards">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="13" height="13" rx="2"/><path d="M7 4h11a2 2 0 0 1 2 2v11"/><path d="M9.5 13h4"/></svg>
      </button>
      <button class="hn-icon-btn" id="hn-action-obsidian" title="Open in Obsidian">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3h7v7"/><path d="M10 14 21 3"/><path d="M19 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"/></svg>
      </button>
    </div>
    <div class="hn-body" id="hn-body">
      <div class="hn-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6M9 9h1"/></svg>
        <p>Press "Start AI Notes" to generate live notes from this video's transcript.</p>
      </div>
    </div>
    <div class="hn-toolbar">
      <button class="hn-btn hn-btn-primary" id="hn-toggle">
        <span class="hn-btn-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 3 14 9-14 9V3z"/></svg>
        </span>
        <span id="hn-toggle-label">Start AI Notes</span>
      </button>
      <span class="hn-shortcut-hint" title="Insert a timestamp jump-link at the current playhead">
        <span class="hn-kbd">⌘</span><span class="hn-kbd">J</span>
      </span>
    </div>
  `;
  document.body.appendChild(panel);
  reserveSpaceForPanel();

  startStatusPolling();

  const panelModulePromise = import(chrome.runtime.getURL('panel.js'));

  document.getElementById('hn-close').addEventListener('click', () => {
    if (statusPollIntervalId) clearInterval(statusPollIntervalId);
    panelModulePromise.then(({ stopAiNotes }) => stopAiNotes());
    panel.remove();
    releaseSpaceForPanel();
  });

  panelModulePromise.then(({ wirePanelButtons }) => wirePanelButtons());
}

// YouTube is a single-page app; re-inject on navigation.
let lastUrl = location.href;
new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    if (location.href.includes('/watch')) injectPanel();
  }
}).observe(document.body, { childList: true, subtree: true });

if (location.href.includes('/watch')) injectPanel();

// Toolbar-icon click (background.js) toggles the panel — the only way to
// bring it back after closing it, since injectPanel() above only runs once
// automatically per page load.
chrome.runtime.onMessage.addListener((message) => {
  if (message.type !== 'hn:toggle-panel') return;
  const existing = document.getElementById('margin-panel');
  if (existing) {
    document.getElementById('hn-close')?.click();
  } else if (location.href.includes('/watch')) {
    injectPanel();
  }
});
