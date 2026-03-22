let currentApiKey = '';
let configChart;
let stagedRules = [];
let userRole = 'VIEWER';

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

function updateVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function showSaveBar() {
    const el = document.getElementById('saveBar');
    if (el) el.classList.add('active');
}

function hideSaveBar() {
    const el = document.getElementById('saveBar');
    if (el) el.classList.remove('active');
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('active');
    setTimeout(() => t.classList.remove('active'), 4000);
}

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(t => {
        t.classList.toggle('active', t.textContent.toLowerCase().includes(tabId.toLowerCase()));
    });
    document.querySelectorAll('.tab-content').forEach(c => {
        c.classList.add('hidden');
    });
    const content = document.getElementById(`tab-${tabId}`);
    if (content) content.classList.remove('hidden');
}

function generateSecret() {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()';
    let secret = '';
    for (let i = 0; i < 32; i++) {
        secret += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const el = document.getElementById('webhookSecret');
    if (el) {
        el.value = secret;
        el.type = 'text';
    }
}

async function saveWebhookSettings() {
    const url = document.getElementById('alertWebhookUrl').value;
    const secret = document.getElementById('webhookSecret').value;
    try {
        const res = await fetch('/v1/auth/settings/webhooks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCookie('vp_csrf')
            },
            body: JSON.stringify({ alert_webhook_url: url, webhook_secret: secret })
        });
        if (res.ok) showToast('Neural Alert Engine updated.');
        else showToast('Failed to update alert engine.');
    } catch (e) {
        showToast('Synchronisation failed.');
    }
}

function copyKey() {
    if (currentApiKey) {
        navigator.clipboard.writeText(currentApiKey);
        showToast('API Master Key secured to clipboard.');
    }
}

async function authenticate() {
    const key = document.getElementById('apiKeyInput').value;
    const err = document.getElementById('authError');
    if (!key) return;
    try {
        const res = await fetch('/v1/merchant/config', {
            headers: { 'X-API-Key': key }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Neural Handshake Refused');
        
        currentApiKey = key;
        loadDashboard(data);
        fetchStats();
        fetchWebhookSettings();
        fetchRules();
        fetchActionHistory();
        fetchShieldStats();
        fetchTeamMembers();
        fetchTeamInvites();
        
        // Phase 27: Initialise SDK credentials view
        const sdkEl = document.getElementById('sdkCredentials');
        if (sdkEl) sdkEl.textContent = `api_key: "${currentApiKey}"`;
        
        if (typeof initNeuralMap === 'function') initNeuralMap();
    } catch (e) {
        if (err) {
            err.textContent = e.message;
            err.style.display = 'block';
        }
    }
}

async function fetchWebhookSettings() {
    try {
        const res = await fetch('/v1/auth/settings/webhooks');
        const data = await res.json();
        if (res.ok) {
            const urlEl = document.getElementById('alertWebhookUrl');
            if (urlEl) urlEl.value = data.webhook_url || '';
            if (data.has_secret) {
                const secEl = document.getElementById('webhookSecret');
                if (secEl) secEl.placeholder = '•••••••••••••••• (Secret Set)';
            }
        }
    } catch (e) {}
}

function loadDashboard(data) {
    document.getElementById('authOverlay').style.display = 'none';
    document.getElementById('mainApp').style.display = 'block';
    document.getElementById('merchantEmail').textContent = data.email;
    userRole = data.role || 'VIEWER';
    document.getElementById('userBadge').textContent = userRole;
    document.getElementById('displayApiKey').textContent = currentApiKey;
    if (data.team_id) document.getElementById('displayTeamId').textContent = `TEAM_ID: ${data.team_id}`;

    if (userRole === 'ADMIN') {
        document.getElementById('teamTab').classList.remove('hidden');
    } else {
        document.querySelectorAll('button:not(.logout-btn):not(.primary)').forEach(btn => {
           if (btn.textContent.toLowerCase().includes('save') || btn.textContent.toLowerCase().includes('sync')) {
               btn.disabled = true;
               btn.style.opacity = '0.5';
               btn.title = 'Admin privileges required';
           }
        });
    }
    
    
    const c = data.risk_config || {};
    setRangeValue('weight_email_name', 'val_email_name', c.email_name_mismatch_weight || 15);
    setRangeValue('weight_poor_address', 'val_poor_address', c.poor_address_weight || 15);
    setRangeValue('weight_bot_speed', 'val_bot_speed', c.bot_speed_weight || 30);
    setRangeValue('weight_global_reputation', 'val_global_reputation', c.global_network_weight || 20);
    setRangeValue('threshold_range', 'val_threshold', c.decision_threshold || 50);
    
    // Phase 28: Initialise Shadow Mode
    const smToggle = document.getElementById('shadowModeToggle');
    if (smToggle) smToggle.checked = c.shadow_mode === 1;
    
    initChart();
    initThreatMap();
}

function setRangeValue(inputId, labelId, val) {
    const input = document.getElementById(inputId);
    if (input) input.value = val;
    const label = document.getElementById(labelId);
    if (label) label.textContent = val;
}

async function fetchStats() {
    try {
        const res = await fetch('/v1/merchant/stats', {
            headers: { 'X-API-Key': currentApiKey }
        });
        const stats = await res.json();
        
        document.getElementById('statSavings').textContent = `₹${stats.total_savings_inr.toLocaleString()}`;
        
        const usage = stats.usage_this_month || 0;
        const limit = stats.plan === 'STARTER' ? 1000 : 10000;
        const usageEl = document.getElementById('statUsage');
        if (usageEl) usageEl.textContent = `${usage} / ${limit}`;
        const barEl = document.getElementById('usageBar');
        if (barEl) barEl.style.width = `${(usage / limit) * 100}%`;
        
        const latContent = document.getElementById('statLatency');
        if (latContent) {
            const lastLat = parseFloat(stats.last_latency || 0);
            latContent.textContent = `${lastLat.toFixed(1)}ms`;
            if (lastLat < 10) latContent.style.color = 'var(--success)';
            else if (lastLat < 50) latContent.style.color = 'var(--accent)';
            else latContent.style.color = 'var(--text)';
        }

        const br = usage > 0 ? (stats.total_blocks / usage * 100).toFixed(1) : '0.0';
        document.getElementById('statBlockRate').textContent = `${br}%`;
        
        renderActivity(stats.recent_activity || []);
    } catch (e) { console.error(e); }
}

function renderActivity(activity) {
    const feed = document.getElementById('activityFeed');
    if (!feed) return;
    feed.innerHTML = '';
    activity.forEach(item => {
        const div = document.createElement('div');
        div.className = 'activity-item';
        div.innerHTML = `
            <div class="activity-icon">⚡</div>
            <div>
                <div style="font-weight:700;">${item.decision} Scan</div>
                <div style="color:var(--text-muted);">Neural Score: ${item.risk_score} | User: ${item.email}</div>
                <div class="time">${new Date(item.timestamp * 1000).toLocaleTimeString()}</div>
            </div>
        `;
        feed.appendChild(div);
    });
}

async function saveChanges() {
    const payload = {
        email_name_mismatch_weight: Number(document.getElementById('weight_email_name').value),
        poor_address_weight: Number(document.getElementById('weight_poor_address').value),
        bot_speed_weight: Number(document.getElementById('weight_bot_speed').value),
        global_network_weight: Number(document.getElementById('weight_global_reputation').value),
        decision_threshold: Number(document.getElementById('threshold_range').value)
    };

    try {
        const res = await fetch('/v1/merchant/config', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-Key': currentApiKey,
                'X-CSRF-Token': getCookie('vp_csrf')
            },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            showToast('Configuration synced to core neurons.');
            hideSaveBar();
        } else {
            showToast('Failed to sync intelligence weights.');
        }
    } catch (e) {
        showToast('Network error.');
    }
}

function logout() {
    document.cookie = 'vantix_token=; Max-Age=0; path=/;';
    window.location.reload();
}

async function runSimulation() {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Scanning...';
    btn.disabled = true;

    const payload = {
        uid: 'sim_' + Date.now(),
        amt: 5000,
        email: document.getElementById('sim_email').value || 'test@example.com',
        addr: document.getElementById('sim_addr').value || 'No 45, High Risk Lane, City',
        ip: '1.2.3.4',
        pin: '560001',
        device_hash: 'sim_device',
        checkout_time_secs: 1.5
    };

    try {
        const res = await fetch('/v1/merchant/simulate', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-Key': currentApiKey,
                'X-CSRF-Token': getCookie('vp_csrf')
            },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        const box = document.getElementById('simResult');
        const stat = document.getElementById('simStatus');
        const score = document.getElementById('simScore');
        const flags = document.getElementById('simFlags');

        if (box) {
            box.style.display = 'block';
            stat.textContent = data.decision === 'ALLOW_COD' ? '✓ NEURAL CLEARANCE' : '⚠ ACCESS DENIED';
            stat.style.color = data.decision === 'ALLOW_COD' ? 'var(--success)' : 'var(--danger)';
            score.textContent = `Neural Risk: ${data.risk_score.toFixed(1)} / Threshold: ${document.getElementById('threshold_range').value}`;
            flags.textContent = data.risk_factors.length ? 'Neural Inhibitors: ' + data.risk_factors.join(', ') : 'No anomalies detected in subject profile.';
        }
    } catch (e) {
        showToast('Simulation aborted by neural firewall.');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function fetchRules() {
    try {
        const res = await fetch('/v1/auth/rules');
        const data = await res.json();
        renderRules(data.rules || []);
    } catch (e) {
        console.error("Rules fetch failed", e);
    }
}

function renderRules(rules) {
    stagedRules = rules;
    const list = document.getElementById('activeRulesList');
    const empty = document.getElementById('rulesEmptyState');
    if (!list) return;
    list.innerHTML = '';
    
    if (rules.length === 0) {
        if (empty) empty.classList.remove('hidden');
        return;
    }
    if (empty) empty.classList.add('hidden');

    rules.forEach((rule, idx) => {
        const row = document.createElement('div');
        row.className = 'config-row';
        row.style = 'background:rgba(255,255,255,0.02); padding:16px; border-radius:14px; margin-bottom:8px; border:1px solid var(--border);';
        row.innerHTML = `
            <div class="config-info">
                <div style="font-weight:700; font-size:14px; margin-bottom:4px; display:flex; align-items:center; gap:8px;">
                    ${rule.action === 'CANCEL' ? '🔴 Auto-Cancel' : rule.action === 'VERIFY' ? '🔵 Auto-Verify (OTP)' : '🟡 Alert Notification'}
                </div>
                <div style="font-size:12px; color:var(--text-muted)">Triggered when risk score exceeds <strong>${rule.threshold}</strong></div>
            </div>
            <button class="logout-btn" style="background:transparent; border-color:var(--border); width:auto;" onclick="removeRule(${idx})">Delete</button>
        `;
        list.appendChild(row);
    });
}

function addRuleRow() {
    const threshold = prompt("Enter Risk Score Threshold (0-100):", "85");
    if (threshold === null) return;
    
    const action = prompt("Enter Action (CANCEL, VERIFY, NOTIFY):", "CANCEL");
    if (!action) return;

    const newRule = {
        id: 'rule_' + Date.now(),
        threshold: parseFloat(threshold),
        action: action.toUpperCase()
    };
    
    stagedRules.push(newRule);
    renderRules(stagedRules);
    document.getElementById('saveRulesBtn').style.display = 'block';
}

function removeRule(idx) {
    stagedRules.splice(idx, 1);
    renderRules(stagedRules);
    document.getElementById('saveRulesBtn').style.display = 'block';
}

async function saveRules() {
    try {
        const res = await fetch('/v1/auth/rules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCookie('vp_csrf')
            },
            body: JSON.stringify({ rules: stagedRules })
        });
        if (res.ok) {
            showToast('Autonomous rules committed to engine.');
            document.getElementById('saveRulesBtn').style.display = 'none';
        }
    } catch (e) {
        showToast('Failed to sync rules.');
    }
}

async function fetchActionHistory() {
    try {
        const res = await fetch('/v1/auth/actions/history');
        const data = await res.json();
        renderActionHistory(data.history || []);
    } catch (e) {
        console.error("History fetch failed", e);
    }
}

function renderActionHistory(history) {
    const feed = document.getElementById('actionHistoryFeed');
    if (!feed) return;
    feed.innerHTML = '';
    
    if (history.length === 0) {
        feed.innerHTML = '<div style="color:var(--text-muted); font-size:13px; text-align:center; padding:20px;">Waiting for neural triggers...</div>';
        return;
    }

    history.forEach(item => {
        const div = document.createElement('div');
        div.className = 'activity-item';
        const timeStr = new Date(item.timestamp * 1000).toLocaleTimeString();
        div.innerHTML = `
            <div class="activity-icon" style="color:${item.action === 'CANCEL' ? 'var(--danger)' : 'var(--accent)'}; background:rgba(255,255,255,0.05)">
                ${item.action === 'CANCEL' ? '✕' : '⚡'}
            </div>
            <div>
                <div style="font-weight:700;">${item.action} Executed</div>
                <div style="color:var(--text-muted);">Neural Score: ${item.score} | Order: ${item.order_id}</div>
                <div class="time">${timeStr}</div>
            </div>
        `;
        feed.appendChild(div);
    });
}

function switchSdkTab(sdk) {
    document.querySelectorAll('#tab-integration .tab').forEach(t => {
        t.classList.toggle('active', t.textContent.toLowerCase().includes(sdk));
    });
    document.querySelectorAll('.sdk-content').forEach(c => c.classList.add('hidden'));
    const sdkEl = document.getElementById(`sdk-${sdk}`);
    if (sdkEl) sdkEl.classList.remove('hidden');
}

async function runConnectionTest() {
    const dot = document.getElementById('testerStatus');
    const txt = document.getElementById('testerText');
    if (txt) txt.textContent = 'VERIFYING...';
    
    try {
        const res = await fetch('/v1/auth/test-connection', {
            method: 'POST',
            headers: { 'X-API-Key': currentApiKey }
        });
        if (res.ok) {
            if (dot) {
                dot.style.background = 'var(--success)';
                dot.style.boxShadow = '0 0 15px var(--success)';
            }
            if (txt) {
                txt.textContent = 'CONNECTION ACTIVE';
                txt.style.color = 'var(--success)';
            }
            showToast('Neural handshake verified.');
        } else {
            throw new Error();
        }
    } catch (e) {
        if (dot) {
            dot.style.background = 'var(--danger)';
            dot.style.boxShadow = '0 0 15px var(--danger)';
        }
        if (txt) {
            txt.textContent = 'HANDSHAKE FAILED';
            txt.style.color = 'var(--danger)';
        }
        showToast('Authentication failed.');
    }
}

async function fetchShieldStats() {
    try {
        const res = await fetch('/v1/auth/financial-shield/stats');
        const data = await res.json();
        if (data.is_active) {
            const optIn = document.getElementById('shieldOptIn');
            if (optIn) optIn.classList.add('hidden');
            const stats = document.getElementById('shieldStats');
            if (stats) stats.classList.remove('hidden');
            const shielded = document.getElementById('statShielded');
            if (shielded) shielded.textContent = `₹${data.shielded_capital.toLocaleString()}`;
            const claims = document.getElementById('statClaims');
            if (claims) claims.textContent = data.active_claims;
        }
    } catch (e) {}
}

async function optInShield() {
    try {
        const res = await fetch('/v1/auth/financial-shield/opt-in', {
            method: 'POST',
            headers: { 'X-CSRF-Token': getCookie('vp_csrf') }
        });
        if (res.ok) {
            showToast('Financial Shield Activated');
            fetchShieldStats();
        }
    } catch (e) {
        showToast('Pilot activation failed.');
    }
}

async function generateAuditReport(format = 'json') {
    const startStr = prompt("Enter Start Timestamp (Unix seconds):", (Date.now()/1000 - 86400*7).toFixed(0));
    if (!startStr) return;
    
    try {
        const res = await fetch(`/v1/compliance/report?start_timestamp=${startStr}&format=${format}`, {
            headers: { 'X-API-Key': currentApiKey }
        });
        const data = await res.json();
        
        if (format === 'csv') {
            const blob = new Blob([data.csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('hidden', '');
            a.setAttribute('href', url);
            a.setAttribute('download', `Vantix_Audit_${data.report_id || 'REPORT'}.csv`);
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            const preview = document.getElementById('compliancePreview');
            if (preview) preview.classList.remove('hidden');
            const content = document.getElementById('auditPreviewContent');
            if (content) content.textContent = JSON.stringify(data, null, 2);
            const date = document.getElementById('lastReportDate');
            if (date) date.textContent = new Date().toLocaleTimeString();
            showToast('Compliance report generated.');
        }
    } catch (e) {
        showToast('Report generation failed.');
    }
}

async function runForensicAnalysis() {
    const riskIdEl = document.getElementById('forensicRiskId');
    if (!riskIdEl) return;
    const riskId = riskIdEl.value.trim();
    if (!riskId) return showToast('Please enter a Risk ID.');
    
    const query = document.getElementById('forensicQuery').value.trim();
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Analyzing Neural Clusters...';
    btn.disabled = true;

    try {
        const res = await fetch('/v1/forensics/ask', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-API-Key': currentApiKey 
            },
            body: JSON.stringify({ risk_id: riskId, query: query })
        });
        const data = await res.json();
        
        if (res.ok) {
            const card = document.getElementById('forensicResultsCard');
            if (card) card.style.display = 'block';
            document.getElementById('forensicNarrative').textContent = data.adjudication_narrative;
            document.getElementById('forensicTitle').textContent = `AI Adjudication: ${riskId}`;
            
            const signals = document.getElementById('forensicSignals');
            signals.innerHTML = '';
            Object.entries(data.forensic_signals).forEach(([key, val]) => {
                const item = document.createElement('div');
                item.className = 'activity-item';
                item.innerHTML = `
                    <div class="activity-icon">${key[0].toUpperCase()}</div>
                    <div>
                        <div style="font-weight:700; text-transform:capitalize;">${key} Sensor</div>
                        <div style="color:var(--text-muted);">${val}</div>
                    </div>
                `;
                signals.appendChild(item);
            });
            showToast('Forensic analysis complete.');
        } else {
            showToast(data.detail || 'Analysis failed.');
        }
    } catch (e) {
        showToast('Neural network timeout.');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function fetchTeamMembers() {
    try {
        const res = await fetch('/v1/team/members');
        const data = await res.json();
        const list = document.getElementById('teamMembersList');
        if (!list) return;
        
        const members = data.members || data;
        list.innerHTML = '';
        members.forEach(m => {
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid var(--border)';
            row.innerHTML = `
                <td style="padding:16px; font-weight:600;">${m.email}</td>
                <td style="padding:16px;"><span style="background:rgba(20,184,166,0.1); color:var(--accent); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700;">${m.role}</span></td>
                <td style="padding:16px; color:var(--text-muted);">${new Date(m.joined_at * 1000).toLocaleDateString()}</td>
                <td style="padding:16px; text-align:right;">
                    <button class="logout-btn" style="background:transparent; border-color:var(--border); font-size:10px;">Edit</button>
                </td>
            `;
            list.appendChild(row);
        });
    } catch (e) {}
}

async function fetchTeamInvites() {
    try {
        const res = await fetch('/v1/team/invites');
        const invites = await res.json();
        console.log("Team Invites:", invites);
    } catch (e) {}
}

async function showInviteModal() {
    const email = prompt("Enter team member email to invite:");
    if (!email) return;
    const role = prompt("Assign role (ADMIN, ANALYST, VIEWER):", "ANALYST");
    if (!role) return;
    
    try {
        const res = await fetch(`/v1/team/invite?email=${encodeURIComponent(email)}&role=${role}`, {
            method: 'POST',
            headers: { 'X-CSRF-Token': getCookie('vp_csrf') }
        });
        if (res.ok) {
            showToast(`Invitation sent to ${email} as ${role}.`);
            fetchTeamInvites();
        } else {
            showToast('Failed to send invitation.');
        }
    } catch (e) {
        showToast('Network error during invitation.');
    }
}

function initChart() {
    const canvas = document.getElementById('blocksChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(20, 184, 166, 0.2)');
    gradient.addColorStop(1, 'rgba(20, 184, 166, 0)');

    if (configChart) configChart.destroy();

    configChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Neural Scans',
                data: [120, 190, 150, 210, 240, 180, 290],
                borderColor: '#14b8a6',
                borderWidth: 3,
                pointBackgroundColor: '#14b8a6',
                backgroundColor: gradient,
                fill: true,
                tension: 0.45
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#475569', font: { weight: '600' } } },
                y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#475569', font: { weight: '600' } } }
            }
        }
    });
}

function toggleShadowMode() {
    const active = document.getElementById('shadowModeToggle').checked;
    showToast(`Neural Shadow Mode ${active ? 'ENGAGED' : 'DISENGAGED'}. Decisions will ${active ? 'not block' : 'now block'} real traffic.`);
    showSaveBar();
}

let threatNodes = [];
function initThreatMap() {
    const canvas = document.getElementById('threatMapCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    function resize() {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
    }
    window.addEventListener('resize', resize);
    resize();
    
    // Generate mock threat nodes
    threatNodes = Array.from({length: 40}, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        type: Math.random() > 0.8 ? 'danger' : 'accent',
        pulse: Math.random() * Math.PI * 2
    }));
    
    function animate() {
        if (document.getElementById('tab-neural-map').classList.contains('hidden')) {
            requestAnimationFrame(animate);
            return;
        }
        
        ctx.fillStyle = '#050505';
        ctx.fillRect(0,0,canvas.width, canvas.height);
        
        // Draw connections
        ctx.strokeStyle = 'rgba(255,255,255,0.03)';
        ctx.lineWidth = 1;
        for(let i=0; i<threatNodes.length; i++) {
            for(let j=i+1; j<threatNodes.length; j++) {
                const dx = threatNodes[i].x - threatNodes[j].x;
                const dy = threatNodes[i].y - threatNodes[j].y;
                const dist = Math.sqrt(dx*dx + dy*dy);
                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(threatNodes[i].x, threatNodes[i].y);
                    ctx.lineTo(threatNodes[j].x, threatNodes[j].y);
                    ctx.stroke();
                }
            }
        }
        
        // Draw nodes
        threatNodes.forEach(n => {
            n.x += n.vx;
            n.y += n.vy;
            if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
            if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
            
            n.pulse += 0.05;
            const s = 2 + Math.sin(n.pulse) * 1;
            ctx.fillStyle = n.type === 'danger' ? 'var(--danger)' : 'var(--accent)';
            ctx.shadowBlur = 10;
            ctx.shadowColor = ctx.fillStyle;
            ctx.beginPath();
            ctx.arc(n.x, n.y, s, 0, Math.PI*2);
            ctx.fill();
            ctx.shadowBlur = 0;
        });
        
        requestAnimationFrame(animate);
    }
    animate();
}

function exportData() {
    showToast('Neural scan export initiated.');
}

// Global scope
window.getCookie = getCookie;
window.updateVal = updateVal;
window.showSaveBar = showSaveBar;
window.hideSaveBar = hideSaveBar;
window.showToast = showToast;
window.switchTab = switchTab;
window.generateSecret = generateSecret;
window.saveWebhookSettings = saveWebhookSettings;
window.copyKey = copyKey;
window.authenticate = authenticate;
window.fetchStats = fetchStats;
window.saveChanges = saveChanges;
window.logout = logout;
window.runSimulation = runSimulation;
window.renderRules = renderRules;
window.addRuleRow = addRuleRow;
window.removeRule = removeRule;
window.saveRules = saveRules;
window.switchSdkTab = switchSdkTab;
window.runConnectionTest = runConnectionTest;
window.optInShield = optInShield;
window.generateAuditReport = generateAuditReport;
window.runForensicAnalysis = runForensicAnalysis;
window.showInviteModal = showInviteModal;
window.initChart = initChart;
window.exportData = exportData;
window.toggleShadowMode = toggleShadowMode;
window.initThreatMap = initThreatMap;
