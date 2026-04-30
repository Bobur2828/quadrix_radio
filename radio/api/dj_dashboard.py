"""DJ Dashboard HTML page — login required."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View


@method_decorator(login_required(login_url='/admin/login/'), name='dispatch')
class DJDashboardView(View):
    def get(self, request):
        return HttpResponse(_HTML, content_type='text/html; charset=utf-8')


_HTML = r"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quadrix DJ Dashboard</title>
<style>
:root {
    --bg: #0b1120; --panel: #131c2f; --panel-2: #0f172a;
    --line: #1e293b; --line-2: #334155;
    --text: #e2e8f0; --muted: #94a3b8; --dim: #64748b;
    --accent: #10b981; --accent-2: #34d399; --warn: #fbbf24; --danger: #ef4444;
    --indigo: #6366f1; --pink: #ec4899;
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, system-ui, "Segoe UI",
                          Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); font-size: 14px;
}

/* ---------- shell ---------- */
.shell { display: grid; grid-template-rows: auto 1fr; min-height: 100vh; }
header.top {
    display: flex; align-items: center; gap: 16px;
    padding: 14px 28px; border-bottom: 1px solid var(--line);
    background: linear-gradient(180deg, #14213d 0%, #0b1120 100%);
}
header.top .brand { font-weight: 700; font-size: 18px; letter-spacing: .3px; }
header.top .brand .dot {
    display: inline-block; width: 8px; height: 8px; background: var(--accent);
    border-radius: 50%; margin-right: 8px; box-shadow: 0 0 8px var(--accent);
}
header.top .spacer { flex: 1; }
header.top .station-pick {
    background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2);
    padding: 8px 12px; border-radius: 8px; font-size: 14px; min-width: 200px;
}
header.top .user { color: var(--muted); font-size: 13px; }

.layout { display: grid; grid-template-columns: 320px 1fr; gap: 18px; padding: 18px; }
@media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } }

/* ---------- panels ---------- */
.panel { background: var(--panel); border: 1px solid var(--line);
         border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,.25); }
.panel + .panel { margin-top: 18px; }
.panel .panel-head {
    padding: 14px 18px; border-bottom: 1px solid var(--line);
    display: flex; align-items: center; gap: 10px;
}
.panel .panel-head h3 { margin: 0; font-size: 14px; text-transform: uppercase;
                         letter-spacing: .8px; color: var(--muted); }
.panel .panel-body { padding: 16px 18px; }

/* ---------- buttons / forms ---------- */
button, .btn {
    background: var(--accent); color: #052e1e; border: 0;
    padding: 9px 16px; border-radius: 8px; font-weight: 600; cursor: pointer;
    font-size: 13px; transition: filter .15s, transform .05s;
}
button:hover:not(:disabled), .btn:hover:not(:disabled) { filter: brightness(1.08); }
button:active:not(:disabled) { transform: scale(.98); }
button:disabled { opacity: .45; cursor: not-allowed; }
button.danger { background: var(--danger); color: #fff; }
button.muted { background: var(--line-2); color: var(--text); }
button.ghost { background: transparent; color: var(--text); border: 1px solid var(--line-2); }
button.tiny { padding: 5px 10px; font-size: 12px; border-radius: 6px; }

input[type=text], input[type=date], input[type=time], input[type=search], select, textarea {
    background: var(--panel-2); color: var(--text); border: 1px solid var(--line-2);
    padding: 9px 12px; border-radius: 8px; font-size: 13px; width: 100%;
    font-family: inherit;
}
input:focus, select:focus, textarea:focus {
    outline: none; border-color: var(--accent);
}
label.lbl { display: block; color: var(--muted); font-size: 11px; text-transform: uppercase;
            letter-spacing: .5px; margin-bottom: 4px; }
.form-row { display: flex; gap: 10px; align-items: end; flex-wrap: wrap; }
.form-row > * { flex: 1; min-width: 0; }
.form-row > .grow { flex: 2; }
.row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }

/* ---------- live broadcast widget (left column) ---------- */
.live-card .panel-body { display: flex; flex-direction: column; gap: 12px; }
.status-pill {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
    border-radius: 99px; font-size: 11px; font-weight: 700; letter-spacing: .4px;
}
.status-pill.idle { background: var(--line-2); color: var(--muted); }
.status-pill.live { background: var(--danger); color: #fff;
                    box-shadow: 0 0 0 0 rgba(239,68,68,.7); animation: pulse 1.4s infinite; }
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(239,68,68,.7); }
    70% { box-shadow: 0 0 0 8px rgba(239,68,68,0); }
    100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
}
.meter { background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 6px;
         height: 14px; position: relative; overflow: hidden; }
.meter-bar {
    position: absolute; left: 0; top: 0; bottom: 0; width: 0;
    background: linear-gradient(90deg, var(--accent), var(--warn) 70%, var(--danger));
    transition: width 60ms linear;
}
.stat-grid {
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;
}
.stat { background: var(--panel-2); border: 1px solid var(--line-2);
        border-radius: 8px; padding: 10px 12px; }
.stat .v { font-size: 20px; font-weight: 700; }
.stat .l { color: var(--dim); font-size: 11px; text-transform: uppercase; letter-spacing: .4px; }

/* ---------- now-playing widget ---------- */
.now-card .panel-body { padding-top: 4px; }
.np-current {
    background: var(--panel-2); border: 1px solid var(--line-2); border-radius: 12px;
    padding: 14px; margin-bottom: 12px;
}
.np-current .lbl { margin-bottom: 6px; }
.np-current .title { font-size: 16px; font-weight: 600; }
.np-current .artist { color: var(--muted); font-size: 13px; }
.np-current .progress { background: var(--line); border-radius: 6px;
                        height: 6px; overflow: hidden; margin-top: 10px; }
.np-current .progress-bar { height: 100%; background: var(--accent); width: 0;
                            transition: width 1s linear; }
.np-current .times { display: flex; justify-content: space-between;
                     color: var(--dim); font-size: 11px; margin-top: 5px; }

/* ---------- tabs ---------- */
.tabs { display: flex; gap: 6px; border-bottom: 1px solid var(--line);
        padding: 0 18px; margin-top: -1px; }
.tabs button {
    background: transparent; color: var(--muted); border: 0; padding: 12px 14px;
    font-size: 13px; cursor: pointer; border-bottom: 2px solid transparent;
    border-radius: 0; font-weight: 500;
}
.tabs button:hover { color: var(--text); }
.tabs button.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
.tab-body { padding: 16px 18px; }

/* ---------- track list ---------- */
.track-list { display: flex; flex-direction: column; gap: 6px; }
.track-row {
    display: grid; grid-template-columns: 28px 1fr auto auto;
    align-items: center; gap: 10px; padding: 8px 12px;
    background: var(--panel-2); border: 1px solid var(--line-2);
    border-radius: 8px; transition: background .12s;
}
.track-row:hover { background: #1a2538; }
.track-row.played { opacity: .55; }
.track-row.played .track-title { text-decoration: line-through; }
.track-row.playing { border-color: var(--accent); background: #0f2d22; }
.track-row .idx { color: var(--dim); font-size: 12px; text-align: right; }
.track-row .track-title { font-weight: 500; }
.track-row .track-meta { color: var(--muted); font-size: 12px; }
.track-row .duration { color: var(--muted); font-size: 12px; }
.track-row .actions { display: flex; gap: 4px; }
.track-row.dragging { opacity: .5; }
.track-row.drag-over { border-color: var(--accent); border-style: dashed; }

.tag { display: inline-block; padding: 1px 6px; border-radius: 99px;
       font-size: 10px; font-weight: 600; letter-spacing: .3px; }
.tag.played { background: var(--line-2); color: var(--dim); }
.tag.playing { background: var(--accent); color: #052e1e; }
.tag.queued { background: var(--indigo); color: #fff; }

/* ---------- library ---------- */
.lib-toolbar { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
.lib-toolbar input[type=search] { flex: 1; }
.lib-table { display: flex; flex-direction: column; gap: 4px; max-height: 460px; overflow: auto; }
.lib-row {
    display: grid; grid-template-columns: 1fr 110px 90px 60px 110px;
    gap: 10px; align-items: center; padding: 8px 12px;
    background: var(--panel-2); border: 1px solid var(--line-2);
    border-radius: 7px; font-size: 13px;
}
.lib-row .meta { color: var(--muted); font-size: 11px; }
.lib-row.empty { color: var(--dim); padding: 28px; text-align: center;
                 grid-template-columns: 1fr; }

/* ---------- modals ---------- */
.modal-overlay {
    position: fixed; inset: 0; background: rgba(0,0,0,.7); z-index: 100;
    display: flex; align-items: center; justify-content: center;
    backdrop-filter: blur(4px); animation: fadeIn .15s;
}
@keyframes fadeIn { from { opacity: 0; } }
.modal-card {
    background: var(--panel); border: 1px solid var(--line-2);
    border-radius: 14px; padding: 24px; width: 100%; max-width: 480px;
    box-shadow: 0 20px 60px rgba(0,0,0,.6); animation: slideUp .2s;
    max-height: 90vh; overflow: auto;
}
@keyframes slideUp { from { transform: translateY(20px); opacity: 0; } }
.modal-card h3 {
    margin: 0 0 4px; font-size: 18px; display: flex; align-items: center; gap: 10px;
}
.modal-card .modal-sub { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
.modal-card .field { margin-bottom: 14px; }
.modal-card .field-row { display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }
.modal-card .actions {
    display: flex; gap: 8px; margin-top: 20px; justify-content: flex-end;
    border-top: 1px solid var(--line); padding-top: 16px;
}
.color-picker { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
.color-swatch {
    width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
    border: 2px solid transparent; transition: transform .1s;
}
.color-swatch:hover { transform: scale(1.15); }
.color-swatch.active { border-color: #fff; transform: scale(1.15); }

/* ---------- weekly grid ---------- */
:root {
    --wg-hours-w: 64px;
    --wg-hour-h: 36px;
    --wg-head-h: 32px;
}
.week-grid {
    display: grid;
    grid-template-columns: var(--wg-hours-w) repeat(7, 1fr);
    grid-auto-rows: var(--wg-hour-h);
    background: var(--panel-2);
    border: 1px solid var(--line-2);
    border-radius: 10px;
    overflow: hidden;
    user-select: none;
    position: relative;       /* anchors the absolutely-positioned blocks */
}
.week-grid .wg-head {
    background: var(--panel); padding: 8px 6px; font-size: 11px;
    text-align: center; color: var(--muted); font-weight: 600;
    border-bottom: 1px solid var(--line-2);
    height: var(--wg-head-h);
    box-sizing: border-box;
}
.week-grid .wg-cell {
    border-right: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    cursor: pointer;
    height: var(--wg-hour-h);
    box-sizing: border-box;
}
.week-grid .wg-cell:hover { background: rgba(255,255,255,.03); }
.week-grid .wg-hour {
    background: var(--panel); color: var(--dim); font-size: 10px;
    padding: 2px 6px; text-align: right;
    border-right: 1px solid var(--line-2);
    height: var(--wg-hour-h);
    box-sizing: border-box;
}

/* Schedule blocks are placed with calc() so they reflow with browser zoom.
   --d = day_of_week (0..6), --start-min, --span-min from JS. */
.wg-block {
    position: absolute;
    left:  calc(var(--wg-hours-w) + var(--d) * (100% - var(--wg-hours-w)) / 7 + 2px);
    width: calc((100% - var(--wg-hours-w)) / 7 - 4px);
    top:    calc(var(--wg-head-h) + var(--start-min) * var(--wg-hour-h) / 60);
    height: calc(var(--span-min) * var(--wg-hour-h) / 60 - 2px);
    border-radius: 4px; padding: 3px 6px;
    font-size: 11px; font-weight: 600; color: #fff;
    overflow: hidden; cursor: pointer;
    box-shadow: 0 1px 2px rgba(0,0,0,.3);
    box-sizing: border-box;
}
.wg-block:hover { filter: brightness(1.1); }

.wg-now-line {
    position: absolute;
    left:  calc(var(--wg-hours-w) + var(--d) * (100% - var(--wg-hours-w)) / 7);
    width: calc((100% - var(--wg-hours-w)) / 7);
    top:   calc(var(--wg-head-h) + var(--now-min) * var(--wg-hour-h) / 60);
    height: 1px;
    background: var(--danger); z-index: 5; pointer-events: none;
}
.wg-now-line::before {
    content: ''; position: absolute; left: -3px; top: -3px;
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--danger);
}

/* ---------- log ---------- */
pre.log {
    background: #060e1f; color: var(--muted); padding: 12px; border-radius: 8px;
    font-size: 11px; max-height: 160px; overflow: auto; white-space: pre-wrap;
    margin: 0; font-family: ui-monospace, monospace;
}

/* ---------- toast ---------- */
#toast {
    position: fixed; bottom: 24px; right: 24px; z-index: 999;
    display: flex; flex-direction: column; gap: 8px;
}
.toast {
    background: var(--panel); border: 1px solid var(--line-2);
    padding: 12px 16px; border-radius: 10px; min-width: 240px;
    font-size: 13px; box-shadow: 0 8px 30px rgba(0,0,0,.35);
    animation: slideIn .25s ease-out;
}
.toast.error { border-color: var(--danger); }
.toast.success { border-color: var(--accent); }
@keyframes slideIn { from { transform: translateX(20px); opacity: 0; } }

</style>
</head>
<body>
<div class="shell">

<!-- ─────── HEADER ─────── -->
<header class="top">
    <div class="brand"><span class="dot"></span>Quadrix DJ</div>
    <div class="spacer"></div>
    <select id="station-select" class="station-pick"></select>
    <span class="user" id="user-name">…</span>
    <a href="/admin/logout/" class="user" style="color:var(--muted);text-decoration:none">↪ logout</a>
</header>

<!-- ─────── BODY ─────── -->
<div class="layout">
<!-- LEFT COLUMN — live + now playing -->
<aside>
    <section class="panel live-card">
        <div class="panel-head">
            <h3>🎙 Live broadcast</h3>
            <span class="spacer" style="flex:1"></span>
            <span id="live-status" class="status-pill idle">IDLE</span>
        </div>
        <div class="panel-body">
            <div>
                <label class="lbl">On-air title</label>
                <input id="live-title" type="text" value="Live with DJ">
            </div>
            <div class="row">
                <button id="go-live">🔴 Go Live</button>
                <button id="end-live" class="danger" disabled>■ End</button>
            </div>
            <div>
                <label class="lbl">Mic level</label>
                <div class="meter"><div id="meter" class="meter-bar"></div></div>
            </div>
            <div class="stat-grid">
                <div class="stat"><div class="v" id="stat-listeners">0</div><div class="l">Listeners</div></div>
                <div class="stat"><div class="v" id="stat-duration">0:00</div><div class="l">Live for</div></div>
                <div class="stat"><div class="v" id="stat-bytes-in">0 KB</div><div class="l">Mic in</div></div>
                <div class="stat"><div class="v" id="stat-bytes-out">0 KB</div><div class="l">MP3 out</div></div>
            </div>
        </div>
    </section>

    <section class="panel now-card">
        <div class="panel-head"><h3>▶ Now playing</h3></div>
        <div class="panel-body">
            <div class="np-current">
                <div class="lbl">CURRENT</div>
                <div class="title" id="np-title">—</div>
                <div class="artist" id="np-artist">—</div>
                <div class="progress"><div class="progress-bar" id="np-progress"></div></div>
                <div class="times"><span id="np-elapsed">0:00</span><span id="np-duration">0:00</span></div>
            </div>
            <div class="np-current" style="background:var(--panel)">
                <div class="lbl">UP NEXT</div>
                <div class="title" id="np-next">—</div>
                <div class="artist" id="np-next-artist">—</div>
            </div>
            <div class="row" style="margin-top:8px">
                <button id="skip" class="muted">⏭ Skip current</button>
                <audio id="preview" controls preload="none" style="margin-left:auto;width:160px"></audio>
            </div>
        </div>
    </section>

    <section class="panel">
        <div class="panel-head"><h3>📜 Activity log</h3></div>
        <div class="panel-body" style="padding:8px 8px"><pre id="log" class="log"></pre></div>
    </section>
</aside>

<!-- RIGHT COLUMN — schedule / library -->
<main class="panel" style="margin-top:0">
    <div class="tabs">
        <button class="tab-btn active" data-tab="schedule">📅 Playlist</button>
        <button class="tab-btn" data-tab="shows">📡 Shows</button>
        <button class="tab-btn" data-tab="library">🎵 Library</button>
        <button class="tab-btn" data-tab="upload">⬆ Upload</button>
    </div>

    <!-- ─── SCHEDULE tab ─── -->
    <div class="tab-body" id="tab-schedule">
        <div class="form-row" style="margin-bottom:12px">
            <div>
                <label class="lbl">Date</label>
                <input id="schedule-date" type="date">
            </div>
            <div class="grow">
                <label class="lbl">Playlist title</label>
                <input id="playlist-title" type="text" placeholder="(optional, auto)">
            </div>
            <button id="load-playlist" class="muted">Load</button>
            <button id="create-playlist">+ Create</button>
        </div>

        <div id="playlist-meta" style="color:var(--muted);font-size:12px;margin-bottom:8px"></div>
        <div id="playlist-items" class="track-list">
            <div class="lib-row empty">No playlist loaded.</div>
        </div>

        <div style="margin-top:12px;display:flex;gap:8px;align-items:center">
            <button id="add-from-library" class="ghost">+ Add tracks from library</button>
            <span style="color:var(--dim);font-size:11px;margin-left:auto">
                Reorder ↑↓ or drag — auto-saved
            </span>
        </div>
    </div>

    <!-- ─── SHOWS tab — weekly grid + show CRUD ─── -->
    <div class="tab-body" id="tab-shows" style="display:none">
        <div id="now-airing" style="margin-bottom:14px;padding:12px;background:var(--panel-2);
             border:1px solid var(--line-2);border-radius:10px;display:none">
            <div class="lbl">Currently airing</div>
            <div id="now-airing-body" style="font-size:15px"></div>
        </div>

        <div class="row" style="margin-bottom:8px;justify-content:space-between">
            <span class="lbl" style="margin:0">Weekly schedule</span>
            <span style="color:var(--dim);font-size:11px">click empty cell to schedule a slot</span>
        </div>
        <div id="week-grid" class="week-grid">
            <div class="lib-row empty">Loading…</div>
        </div>

        <div class="row" style="margin-top:18px;margin-bottom:8px;justify-content:space-between">
            <span class="lbl" style="margin:0">All shows on this station</span>
            <button id="create-show" class="tiny">+ New show</button>
        </div>
        <div id="show-list" class="track-list"></div>
    </div>

    <!-- ─── LIBRARY tab ─── -->
    <div class="tab-body" id="tab-library" style="display:none">
        <div class="lib-toolbar">
            <input id="lib-search" type="search" placeholder="Search title or artist…">
            <select id="lib-category">
                <option value="">All categories</option>
            </select>
            <select id="lib-ordering">
                <option value="-created_at">Newest</option>
                <option value="title">Title A→Z</option>
                <option value="-play_count">Most played</option>
                <option value="-last_played_at">Recently played</option>
            </select>
            <button id="lib-refresh" class="muted">↻</button>
        </div>
        <div id="lib-table" class="lib-table">
            <div class="lib-row empty">Loading…</div>
        </div>
    </div>

    <!-- ─── UPLOAD tab ─── -->
    <div class="tab-body" id="tab-upload" style="display:none">
        <div style="max-width:520px">
            <div class="form-row" style="margin-bottom:10px">
                <div class="grow">
                    <label class="lbl">Audio file (mp3/m4a/wav/ogg)</label>
                    <input id="upload-file" type="file" accept="audio/*"
                        style="background:var(--panel-2);padding:8px;border:1px solid var(--line-2);
                               border-radius:8px;color:var(--text);width:100%">
                </div>
            </div>
            <div class="form-row" style="margin-bottom:10px">
                <div class="grow">
                    <label class="lbl">Title (optional)</label>
                    <input id="upload-title" type="text">
                </div>
                <div class="grow">
                    <label class="lbl">Artist (optional)</label>
                    <input id="upload-artist" type="text">
                </div>
            </div>
            <div class="form-row" style="margin-bottom:14px">
                <div>
                    <label class="lbl">Category</label>
                    <select id="upload-category"></select>
                </div>
                <div class="grow">
                    <label class="lbl">Description</label>
                    <input id="upload-desc" type="text">
                </div>
            </div>
            <div class="row">
                <button id="do-upload">Upload</button>
                <span id="upload-status" style="color:var(--muted);font-size:12px"></span>
            </div>
        </div>
    </div>
</main>

</div>
</div>

<div id="toast"></div>
<div id="modal-root"></div>

<!-- ───────── JS ───────── -->
<script>
// ────── helpers ──────
const $ = (id) => document.getElementById(id);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const csrf = (() => {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
})();
const fmtBytes = (n) => n < 1024 ? `${n} B` : n < 1048576 ? `${(n/1024).toFixed(0)} KB` : `${(n/1048576).toFixed(1)} MB`;
const fmtTime = (s) => {
    if (!s || s < 0) s = 0;
    const m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return `${m}:${String(sec).padStart(2,'0')}`;
};
const todayISO = () => new Date().toISOString().slice(0, 10);

function toast(msg, kind) {
    const el = document.createElement('div');
    el.className = 'toast' + (kind ? ' ' + kind : '');
    el.textContent = msg;
    $('toast').appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(8px)';
                       el.style.transition = 'all .25s'; }, 2700);
    setTimeout(() => el.remove(), 3100);
}

function log(msg) {
    const t = new Date().toLocaleTimeString();
    $('log').textContent = `[${t}] ${msg}\n` + $('log').textContent;
}

async function api(url, opts = {}) {
    const headers = { 'X-CSRFToken': csrf, ...(opts.headers || {}) };
    let body = opts.body;
    if (body && !(body instanceof FormData) && !(body instanceof ArrayBuffer)
        && typeof body !== 'string') {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(body);
    }
    const r = await fetch(url, {
        method: opts.method || 'GET', credentials: 'same-origin',
        headers, body,
    });
    if (!r.ok) {
        let detail = '';
        try { detail = (await r.json()).detail || ''; }
        catch (_) { detail = await r.text(); }
        throw new Error(`HTTP ${r.status}: ${detail || r.statusText}`);
    }
    if (r.status === 204) return null;
    const ct = r.headers.get('Content-Type') || '';
    return ct.includes('json') ? r.json() : r.text();
}

// ────── global state ──────
const state = {
    stations: [], currentStation: null,
    livePollTimer: null, nowPollTimer: null,
    broadcastId: null, streamKey: null, mediaRecorder: null,
    micStream: null, audioCtx: null, meterTimer: null, liveStartedAt: null,
    activeTab: 'schedule',
    playlist: null, playlistItems: [], orderDirty: false,
    libraryCache: [], categoryChoices: [],
};

// ────── stations ──────
async function loadStations() {
    state.stations = await api('/api/radio/stations/');
    const sel = $('station-select');
    sel.innerHTML = '';
    state.stations.forEach(s => {
        const o = document.createElement('option');
        o.value = s.slug; o.textContent = s.name;
        sel.appendChild(o);
    });
    state.currentStation = state.stations.find(s => s.is_default) || state.stations[0];
    if (state.currentStation) sel.value = state.currentStation.slug;
}

$('station-select').addEventListener('change', (e) => {
    state.currentStation = state.stations.find(s => s.slug === e.target.value);
    log(`switched station → ${e.target.value}`);
    refreshNow();
    if (state.activeTab === 'schedule') loadPlaylistForDate();
});

async function loadMe() {
    try {
        const me = await api('/api/radio/dj/me/');
        $('user-name').textContent = '👤 ' + me.user.username;
    } catch (_) {}
}

// ────── tabs ──────
$$('.tab-btn').forEach(btn => btn.addEventListener('click', () => {
    $$('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.activeTab = btn.dataset.tab;
    $$('#tab-schedule, #tab-library, #tab-upload').forEach(el => el.style.display = 'none');
    $('tab-' + state.activeTab).style.display = 'block';
    if (state.activeTab === 'library') loadLibrary();
    if (state.activeTab === 'schedule' && !state.playlist) loadPlaylistForDate();
    if (state.activeTab === 'shows') loadShowsTab();
}));

// ════════════════════════════════════════════════════════════════════════
// LIVE BROADCAST
// ════════════════════════════════════════════════════════════════════════

function pickMime() {
    const candidates = [
        'audio/webm;codecs=opus', 'audio/webm',
        'audio/ogg;codecs=opus', 'audio/mp4',
    ];
    for (const m of candidates)
        if (window.MediaRecorder && MediaRecorder.isTypeSupported(m)) return m;
    return '';
}

async function goLive() {
    if (!state.currentStation) { toast('Pick a station', 'error'); return; }

    // navigator.mediaDevices is only exposed on secure contexts (HTTPS or
    // localhost). HTTP-on-public-IP gets undefined here — give a clear hint.
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const msg = location.protocol === 'https:'
            ? 'Mic API not available in this browser.'
            : 'Mic requires HTTPS. Use https://, localhost, or enable Chrome flag '
              + '"unsafely-treat-insecure-origin-as-secure" for ' + location.origin;
        toast(msg, 'error');
        log('✗ ' + msg);
        return;
    }

    const mime = pickMime();
    if (!mime) { toast('Browser unsupported', 'error'); return; }

    let stream;
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        });
    } catch (e) { toast('Mic denied: ' + e.message, 'error'); return; }
    state.micStream = stream;

    let resp;
    try {
        resp = await api('/api/radio/dj/live/start/', {
            method: 'POST', body: {
                station: state.currentStation.slug,
                title: $('live-title').value || 'Live',
            },
        });
    } catch (e) {
        toast('Start failed: ' + e.message, 'error');
        stream.getTracks().forEach(t => t.stop()); return;
    }
    state.broadcastId = resp.broadcast_id;
    state.streamKey = resp.stream_key;
    state.liveStartedAt = Date.now();

    const inputFmt = mime.startsWith('audio/mp4') ? 'mp4'
                  : mime.startsWith('audio/ogg') ? 'ogg' : 'webm';

    // ── Open WebSocket for low-latency mic transport ──
    // Single TCP connection, no per-chunk HTTP overhead, no middleware.
    // Falls back to HTTP per-chunk if the server doesn't support WS.
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${proto}://${location.host}/ws/dj/live/${state.broadcastId}/`
                + `?key=${encodeURIComponent(state.streamKey)}&fmt=${inputFmt}`;

    let useWs = false;
    state.ws = null;
    try {
        await new Promise((resolve, reject) => {
            const ws = new WebSocket(wsUrl);
            ws.binaryType = 'arraybuffer';
            const timer = setTimeout(() => { reject(new Error('ws timeout')); ws.close(); }, 4000);
            ws.onopen = () => { clearTimeout(timer); state.ws = ws; useWs = true; resolve(); };
            ws.onerror = () => { clearTimeout(timer); reject(new Error('ws error')); };
            ws.onclose = () => { state.ws = null; };
        });
        log(`✓ WebSocket connected (low-latency mode)`);
    } catch (e) {
        log(`WebSocket unavailable, falling back to HTTP: ${e.message}`);
    }

    // 100ms timeslice → tighter latency than 250ms.
    state.mediaRecorder = new MediaRecorder(stream, { mimeType: mime });
    state.mediaRecorder.ondataavailable = async (e) => {
        if (!e.data || e.data.size === 0) return;
        const buf = await e.data.arrayBuffer();
        if (useWs && state.ws && state.ws.readyState === WebSocket.OPEN) {
            try { state.ws.send(buf); } catch (_) {}
            return;
        }
        // HTTP fallback
        try {
            await fetch(`/api/radio/dj/live/${state.broadcastId}/upload/`, {
                method: 'POST',
                headers: { 'Content-Type': mime, 'X-Stream-Key': state.streamKey,
                           'X-Audio-Format': inputFmt },
                body: buf,
            });
        } catch (err) { /* ignore single-chunk errors */ }
    };
    state.mediaRecorder.start(100);
    log(`🔴 LIVE on ${state.currentStation.slug}` + (useWs ? ' [WS]' : ' [HTTP]'));

    $('live-status').textContent = 'LIVE'; $('live-status').className = 'status-pill live';
    $('go-live').disabled = true; $('end-live').disabled = false;
    $('preview').src = `/api/radio/stream.mp3?station=${state.currentStation.slug}&_t=${Date.now()}`;

    startMeter(stream);
    if (state.livePollTimer) clearInterval(state.livePollTimer);
    state.livePollTimer = setInterval(pollLiveStatus, 2000);
    pollLiveStatus();
}

async function endLive() {
    if (!state.broadcastId) return;
    try { state.mediaRecorder?.stop(); } catch (_) {}
    state.micStream?.getTracks().forEach(t => t.stop());
    if (state.ws) { try { state.ws.close(); } catch (_) {} state.ws = null; }
    stopMeter();
    if (state.livePollTimer) { clearInterval(state.livePollTimer); state.livePollTimer = null; }
    try {
        await api(`/api/radio/dj/live/${state.broadcastId}/stop/`, { method: 'POST' });
    } catch (_) {}
    $('live-status').textContent = 'IDLE'; $('live-status').className = 'status-pill idle';
    $('go-live').disabled = false; $('end-live').disabled = true;
    state.broadcastId = null; state.streamKey = null;
    log('Broadcast ended.');
}

async function pollLiveStatus() {
    if (!state.broadcastId) return;
    try {
        const s = await api(`/api/radio/dj/live/${state.broadcastId}/status/`);
        $('stat-listeners').textContent = s.listeners;
        $('stat-bytes-in').textContent = fmtBytes(s.bytes_in);
        $('stat-bytes-out').textContent = fmtBytes(s.bytes_out);
        $('stat-duration').textContent = fmtTime((Date.now() - state.liveStartedAt) / 1000);
    } catch (_) {}
}

function startMeter(stream) {
    state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = state.audioCtx.createMediaStreamSource(stream);
    const analyser = state.audioCtx.createAnalyser();
    analyser.fftSize = 1024;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);
    state.meterTimer = setInterval(() => {
        analyser.getByteTimeDomainData(buf);
        let max = 0;
        for (let i = 0; i < buf.length; i++) {
            const v = Math.abs(buf[i] - 128);
            if (v > max) max = v;
        }
        $('meter').style.width = Math.min(100, (max / 128) * 200) + '%';
    }, 60);
}
function stopMeter() {
    if (state.meterTimer) clearInterval(state.meterTimer);
    state.meterTimer = null;
    if (state.audioCtx) { state.audioCtx.close(); state.audioCtx = null; }
    $('meter').style.width = '0';
}

$('go-live').addEventListener('click', goLive);
$('end-live').addEventListener('click', endLive);
window.addEventListener('beforeunload', () => { if (state.broadcastId) endLive(); });

// ════════════════════════════════════════════════════════════════════════
// NOW PLAYING
// ════════════════════════════════════════════════════════════════════════

async function refreshNow() {
    if (!state.currentStation) return;
    try {
        const d = await api(`/api/radio/dj/now/?station=${state.currentStation.slug}`);
        if (d.is_live) {
            $('np-title').textContent = '🎙 LIVE BROADCAST';
            $('np-artist').textContent = '—';
            $('np-progress').style.width = '100%';
            $('np-elapsed').textContent = ''; $('np-duration').textContent = '';
            $('np-next').textContent = '—'; $('np-next-artist').textContent = '—';
        } else if (d.current) {
            const t = d.current.track;
            $('np-title').textContent = t.title;
            $('np-artist').textContent = t.artist;
            const pct = t.duration_seconds ? (d.current.elapsed_seconds / t.duration_seconds * 100) : 0;
            $('np-progress').style.width = Math.min(100, pct) + '%';
            $('np-elapsed').textContent = fmtTime(d.current.elapsed_seconds);
            $('np-duration').textContent = fmtTime(t.duration_seconds);
            const next = d.upcoming[0];
            $('np-next').textContent = next ? next.track.title : '—';
            $('np-next-artist').textContent = next ? next.track.artist : '—';
        } else {
            $('np-title').textContent = '—'; $('np-artist').textContent = '—';
            $('np-progress').style.width = '0';
            $('np-elapsed').textContent = '0:00'; $('np-duration').textContent = '0:00';
            $('np-next').textContent = '—'; $('np-next-artist').textContent = '—';
        }

        // Refresh playlist UI if user is on the schedule tab
        if (state.activeTab === 'schedule' && state.playlist
            && d.playlist && d.playlist.id === state.playlist.id) {
            renderPlaylistItemsWithState(d.current?.id, d.history || [], d.upcoming || []);
        }
    } catch (e) { /* silent */ }
}

$('skip').addEventListener('click', async () => {
    try {
        await api('/api/radio/dj/skip/', { method: 'POST',
            body: { station: state.currentStation.slug } });
        toast('Skipped current track', 'success');
        log('⏭ skip');
        setTimeout(refreshNow, 300);
    } catch (e) { toast('Skip failed: ' + e.message, 'error'); }
});

// ════════════════════════════════════════════════════════════════════════
// SCHEDULE / PLAYLIST EDITOR
// ════════════════════════════════════════════════════════════════════════

$('schedule-date').value = todayISO();

async function loadPlaylistForDate() {
    if (!state.currentStation) return;
    const d = $('schedule-date').value || todayISO();
    try {
        const lists = await api(
            `/api/radio/dj/playlists/?station=${state.currentStation.slug}&date_from=${d}&date_to=${d}`
        );
        if (lists.length === 0) {
            state.playlist = null; state.playlistItems = [];
            $('playlist-meta').textContent = `No playlist for ${d}. Click "Create" to make one.`;
            $('playlist-items').innerHTML = '<div class="lib-row empty">No playlist loaded.</div>';
            return;
        }
        const pl = lists.find(p => !p.is_fallback) || lists[0];
        await openPlaylist(pl.id);
    } catch (e) { toast('Load failed: ' + e.message, 'error'); }
}

async function openPlaylist(id) {
    const pl = await api(`/api/radio/dj/playlists/${id}/`);
    state.playlist = pl;
    state.playlistItems = pl.items;
    state.orderDirty = false;
    $('playlist-title').value = pl.title;
    $('playlist-meta').textContent =
        `${pl.title} • ${pl.date} • ${pl.item_count} tracks • ${fmtTime(pl.total_duration)} • ${pl.status}`;
    renderPlaylistItems();
    refreshNow();
}

function renderPlaylistItems() {
    renderPlaylistItemsWithState(null, [], []);
}

function renderPlaylistItemsWithState(currentItemId, history, upcoming) {
    const playedIds = new Set(history.map(h => h.id));
    const root = $('playlist-items');
    root.innerHTML = '';
    if (state.playlistItems.length === 0) {
        root.innerHTML = '<div class="lib-row empty">Empty playlist. Add tracks from the library.</div>';
        return;
    }
    state.playlistItems.forEach((it, idx) => {
        const row = document.createElement('div');
        row.className = 'track-row';
        row.draggable = true;
        row.dataset.id = it.id;

        let stateLabel = '';
        if (it.id === currentItemId) { row.classList.add('playing'); stateLabel = 'PLAYING'; }
        else if (playedIds.has(it.id)) { row.classList.add('played'); stateLabel = 'PLAYED'; }
        else stateLabel = 'QUEUED';

        const startTime = it.planned_start ? `<span class="track-meta">⏰ ${it.planned_start}</span>` : '';
        row.innerHTML = `
            <div class="idx">${idx + 1}</div>
            <div>
                <div class="track-title">${escape(it.track.title)}</div>
                <div class="track-meta">${escape(it.track.artist)} ${startTime}
                    <span class="tag ${stateLabel.toLowerCase()}">${stateLabel}</span></div>
            </div>
            <div class="duration">${it.track.duration_display || ''}</div>
            <div class="actions">
                <button class="tiny ghost" data-act="up">↑</button>
                <button class="tiny ghost" data-act="down">↓</button>
                <button class="tiny danger" data-act="del">✕</button>
            </div>
        `;
        // event delegation
        row.addEventListener('click', async (e) => {
            const act = e.target.dataset?.act;
            if (!act) return;
            if (act === 'del') return removeItem(it.id);
            if (act === 'up') return moveItem(idx, idx - 1);
            if (act === 'down') return moveItem(idx, idx + 1);
        });
        // drag-and-drop
        row.addEventListener('dragstart', (e) => {
            row.classList.add('dragging');
            e.dataTransfer.setData('text/plain', String(idx));
            e.dataTransfer.effectAllowed = 'move';
        });
        row.addEventListener('dragend', () => row.classList.remove('dragging'));
        row.addEventListener('dragover', (e) => { e.preventDefault(); row.classList.add('drag-over'); });
        row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
        row.addEventListener('drop', (e) => {
            e.preventDefault();
            row.classList.remove('drag-over');
            const from = parseInt(e.dataTransfer.getData('text/plain'), 10);
            if (Number.isFinite(from)) moveItem(from, idx);
        });
        root.appendChild(row);
    });
}

async function moveItem(from, to) {
    if (to < 0 || to >= state.playlistItems.length) return;
    if (from === to) return;
    const [it] = state.playlistItems.splice(from, 1);
    state.playlistItems.splice(to, 0, it);
    renderPlaylistItems();
    // Auto-save: every reorder is sent to the server immediately so the
    // broadcaster picks up the new order on the next track switch.
    await saveOrder({ silent: true });
}

async function saveOrder({ silent = false } = {}) {
    const ids = state.playlistItems.map(i => i.id);
    try {
        const pl = await api(`/api/radio/dj/playlists/${state.playlist.id}/reorder/`, {
            method: 'POST', body: { item_ids: ids },
        });
        state.playlistItems = pl.items;
        if (!silent) toast('Order saved', 'success');
    } catch (e) {
        toast('Save failed: ' + e.message, 'error');
        // Re-fetch to recover correct order
        try { await openPlaylist(state.playlist.id); } catch (_) {}
    }
}

async function removeItem(itemId) {
    if (!confirm('Remove this track from the playlist?')) return;
    try {
        await api(`/api/radio/dj/playlist-items/${itemId}/`, { method: 'DELETE' });
        await openPlaylist(state.playlist.id);
        toast('Removed', 'success');
    } catch (e) { toast('Remove failed: ' + e.message, 'error'); }
}

async function addTrackToPlaylist(trackId) {
    if (!state.playlist) return toast('Open a playlist first', 'error');
    try {
        await api(`/api/radio/dj/playlists/${state.playlist.id}/items/`, {
            method: 'POST', body: { track_id: trackId },
        });
        await openPlaylist(state.playlist.id);
        toast('Added', 'success');
    } catch (e) { toast('Add failed: ' + e.message, 'error'); }
}

$('load-playlist').addEventListener('click', loadPlaylistForDate);
$('schedule-date').addEventListener('change', loadPlaylistForDate);

$('create-playlist').addEventListener('click', async () => {
    if (!state.currentStation) return;
    const d = $('schedule-date').value || todayISO();
    const title = $('playlist-title').value;
    try {
        const pl = await api('/api/radio/dj/playlists/', {
            method: 'POST',
            body: {
                station: state.currentStation.slug, date: d, title,
                status: 'active',
            },
        });
        await openPlaylist(pl.id);
        toast('Playlist ready', 'success');
    } catch (e) { toast('Create failed: ' + e.message, 'error'); }
});

$('add-from-library').addEventListener('click', () => {
    document.querySelector('.tab-btn[data-tab="library"]').click();
});

// ════════════════════════════════════════════════════════════════════════
// LIBRARY
// ════════════════════════════════════════════════════════════════════════

let libSearchTimer = null;
$('lib-search').addEventListener('input', () => {
    clearTimeout(libSearchTimer);
    libSearchTimer = setTimeout(loadLibrary, 250);
});
$('lib-category').addEventListener('change', loadLibrary);
$('lib-ordering').addEventListener('change', loadLibrary);
$('lib-refresh').addEventListener('click', loadLibrary);

async function loadLibrary() {
    const params = new URLSearchParams({
        q: $('lib-search').value,
        category: $('lib-category').value,
        ordering: $('lib-ordering').value,
        limit: '100',
    });
    try {
        const r = await api('/api/radio/dj/library/?' + params);
        state.libraryCache = r.results;
        if (state.categoryChoices.length === 0 && r.categories) {
            state.categoryChoices = r.categories;
            const sel = $('lib-category');
            r.categories.forEach(c => {
                const o = document.createElement('option');
                o.value = c.value; o.textContent = c.label;
                sel.appendChild(o);
            });
            const upSel = $('upload-category');
            upSel.innerHTML = '';
            r.categories.forEach(c => {
                const o = document.createElement('option');
                o.value = c.value; o.textContent = c.label;
                upSel.appendChild(o);
            });
        }
        renderLibrary(r);
    } catch (e) { toast('Library load failed: ' + e.message, 'error'); }
}

function renderLibrary(r) {
    const root = $('lib-table');
    root.innerHTML = '';
    if (r.results.length === 0) {
        root.innerHTML = '<div class="lib-row empty">No tracks found.</div>'; return;
    }
    r.results.forEach(t => {
        const row = document.createElement('div');
        row.className = 'lib-row';
        row.innerHTML = `
            <div>
                <div>${escape(t.title)}</div>
                <div class="meta">${escape(t.artist)} • ${t.category} • ${t.play_count} plays</div>
            </div>
            <div class="meta">${t.duration_display}</div>
            <div class="meta">${fmtBytes(t.file_size)}</div>
            <div><audio src="${t.audio_url}" controls preload="none" style="height:30px;width:60px"></audio></div>
            <div style="display:flex;gap:4px">
                <button class="tiny" data-act="add">+ Playlist</button>
                <button class="tiny ghost" data-act="del">✕</button>
            </div>
        `;
        row.addEventListener('click', async (e) => {
            const act = e.target.dataset?.act;
            if (act === 'add') return addTrackToPlaylist(t.id);
            if (act === 'del') {
                if (!confirm(`Delete "${t.title}"? This cannot be undone.`)) return;
                try {
                    await api(`/api/radio/dj/library/${t.id}/`, { method: 'DELETE' });
                    toast('Deleted', 'success');
                    loadLibrary();
                } catch (err) { toast('Delete failed: ' + err.message, 'error'); }
            }
        });
        root.appendChild(row);
    });
}

// ════════════════════════════════════════════════════════════════════════
// UPLOAD
// ════════════════════════════════════════════════════════════════════════

$('do-upload').addEventListener('click', async () => {
    const f = $('upload-file').files[0];
    if (!f) return toast('Pick a file', 'error');
    const fd = new FormData();
    fd.append('audio_file', f);
    if ($('upload-title').value) fd.append('title', $('upload-title').value);
    if ($('upload-artist').value) fd.append('artist', $('upload-artist').value);
    fd.append('description', $('upload-desc').value);
    fd.append('category', $('upload-category').value);

    $('upload-status').textContent = 'Uploading…';
    $('do-upload').disabled = true;
    try {
        await api('/api/radio/dj/library/', { method: 'POST', body: fd });
        $('upload-status').textContent = 'Uploaded ✓';
        $('upload-file').value = ''; $('upload-title').value = '';
        $('upload-artist').value = ''; $('upload-desc').value = '';
        toast('Track uploaded', 'success');
    } catch (e) {
        $('upload-status').textContent = 'Failed: ' + e.message;
        toast('Upload failed: ' + e.message, 'error');
    } finally {
        $('do-upload').disabled = false;
    }
});

// ════════════════════════════════════════════════════════════════════════
// MODAL HELPER
// ════════════════════════════════════════════════════════════════════════

function openModal(html) {
    const root = $('modal-root');
    root.innerHTML = `<div class="modal-overlay" id="modal-overlay">
        <div class="modal-card" id="modal-card">${html}</div>
    </div>`;
    const overlay = $('modal-overlay');
    const card = $('modal-card');
    const close = () => { root.innerHTML = ''; };
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
    document.addEventListener('keydown', function esc(e) {
        if (e.key === 'Escape') { close(); document.removeEventListener('keydown', esc); }
    });
    return { card, close };
}

const SHOW_COLORS = [
    '#10b981', '#3b82f6', '#ec4899', '#f59e0b', '#ef4444',
    '#8b5cf6', '#06b6d4', '#84cc16', '#f97316', '#64748b',
];

function colorPickerHTML(selected = '#10b981') {
    return SHOW_COLORS.map(c =>
        `<div class="color-swatch ${c === selected ? 'active' : ''}"
              data-color="${c}" style="background:${c}"></div>`
    ).join('');
}

function bindColorPicker(rootEl, hiddenInputId) {
    rootEl.querySelectorAll('.color-swatch').forEach(sw => {
        sw.addEventListener('click', () => {
            rootEl.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('active'));
            sw.classList.add('active');
            $(hiddenInputId).value = sw.dataset.color;
        });
    });
}

// ════════════════════════════════════════════════════════════════════════
// SHOWS / SCHEDULE
// ════════════════════════════════════════════════════════════════════════

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

async function loadShowsTab() {
    if (!state.currentStation) return;
    // Sequential: state.scheduleList is set by loadWeekGrid and READ by loadShowsList,
    // so order matters.
    await loadCurrentShow();
    await loadWeekGrid();
    await loadShowsList();
    try {
        state.allPlaylists = await api(
            `/api/radio/dj/playlists/?station=${state.currentStation.slug}`
        );
    } catch (_) { state.allPlaylists = []; }
}

async function loadShowsList() {
    const shows = await api(`/api/radio/dj/shows/?station=${state.currentStation.slug}`);
    state.showsList = shows;

    // Schedules-by-show for richer display
    const schedules = state.scheduleList || [];
    const schedByShow = {};
    schedules.forEach(s => {
        (schedByShow[s.show_id] = schedByShow[s.show_id] || []).push(s);
    });

    const root = $('show-list');
    root.innerHTML = '';
    if (shows.length === 0) {
        root.innerHTML = `<div class="lib-row empty">No shows yet. Click "+ New show" to add one.</div>`;
        return;
    }
    shows.forEach(s => {
        const slots = schedByShow[s.id] || [];
        const slotText = slots.length === 0
            ? '<span style="color:var(--dim)">not scheduled</span>'
            : slots.map(sl => `${DAY_LABELS[sl.day_of_week]} ${sl.start_time}–${sl.end_time}`).join(' · ');

        const row = document.createElement('div');
        row.className = 'track-row';
        row.style.cursor = 'pointer';
        row.innerHTML = `
            <div class="idx" style="width:14px;height:14px;border-radius:3px;background:${s.color}"></div>
            <div>
                <div class="track-title">${escape(s.name)}</div>
                <div class="track-meta" style="margin-top:2px">
                    ${s.host_name ? '👤 ' + escape(s.host_name) + ' · ' : ''}
                    🎵 ${escape(s.playlist_title || 'default playlist')}
                    ${s.is_active ? '' : ' · <span style="color:var(--warn)">disabled</span>'}
                </div>
                <div class="track-meta" style="margin-top:2px;font-size:11px">⏰ ${slotText}</div>
            </div>
            <div></div>
            <div class="actions" onclick="event.stopPropagation()">
                <button class="tiny ghost" data-act="edit">✏ Edit</button>
                <button class="tiny danger" data-act="del">✕</button>
            </div>
        `;
        row.querySelector('[data-act="edit"]').addEventListener('click', () => openShowModal(s));
        row.querySelector('[data-act="del"]').addEventListener('click', async () => {
            if (!confirm(`Delete "${s.name}"? All its schedules will be removed.`)) return;
            try {
                await api(`/api/radio/dj/shows/${s.id}/`, { method: 'DELETE' });
                toast('Show deleted', 'success');
                loadShowsTab();
            } catch (e) { toast('Delete failed: ' + e.message, 'error'); }
        });
        // click row → edit
        row.addEventListener('click', () => openShowModal(s));
        root.appendChild(row);
    });
}

async function loadCurrentShow() {
    const r = await api(`/api/radio/dj/schedule/current/?station=${state.currentStation.slug}`);
    const box = $('now-airing');
    const body = $('now-airing-body');
    if (r.now) {
        const s = r.now;
        box.style.display = 'block';
        body.innerHTML = `<span style="display:inline-block;width:10px;height:10px;background:${s.show_color};
            border-radius:50%;margin-right:8px"></span>
            <strong>${escape(s.show_name)}</strong>
            <span style="color:var(--muted)"> · ${s.day_label} ${s.start_time}–${s.end_time}</span>`;
    } else {
        box.style.display = 'block';
        body.innerHTML = '<span style="color:var(--muted)">No show on air. Default playlist.</span>';
    }
    return r;
}

async function loadWeekGrid() {
    const schedules = await api(`/api/radio/dj/schedules/?station=${state.currentStation.slug}`);
    state.scheduleList = schedules;
    renderWeekGrid(schedules);
}

function renderWeekGrid(schedules) {
    const grid = $('week-grid');
    grid.innerHTML = '';

    // Header row: empty + 7 day labels
    const corner = document.createElement('div');
    corner.className = 'wg-head';
    grid.appendChild(corner);
    DAY_LABELS.forEach(d => {
        const h = document.createElement('div');
        h.className = 'wg-head';
        h.textContent = d;
        grid.appendChild(h);
    });

    // 24 hour rows × 8 columns (hour label + 7 days)
    for (let h = 0; h < 24; h++) {
        const lbl = document.createElement('div');
        lbl.className = 'wg-hour';
        lbl.textContent = String(h).padStart(2, '0') + ':00';
        grid.appendChild(lbl);

        for (let d = 0; d < 7; d++) {
            const cell = document.createElement('div');
            cell.className = 'wg-cell';
            cell.dataset.day = d;
            cell.dataset.hour = h;
            cell.addEventListener('click', () => addScheduleAt(d, h));
            grid.appendChild(cell);
        }
    }

    // Overlay schedule blocks — positioned via CSS calc() with per-block
    // custom properties, so they always track container width (zoom-proof).
    schedules.forEach(s => {
        if (!s.is_active) return;
        const [sh, sm] = s.start_time.split(':').map(Number);
        const [eh, em] = s.end_time.split(':').map(Number);
        const startMin = sh * 60 + sm;
        let endMin = eh * 60 + em;
        if (endMin <= startMin) endMin = 24 * 60;
        const span = endMin - startMin;

        const block = document.createElement('div');
        block.className = 'wg-block';
        block.style.background = s.show_color;
        block.style.setProperty('--d', s.day_of_week);
        block.style.setProperty('--start-min', startMin);
        block.style.setProperty('--span-min', span);
        block.title = `${s.show_name} (${s.start_time}–${s.end_time})`;
        block.textContent = s.show_name;
        block.addEventListener('click', (e) => {
            e.stopPropagation();
            openScheduleModal({ existing: s });
        });
        grid.appendChild(block);
    });

    // Red "now" indicator line on the current day column
    const now = new Date();
    const nowDay = (now.getDay() + 6) % 7;            // JS Sun=0; we want Mon=0
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const line = document.createElement('div');
    line.className = 'wg-now-line';
    line.style.setProperty('--d', nowDay);
    line.style.setProperty('--now-min', nowMin);
    grid.appendChild(line);
}

// ────── Show editor modal (create/edit) ──────
function openShowModal(existing = null) {
    const isEdit = !!existing;
    const playlists = state.allPlaylists || [];
    const playlistOptions = ['<option value="">— default daily playlist —</option>']
        .concat(playlists.map(p =>
            `<option value="${p.id}" ${existing && existing.playlist_id === p.id ? 'selected' : ''}>
                ${escape(p.title)} (${p.date}, ${p.item_count} tracks)
            </option>`
        )).join('');

    const { card, close } = openModal(`
        <h3>${isEdit ? '✏️ Edit show' : '✨ New show'}</h3>
        <div class="modal-sub">${isEdit ? existing.name : 'Add a recurring program (e.g. "Morning Drive")'}</div>

        <div class="field">
            <label class="lbl">Name</label>
            <input id="m-show-name" type="text" placeholder="e.g. Morning Drive"
                   value="${isEdit ? escape(existing.name) : ''}">
        </div>
        <div class="field">
            <label class="lbl">Description</label>
            <input id="m-show-desc" type="text" placeholder="(optional)"
                   value="${isEdit ? escape(existing.description || '') : ''}">
        </div>
        <div class="field">
            <label class="lbl">Color</label>
            <div class="color-picker" id="m-show-color-picker">
                ${colorPickerHTML(existing ? existing.color : '#10b981')}
            </div>
            <input type="hidden" id="m-show-color" value="${existing ? existing.color : '#10b981'}">
        </div>
        <div class="field">
            <label class="lbl">Auto-DJ playlist (plays when no DJ live)</label>
            <select id="m-show-playlist">${playlistOptions}</select>
        </div>
        <div class="field">
            <label style="display:flex;gap:8px;align-items:center;cursor:pointer;color:var(--muted)">
                <input type="checkbox" id="m-show-active"
                       ${!isEdit || existing.is_active ? 'checked' : ''}>
                <span>Active (uncheck to disable without deleting)</span>
            </label>
        </div>

        <div class="actions">
            ${isEdit ? '<button class="muted" id="m-show-cancel" style="margin-right:auto">Cancel</button>' : ''}
            <button class="ghost" id="m-show-cancel${isEdit ? '2' : ''}">Cancel</button>
            <button id="m-show-save">${isEdit ? 'Save changes' : 'Create show'}</button>
        </div>
    `);

    bindColorPicker(card, 'm-show-color');
    card.querySelectorAll('[id^="m-show-cancel"]').forEach(b =>
        b.addEventListener('click', close));

    card.querySelector('#m-show-save').addEventListener('click', async () => {
        const name = card.querySelector('#m-show-name').value.trim();
        if (!name) return toast('Name required', 'error');
        const body = {
            name,
            description: card.querySelector('#m-show-desc').value,
            color: card.querySelector('#m-show-color').value,
            is_active: card.querySelector('#m-show-active').checked,
        };
        const playlistId = card.querySelector('#m-show-playlist').value;
        body.playlist_id = playlistId ? parseInt(playlistId, 10) : null;

        try {
            if (isEdit) {
                await api(`/api/radio/dj/shows/${existing.id}/`, {
                    method: 'PATCH', body,
                });
                toast('Show updated', 'success');
            } else {
                await api('/api/radio/dj/shows/', {
                    method: 'POST',
                    body: { ...body, station: state.currentStation.slug, host_self: true },
                });
                toast('Show created', 'success');
            }
            close();
            loadShowsTab();
        } catch (e) { toast('Failed: ' + e.message, 'error'); }
    });
}

// ────── Schedule slot modal (create/edit) ──────
function openScheduleModal({ existing = null, defaultDay = 0, defaultHour = 0 } = {}) {
    const isEdit = !!existing;
    const day = isEdit ? existing.day_of_week : defaultDay;
    const startTime = isEdit ? existing.start_time : `${String(defaultHour).padStart(2,'0')}:00`;
    const endTime = isEdit ? existing.end_time : `${String((defaultHour + 1) % 24).padStart(2,'0')}:00`;
    const showId = isEdit ? existing.show_id : (state.showsList[0]?.id || null);

    const dayOptions = DAY_LABELS.map((d, i) =>
        `<option value="${i}" ${i === day ? 'selected' : ''}>${d}</option>`
    ).join('');

    let showOptions;
    if (state.showsList.length === 0) {
        showOptions = '<option value="">— Create a show first —</option>';
    } else {
        showOptions = state.showsList.map(s =>
            `<option value="${s.id}" ${s.id === showId ? 'selected' : ''}>${escape(s.name)}</option>`
        ).join('');
    }

    const { card, close } = openModal(`
        <h3>${isEdit ? '✏️ Edit slot' : '⏰ Schedule a show'}</h3>
        <div class="modal-sub">${isEdit
            ? existing.show_name + ' · ' + DAY_LABELS[existing.day_of_week]
            : 'Pick a show and a weekly time slot'}</div>

        <div class="field">
            <label class="lbl">Show</label>
            <select id="m-sch-show" ${isEdit ? 'disabled' : ''}>${showOptions}</select>
            ${state.showsList.length === 0
                ? '<button class="tiny ghost" id="m-sch-create-show" style="margin-top:6px">+ Create show first</button>'
                : ''}
        </div>
        <div class="field">
            <label class="lbl">Day of week</label>
            <select id="m-sch-day">${dayOptions}</select>
        </div>
        <div class="field-row">
            <div class="field">
                <label class="lbl">Start time</label>
                <input id="m-sch-start" type="time" value="${startTime}" required>
            </div>
            <div class="field">
                <label class="lbl">End time</label>
                <input id="m-sch-end" type="time" value="${endTime}" required>
            </div>
        </div>
        <div class="field" style="font-size:12px;color:var(--dim)">
            Tip: end time after midnight (e.g. 22:00 → 02:00) is supported.
        </div>

        <div class="actions">
            ${isEdit
                ? '<button class="danger" id="m-sch-delete" style="margin-right:auto">Delete slot</button>'
                : ''}
            <button class="ghost" id="m-sch-cancel">Cancel</button>
            <button id="m-sch-save" ${state.showsList.length === 0 ? 'disabled' : ''}>
                ${isEdit ? 'Save' : 'Schedule'}
            </button>
        </div>
    `);

    card.querySelector('#m-sch-cancel').addEventListener('click', close);
    const createBtn = card.querySelector('#m-sch-create-show');
    if (createBtn) {
        createBtn.addEventListener('click', () => { close(); openShowModal(); });
    }
    const delBtn = card.querySelector('#m-sch-delete');
    if (delBtn) {
        delBtn.addEventListener('click', async () => {
            if (!confirm('Delete this slot?')) return;
            try {
                await api(`/api/radio/dj/schedules/${existing.id}/`, { method: 'DELETE' });
                toast('Slot removed', 'success');
                close(); loadShowsTab();
            } catch (e) { toast('Delete failed: ' + e.message, 'error'); }
        });
    }

    card.querySelector('#m-sch-save').addEventListener('click', async () => {
        const showId = card.querySelector('#m-sch-show').value;
        const dayOfWeek = parseInt(card.querySelector('#m-sch-day').value, 10);
        const start = card.querySelector('#m-sch-start').value;
        const end = card.querySelector('#m-sch-end').value;
        if (!showId || !start || !end) return toast('All fields required', 'error');

        try {
            if (isEdit) {
                await api(`/api/radio/dj/schedules/${existing.id}/`, {
                    method: 'PATCH',
                    body: { day_of_week: dayOfWeek, start_time: start, end_time: end },
                });
                toast('Slot updated', 'success');
            } else {
                await api('/api/radio/dj/schedules/', {
                    method: 'POST',
                    body: {
                        show_id: parseInt(showId, 10),
                        day_of_week: dayOfWeek,
                        start_time: start,
                        end_time: end,
                    },
                });
                toast('Slot scheduled', 'success');
            }
            close(); loadShowsTab();
        } catch (e) { toast('Failed: ' + e.message, 'error'); }
    });
}

function addScheduleAt(day, hour) {
    openScheduleModal({ defaultDay: day, defaultHour: hour });
}

// ────── One-shot wizard modal: show + playlist + schedule in one go ──────
async function openShowWizard() {
    if (!state.currentStation) return toast('Pick a station', 'error');

    // Load library tracks (lots of them) for the picker
    let lib;
    try {
        lib = await api('/api/radio/dj/library/?limit=500&ordering=title');
    } catch (e) { return toast('Library load failed: ' + e.message, 'error'); }
    const tracks = lib.results;

    const today = new Date();
    const day = (today.getDay() + 6) % 7;  // JS Sun=0; we want Mon=0
    const defaultStart = String(today.getHours()).padStart(2, '0') + ':00';

    const dayOpts = DAY_LABELS.map((d, i) =>
        `<option value="${i}" ${i === day ? 'selected' : ''}>${d}</option>`
    ).join('');

    const trackList = tracks.map(t => `
        <label class="m-wiz-row" data-search="${escape((t.title + ' ' + t.artist).toLowerCase())}"
               style="display:flex;align-items:center;gap:8px;padding:6px 8px;
                      cursor:pointer;font-size:13px;border-radius:5px">
            <input type="checkbox" data-id="${t.id}" data-dur="${t.duration_seconds}"
                   data-title="${escape(t.title)}">
            <span style="flex:1">${escape(t.title)}</span>
            <span style="color:var(--dim);font-size:11px">${escape(t.artist || '')}</span>
            <span style="color:var(--muted);font-size:12px;min-width:40px;text-align:right">
                ${t.duration_display || '0:00'}
            </span>
        </label>
    `).join('');

    const { card, close } = openModal(`
        <h3>✨ New show</h3>
        <div class="modal-sub">Show + playlist + schedule — bitta yerda yarating</div>

        <div class="field">
            <label class="lbl">Show name</label>
            <input id="m-wiz-name" type="text" placeholder="e.g. Tongi efir" autofocus>
        </div>
        <div class="field">
            <label class="lbl">Color</label>
            <div class="color-picker" id="m-wiz-color-picker">${colorPickerHTML('#10b981')}</div>
            <input type="hidden" id="m-wiz-color" value="#10b981">
        </div>

        <div class="field" style="border-top:1px solid var(--line);padding-top:14px">
            <label class="lbl">When does it air? (ixtiyoriy)</label>
        </div>
        <div class="field-row">
            <div>
                <label class="lbl" style="font-size:10px">Day</label>
                <select id="m-wiz-day">${dayOpts}</select>
            </div>
            <div>
                <label class="lbl" style="font-size:10px">Start</label>
                <input id="m-wiz-start" type="time" value="${defaultStart}">
            </div>
        </div>
        <div class="field" style="font-size:12px;color:var(--muted);margin-top:-6px">
            <label style="display:flex;gap:6px;align-items:center;cursor:pointer">
                <input type="checkbox" id="m-wiz-auto-end" checked>
                Auto end-time from tracks
            </label>
            <div id="m-wiz-end-row" style="display:none;margin-top:6px">
                <input id="m-wiz-end" type="time" value="04:00" style="max-width:140px">
            </div>
        </div>
        <div class="field" id="m-wiz-end-display" style="font-size:13px;
             background:var(--panel-2);border:1px solid var(--line-2);
             border-radius:8px;padding:8px 12px">
            ⏱ <strong id="m-wiz-end-text">add tracks to compute end time</strong>
        </div>

        <div class="field" style="border-top:1px solid var(--line);padding-top:14px">
            <label class="lbl">Tracks (click to add)</label>
            <input id="m-wiz-search" type="search" placeholder="Search title or artist…"
                   style="margin-bottom:6px">
            <div id="m-wiz-tracks" style="max-height:240px;overflow:auto;
                background:var(--panel-2);border:1px solid var(--line-2);
                border-radius:8px;padding:4px">
                ${tracks.length === 0
                    ? '<div style="padding:20px;text-align:center;color:var(--dim)">No tracks. Upload some first.</div>'
                    : trackList}
            </div>
            <div id="m-wiz-summary" style="margin-top:8px;color:var(--muted);
                 font-size:12px;display:flex;justify-content:space-between">
                <span>0 tracks selected</span>
                <span>0:00 total</span>
            </div>
        </div>

        <div class="actions">
            <button class="ghost" id="m-wiz-cancel">Cancel</button>
            <button id="m-wiz-create">Create show</button>
        </div>
    `);

    bindColorPicker(card, 'm-wiz-color');

    // Search filter
    card.querySelector('#m-wiz-search').addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase();
        card.querySelectorAll('.m-wiz-row').forEach(row => {
            row.style.display = !q || row.dataset.search.includes(q) ? '' : 'none';
        });
    });

    // Track ordering — preserve click order
    const selectedOrder = [];

    function fmtTime(sec) {
        const m = Math.floor(sec / 60), s = Math.floor(sec % 60);
        return `${m}:${String(s).padStart(2, '0')}`;
    }
    function addMinutesToHHMM(hhmm, minutes) {
        const [h, m] = hhmm.split(':').map(Number);
        let total = h * 60 + m + Math.ceil(minutes);
        total = ((total % (24 * 60)) + 24 * 60) % (24 * 60);
        return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
    }

    function updateSummary() {
        const checked = Array.from(card.querySelectorAll('input[data-id]:checked'));
        let totalSec = 0;
        checked.forEach(cb => totalSec += parseInt(cb.dataset.dur, 10) || 0);

        card.querySelector('#m-wiz-summary').innerHTML =
            `<span><strong>${checked.length}</strong> tracks selected</span>` +
            `<span>${fmtTime(totalSec)} total</span>`;

        // Compute end time
        const start = card.querySelector('#m-wiz-start').value || '00:00';
        const auto = card.querySelector('#m-wiz-auto-end').checked;
        let endStr;
        if (totalSec > 0) {
            const computed = addMinutesToHHMM(start, totalSec / 60);
            endStr = computed;
            if (auto) card.querySelector('#m-wiz-end').value = computed;
        }

        const display = card.querySelector('#m-wiz-end-text');
        if (totalSec === 0) {
            display.textContent = 'add tracks to compute end time';
        } else if (auto) {
            display.innerHTML = `<strong>${start} → ${endStr}</strong>` +
                ` <span style="color:var(--muted)">(${checked.length} tracks · ${fmtTime(totalSec)})</span>`;
        } else {
            const manualEnd = card.querySelector('#m-wiz-end').value;
            display.innerHTML = `<strong>${start} → ${manualEnd}</strong>` +
                ` <span style="color:var(--muted)">(tracks fill ${fmtTime(totalSec)}, then loop)</span>`;
        }
    }

    card.addEventListener('change', (e) => {
        if (e.target.matches('input[type=checkbox][data-id]')) {
            const id = parseInt(e.target.dataset.id, 10);
            if (e.target.checked) {
                if (!selectedOrder.includes(id)) selectedOrder.push(id);
            } else {
                const i = selectedOrder.indexOf(id);
                if (i >= 0) selectedOrder.splice(i, 1);
            }
            updateSummary();
        }
    });

    const autoEndCb = card.querySelector('#m-wiz-auto-end');
    autoEndCb.addEventListener('change', () => {
        card.querySelector('#m-wiz-end-row').style.display =
            autoEndCb.checked ? 'none' : 'block';
        updateSummary();
    });
    card.querySelector('#m-wiz-start').addEventListener('change', updateSummary);
    card.querySelector('#m-wiz-end')?.addEventListener('change', updateSummary);

    card.querySelector('#m-wiz-cancel').addEventListener('click', close);

    card.querySelector('#m-wiz-create').addEventListener('click', async () => {
        const name = card.querySelector('#m-wiz-name').value.trim();
        if (!name) return toast('Show name required', 'error');

        const body = {
            station: state.currentStation.slug,
            name,
            color: card.querySelector('#m-wiz-color').value,
            track_ids: selectedOrder,
        };
        const day = card.querySelector('#m-wiz-day').value;
        const start = card.querySelector('#m-wiz-start').value;
        if (day !== '' && start) {
            body.day_of_week = parseInt(day, 10);
            body.start_time = start;
            const auto = card.querySelector('#m-wiz-auto-end').checked;
            if (!auto) body.end_time = card.querySelector('#m-wiz-end').value;
        }

        try {
            const r = await api('/api/radio/dj/shows/wizard/', { method: 'POST', body });
            close();
            const parts = ['Show created'];
            if (r.playlist) parts.push(`${r.playlist.item_count} tracks`);
            if (r.schedule) parts.push(`scheduled ${DAY_LABELS[r.schedule.day_of_week]} ${r.schedule.start_time}–${r.schedule.end_time}`);
            toast('✓ ' + parts.join(' · '), 'success');
            loadShowsTab();
        } catch (e) { toast('Failed: ' + e.message, 'error'); }
    });
}

$('create-show').addEventListener('click', () => openShowWizard());

// ────── escaping helper ──────
function escape(s) {
    if (s == null) return '';
    return String(s).replace(/[<>&"']/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;',"'":'&#39;'}[c]));
}

// ────── boot ──────
(async () => {
    await loadMe();
    await loadStations();
    await loadPlaylistForDate();
    await loadLibrary();
    refreshNow();
    state.nowPollTimer = setInterval(refreshNow, 3000);
})();
</script>
</body>
</html>"""
