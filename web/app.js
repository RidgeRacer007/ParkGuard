const $ = s => document.querySelector(s);
let chart, map, hotspotMap, lastIncident = '';
const mockSeries = {
  labels: ['-30m', '-27m', '-24m', '-21m', '-18m', '-15m', '-12m', '-9m', '-6m', '-3m', 'now'],
  temp: [31, 32, 31, 33, 34, 37, 40, 48, 54, 66, 76],
  air: [27, 26, 28, 29, 31, 34, 38, 48, 57, 71, 82]
};

document.querySelectorAll('[data-page]').forEach(b => b.addEventListener('click', () => show(b.dataset.page)));
document.querySelectorAll('nav button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('nav button').forEach(n => n.classList.toggle('active', n === b));
}));
function show(id) {
  document.querySelectorAll('.page').forEach(x => x.classList.toggle('hidden', x.id !== id));
  document.querySelectorAll('nav button').forEach(n => n.classList.toggle('active', n.dataset.page === id));
  if (id === 'location') setTimeout(() => { initHotspotMap(); if (hotspotMap) hotspotMap.invalidateSize(); }, 100);
  if (id === 'emergency') setTimeout(() => { initMap(); if (map) map.invalidateSize(); }, 100);
  if (id === 'emergency') renderEmergencyFromNodes();
}
async function api(url, opt) {
  const r = await fetch(url, opt);
  if (!r.ok) throw Error(await r.text());
  return r.json();
}
function initMap() {
  if (map || !window.L) return;
  map = L.map('map').setView([19.0760, 72.8777], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors' }).addTo(map);
}
const mumbaiCases = [
  { date: '17 Oct 2025', place: 'MMRDA parking, Free Press Journal Marg · Nariman Point', title: 'EV buggy fire in underground parking', summary: 'A fire in an EV buggy’s battery box was reported at an underground parking lot. Three fire tenders responded; the fire was doused within minutes and no injuries were reported.', category: 'UNDERGROUND PARKING', source: 'Free Press Journal', url: 'https://www.freepressjournal.in/mumbai/mumbai-fire-breaks-out-at-mcgm-parking-lot-in-nariman-point-photos', action: 'Read report', lat: 18.9258, lon: 72.8235, pin: 'FPJ Marg / Nariman Point (approx.)' },
  { date: '3 Sep 2025', place: 'Dadar station · outside platform 14', title: 'More than 15 two-wheelers burned in station parking', summary: 'A fire spread through the two-wheeler parking beside Dadar railway station. Local fire equipment was used to bring it under control; reports said there were no injuries.', category: 'STATION PARKING', source: 'TV9 Marathi', url: 'https://www.tv9marathi.com/maharashtra/mumbai/major-fire-breaks-out-at-parking-lot-near-dadar-railway-station-more-than-15-two-wheelers-gutted-1484730.html', action: 'Read report', lat: 19.0183, lon: 72.8432, pin: 'Dadar station, platform 14 side (approx.)' },
  { date: '25 Mar 2025', place: 'PNGP Colony · near Maharashtra Nature Park, Dharavi', title: 'LPG truck fire followed by cylinder explosions', summary: 'A blaze near an illegal parking area involved an LPG-cylinder truck and nearby vehicles. Reports described multiple explosions; no injuries were reported. This is a fire/explosion reference case, not a sensor detection.', category: 'FIRE / EXPLOSION', source: 'The Indian Express', url: 'https://indianexpress.com/article/cities/mumbai/dharavi-fire-mumbai-police-book-truck-drivers-gas-agency-9905149/', action: 'Read report', lat: 19.0525, lon: 72.8615, pin: 'Maharashtra Nature Park / PNGP Colony (approx.)' },
  { date: '16 Feb 2024', place: 'Moksh Plaza area · S.V. Road, Borivali West', title: 'Parking-area fire damaged dozens of vehicles', summary: 'A fire affected vehicles parked in the Borivali West area near Moksh Plaza. The precise number differed between early reports; the cause was not confirmed in the report.', category: 'OPEN PARKING', source: 'Free Press Journal', url: 'https://www.freepressjournal.in/mumbai/mumbai-massive-fire-breaks-out-in-borivali-25-26-vehicles-gutted-video', action: 'Read report', lat: 19.2260, lon: 72.8547, pin: 'Moksh Plaza, Borivali West (approx.)' },
  { date: '25 Dec 2023', place: 'Phoenix Mall open parking · Lower Parel', title: 'Bike fire spread to 25–30 two-wheelers', summary: 'A motorcycle fire in an open mall parking lot spread to nearby two-wheelers. Firefighters used the site hydrant; no injuries were reported.', category: 'OPEN PARKING', source: 'Hindustan Times', url: 'https://www.hindustantimes.com/cities/mumbai-news/bike-catches-fire-at-lower-parel-mall-takes-30-others-with-it-101703531921238.html', action: 'Read report', lat: 18.9947, lon: 72.8234, pin: 'High Street Phoenix, Lower Parel (approx.)' }
];
function initHotspotMap() {
  if (!window.L) return;
  if (!hotspotMap) {
    hotspotMap = L.map('mumbai-hotspot-map').setView([19.0760, 72.8777], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap contributors' }).addTo(hotspotMap);
    const bounds = [];
    mumbaiCases.forEach((c, i) => {
      const point = [c.lat, c.lon]; bounds.push(point);
      const marker = L.circleMarker(point, { radius: 9, color: '#fff', weight: 2, fillColor: i < 3 ? '#dc554e' : '#e39a37', fillOpacity: .95 }).addTo(hotspotMap);
      marker.bindPopup(`<strong>${c.title}</strong><br>${c.place}<br>${c.date}<br><small>Approx. ${c.lat.toFixed(4)}, ${c.lon.toFixed(4)}</small><br><a href="${c.url}" target="_blank" rel="noopener noreferrer">${c.source} report ↗</a>`);
    });
    hotspotMap.fitBounds(bounds, { padding: [28, 28] });
  }
}
function renderMumbaiHotspots() {
  const host = $('#mumbai-hotspots');
  if (!host) return;
  host.innerHTML = mumbaiCases.map((c, i) => `<article class="reported-case hotspot-case"><div class="case-top"><span class="case-number">0${i + 1}</span><span class="case-type">${c.category}</span><time>${c.date}</time></div><h3>${c.title}</h3><p class="case-place">⌖ ${c.place}</p><p class="case-summary">${c.summary}</p><div class="case-coordinates"><span><b>Approx. coordinates</b><br>${c.lat.toFixed(5)}, ${c.lon.toFixed(5)}</span><a href="https://www.openstreetmap.org/?mlat=${c.lat}&mlon=${c.lon}#map=17/${c.lat}/${c.lon}" target="_blank" rel="noopener noreferrer">Open map ↗</a></div><div class="case-source"><span>Source: <b>${c.source}</b></span><a href="${c.url}" target="_blank" rel="noopener noreferrer">Read report ↗</a></div></article>`).join('');
}
function setText(id, value) { const el = $(id); if (el) el.textContent = value; }
function render(nodes) {
  window._nodes = nodes;
  const vals = Object.values(nodes || {});
  renderHardwareTelemetry(vals);
  const temps = vals.map(s => Number(s.reading?.temperature)).filter(Number.isFinite);
  const alerts = vals.filter(s => Number(s.escalation?.level || 0) >= 2).length;
  setText('#kpi-nodes', String(Math.max(vals.length, 3)).padStart(2, '0'));
  setText('#kpi-online', `${vals.filter(s => s.online).length || Math.max(vals.length, 3)} online`);
  setText('#kpi-alerts', String(alerts || 1).padStart(2, '0'));
  setText('#kpi-temp', (temps.length ? Math.max(...temps) : 76).toFixed(1));
  // The air score and timeline are intentionally illustrative, not calibrated measurements.
  setText('#kpi-air', '82');
  const nodeList = $('#node-list');
  if (nodeList && vals.length) nodeList.innerHTML = vals.slice(0, 3).map((s, i) => {
    const p = s.position || {};
    const level = Number(s.escalation?.level || 0);
    const severity = level >= 3 ? 'HIGH' : level === 2 ? 'WATCH' : (s.online ? 'ONLINE' : 'OFFLINE');
    return `<div class="node-row"><span class="node-light ${level >= 2 ? 'red' : ''}"></span><b>${s.node_id || `NODE-${i + 1}`}</b><span>${p.floor || 'Open lot'} · ${p.bay || 'Demo bay'}</span><strong class="${level < 2 ? 'green-text' : ''}">${severity}</strong></div>`;
  }).join('');
  if (chart) chart.destroy();
  const canvas = $('#trend');
  if (canvas && window.Chart) chart = new Chart(canvas, {
    type: 'line',
    data: { labels: mockSeries.labels, datasets: [
      { label: 'Temperature °C', data: mockSeries.temp, yAxisID: 'temp', borderColor: '#78ed83', backgroundColor: '#78ed831c', fill: true, tension: .38, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 },
      { label: 'Air index', data: mockSeries.air, yAxisID: 'air', borderColor: '#c5ef8a', backgroundColor: '#c5ef8a1c', fill: false, tension: .38, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2 }
    ] },
    options: { maintainAspectRatio: false, interaction: { intersect: false, mode: 'index' }, plugins: { legend: { display: false }, tooltip: { backgroundColor: '#102033', padding: 11 } }, scales: {
      x: { grid: { display: false }, ticks: { color: '#78ba80', maxTicksLimit: 6, font: { size: 10 } } },
      temp: { type: 'linear', position: 'left', min: 20, max: 90, grid: { color: '#173b20' }, ticks: { color: '#78ba80', font: { size: 10 } }, title: { display: true, text: '°C', color: '#78ba80' } },
      air: { type: 'linear', position: 'right', min: 0, max: 100, grid: { drawOnChartArea: false }, ticks: { color: '#78ba80', font: { size: 10 } }, title: { display: true, text: 'index', color: '#78ba80' } }
    } }
  });
}
function renderHardwareTelemetry(nodes) {
  const state = $('#hardware-live-state');
  const node = nodes.find(s => s.node_id === 'demo-node') || nodes[0];
  const reading = node?.reading;
  if (!reading) {
    if (state) { state.textContent = 'Waiting for sensor data'; state.classList.remove('is-live'); }
    setText('#live-temperature', '—');
    setText('#live-humidity', '—');
    setText('#live-mq135', '—');
    setText('#live-mq4', '—');
    setText('#live-node-time', 'Waiting for first COM4 update');
    return;
  }
  setText('#live-temperature', Number.isFinite(Number(reading.temperature)) ? Number(reading.temperature).toFixed(1) : '—');
  setText('#live-humidity', Number.isFinite(Number(reading.humidity)) ? Number(reading.humidity).toFixed(1) : '—');
  setText('#live-mq135', Number.isFinite(Number(reading.mq135)) ? Math.round(Number(reading.mq135)).toString() : '—');
  setText('#live-mq4', Number.isFinite(Number(reading.mq4)) ? Math.round(Number(reading.mq4)).toString() : '—');
  if (state) {
    state.textContent = node.online ? '● LIVE · COM4' : '○ NODE OFFLINE';
    state.classList.toggle('is-live', Boolean(node.online));
  }
  const stamp = node.time || reading.timestamp;
  setText('#live-node-time', stamp ? `Last node update ${new Date(stamp).toLocaleTimeString()}` : 'Receiving live serial updates');
}
function renderIncidents(items) {
  const timeline = $('#timeline');
  if (timeline) timeline.innerHTML = items.length ? items.map(i => `<article class="timeline-item"><b>${i.decision?.label || 'Simulated event'} · Level ${i.escalation?.level ?? 1}</b><div>${i.time || 'Demo time'} · ${i.position?.building || 'Open parking'}, ${i.position?.floor || 'Lot'}, ${i.position?.bay || 'East row'} (${i.position?.source || 'simulation'})</div>${i.photo ? `<img src="${i.photo}" alt="Uploaded incident capture">` : ''}<small>SHA-256 ${i.hash || 'hash pending'}</small></article>`).join('') : '<p class="muted">No incidents recorded yet. Use Scenarios to populate this demo.</p>';
  const activity = $('#activity-list');
  if (activity && items.length) activity.innerHTML = items.slice(0, 3).map((i, idx) => `<div class="activity-row"><i class="activity-mark ${idx === 0 ? 'red' : 'amber'}"></i><span><b>${i.decision?.label || 'Simulated event'}</b><small>${i.position?.bay || 'Demo bay'} · ${i.position?.floor || 'Open lot'} · ${i.time || 'recently'}</small></span><strong class="activity-level">LEVEL ${i.escalation?.level ?? 1}</strong></div>`).join('');
}
function renderEmergencyFromNodes() {
  const active = Object.values(window._nodes || {}).find(s => Number(s.escalation?.level || 0) >= 2);
  if (active) emergency(active);
  else renderNoEmergency();
}
function renderNoEmergency() {
  $('#emergency-content').innerHTML = `<div class="response-empty"><span class="empty-check">✓</span><div><div class="eyebrow">SYSTEM STATUS</div><h2>No active project alert</h2><p>There is no node currently reporting a Level 2 or Level 3 event. When a node reports an alert, its bay, readings, map pin, and response actions will appear here.</p><span class="response-state"><i></i> Monitoring demo fleet</span></div></div><div class="response-guidance"><b>Response reminder</b><span>Verify the reported bay and conditions before dispatch. For a confirmed fire in India, contact Fire Services at <a href="tel:101">101</a>.</span></div>`;
  setText('#emergency-map-coordinates', 'Mumbai · demo map view');
  initMap();
  if (map) { map.setView([19.0760, 72.8777], 12); map.eachLayer(layer => { if (layer instanceof L.CircleMarker || layer instanceof L.Marker) map.removeLayer(layer); }); }
}
function emergency(s) {
  const p = s.position || {}, e = s.escalation || {}, d = s.decision || {};
  const lat = Number(p.latitude), lon = Number(p.longitude);
  const hasCoords = Number.isFinite(lat) && Number.isFinite(lon);
  const latText = hasCoords ? lat.toFixed(5) : 'Not configured';
  const lonText = hasCoords ? lon.toFixed(5) : 'Not configured';
  const loc = `${p.building || 'Demo Garage'} · ${p.floor || 'Open lot'} · ${p.bay || 'A-01'}`;
  const mapsLink = hasCoords ? `https://www.google.com/maps?q=${lat},${lon}` : '#';
  const directionsLink = hasCoords ? `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}` : '#';
  const reading = s.reading || {};
  const temp = Number(reading.temperature);
  const gas = Number(reading.gas_raw);
  $('#emergency-content').innerHTML = `<div class="response-grid"><article class="response-alert-card"><div class="response-card-top"><span class="response-live-dot"></span><span>NODE ALERT · LEVEL ${Number(e.level || 2)}</span><span class="response-node-id">${s.node_id || 'NODE'}</span></div><div class="response-alert-title"><span class="status-chip high">${e.spreading ? 'SPREADING · ' : ''}${d.label || 'Potential hazard'}</span><span class="response-demo-tag">VERIFY CONDITIONS</span></div><h2>${loc}</h2><p class="response-summary">Review the readings and confirm this node’s bay before initiating a response. This dashboard event may be simulated.</p><div class="response-readings"><div><span>Temperature</span><b>${Number.isFinite(temp) ? `${temp.toFixed(1)} °C` : 'No reading'}</b></div><div><span>Gas / smoke raw</span><b>${Number.isFinite(gas) ? gas : 'No reading'}</b></div><div><span>Event confidence</span><b>${Number.isFinite(Number(d.confidence)) ? `${Math.round(Number(d.confidence) * 100)}%` : 'Not provided'}</b></div></div><div class="response-actions"><button class="response-primary" onclick="ack('${s.node_id}','watchman')">Acknowledge alert</button><button onclick="ack('${s.node_id}','watchman at scene')">Mark watchman on scene</button></div><div id="ack-result" class="ack-result" aria-live="polite">Waiting for acknowledgement</div></article><aside class="response-location-card"><div class="eyebrow">REPORTED NODE POSITION</div><h3>${p.building || 'Demo Garage'}</h3><p>${p.floor || 'Open lot'} · Bay ${p.bay || 'A-01'}</p><div class="response-coordinates"><span>LATITUDE</span><b>${latText}</b><span>LONGITUDE</span><b>${lonText}</b></div><small>Source: ${p.source || 'registered node config'}</small><div class="response-links"><a href="${mapsLink}" target="_blank" rel="noopener noreferrer" ${hasCoords ? '' : 'aria-disabled="true"'}>Open map ↗</a><a href="${directionsLink}" target="_blank" rel="noopener noreferrer" ${hasCoords ? '' : 'aria-disabled="true"'}>Get directions ↗</a></div></aside></div><div class="response-guidance"><b>Response checklist</b><span><i>1</i> Confirm node and bay from the map.</span><span><i>2</i> Verify conditions with the watchman / camera.</span><span><i>3</i> For a confirmed fire, contact Fire Services at <a href="tel:101">101</a>.</span></div>`;
  setText('#emergency-map-coordinates', hasCoords ? `${latText}, ${lonText}` : 'Node coordinates not configured');
  initMap();
  if (map) {
    map.eachLayer(layer => { if (layer instanceof L.CircleMarker || layer instanceof L.Marker) map.removeLayer(layer); });
    if (hasCoords) {
      const marker = L.circleMarker([lat, lon], { radius: 13, color: '#fff', weight: 3, fillColor: '#df514a', fillOpacity: 1, className: 'pulse' }).addTo(map).bindPopup(`<strong>${s.node_id || 'Demo node'}</strong><br>${loc}<br>${latText}, ${lonText}`);
      map.setView([lat, lon], 17);
      marker.openPopup();
    } else map.setView([19.0760, 72.8777], 12);
  }
}
async function refresh() {
  try {
    const x = await api('/api/status');
    setText('#connection', '● API connected');
    render(x.nodes || {});
    renderIncidents(x.incidents || []);
    setText('#updated-at', `Updated ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`);
  } catch (e) {
    setText('#connection', '● API offline');
    render({});
  }
}
window.ack = async (n, who) => {
  const feedback = $('#ack-result');
  if (feedback) feedback.textContent = 'Saving acknowledgement…';
  try {
    const result = await api('/api/ack/' + n, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ who }) });
    if (feedback) feedback.textContent = `${result.acknowledged ? 'Acknowledged' : 'Acknowledgement recorded'} by ${result.who || who} · ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    refresh();
  } catch (e) { if (feedback) feedback.textContent = `Could not save acknowledgement: ${e.message}`; }
};
const reportedCases = [
  { date: '29 May 2024', place: 'Mandawali · East Delhi, India', title: '17 cars damaged at an open MCD parking lot', summary: 'Fire spread through parked cars at an open lot. Eight fire tenders responded; officials said the blaze was brought under control in about two hours, with no casualties reported.', category: 'OPEN PARKING', source: 'Hindustan Times', url: 'https://www.hindustantimes.com/cities/delhi-news/vehicles-shops-gutted-in-two-fire-incidents-in-delhi-101717004450397.html', action: 'Read incident report' },
  { date: '15 Mar 2024', place: 'Bibwewadi · Pune, India', title: '17 vehicles caught fire in an open garage space', summary: 'Cars parked in the open space of a garage were badly damaged. Pune fire brigade officials said the fire was doused within 30 minutes; no casualties were reported.', category: 'OPEN GARAGE', source: 'The Indian Express', url: 'https://indianexpress.com/article/cities/pune/fire-garage-pune-bibwewadi-luxury-cars-9215289/', action: 'Read incident report' },
  { date: '30 Nov 2024', place: 'Cantt station · Varanasi, India', title: 'More than 200 two-wheelers charred in station parking', summary: 'A large fire spread through the railway-station parking area. Around 12 fire brigade vehicles responded; the initial investigation cited a short circuit. No injuries were reported.', category: 'TRANSIT PARKING', source: 'NDTV', url: 'https://www.ndtv.com/india-news/massive-fire-breaks-out-at-varanasi-railway-station-200-vehicles-destroyed-7138646', action: 'Read report & view footage' },
  { date: '22 Nov 2024', place: 'Frazier Avenue · Chattanooga, USA', title: 'EV-linked apartment parking-garage fire', summary: 'City investigators said an EV was believed to have started the garage fire. Two adjacent vehicles burned, most cars had heat damage, and seven people were rescued; smoke-inhalation patients were treated and released.', category: 'PARKING GARAGE', source: 'City of Chattanooga Fire Department', url: 'https://chattanooga.gov/stay-informed/latest-news/update-frazier-ave-apartment-fire-caused-electric-vehicle', action: 'City report + response footage' },
  { date: '10 Jun 2025', place: 'Downtown · Nashville, USA', title: 'Garage fire damaged vehicles and a parking structure', summary: 'Vehicles burned across the fourth floor of the public-library garage. A ramp between levels collapsed, nearby hotel guests were evacuated, and officials reported no injuries.', category: 'MULTI-LEVEL GARAGE', source: 'Associated Press', url: 'https://apnews.com/article/tennessee-nashville-library-fire-explosions-e00ed028d76fda525892a2b76a70d507', action: 'Read AP report' }
];
function renderReportedCases() {
  const host = $('#reported-cases');
  if (!host) return;
  host.innerHTML = reportedCases.map((c, i) => `<article class="reported-case"><div class="case-top"><span class="case-number">0${i + 1}</span><span class="case-type">${c.category}</span><time>${c.date}</time></div><h3>${c.title}</h3><p class="case-place">⌖ ${c.place}</p><p class="case-summary">${c.summary}</p><div class="case-source"><span>Source: <b>${c.source}</b></span><a href="${c.url}" target="_blank" rel="noopener noreferrer">${c.action} ↗</a></div></article>`).join('');
}
renderReportedCases();
renderMumbaiHotspots();
const scenarios = [
  { id: 'normal', name: 'Normal baseline', group: 'BASELINE', level: 'Level 0', description: 'Routine air, gas, temperature and humidity readings.' },
  { id: 'exhaust', name: 'Vehicle exhaust', group: 'AIR QUALITY', level: 'Trend check', description: 'Elevated gas reading without a fire signal.' },
  { id: 'firecracker_smoke', name: 'Festival smoke', group: 'SEASONAL', level: 'Smoke check', description: 'Short smoke event to review nuisance-alarm handling.' },
  { id: 'cng_leak', name: 'CNG / gas leak', group: 'GAS HAZARD', level: 'Gas rise', description: 'High gas reading with a modest temperature change.' },
  { id: 'ev_fault', name: 'EV battery heat', group: 'HEAT RISE', level: 'Heat trend', description: 'Temperature climbs while air-quality readings change.' },
  { id: 'vehicle_fire', name: 'Vehicle fire', group: 'FIRE', level: 'High alert', description: 'Combined heat, gas and smoke readings at one node.' },
  { id: 'explosion', name: 'Rapid fire / gas event', group: 'COMBINED HAZARD', level: 'Critical pattern', description: 'Fast rise in heat and gas with a smoke signal; heuristic demo only.' },
  { id: 'unwarranted_fire', name: 'Unexpected fire signal', group: 'VERIFICATION', level: 'Verify event', description: 'Fire signal appears outside a registered event window.' },
  { id: 'spreading_fire', name: 'Fire spreading to neighbor', group: 'MULTI-NODE', level: 'Escalation', description: 'Two adjacent demo nodes report a matching fire pattern.' },
  { id: 'network_outage', name: 'Network outage queue', group: 'CONNECTIVITY', level: 'Offline queue', description: 'Shows the demo response for buffered, emergency-priority readings.' }
];
$('#scenarios').innerHTML = scenarios.map((s, i) => `<article class="scenario-card"><div class="scenario-card-top"><span class="scenario-number">${String(i + 1).padStart(2, '0')}</span><span class="scenario-group">${s.group}</span></div><h2>${s.name}</h2><p>${s.description}</p><div class="scenario-card-bottom"><span>${s.level}</span><button data-scenario="${s.id}" onclick="runDemo('${s.id}')">Run scenario <span>↗</span></button></div></article>`).join('');
window.runDemo = async s => {
  const scenario = scenarios.find(item => item.id === s);
  const button = document.querySelector(`[data-scenario="${s}"]`);
  const status = $('#demo-status');
  const title = $('#demo-result-title');
  const summary = $('#demo-result-summary');
  if (button) { button.disabled = true; button.textContent = 'Running…'; }
  if (status) status.textContent = `Sending ${scenario?.name || s} sample to the ParkGuard demo API…`;
  try {
    const result = await api('/api/demo/' + s, { method: 'POST' });
    $('#demo-output').textContent = JSON.stringify(result, null, 2);
    if (title) title.textContent = scenario?.name || s;
    if (s === 'network_outage') {
      if (summary) summary.textContent = 'Queue behavior preview returned. The dashboard API itself remains online; this card does not disconnect your network.';
      if (status) status.textContent = 'QUEUE PREVIEW COMPLETE · no live network was disconnected';
    } else {
      const rows = Array.isArray(result) ? result : [result];
      const highest = rows.reduce((n, row) => Math.max(n, Number(row?.escalation?.level || 0)), 0);
      const labels = rows.map(row => row?.decision?.label).filter(Boolean);
      if (summary) summary.textContent = `${rows.length} node response${rows.length === 1 ? '' : 's'} returned${labels.length ? ` · ${[...new Set(labels)].join(', ')}` : ''} · highest escalation level ${highest}. Open Response to view a qualifying alert.`;
      if (status) status.textContent = `SCENARIO COMPLETE · ${rows.length} response${rows.length === 1 ? '' : 's'} received`;
    }
    await refresh();
  } catch (e) {
    $('#demo-output').textContent = e.message;
    if (title) title.textContent = 'Scenario could not run';
    if (summary) summary.textContent = 'Check that the local ParkGuard API is running, then try again.';
    if (status) status.textContent = 'SCENARIO FAILED · API request did not complete';
  } finally {
    if (button) { button.disabled = false; button.innerHTML = 'Run scenario <span>↗</span>'; }
  }
};
$('#open-response-plan').addEventListener('click', async event => {
  const button = event.currentTarget;
  const status = $('#response-plan-status');
  button.disabled = true;
  button.querySelector('span').textContent = 'Preparing response plan…';
  if (status) status.textContent = 'Checking the current node alerts…';
  try {
    await refresh();
    let active = Object.values(window._nodes || {}).find(node => Number(node.escalation?.level || 0) >= 2);
    if (!active) {
      if (status) status.textContent = 'No active alert found · starting the clearly labeled demo fire preview…';
      await api('/api/demo/vehicle_fire', { method: 'POST' });
      await refresh();
      active = Object.values(window._nodes || {}).find(node => Number(node.escalation?.level || 0) >= 2);
    }
    if (!active) throw Error('No response-level alert was returned by the demo API.');
    if (status) status.textContent = `Opening ${active.node_id || 'node'} · Level ${active.escalation?.level || 2} response plan.`;
    show('emergency');
  } catch (error) {
    if (status) status.textContent = `Could not open the response plan: ${error.message}`;
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Open response plan';
  }
});
(async () => {
  try {
    const ns = await api('/api/nodes');
    window._nodes = Object.fromEntries(ns.map(n => [n.node_id, n.status]));
    $('#locations').innerHTML = ns.map(n => `<article><b>${n.config.building} · ${n.config.floor} · ${n.config.bay}</b><p>${n.config.latitude}, ${n.config.longitude}</p><small>${n.config.source} · ${n.node_id}</small></article>`).join('');
  } catch { $('#locations').innerHTML = '<p class="muted">Location API is offline.</p>'; }
})();
$('#locate').onclick = () => {
  const status = $('#phone-status');
  if (!navigator.geolocation) { status.textContent = 'This browser does not support location sharing.'; return; }
  status.textContent = 'Waiting for browser location permission…';
  navigator.geolocation.getCurrentPosition(async p => {
    try {
      const coords = { latitude: Number(p.coords.latitude.toFixed(6)), longitude: Number(p.coords.longitude.toFixed(6)), accuracy_m: Math.round(p.coords.accuracy) };
      $('#phone-result').textContent = JSON.stringify(await api('/api/phone-location', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(coords) }), null, 2);
      status.textContent = `Location shared · accuracy about ${coords.accuracy_m} m · ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch (e) { status.textContent = `Could not send location to the demo API: ${e.message}`; }
  }, e => { status.textContent = `Location unavailable: ${e.message}`; }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 });
};
let micStream, micContext, micFrame;
$('#mic').onclick = async () => {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micContext = new AudioContext();
    const src = micContext.createMediaStreamSource(micStream), an = micContext.createAnalyser();
    src.connect(an); const data = new Uint8Array(an.fftSize);
    $('#mic-status').textContent = 'Microphone is on · relative loudness only';
    $('#mic').disabled = true; $('#mic-stop').disabled = false;
    function tick() { an.getByteTimeDomainData(data); const rms = Math.sqrt(data.reduce((a, v) => a + (v - 128) ** 2, 0) / data.length) / 128; $('#meter').value = rms; $('#meter-value').textContent = `${Math.round(rms * 100)}%`; micFrame = requestAnimationFrame(tick); }
    tick();
  } catch (e) { $('#mic-status').textContent = `Microphone unavailable: ${e.message}`; }
};
$('#mic-stop').onclick = async () => {
  if (micFrame) cancelAnimationFrame(micFrame);
  if (micStream) micStream.getTracks().forEach(track => track.stop());
  if (micContext && micContext.state !== 'closed') await micContext.close();
  micStream = micContext = micFrame = null;
  $('#meter').value = 0; $('#meter-value').textContent = '0%';
  $('#mic-status').textContent = 'Microphone is off.'; $('#mic').disabled = false; $('#mic-stop').disabled = true;
};
const cameraInput = $('#camera-url'), cameraPreview = $('#camera-preview'), cameraStatus = $('#camera-status');
$('#camera-connect').onclick = () => {
  const raw = cameraInput.value.trim();
  if (!raw) { cameraStatus.textContent = 'Enter the camera IP address first'; return; }
  try {
    const u = new URL(raw.includes('://') ? raw : `http://${raw}`);
    if (!['http:', 'https:'].includes(u.protocol)) throw Error('Use an http or https camera address');
    u.pathname = '/stream'; u.search = ''; u.hash = '';
    cameraStatus.textContent = 'Connecting…'; cameraPreview.hidden = false;
    cameraPreview.onload = () => cameraStatus.textContent = 'Live camera feed';
    cameraPreview.onerror = () => cameraStatus.textContent = 'Camera not reachable — check its IP, Wi-Fi and firmware';
    cameraPreview.src = u.href + '?t=' + Date.now();
  } catch (e) { cameraStatus.textContent = e.message; }
};
cameraInput.addEventListener('keydown', e => { if (e.key === 'Enter') $('#camera-connect').click(); });
setInterval(refresh, 3000);
refresh();
