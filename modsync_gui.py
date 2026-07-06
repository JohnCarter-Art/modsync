#!/usr/bin/env python3
"""ModSync GUI — веб-интерфейс на http://localhost:9876"""
import os, sys, json, time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).parent))
from modsync import (
    find_mods_dir, scan_mods, check_mods, check_reliability, SOURCES, format_size, cmd_info
)

PORT = 9876
mods_cache = []
results_cache = []

HTML = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ModSync — The Sims 4</title>
<style>
:root{--bg:#0f172a;--bg2:#1e293b;--text:#e2e8f0;--accent:#22c55e;--warn:#eab308;--err:#ef4444;--border:#334155;--radius:8px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.header{background:var(--bg2);padding:12px 20px;border-bottom:2px solid var(--accent);display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:1.2rem;color:var(--accent)}
.container{padding:16px;max-width:1200px;margin:0 auto}
.panel{background:var(--bg2);border-radius:var(--radius);padding:14px;margin-bottom:12px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.btn{padding:8px 18px;border-radius:var(--radius);border:none;cursor:pointer;font-size:14px;font-weight:600;transition:all .2s}
.btn-scan{background:var(--accent);color:#000}
.btn-check{background:#3b82f6;color:#fff}
.btn-rescan{background:var(--warn);color:#000}
.btn:hover{opacity:.85;transform:translateY(-1px)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid var(--border)}
.chip input{cursor:pointer}
.source-info{font-size:11px;color:#94a3b8;margin-left:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 6px;border-bottom:2px solid var(--accent);color:var(--accent);font-size:11px;text-transform:uppercase}
td{padding:8px 6px;border-bottom:1px solid var(--border);word-break:break-word}
tr:hover{background:rgba(255,255,255,.03)}
.status-ok{color:var(--accent)}
.status-warn{color:var(--warn)}
.status-err{color:var(--err)}
.score-bar{height:4px;border-radius:2px;background:var(--border);margin-top:2px}
.score-fill{height:100%;border-radius:2px;transition:width .3s}
.score-high{background:var(--accent)}
.score-mid{background:var(--warn)}
.score-low{background:var(--err)}
#results{max-height:500px;overflow-y:auto}
#loading{display:none;text-align:center;padding:20px}
.spinner{width:24px;height:24px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite;margin:0 auto}
@keyframes spin{to{transform:rotate(360deg)}}
.empty{padding:30px;text-align:center;color:#64748b;font-size:14px}
.stats{font-size:12px;color:#94a3b8}
.stats b{color:var(--text)}
</style>
</head>
<body>
<div class="header">
  <h1>📦 ModSync — The Sims 4</h1>
  <div class="stats" id="infoStats">Загрузка...</div>
</div>
<div class="container">

  <div class="panel">
    <div class="row">
      <button class="btn btn-scan" onclick="doScan()">🔍 Сканировать моды</button>
      <button class="btn btn-check" onclick="doCheck()">🔗 Проверить обновления</button>
    </div>
    <div style="margin-top:12px">
      <div class="row" id="sourceChips"></div>
    </div>
  </div>

  <div class="panel">
    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
      <span><b>📦 Моды</b> <span id="modCount">0</span></span>
      <span id="modSize">—</span>
    </div>
    <div style="max-height:400px;overflow-y:auto">
      <table><thead><tr><th>Файл</th><th>Автор</th><th>Версия</th><th>Размер</th><th>Дата</th></tr></thead>
      <tbody id="modTable"><tr><td colspan="5" class="empty">Нажми «Сканировать», чтобы начать</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="panel">
    <div style="display:flex;justify-content:space-between;margin-bottom:8px">
      <span><b>🔄 Обновления</b> <span id="updCount">0</span></span>
    </div>
    <div id="results"><div class="empty">Нажми «Проверить обновления»</div></div>
  </div>

  <div class="panel" id="sourcesStatus" style="display:none">
    <b>🔐 Надёжность источников</b>
    <div id="sourceBars" style="margin-top:8px"></div>
  </div>

  <div id="loading"><div class="spinner"></div><p style="margin-top:8px">Работаю...</p></div>

</div>

<script>
let mods=[], results=[];

function doScan(){showLoading();fetch('/api/scan').then(r=>r.json()).then(d=>{mods=d.mods;renderMods();updateStats(d);hideLoading()})}
function doCheck(){
  showLoading();
  let srcs=[...document.querySelectorAll('.chip input:checked')].map(e=>e.value).join(',');
  fetch('/api/check?source='+encodeURIComponent(srcs)).then(r=>r.json()).then(d=>{results=d.updates;renderResults();updateSources(d.sources);hideLoading()})
}
function getAll(){doScan().then(()=>setTimeout(doCheck,500))}

function renderMods(){
  document.getElementById('modCount').textContent=mods.length+' модов';
  let h='';
  mods.sort((a,b)=>a.name.localeCompare(b.name));
  mods.forEach(m=>{
    let auth=m.author||'-',ver=m.version_raw||'-';
    h+=`<tr><td title="${m.file}">${esc(m.name)}</td><td>${esc(auth)}</td><td>${esc(ver)}</td><td>${esc(formatSize(m.size))}</td><td>${esc(m.modified.substring(0,10))}</td></tr>`;
  });
  document.getElementById('modTable').innerHTML=h||'<tr><td colspan=5 class=empty>Моды не найдены</td></tr>';
}

function renderResults(){
  document.getElementById('updCount').textContent=results.length+' найдено';
  if(!results.length){document.getElementById('results').innerHTML='<div class=empty>✅ Обновлений не найдено (или нет ключей API)</div>';return}
  let h='<table><tr><th>Источник</th><th>Локальный</th><th>Найден</th><th>Ссылка</th></tr>';
  results.forEach(r=>{
    h+=`<tr><td>${esc(r.source)}</td><td>${esc(r.local_name)}</td><td>${esc(r.online_name||'—')}</td><td>${r.url?`<a href="${esc(r.url)}" target=_blank style=color:var(--accent) title="${esc(r.status||'')}">открыть</a>`:'—'}</td></tr>`;
  });
  document.getElementById('results').innerHTML=h+'</table>';
}

function updateStats(d){
  document.getElementById('infoStats').innerHTML=`📁 <b>${esc(d.path||'?')}</b> &nbsp; 📦 <b>${d.count||0}</b> &nbsp; 💾 <b>${esc(d.size||'?')}</b>`;
  document.getElementById('modSize').innerHTML='💾 '+esc(d.size||'0');
}

function updateSources(sources){
  let d=document.getElementById('sourceBars');
  let h='';
  for(let[s,info] of Object.entries(sources||{})){
    let cl=info.score>=70?'score-high':info.score>=40?'score-mid':'score-low';
    h+=`<div style="margin-bottom:6px"><div style="display:flex;justify-content:space-between;font-size:12px"><span><b>${esc(s)}</b></span><span>${info.score}%</span></div>`;
    h+=`<div class=score-bar><div class="score-fill ${cl}" style="width:${info.score}%"></div></div>`;
    if(info.warnings)info.warnings.forEach(w=>h+=`<div style="font-size:10px;color:var(--warn)">${esc(w)}</div>`);
    h+='</div>';
  }
  d.innerHTML=h;
  document.getElementById('sourcesStatus').style.display='block';
}

function showLoading(){document.getElementById('loading').style.display='block'}
function hideLoading(){document.getElementById('loading').style.display='none'}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function formatSize(b){return b<1024?b+' B':b<1048576?(b/1024).toFixed(0)+' KB':(b/1048576).toFixed(1)+' MB'}

// Источники-чипсы
(function(){
  let srcs=['curseforge','modthesims','thesimscc','patreon','vk'];
  let labels={'curseforge':'CurseForge','modthesims':'ModTheSims','thesimscc':'thesims.cc','patreon':'Patreon','vk':'ВКонтакте'};
  let tips={'curseforge':'CURSEFORGE_API_KEY','modthesims':'MODTHESIMS_API_KEY','patreon':'PATREON_API_KEY','vk':'VK_API_KEY','thesimscc':'без ключа'};
  let h='';
  srcs.forEach(s=>h+=`<label class="chip" title="${esc(tips[s])}"><input type=checkbox value="${s}" checked> ${esc(labels[s])}<span class=source-info>${esc(tips[s])}</span></label>`);
  h+='<button class="btn btn-rescan" onclick="getAll()" style="margin-left:auto">🔄 Всё сразу</button>';
  document.getElementById('sourceChips').innerHTML=h;
})();

// Авто-загрузка при открытии
fetch('/api/info').then(r=>r.json()).then(d=>updateStats(d));
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/" or path == "/index.html":
            self._html(HTML)
        elif path == "/api/info":
            d = find_mods_dir()
            info = {"path": str(d) if d else "?",
                    "count": 0, "size": "0"}
            if d and d.exists():
                mods = scan_mods(d)
                total = sum(m["size"] for m in mods)
                info["count"] = len(mods)
                info["size"] = format_size(total)
            self._json(info)
        elif path == "/api/scan":
            d = find_mods_dir()
            if not d:
                self._json({"error": "no mods dir", "mods": []})
                return
            global mods_cache
            mods_cache = scan_mods(d)
            total = sum(m["size"] for m in mods_cache)
            self._json({
                "mods": mods_cache,
                "count": len(mods_cache),
                "size": format_size(total),
                "path": str(d),
            })
        elif path == "/api/check":
            import urllib.parse
            params = urllib.parse.parse_qs(self.path.split("?")[1]) if "?" in self.path else {}
            src = params.get("source", [""])[0]
            source = src if src else None

            mods = mods_cache or []
            if not mods:
                d = find_mods_dir()
                if d:
                    mods = scan_mods(d)

            sources_status = {}
            updates = check_mods(mods, source)

            # Reliability check
            urls = {
                "CurseForge": "https://api.curseforge.com",
                "ModTheSims": "https://api.modthesims.info",
                "thesims.cc": "https://thesims.cc",
                "Patreon": "https://www.patreon.com",
                "ВКонтакте": "https://api.vk.com",
            }
            for s, url in urls.items():
                sources_status[s] = check_reliability(url)

            self._json({"updates": updates, "sources": sources_status})
        else:
            self._404()

    def _html(self, c):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(c.encode())

    def _json(self, d):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(d, ensure_ascii=False, default=str).encode())

    def _404(self):
        self.send_error(404)


def run_gui():
    mods_dir = find_mods_dir()
    if mods_dir:
        print(f"📁 Папка модов: {mods_dir}")
    else:
        print("⚠️  Папка Mods не найдена. Укажи --dir при сканировании вручную.")

    print(f"\n🎨 ModSync GUI: http://localhost:{PORT}")
    print(f"   Открой в браузере ↑")

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Закрыто")


if __name__ == "__main__":
    run_gui()
