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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#0a0e17;--bg2:#111827;--bg3:#1e293b;--text:#f1f5f9;--text2:#94a3b8;--accent:#22c55e;--accent2:#16a34a;--warn:#f59e0b;--err:#ef4444;--blue:#3b82f6;--purple:#8b5cf6;--pink:#ec4899;--orange:#f97316;--border:#1e293b;--border2:#334155;--radius:12px;--shadow:0 4px 24px rgba(0,0,0,.3)}
body{font-family:Inter,-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
::-webkit-scrollbar{width:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
.header{background:linear-gradient(135deg,#0f172a,#1a2332,#0f172a);border-bottom:1px solid var(--border2);padding:16px 24px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}
.header h1{font-size:1.1rem;font-weight:700;background:linear-gradient(90deg,var(--accent),var(--blue));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header h1 span{font-weight:400;background:none;-webkit-text-fill-color:var(--text2);font-size:0.9rem}
.stats{font-size:12px;color:var(--text2);display:flex;gap:16px;align-items:center}
.badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600}
.badge-green{background:rgba(34,197,94,.15);color:var(--accent)}
.container{max-width:1280px;margin:0 auto;padding:20px 24px}

.card{background:var(--bg2);border-radius:var(--radius);padding:20px;margin-bottom:16px;border:1px solid var(--border);transition:border-color .2s}
.card:hover{border-color:var(--border2)}
.card-title{font-size:13px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px}
.card-title .count{color:var(--text);margin-left:6px}

.btn-group{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.btn{padding:9px 20px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:600;transition:all .2s;display:inline-flex;align-items:center;gap:6px;font-family:inherit}
.btn:active{transform:scale(.96)}
.btn-primary{background:var(--accent);color:#000;box-shadow:0 2px 12px rgba(34,197,94,.25)}
.btn-primary:hover{background:var(--accent2);box-shadow:0 4px 20px rgba(34,197,94,.35)}
.btn-secondary{background:var(--blue);color:#fff;box-shadow:0 2px 12px rgba(59,130,246,.25)}
.btn-secondary:hover{background:#2563eb;box-shadow:0 4px 20px rgba(59,130,246,.35)}
.btn-all{background:linear-gradient(135deg,var(--accent),var(--blue));color:#fff;box-shadow:0 2px 12px rgba(34,197,94,.2)}
.btn-all:hover{opacity:.9}

.chip-group{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:5px 12px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid var(--border2);background:var(--bg3);color:var(--text2);transition:all .2s;user-select:none}
.chip:hover{border-color:var(--accent);color:var(--text)}
.chip.checked{background:rgba(34,197,94,.1);border-color:var(--accent);color:var(--accent)}
.chip .dot{width:6px;height:6px;border-radius:50%;display:inline-block}
.dot-curseforge{background:var(--orange)}.dot-modthesims{background:var(--purple)}
.dot-thesimscc{background:var(--pink)}.dot-patreon{background:var(--err)}.dot-vk{background:var(--blue)}
.key-hint{font-size:9px;color:var(--text2);opacity:.6}

.stat-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.stat-card{padding:16px;border-radius:8px;border:1px solid var(--border);text-align:center}
.stat-card .num{font-size:24px;font-weight:700;color:var(--text)}
.stat-card .label{font-size:11px;color:var(--text2);margin-top:2px}

.table-wrap{overflow-x:auto;border-radius:8px;border:1px solid var(--border)}
table{width:100%;border-collapse:collapse;font-size:13px;min-width:600px}
th{text-align:left;padding:10px 12px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--text2);border-bottom:1px solid var(--border);background:var(--bg3)}
td{padding:9px 12px;border-bottom:1px solid var(--border);color:var(--text)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(255,255,255,.02)}
.file-name{font-weight:500;color:var(--text)}
.file-path{font-size:10px;color:var(--text2);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:300px}

.result-item{padding:12px;border-radius:8px;border:1px solid var(--border);margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;transition:all .2s}
.result-item:hover{border-color:var(--border2);background:rgba(255,255,255,.01)}
.result-left{flex:1;min-width:200px}
.result-right{display:flex;align-items:center;gap:8px}
.result-source{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:4px}
.src-curseforge{background:rgba(249,115,22,.1);color:var(--orange)}
.src-modthesims{background:rgba(139,92,246,.1);color:var(--purple)}
.src-thesimscc{background:rgba(236,72,153,.1);color:var(--pink)}
.src-patreon{background:rgba(239,68,68,.1);color:var(--err)}
.src-vk{background:rgba(59,130,246,.1);color:var(--blue)}

.source-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin-top:8px}
.source-card{padding:12px;border-radius:8px;border:1px solid var(--border)}
.source-card .name{font-size:12px;font-weight:600}
.bar-full{height:3px;border-radius:2px;background:var(--border);margin-top:6px;overflow:hidden}
.bar-fill{height:100%;border-radius:2px;transition:width .6s cubic-bezier(.4,0,.2,1)}
.bar-green{background:var(--accent)}.bar-yellow{background:var(--warn)}.bar-red{background:var(--err)}
.source-warn{font-size:9px;color:var(--warn);margin-top:2px}

#loadingOverlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(10,14,23,.7);backdrop-filter:blur(4px);z-index:999;justify-content:center;align-items:center}
#loadingOverlay.active{display:flex}
.loading-card{background:var(--bg2);padding:30px 40px;border-radius:var(--radius);text-align:center;border:1px solid var(--border);box-shadow:var(--shadow)}
.spinner{width:32px;height:32px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-text{font-size:13px;color:var(--text2)}

.empty{text-align:center;padding:30px 20px;color:var(--text2);font-size:13px}
.empty-icon{font-size:32px;margin-bottom:8px;opacity:.5}

.status{font-weight:600;font-size:12px;display:inline-flex;align-items:center;gap:4px}
.status-older{color:var(--err)}.status-same{color:var(--accent)}.status-unknown{color:var(--warn)}
.link-btn{color:var(--blue);font-size:12px;text-decoration:none;font-weight:500}
.link-btn:hover{text-decoration:underline}

.toast{position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:8px;font-size:13px;font-weight:500;z-index:1000;box-shadow:var(--shadow);animation:slideUp .3s ease}
.toast-success{background:var(--accent);color:#000}
.toast-error{background:var(--err);color:#fff}
.toast-info{background:var(--blue);color:#fff}
@keyframes slideUp{from{opacity:0;transform:translateY(20px)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}}
.card{animation:fadeIn .3s ease}
</style>
</head>
<body>
<div class="header">
  <h1>ModSync <span>The Sims 4</span></h1>
  <div class="stats" id="infoStats"><span class="badge badge-green">⏳ загрузка...</span></div>
</div>
<div class="container">

  <div class="stat-cards" id="statCards">
    <div class="stat-card"><div class="num">—</div><div class="label">Модов</div></div>
    <div class="stat-card"><div class="num">—</div><div class="label">Размер</div></div>
    <div class="stat-card"><div class="num">—</div><div class="label">Найдено</div></div>
  </div>

  <div class="card">
    <div class="btn-group">
      <button class="btn btn-primary" onclick="doScan()">Сканировать</button>
      <button class="btn btn-secondary" onclick="doCheck()">Проверить</button>
      <button class="btn btn-all" onclick="getAll()">Сканировать + проверить</button>
    </div>
    <div class="chip-group" id="sourceChips"></div>
  </div>

  <div class="card">
    <div class="card-title" style="margin-bottom:0">Установленные <span class="count" id="modCount">0</span></div>
    <div class="table-wrap" style="max-height:360px;overflow-y:auto">
      <table><thead><tr><th>Файл</th><th>Автор</th><th>Версия</th><th>Размер</th><th>Дата</th></tr></thead>
      <tbody id="modTable"><tr><td colspan="5"><div class="empty"><div class="empty-icon">📂</div>Нажми Сканировать</div></td></tr></tbody></table>
    </div>
  </div>

  <div class="card">
    <div class="card-title" style="margin-bottom:12px">Обновления <span class="count" id="updCount">0</span></div>
    <div id="results"><div class="empty"><div class="empty-icon">🔍</div>Нажми Проверить обновления</div></div>
  </div>

  <div class="card" id="sourcesCard" style="display:none">
    <div class="card-title" style="margin-bottom:12px">Наджность источников</div>
    <div class="source-grid" id="sourceGrid"></div>
  </div>

</div>

<div id="loadingOverlay">
  <div class="loading-card">
    <div class="spinner"></div>
    <div class="loading-text">Работаю...</div>
  </div>
</div>

<script>
let mods=[],results=[];
const L={curseforge:'CurseForge',modthesims:'ModTheSims',thesimscc:'thesims.cc',patreon:'Patreon',vk:'VK'};
const T={curseforge:'CURSEFORGE_API_KEY',modthesims:'MODTHESIMS_API_KEY',thesimscc:'no key',patreon:'PATREON_API_KEY',vk:'VK_API_KEY'};

function toast(m,t){const e=document.createElement('div');e.className='toast toast-'+t;e.textContent=m;document.body.appendChild(e);setTimeout(()=>e.remove(),3000)}
function ld(t){document.querySelector('.loading-text').textContent=t;document.getElementById('loadingOverlay').classList.add('active')}
function hl(){document.getElementById('loadingOverlay').classList.remove('active')}

function doScan(){ld('Сканирование...');fetch('/api/scan').then(r=>r.json()).then(d=>{mods=d.mods;rM();rS(d);hl();toast('Найдено '+d.count+' модов','success')}).catch(()=>{hl();toast('Ошибка','error')})}
function doCheck(){ld('Проверка...');let s=[...document.querySelectorAll('.chip.checked')].map(e=>e.dataset.src).join(',');fetch('/api/check?source='+encodeURIComponent(s)).then(r=>r.json()).then(d=>{results=d.updates;rR();uS(d.sources);hl();toast(results.length?'Найдено '+results.length:'Вс актуально',results.length?'info':'success')}).catch(()=>{hl();toast('Ошибка','error')})}
function getAll(){ld('Полный цикл...');fetch('/api/scan').then(r=>r.json()).then(d=>{mods=d.mods;rM();return fetch('/api/check?source='+[...document.querySelectorAll('.chip.checked')].map(e=>e.dataset.src).join(','))}).then(r=>r.json()).then(d=>{results=d.updates;rR();uS(d.sources);hl();toast('Готово!','success')}).catch(()=>{hl();toast('Ошибка','error')})}

function rM(){
  document.getElementById('modCount').textContent=mods.length;
  let h='';mods.sort((a,b)=>a.name.localeCompare(b.name));
  mods.forEach(m=>{
    let a=m.author||'-',v=m.version_raw||'<span style=color:var(--text2)>--</span>';
    h+='<tr><td><div class=file-name>'+esc(m.name)+'</div><div class=file-path>'+esc(m.file)+'</div></td><td>'+esc(a)+'</td><td>'+v+'</td><td>'+fs(m.size)+'</td><td>'+esc((m.modified||'').substring(0,10))+'</td></tr>'
  });
  document.getElementById('modTable').innerHTML=h||'<tr><td colspan=5><div class=empty><div class=empty-icon>📭</div>Моды не найдены</div></td></tr>'
}

function rR(){
  document.getElementById('updCount').textContent=results.length;
  if(!results.length){document.getElementById('results').innerHTML='<div class=empty><div class=empty-icon>✅</div>Обновлений не найдено</div>';return}
  let h='';
  results.forEach(r=>{
    let sc='src-'+r.source.toLowerCase().replace(/[^a-z]/g,'');
    let st=r.status||'',stc='';if(st.includes('устарел'))stc='status-older';else if(st.includes('актуален'))stc='status-same';else stc='status-unknown';
    h+='<div class=result-item><div class=result-left><div style=display:flex;align-items:center;gap:6px;margin-bottom:2px><span class="result-source '+sc+'">'+esc(r.source)+'</span><span class=file-name>'+esc(r.local_name)+'</span></div>';
    if(r.local_version)h+='<span style=font-size:11px;color:var(--text2)>v'+esc(r.local_version)+(r.online_version?' vs '+esc(r.online_version):'')+'</span>';
    h+='</div><div class=result-right><span class="status '+stc+'">'+esc(st)+'</span>';
    if(r.url)h+='<a class=link-btn href='+esc(r.url)+' target=_blank>открыть</a>';
    h+='</div></div>'
  });
  document.getElementById('results').innerHTML=h
}

function uS(s){
  let g=document.getElementById('sourceGrid'),h='';
  for(let[n,i] of Object.entries(s||{})){
    let cl=i.score>=70?'bar-green':i.score>=40?'bar-yellow':'bar-red';
    h+='<div class=source-card><div style=display:flex;justify-content:space-between><span class=name>'+esc(n)+'</span><span style=font-size:11px;color:var(--text2)>'+i.score+'%</span></div><div class=bar-full><div class="bar-fill '+cl+'" style=width:'+i.score+'%></div></div>';
    if(i.warnings)i.warnings.forEach(w=>h+='<div class=source-warn>'+esc(w)+'</div>');
    h+='</div>'
  }
  g.innerHTML=h;document.getElementById('sourcesCard').style.display='block'
}

function rS(d){
  document.getElementById('statCards').innerHTML='<div class=stat-card><div class=num>'+(d.count||0)+'</div><div class=label>Модов</div></div><div class=stat-card><div class=num>'+esc(d.size||'0')+'</div><div class=label>Размер</div></div><div class=stat-card><div class=num>'+results.length+'</div><div class=label>Найдено</div></div>';
  document.getElementById('infoStats').innerHTML='<span class="badge badge-green">'+esc(d.path||'')+'</span>'
}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function fs(b){return b<1024?b+' B':b<1048576?(b/1024).toFixed(0)+' KB':(b/1048576).toFixed(1)+' MB'}

!function(){let h='';['curseforge','modthesims','thesimscc','patreon','vk'].forEach(s=>{h+='<label class="chip checked" data-src='+s+' onclick=this.classList.toggle("checked")><span class="dot dot-'+s+'"></span>'+L[s]+'<span class=key-hint>'+T[s]+'</span></label>'});document.getElementById('sourceChips').innerHTML=h}();
fetch('/api/info').then(r=>r.json()).then(d=>{if(d.count>0){fetch('/api/scan').then(r=>r.json()).then(d=>{mods=d.mods;rM();rS(d)})}});
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._html(HTML)
        elif path == "/api/info":
            d = find_mods_dir()
            info = {"path": str(d) if d else "?", "count": 0, "size": "0"}
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

            urls = {
                "CurseForge": "https://api.curseforge.com",
                "ModTheSims": "https://api.modthesims.info",
                "thesims.cc": "https://thesims.cc",
                "Patreon": "https://www.patreon.com",
                "VK": "https://api.vk.com",
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
        print(f"Папка модов: {mods_dir}")
    else:
        print("Папка Mods не найдена.")
    print(f"\nModSync GUI: http://localhost:{PORT}")

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nЗакрыто")


if __name__ == "__main__":
    run_gui()
