const sensorGrid    = document.getElementById('sensorGrid');
const cepAlertsEl   = document.getElementById('cepAlertsList');
const userArea      = document.getElementById('userArea');
const authWall      = document.getElementById('authWall');

// ── JWT token management ─────────────────────────────────────────────────
function getToken() { return localStorage.getItem('jwt_token'); }
function setToken(t) { localStorage.setItem('jwt_token', t); }
function clearToken() { localStorage.removeItem('jwt_token'); }

// Check if the URL fragment contains a token (set after OAuth redirect)
(function captureToken() {
  const hash = window.location.hash;
  if (hash.startsWith('#token=')) {
    setToken(hash.slice(7));
    history.replaceState(null, '', '/');
  }
})();

// Helper: build headers with JWT if available
function authHeaders(extra) {
  const h = Object.assign({}, extra || {});
  const t = getToken();
  if (t) h['Authorization'] = 'Bearer ' + t;
  return h;
}

// Helper: authenticated fetch
function authFetch(url, opts) {
  opts = opts || {};
  opts.headers = authHeaders(opts.headers);
  return fetch(url, opts);
}

// ── Sensor metadata (icon, label, unit, colour class) ────────────────────
const SENSORS = {
  pv_power:      { icon: '☀️', label: 'Solar Production',    unit: 'W', cls: 'positive' },
  load_power:    { icon: '🏠', label: 'Consumption',         unit: 'W', cls: 'neutral'  },
  grid_power:    { icon: '🔌', label: 'Grid Power',          unit: 'W', cls: 'negative' },
  battery_power: { icon: '🔋', label: 'Battery Power',       unit: 'W', cls: 'neutral'  },
  battery:       { icon: '🪫', label: 'Battery (%)',         unit: '%', cls: 'neutral' },
};

// ── Helpers ──────────────────────────────────────────────────────────────
function fmtValue(v) {
  if (v == null) return null;
  const n = Number(v);
  if (Number.isNaN(n)) return v;
  if (Math.abs(n) >= 1000) return n.toLocaleString('en-US', { maximumFractionDigits: 0 });
  return n.toLocaleString('en-US', { maximumFractionDigits: 1 });
}

function fmtTimestamp(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function timeAgo(ts) {
  if (!ts) return '';
  const secs = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (secs < 5) return 'now';
  if (secs < 60) return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  return `${Math.floor(secs / 3600)}h ago`;
}

// ── Render sensors ───────────────────────────────────────────────────────
function renderStats(data) {
  const vals = data.values || {};
  const derived = data.derived || {};

  // Sensor cards
  let html = '';
  for (const [key, meta] of Object.entries(SENSORS)) {
    const entry = vals[key] || {};
    const v = entry.value;
    const hasData = v != null;

    html += `<div class="sensor-card${hasData ? '' : ' no-data'}">
      <div class="sensor-icon">${meta.icon}</div>
      <div class="sensor-label">${meta.label}</div>
      <div class="sensor-value ${hasData ? meta.cls : ''}">
        ${hasData ? fmtValue(v) : '—'}${hasData ? `<span class="sensor-unit">${meta.unit}</span>` : ''}
      </div>
      <div class="sensor-ts">${hasData ? timeAgo(entry.timestamp) : 'No data'}</div>
    </div>`;
  }
  sensorGrid.innerHTML = html;
}

// ── Data fetching ────────────────────────────────────────────────────────
async function fetchStats() {
  try {
    const res = await authFetch('/api/stats');
    const j = await res.json();
    renderStats(j);
  } catch (e) {
    sensorGrid.innerHTML = '<p style="color:#d93025">Error fetching data</p>';
  }
}

// ── CEP alerts ───────────────────────────────────────────────────────────
function renderCEPAlerts(alerts) {
  if (!alerts.length) {
    cepAlertsEl.innerHTML = '<p class="no-alerts">No CEP alerts</p>';
    return;
  }
  cepAlertsEl.innerHTML = alerts.map(a => {
    return `<div class="cep-alert ${a.severity}">
      <span class="cep-severity ${a.severity}">${a.severity}</span>
      <div>
        <div class="cep-msg">${a.message}</div>
        <div class="cep-meta">${a.rule} · ${timeAgo(a.created_at)}</div>
      </div>
    </div>`;
  }).join('');
}

async function fetchCEPAlerts() {
  try {
    const res = await authFetch('/api/cep/alerts');
    if (res.status === 401) return;
    const j = await res.json();
    renderCEPAlerts(j.cep_alerts || []);
  } catch (e) {
    cepAlertsEl.innerHTML = '<p style="color:#d93025">Error fetching CEP alerts</p>';
  }
}

async function clearCEPAlerts() {
  try {
    await authFetch('/api/cep/alerts', { method: 'DELETE' });
    await fetchCEPAlerts();
  } catch (e) { /* ignore */ }
}

document.getElementById('cepClearBtn').addEventListener('click', clearCEPAlerts);

// ---------- Auth ----------
async function checkAuth(){
  try{
    const res = await authFetch('/api/me');
    const j = await res.json();
    if(j.authenticated){
      userArea.innerHTML = `<span class="user-pill"><img src="${j.picture}" alt=""> ${j.name} <a href="#" data-action="logout">Sign out</a></span>`;
    } else {
      clearToken();
      userArea.innerHTML = '<a href="/api/login" class="google-btn">Sign in with Google</a>';
    }
  }catch(e){
    userArea.innerHTML = '<span style="color:#666">Local mode (no login)</span>';
  } finally {
    // Hide explicit login screen and show app UI regardless of auth state
    document.getElementById('loginScreen').style.display = 'none';
    document.getElementById('appHeader').style.display = 'flex';
    authWall.style.display = 'block';

    // Start polling
    fetchStats();
    fetchCEPAlerts();
    fetchKeys();
    setInterval(fetchStats, 5000);
    setInterval(fetchCEPAlerts, 10000);
  }
}

// ---------- API Keys ----------
async function fetchKeys(){
  try{
    const res = await authFetch('/api/keys');
    if(res.status===401){ document.getElementById('apiKeyCard').style.display='none'; return; }
    const j = await res.json();
    document.getElementById('apiKeyCard').style.display='';
    const list = document.getElementById('keysList');
    if(!j.keys.length){ list.innerHTML='<p style="color:#888">No API keys</p>'; return; }
    list.innerHTML = j.keys.map(k=>`<div class="key-item"><div><strong>${k.name}</strong><div class="key-box">${k.key}</div><small>${k.created_at}</small></div><button data-action="delete-key" data-key="${k.id}">Delete</button></div>`).join('');
  }catch(e){ /* ignore */ }
}

document.getElementById('keyForm').addEventListener('submit', async(ev)=>{
  ev.preventDefault();
  const name = document.getElementById('keyName').value.trim() || 'default';
  try{
    const res = await authFetch('/api/keys',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
    if(res.status===201){
      const data = await res.json();
      const rawKey = data.key; // Raw key is shown only once
      document.getElementById('keyName').value='';
      
      // Show the raw key in a modal that the user MUST close to continue
      showRawKeyModal(rawKey, name);
      
      // After user acknowledges, refresh the list to show masked version
      await fetchKeys();
    } else {
      const j = await res.json();
      alert('Error: '+(j.message||res.status));
    }
  }catch(e){ alert('Network error'); }
});

// Modal to show raw key only once
function showRawKeyModal(rawKey, name) {
  const modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10000;';
  
  const box = document.createElement('div');
  box.style.cssText = 'background:white;padding:2rem;border-radius:8px;max-width:500px;box-shadow:0 4px 6px rgba(0,0,0,0.1);';
  box.innerHTML = `
    <h3 style="margin-top:0;color:#d93025;">API Key Created: ${name}</h3>
    <p style="color:#666;margin:1rem 0;">Your new API key has been created. <strong>Copy it now — it will never be shown again!</strong></p>
    <div style="background:#f5f5f5;padding:1rem;border-radius:4px;border:1px solid #ddd;margin:1rem 0;word-break:break-all;font-family:monospace;font-size:0.9rem;">
      ${rawKey}
    </div>
    <button id="copyBtn" style="padding:0.5rem 1rem;background:#1f73e6;color:white;border:none;border-radius:4px;cursor:pointer;font-weight:bold;margin-right:0.5rem;">📋 Copy</button>
    <button id="closeBtn" style="padding:0.5rem 1rem;background:#999;color:white;border:none;border-radius:4px;cursor:pointer;">Close</button>
  `;
  
  modal.appendChild(box);
  document.body.appendChild(modal);
  
  document.getElementById('copyBtn').addEventListener('click', () => {
    navigator.clipboard.writeText(rawKey).then(() => {
      alert('✓ Copied to clipboard');
    }).catch(() => {
      alert('Please copy manually');
    });
  });
  
  document.getElementById('closeBtn').addEventListener('click', () => {
    modal.remove();
  });
}

async function deleteKey(key){
  if(!confirm('Delete this API key?')) return;
  try{
    await authFetch('/api/keys/'+key,{method:'DELETE'});
    await fetchKeys();
  }catch(e){ alert('Network error'); }
}

// ---------- Logout ----------
function doLogout(){
  clearToken();
  window.location.href = '/';
}

// ── Event delegation for dynamically-generated elements ──────────────────
userArea.addEventListener('click', function(e) {
  const el = e.target.closest('[data-action="logout"]');
  if (el) { e.preventDefault(); doLogout(); }
});

document.getElementById('keysList').addEventListener('click', function(e) {
  const el = e.target.closest('[data-action="delete-key"]');
  if (el) deleteKey(el.dataset.key);
});

// Initialise UI without enforcing login
checkAuth();