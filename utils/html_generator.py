import os
import shutil
from pathlib import Path
from datetime import datetime

def generate_html(png_files,
                  png_dir,
                  pulse_files=None,
                  pulse_dir=None,
                  plots_per_row=4,
                  output_html="view_plots.html"):
    """
    Ultra-feature HTML viewer (fixed):
      • Persistent dark/light mode
      • Grid/List + Shuffle
      • Filter + Sort
      • Lazy loading + spinner
      • Tilt-on-hover + metadata
      • Lightbox + slideshow
      • Help modal & shortcuts
      • Sticky header/footer + stats panel
    """
    # Resolve paths
    html_path = Path(output_html).resolve()
    html_dir  = html_path.parent
    png_dir   = Path(png_dir).resolve()
    pulse_dir = Path(pulse_dir).resolve() if pulse_dir else png_dir

    # Copy logos into assets
    assets_dir = html_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for logo in ["VISTA_Logo.png", "APD_Logo.png", "TTU_Seal.png"]:
        src = Path(__file__).resolve().parent / "images" / logo
        dst = assets_dir / logo
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
    vista_logo = os.path.relpath(assets_dir / "VISTA_Logo.png", html_dir)
    apd_logo   = os.path.relpath(assets_dir / "APD_Logo.png",   html_dir)
    tt_logo    = os.path.relpath(assets_dir / "TTU_Seal.png",   html_dir)

    # Gather metadata
    def build_entries(files, base):
        out = []
        for fn in files or []:
            full = base / fn
            if not full.exists(): continue
            st = full.stat()
            size_kb = st.st_size / 1024.0
            date    = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            out.append({
                "name": fn,
                "rel":  os.path.relpath(full, html_dir),
                "size": f"{size_kb:.1f}KB",
                "date": date
            })
        return out

    events = build_entries(png_files, png_dir)
    pulses = build_entries(pulse_files, pulse_dir)

    # Stats
    all_sizes = [float(e["size"][:-2]) for e in events + pulses]
    avg_size = sum(all_sizes) / (len(all_sizes) or 1)
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Start building HTML
    html = """<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
  <meta charset="UTF-8">
  <title>VISTA Viewer</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link href="https://fonts.googleapis.com/css?family=Roboto:400,500&display=swap" rel="stylesheet">
  <style>
    /* RESET */
    * { margin:0; padding:0; box-sizing:border-box }
    body { font-family:'Roboto',sans-serif; background:var(--bg); color:var(--text); transition:background .3s, color .3s }
    :root { --bg:#fafafa; --card:#fff; --text:#333; --accent:#6200ee; --shadow:rgba(0,0,0,.1); --link:#0645ad }
    [data-theme="dark"] { --bg:#121212; --card:#1e1e1e; --text:#e0e0e0; --accent:#bb86fc; --shadow:rgba(0,0,0,.7); --link:#9ab }
    a { color:var(--link); text-decoration:none }
    header, footer { position:sticky; width:100%; background:var(--card); padding:1rem 2rem; box-shadow:0 2px 4px var(--shadow); z-index:10 }
    footer { bottom:0; box-shadow:0 -2px 4px var(--shadow) }
    .logo-group img { height:80px; margin-right:1rem }
    .controls, .stats-panel { display:flex; align-items:center; gap:1rem }
    .tabs { display:flex; gap:1rem; margin:1rem 2rem }
    .tab { cursor:pointer; padding:.5rem 1rem; border-bottom:2px solid transparent; transition:color .2s,border-color .2s }
    .tab.active { color:var(--accent); border-color:var(--accent) }
    .toolbar { display:flex; gap:.5rem; flex-wrap:wrap; margin:1rem 2rem }
    .toolbar * { padding:.5rem }
    input, select, button { border:1px solid #ccc; border-radius:4px; background:var(--card); color:var(--text) }
    button:hover { background:var(--accent); color:#fff }
    #container, #container2 { display:grid; gap:16px; margin:0 2rem; transition:all .3s }
    .grid { grid-template-columns:repeat(""" + str(plots_per_row) + """,1fr) }
    .list { grid-template-columns:1fr }
    .plot { position:relative; background:var(--card); border-radius:8px; box-shadow:0 1px 3px var(--shadow); overflow:hidden; transform:perspective(600px) rotateX(0); transition:transform .3s }
    .plot:hover { transform:perspective(600px) rotateX(5deg) translateY(-5px) }
    .plot.loading img { filter:blur(8px); transition:filter .5s }
    .plot img { width:100%; display:block }
    .filename { padding:.5rem; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
    .meta-hover { position:absolute; top:8px; right:8px; background:rgba(0,0,0,0.6); color:#fff; padding:2px 6px; border-radius:4px; font-size:.75rem; opacity:0; transition:opacity .2s }
    .plot:hover .meta-hover { opacity:1 }
    .modal { display:none; position:fixed; inset:0; background:rgba(0,0,0,0.8); align-items:center; justify-content:center; z-index:1000 }
    .modal-content { max-width:90%; max-height:80%; border-radius:8px }
    .modal button { position:absolute; background:none; border:none; color:#fff; font-size:2rem; cursor:pointer }
    .modal .close { top:16px; right:24px }
    .modal .prev { left:24px; top:50%; transform:translateY(-50%) }
    .modal .next { right:24px; top:50%; transform:translateY(-50%) }
    #helpModal .help-content { background:var(--card); color:var(--text); padding:2rem; border-radius:8px; max-width:600px; margin:auto; position:relative }
    #helpModal .help-content h2 { margin-bottom:.5rem }
    #helpModal .help-content ul { list-style:disc inside; margin:1rem 0 }
    #spinner { display:none; position:fixed; inset:0; background:rgba(255,255,255,0.7); align-items:center; justify-content:center; z-index:2000 }
    #spinner div { width:64px; height:64px; border:8px solid var(--accent); border-top:8px solid transparent; border-radius:50%; animation:spin 1s linear infinite }
    @keyframes spin { to{ transform:rotate(360deg) } }
  </style>
</head>
<body>
  <header>
    <div class="logo-group">
      <img src=\"""" + vista_logo + """\" alt="VISTA">
      <img src=\"""" + apd_logo   + """\" alt="APD Lab">
    </div>
    <div class="controls">
      <label>Dark: <input type="checkbox" id="themeToggle"></label>
      <button id="toggleView">List/Grid</button>
      <button id="shuffleBtn">Shuffle</button>
      <button id="helpBtn">Help (F1)</button>
    </div>
    <div class="stats-panel">
      <span>Events: """ + str(len(events)) + """</span>
      <span>Pulses: """ + str(len(pulses)) + """</span>
      <span>Avg Size: """ + f"{avg_size:.1f}KB" + """</span>
      <span>Generated: """ + gen_time + """</span>
    </div>
  </header>

  <nav class="tabs">
    <div class="tab active" data-target="events">Event Displays</div>
    <div class="tab" data-target="pulses">Pulse Plots</div>
    <div class="tab" data-target="info">Info</div>
  </nav>

  <div class="toolbar">
    <input type="text" id="filter" placeholder="Filter…">
    <select id="sort">
      <option value="name">Name ⯆</option>
      <option value="size">Size ⯆</option>
      <option value="date">Date ⯆</option>
    </select>
    <button id="slideshowBtn">Start Slideshow</button>
    <button id="downloadAll">Download All</button>
  </div>

  <section id="events" class="content active">
    <div id="container" class="grid">
"""
    # Add event thumbnails
    for i,e in enumerate(events):
        html += """
      <div class="plot loading" data-idx=\""""+str(i)+"""\" data-name=\""""+e['name']+"""\" data-size=\""""+e['size']+"""\" data-date=\""""+e['date']+"""\">
        <div class="meta-hover">"""+e['size']+""" · """+e['date']+"""</div>
        <img src=\""""+e['rel']+"""\" alt=\""""+e['name']+"""\" loading="lazy" onload="this.parentNode.classList.remove('loading')">
        <div class="filename">"""+e['name']+"""</div>
      </div>
"""
    html += """
    </div>
  </section>
  <section id="pulses" class="content">
    <div id="container2" class="grid">
"""
    # Add pulse thumbnails
    for i,p in enumerate(pulses):
        html += """
      <div class="plot loading" data-idx=\""""+str(i)+"""\" data-name=\""""+p['name']+"""\" data-size=\""""+p['size']+"""\" data-date=\""""+p['date']+"""\">
        <div class="meta-hover">"""+p['size']+""" · """+p['date']+"""</div>
        <img src=\""""+p['rel']+"""\" alt=\""""+p['name']+"""\" loading="lazy" onload="this.parentNode.classList.remove('loading')">
        <div class="filename">"""+p['name']+"""</div>
      </div>
"""
    html += """
    </div>
  </section>
  <section id="info" class="content">
    <div style="margin:1rem 2rem;">
      <h2>Viewer Info</h2>
      <p>This page shows """ + str(len(events)) + """ event displays and """ + str(len(pulses)) + """ pulse plots.</p>
      <p>Average image size: """ + f"{avg_size:.1f}KB" + """</p>
      <p>Generated on: """ + gen_time + """</p>
      <p>Host: <code><script>document.write(location.host)</script></code></p>
    </div>
  </section>

  <!-- Lightbox Modal -->
  <div id="modal" class="modal" tabindex="-1">
    <button class="close">&times;</button>
    <button class="prev">&#10094;</button>
    <img class="modal-content" id="modalImage">
    <button class="next">&#10095;</button>
  </div>

  <!-- Help Modal -->
  <div id="helpModal" class="modal" tabindex="-1">
    <div class="help-content">
      <h2>Help & Shortcuts</h2>
      <ul>
        <li><strong>Tabs:</strong> click “Event Displays”, “Pulse Plots”, “Info”.</li>
        <li><strong>Filter:</strong> type to filter by filename.</li>
        <li><strong>Sort:</strong> choose Name/Size/Date.</li>
        <li><strong>View:</strong> toggle List/Grid or Shuffle.</li>
        <li><strong>Slideshow:</strong> auto-advance images every 2s.</li>
        <li><strong>Download All:</strong> placeholder (needs backend).</li>
        <li><strong>Keyboard:</strong> ← → navigate, Esc close, F1 help.</li>
      </ul>
      <button class="close">&times; Close</button>
    </div>
  </div>

  <!-- Spinner -->
  <div id="spinner"><div></div></div>

  <footer>
    <span>VISTA – APD Lab</span>
    <img src=\"""" + tt_logo + """\" alt="TTU">
  </footer>

  <script>
    // Theme persistence
    const toggle = document.getElementById('themeToggle');
    const saved = localStorage.getItem('theme');
    if (saved==='dark') {
      document.documentElement.setAttribute('data-theme','dark');
      toggle.checked = true;
    }
    toggle.onchange = () => {
      const t = toggle.checked ? 'dark':'light';
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('theme', t);
    };

    // Tabs (fixed drop-in)
    document.querySelectorAll('.tab').forEach(function(tab) {
      tab.addEventListener('click', function() {
        // deactivate all tabs & panels
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
        // activate this tab
        tab.classList.add('active');
        // show its target section
        const target = tab.getAttribute('data-target');
        const panel  = document.getElementById(target);
        if (panel) panel.classList.add('active');
      });
    });

    // Filter & Sort
    const filterI = document.getElementById('filter'),
          sortS   = document.getElementById('sort'),
          cont    = document.getElementById('container'),
          cont2   = document.getElementById('container2');
    function applyFS(c) {
      let items = Array.from(c.children);
      const q = filterI.value.toLowerCase();
      items.forEach(i => i.style.display = i.dataset.name.includes(q) ? '' : 'none');
      const key = sortS.value;
      items.sort((a,b) => a.dataset[key].localeCompare(b.dataset[key], undefined, {numeric:true}));
      c.innerHTML=''; items.forEach(i=>c.appendChild(i));
    }
    filterI.oninput = () => {applyFS(cont); applyFS(cont2);};
    sortS.onchange  = () => {applyFS(cont); applyFS(cont2);};

    // View & Shuffle
    document.getElementById('toggleView').onclick = () => {
      [cont,cont2].forEach(c => c.className = c.classList.contains('grid') ? 'list' : 'grid');
    };
    document.getElementById('shuffleBtn').onclick = () => {
      [cont,cont2].forEach(c => {
        let a = Array.from(c.children);
        a.sort(()=>Math.random()-0.5);
        c.innerHTML=''; a.forEach(n=>c.appendChild(n));
      });
    };

    // Lightbox & keyboard
    const modal = document.getElementById('modal'),
          imgE  = document.getElementById('modalImage'),
          imgs  = [...document.querySelectorAll('.plot img')];
    let idx=0;
    function openBox(i) { idx=i; imgE.src=imgs[i].src; modal.style.display='flex'; modal.focus(); }
    imgs.forEach((im,i)=>im.onclick=()=>openBox(i));
    document.querySelectorAll('#modal .close').forEach(b=>b.onclick=()=>modal.style.display='none');
    document.querySelector('.prev').onclick = ()=>openBox((idx-1+imgs.length)%imgs.length);
    document.querySelector('.next').onclick = ()=>openBox((idx+1)%imgs.length);
    modal.onkeydown = e => {
      if (e.key==='Escape') modal.style.display='none';
      if (e.key==='ArrowLeft') document.querySelector('.prev').click();
      if (e.key==='ArrowRight') document.querySelector('.next').click();
    };

    // Slideshow
    let slide;
    document.getElementById('slideshowBtn').onclick = function(){
      if (this.textContent.includes('Start')) {
        this.textContent='Stop Slideshow';
        slide = setInterval(()=>document.querySelector('.next').click(), 2000);
      } else {
        clearInterval(slide);
        this.textContent='Start Slideshow';
      }
    };

    // Download All
    document.getElementById('downloadAll').onclick = () => alert('Download-all needs server support.');

    // Help Modal & F1
    const helpM = document.getElementById('helpModal');
    document.getElementById('helpBtn').onclick = () => helpM.style.display='flex';
    helpM.querySelectorAll('.close').forEach(b=>b.onclick=()=>helpM.style.display='none');
    window.onkeydown = e => { if(e.key==='F1'){ e.preventDefault(); helpM.style.display='flex'; } };
  </script>
</body>
</html>
"""

    # Write out
    html_dir.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Ultra-feature viewer generated at {html_path}")
