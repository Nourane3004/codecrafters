# codecrafters
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TruthGuard — README & Architecture</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #f8f9fc;
  --surface: #ffffff;
  --border: #e2e6f0;
  --border2: #c8d0e8;
  --text: #1a1f36;
  --text2: #4a5278;
  --text3: #8892b0;
  --accent: #2563eb;
  --accent-d: #eff6ff;
  --green: #059669;
  --green-d: #ecfdf5;
  --red: #dc2626;
  --red-d: #fef2f2;
  --amber: #d97706;
  --amber-d: #fffbeb;
  --purple: #7c3aed;
  --purple-d: #f5f3ff;
  --teal: #0891b2;
  --teal-d: #ecfeff;
  --orange: #ea580c;
  --orange-d: #fff7ed;
  --pink: #db2777;
  --pink-d: #fdf2f8;
  --font-head: 'Syne', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --r: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06);
  --shadow-lg: 0 4px 24px rgba(0,0,0,0.10);
}

* { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.7;
}

/* ── LAYOUT ── */
.wrapper { display: flex; min-height: 100vh; }

/* Sidebar TOC */
.sidebar {
  width: 260px; flex-shrink: 0;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 28px 0;
}
.sidebar-logo {
  padding: 0 20px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.sidebar-logo h2 {
  font-family: var(--font-head);
  font-size: 18px; font-weight: 800; letter-spacing: -0.5px;
  color: var(--text);
}
.sidebar-logo span { color: var(--accent); }
.sidebar-badge {
  display: inline-block; margin-top: 4px;
  font-family: var(--font-mono); font-size: 10px;
  background: var(--accent-d); color: var(--accent);
  border: 1px solid #bfdbfe; border-radius: 4px; padding: 1px 7px;
}
.toc-section { margin-bottom: 4px; }
.toc-group {
  font-family: var(--font-mono); font-size: 9px; font-weight: 500;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--text3);
  padding: 12px 20px 4px;
}
.toc-link {
  display: block; padding: 5px 20px;
  font-size: 13px; color: var(--text2); text-decoration: none;
  transition: all .15s; border-left: 2px solid transparent;
}
.toc-link:hover { color: var(--accent); background: var(--accent-d); border-left-color: var(--accent); }
.toc-link.sub { padding-left: 32px; font-size: 12px; color: var(--text3); }
.toc-link.sub:hover { color: var(--accent); }

/* Main content */
.main {
  flex: 1; min-width: 0;
  padding: 48px 56px 80px;
  max-width: 960px;
}

/* ── TYPOGRAPHY ── */
h1 {
  font-family: var(--font-head);
  font-size: 44px; font-weight: 800; letter-spacing: -2px;
  line-height: 1.05; margin-bottom: 16px; color: var(--text);
}
h1 span { color: var(--accent); }
h2 {
  font-family: var(--font-head);
  font-size: 26px; font-weight: 800; letter-spacing: -0.8px;
  margin-top: 60px; margin-bottom: 20px; color: var(--text);
  padding-bottom: 10px; border-bottom: 2px solid var(--border);
  display: flex; align-items: center; gap: 10px;
}
h3 {
  font-size: 17px; font-weight: 700; margin-top: 32px; margin-bottom: 12px;
  color: var(--text); display: flex; align-items: center; gap: 8px;
}
h4 { font-size: 14px; font-weight: 700; margin-top: 20px; margin-bottom: 8px; color: var(--text2); }
p { margin-bottom: 14px; color: var(--text2); line-height: 1.75; }
p strong { color: var(--text); }
code {
  font-family: var(--font-mono); font-size: 12.5px;
  background: var(--bg); border: 1px solid var(--border2);
  padding: 1px 6px; border-radius: 4px; color: var(--accent);
}
pre {
  background: #0f172a; color: #e2e8f0;
  font-family: var(--font-mono); font-size: 12.5px; line-height: 1.7;
  padding: 20px 24px; border-radius: var(--r);
  overflow-x: auto; margin: 16px 0;
  box-shadow: var(--shadow);
}
pre code { background: none; border: none; color: inherit; padding: 0; font-size: inherit; }
ul, ol { padding-left: 24px; margin-bottom: 14px; }
li { margin-bottom: 6px; color: var(--text2); line-height: 1.65; }
li strong { color: var(--text); }

/* ── HERO ── */
.hero {
  background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #2563eb 100%);
  border-radius: 20px; padding: 40px 44px; margin-bottom: 48px;
  color: white; position: relative; overflow: hidden;
  box-shadow: var(--shadow-lg);
}
.hero::before {
  content: '';
  position: absolute; top: -60px; right: -60px;
  width: 280px; height: 280px; border-radius: 50%;
  background: rgba(255,255,255,0.05);
}
.hero::after {
  content: '';
  position: absolute; bottom: -40px; right: 80px;
  width: 160px; height: 160px; border-radius: 50%;
  background: rgba(255,255,255,0.04);
}
.hero h1 { color: white; margin-bottom: 10px; font-size: 38px; }
.hero h1 span { color: #93c5fd; }
.hero p { color: rgba(255,255,255,0.8); margin-bottom: 20px; font-size: 16px; max-width: 560px; }
.hero-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.hero-tag {
  background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.2);
  border-radius: 100px; padding: 4px 14px;
  font-size: 12px; font-weight: 500; color: white;
  backdrop-filter: blur(10px);
}

/* ── CALLOUT BOXES ── */
.callout {
  display: flex; gap: 14px; padding: 16px 20px;
  border-radius: var(--r); margin: 20px 0;
  border: 1px solid; font-size: 14px; line-height: 1.6;
}
.callout-icon { font-size: 20px; flex-shrink: 0; margin-top: 1px; }
.callout.info    { background: var(--accent-d); border-color: #bfdbfe; color: #1e40af; }
.callout.success { background: var(--green-d);  border-color: #a7f3d0; color: #065f46; }
.callout.warn    { background: var(--amber-d);  border-color: #fcd34d; color: #92400e; }
.callout.danger  { background: var(--red-d);    border-color: #fca5a5; color: #991b1b; }
.callout strong  { font-weight: 700; }

/* ── CARDS ── */
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r); padding: 20px 24px;
  box-shadow: var(--shadow); margin-bottom: 12px;
}
.card-grid {
  display: grid; gap: 14px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  margin: 20px 0;
}
.card-sm {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r); padding: 16px 18px;
  box-shadow: var(--shadow);
  position: relative; overflow: hidden;
}
.card-sm::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--c, var(--accent));
}
.card-sm-icon { font-size: 24px; margin-bottom: 8px; }
.card-sm-title {
  font-weight: 700; font-size: 14px; margin-bottom: 4px; color: var(--text);
}
.card-sm-desc { font-size: 12.5px; color: var(--text2); line-height: 1.5; }
.card-sm-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 10px; }
.tag {
  font-family: var(--font-mono); font-size: 10px;
  padding: 2px 7px; border-radius: 4px;
  background: var(--bg); border: 1px solid var(--border2); color: var(--text3);
}
.tag.accent { background: var(--accent-d); border-color: #bfdbfe; color: var(--accent); }
.tag.green  { background: var(--green-d);  border-color: #a7f3d0; color: var(--green); }
.tag.red    { background: var(--red-d);    border-color: #fca5a5; color: var(--red); }
.tag.purple { background: var(--purple-d); border-color: #ddd6fe; color: var(--purple); }
.tag.teal   { background: var(--teal-d);   border-color: #a5f3fc; color: var(--teal); }
.tag.amber  { background: var(--amber-d);  border-color: #fcd34d; color: var(--amber); }
.tag.orange { background: var(--orange-d); border-color: #fdba74; color: var(--orange); }
.tag.pink   { background: var(--pink-d);   border-color: #f9a8d4; color: var(--pink); }

/* ── TABLES ── */
.table-wrap { overflow-x: auto; margin: 20px 0; border-radius: var(--r); box-shadow: var(--shadow); }
table { width: 100%; border-collapse: collapse; background: var(--surface); font-size: 13.5px; }
thead { background: var(--text); color: white; }
th { padding: 12px 16px; text-align: left; font-weight: 600; font-size: 12px; letter-spacing: 0.5px; text-transform: uppercase; }
td { padding: 11px 16px; border-bottom: 1px solid var(--border); color: var(--text2); vertical-align: top; }
td strong { color: var(--text); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--bg); }

/* ── PIPELINE DIAGRAM (SVG-like using CSS) ── */
.pipeline-diagram {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 28px; margin: 24px 0;
  box-shadow: var(--shadow-lg); overflow-x: auto;
}
.pipeline-row {
  display: flex; align-items: stretch; gap: 0;
  margin-bottom: 0;
}
.pipeline-row + .pipeline-row { margin-top: 0; }

.pipe-arrow {
  display: flex; align-items: center; justify-content: center;
  width: 32px; flex-shrink: 0;
  color: var(--text3); font-size: 14px;
}
.pipe-arrow.down {
  flex-direction: column; width: 100%; height: 28px;
  writing-mode: horizontal-tb;
  color: var(--text3);
}

.pipe-node {
  flex: 1; padding: 12px 16px; border-radius: 10px;
  border: 1px solid; text-align: center;
  min-width: 100px; position: relative;
}
.pipe-node-title { font-weight: 700; font-size: 13px; margin-bottom: 2px; }
.pipe-node-sub   { font-size: 11px; opacity: 0.8; }

.pipe-node.user   { background: #eff6ff; border-color: #bfdbfe; color: #1d4ed8; }
.pipe-node.router { background: #f0fdf4; border-color: #bbf7d0; color: #15803d; }
.pipe-node.pre    { background: #ecfeff; border-color: #a5f3fc; color: #0e7490; }
.pipe-node.agent  { background: #fdf4ff; border-color: #e9d5ff; color: #7e22ce; }
.pipe-node.fusion { background: #fffbeb; border-color: #fde68a; color: #92400e; }
.pipe-node.decide { background: #f8fafc; border-color: #cbd5e1; color: #334155; }
.pipe-node.out-allow  { background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }
.pipe-node.out-flag   { background: #fffbeb; border-color: #fcd34d; color: #92400e; }
.pipe-node.out-block  { background: #fef2f2; border-color: #fca5a5; color: #991b1b; }

.agent-committee {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
  margin: 8px 0;
}
.agent-box {
  padding: 10px 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg);
  text-align: center;
}
.agent-box .ab-icon { font-size: 18px; margin-bottom: 4px; }
.agent-box .ab-name { font-size: 11px; font-weight: 700; color: var(--text); }
.agent-box .ab-sub  { font-size: 10px; color: var(--text3); margin-top: 1px; }
.agent-box.active   { border-color: var(--purple); background: var(--purple-d); }

/* ── FLOW STEPS ── */
.flow-steps { display: flex; flex-direction: column; gap: 0; margin: 24px 0; }
.flow-step {
  display: flex; gap: 20px; position: relative;
  padding-bottom: 24px;
}
.flow-step:last-child { padding-bottom: 0; }
.flow-step:not(:last-child)::before {
  content: '';
  position: absolute; left: 19px; top: 40px; bottom: 0;
  width: 2px; background: var(--border2);
}
.flow-num {
  width: 38px; height: 38px; border-radius: 50%;
  background: var(--accent); color: white;
  font-family: var(--font-mono); font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; z-index: 1;
  box-shadow: 0 0 0 4px var(--accent-d);
}
.flow-content { flex: 1; padding-top: 4px; }
.flow-title { font-weight: 700; font-size: 15px; margin-bottom: 6px; color: var(--text); }
.flow-desc  { font-size: 13.5px; color: var(--text2); line-height: 1.6; }

/* ── WHY TABLE ── */
.why-grid { display: grid; gap: 12px; margin: 20px 0; }
.why-row {
  display: grid; grid-template-columns: 200px 1fr;
  gap: 0; border-radius: var(--r); overflow: hidden;
  border: 1px solid var(--border); box-shadow: var(--shadow);
}
.why-tool {
  padding: 16px 18px;
  font-family: var(--font-mono); font-size: 12px; font-weight: 600;
  display: flex; flex-direction: column; gap: 4px;
  border-right: 1px solid var(--border); background: var(--bg);
}
.why-tool .tool-name { color: var(--text); font-size: 13px; }
.why-tool .tool-layer { color: var(--text3); font-size: 10px; letter-spacing: 1px; text-transform: uppercase; }
.why-reason { padding: 16px 18px; background: var(--surface); font-size: 13.5px; color: var(--text2); }
.why-reason strong { color: var(--text); }

/* ── BADGE PILLS ── */
.badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  letter-spacing: 0.5px; text-transform: uppercase;
  padding: 3px 10px; border-radius: 100px;
}
.badge.green  { background: var(--green-d);  color: var(--green);  border: 1px solid #a7f3d0; }
.badge.amber  { background: var(--amber-d);  color: var(--amber);  border: 1px solid #fcd34d; }
.badge.red    { background: var(--red-d);    color: var(--red);    border: 1px solid #fca5a5; }
.badge.blue   { background: var(--accent-d); color: var(--accent); border: 1px solid #bfdbfe; }
.badge.purple { background: var(--purple-d); color: var(--purple); border: 1px solid #ddd6fe; }
.badge.teal   { background: var(--teal-d);   color: var(--teal);   border: 1px solid #a5f3fc; }

/* Weight bars */
.weight-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.weight-label { font-size: 13px; color: var(--text2); width: 140px; flex-shrink: 0; }
.weight-track { flex: 1; height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; }
.weight-fill  { height: 100%; border-radius: 4px; background: var(--accent); }
.weight-pct   { font-family: var(--font-mono); font-size: 12px; color: var(--text3); width: 36px; text-align: right; }

/* Divider */
hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }

/* Section anchor */
section { scroll-margin-top: 24px; }

/* ── RESPONSIVE ── */
@media (max-width: 900px) {
  .sidebar { display: none; }
  .main { padding: 32px 24px 60px; }
  h1 { font-size: 30px; }
  .agent-committee { grid-template-columns: repeat(2,1fr); }
  .why-row { grid-template-columns: 1fr; }
  .why-tool { border-right: none; border-bottom: 1px solid var(--border); }
}

/* Print */
@media print {
  .sidebar { display: none; }
  .main { padding: 0; max-width: 100%; }
}
</style>
</head>
<body>
<div class="wrapper">

<!-- SIDEBAR -->
<aside class="sidebar">
  <div class="sidebar-logo">
    <h2>Truth<span>Guard</span></h2>
    <div class="sidebar-badge">v4.0 · MENACRAFT</div>
  </div>

  <div class="toc-section">
    <div class="toc-group">Overview</div>
    <a class="toc-link" href="#overview">What is TruthGuard?</a>
    <a class="toc-link" href="#quickstart">Quick Start</a>
  </div>

  <div class="toc-section">
    <div class="toc-group">Architecture</div>
    <a class="toc-link" href="#architecture">System Architecture</a>
    <a class="toc-link sub" href="#router">Router (3 layers)</a>
    <a class="toc-link sub" href="#preprocessing">Preprocessing</a>
    <a class="toc-link sub" href="#agents">Agent Committee</a>
    <a class="toc-link sub" href="#fusion">Evidence Fusion</a>
    <a class="toc-link sub" href="#decision">Decision Engine</a>
  </div>

  <div class="toc-section">
    <div class="toc-group">Tools & Why</div>
    <a class="toc-link" href="#tools-image">Image Forensics</a>
    <a class="toc-link" href="#tools-video">Video Forensics</a>
    <a class="toc-link" href="#tools-text">Text & Claims</a>
    <a class="toc-link" href="#tools-infra">Infrastructure</a>
  </div>

  <div class="toc-section">
    <div class="toc-group">Agents</div>
    <a class="toc-link" href="#agent-details">All 8 Agents</a>
    <a class="toc-link sub" href="#agent-claim-extract">Claim Extractor</a>
    <a class="toc-link sub" href="#agent-claim-verify">Claim Verifier</a>
    <a class="toc-link sub" href="#agent-source">Source Credibility</a>
    <a class="toc-link sub" href="#agent-image">Image Forensics</a>
    <a class="toc-link sub" href="#agent-video">Video Forensics</a>
    <a class="toc-link sub" href="#agent-context">Context Agent</a>
    <a class="toc-link sub" href="#agent-network">Network Agent</a>
    <a class="toc-link sub" href="#agent-ling">Linguistic Agent</a>
  </div>

  <div class="toc-section">
    <div class="toc-group">Frontend</div>
    <a class="toc-link" href="#frontend">Wizard UI</a>
    <a class="toc-link" href="#dialogue">Dialogue System</a>
  </div>

  <div class="toc-section">
    <div class="toc-group">Reference</div>
    <a class="toc-link" href="#api">API Reference</a>
    <a class="toc-link" href="#install">Installation</a>
  </div>
</aside>

<!-- MAIN -->
<main class="main">

<!-- HERO -->
<div class="hero">
  <h1>Truth<span>Guard</span></h1>
  <p>A multi-agent AI pipeline for misinformation detection across all content types — images, videos, documents, URLs, and social posts. Built for the MENACRAFT hackathon.</p>
  <div class="hero-tags">
    <span class="hero-tag">FastAPI</span>
    <span class="hero-tag">Prefect</span>
    <span class="hero-tag">8 Parallel Agents</span>
    <span class="hero-tag">Bayesian Fusion</span>
    <span class="hero-tag">Python 3.11+</span>
    <span class="hero-tag">Pillow · OpenCV · Whisper</span>
  </div>
</div>

<!-- OVERVIEW -->
<section id="overview">
<h2>🔍 What is TruthGuard?</h2>

<p>TruthGuard is a <strong>dialogue-driven content verification platform</strong>. Unlike naive content moderation tools that simply scan an uploaded file, TruthGuard first asks the user <em>what</em> the content is and <em>what</em> they need to know. This user context drives the orchestrator to selectively activate only the agents that are relevant — avoiding wasted computation and false conclusions.</p>

<div class="callout info">
  <div class="callout-icon">💡</div>
  <div><strong>Core insight:</strong> A screenshot of a tweet is NOT "just an image." Its file type is <code>image/jpeg</code>, but its <em>semantic nature</em> requires text extraction via OCR, claim verification on the extracted text, source credibility check on the visible URL, and network analysis — in addition to image forensics. The system learns this from the user, not from the file header.</div>
</div>

<h3>Key Design Principles</h3>
<ul>
  <li><strong>User-declared content nature overrides naive file-type routing</strong> — the orchestrator builds its agent plan from user dialogue answers, not just MIME type.</li>
  <li><strong>Minimum sufficient agents</strong> — only the agents needed for the selected goals are activated. No default "run everything."</li>
  <li><strong>Full transparency</strong> — every activation decision is logged in plain English and returned in the audit trail.</li>
  <li><strong>Graceful degradation</strong> — every agent catches exceptions internally; the pipeline never crashes due to a single agent failure.</li>
  <li><strong>No mock data in production</strong> — all results are derived from real input. If text cannot be extracted, the system says so explicitly.</li>
</ul>
</section>

<!-- QUICKSTART -->
<section id="quickstart">
<h2>🚀 Quick Start</h2>

<pre><code># 1. Install dependencies
pip install fastapi uvicorn pillow pymupdf python-docx httpx pydantic
# For full forensics:
pip install opencv-python-headless openai-whisper

# 2. Start the preprocessing service (port 8000)
cd Preprocessing
uvicorn main:app --reload --port 8000

# 3. Start the orchestrator API (port 8001)
uvicorn orchestrator_api:app --reload --port 8001

# 4. Open the frontend
# Open truthguard-v3.html in any browser</code></pre>

<div class="callout success">
  <div class="callout-icon">✅</div>
  <div><strong>The frontend works without a running API.</strong> If <code>localhost:8001</code> is unreachable, the wizard falls back to a deterministic local plan computation and demo result rendering — so you can always demo the UX flow.</div>
</div>
</section>

<!-- ARCHITECTURE -->
<section id="architecture">
<h2>🏗️ System Architecture</h2>

<p>The system is composed of four major layers executed in sequence, with the agent committee running in parallel within layer 3.</p>

<!-- Main pipeline diagram -->
<div class="pipeline-diagram">
  <div style="text-align:center;margin-bottom:20px;">
    <span style="font-family:var(--font-mono);font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--text3);">Full Pipeline · Input to Decision</span>
  </div>

  <!-- User Input -->
  <div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="pipe-node user" style="max-width:360px;width:100%;">
      <div class="pipe-node-title">👤 User Input + Dialogue</div>
      <div class="pipe-node-sub">File · URL · Text &nbsp;+&nbsp; Content nature declaration · Analysis goals</div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Router -->
  <div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="pipe-node router" style="max-width:360px;width:100%;">
      <div class="pipe-node-title">🔀 Input Router · 3 Layers</div>
      <div class="pipe-node-sub">Layer 1: Magic bytes · Layer 2: Content sniff · Layer 3: Pipeline scoring</div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Orchestrator Plan -->
  <div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="pipe-node pre" style="max-width:360px;width:100%;">
      <div class="pipe-node-title">🧮 Orchestrator Agent Plan</div>
      <div class="pipe-node-sub">Maps user dialogue → agent activation plan · logs reasons</div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Preprocessing -->
  <div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="pipe-node pre" style="max-width:360px;width:100%;">
      <div class="pipe-node-title">⚙️ Preprocessing Layer</div>
      <div class="pipe-node-sub">OCR · EXIF · ASR · Metadata · Layout parsing → NormalizedFeatureObject</div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Agent Committee -->
  <div style="background:var(--purple-d);border:1px solid #ddd6fe;border-radius:12px;padding:16px;margin-bottom:8px;">
    <div style="text-align:center;font-size:11px;font-family:var(--font-mono);letter-spacing:1px;text-transform:uppercase;color:var(--purple);margin-bottom:12px;">🤖 Agent Committee · Parallel Execution (Prefect ConcurrentTaskRunner)</div>
    <div class="agent-committee">
      <div class="agent-box active"><div class="ab-icon">📋</div><div class="ab-name">Claim Extract</div><div class="ab-sub">w=0.00</div></div>
      <div class="agent-box active"><div class="ab-icon">✅</div><div class="ab-name">Claim Verify</div><div class="ab-sub">w=0.22</div></div>
      <div class="agent-box active"><div class="ab-icon">🏛️</div><div class="ab-name">Source Cred</div><div class="ab-sub">w=0.18</div></div>
      <div class="agent-box active"><div class="ab-icon">🔬</div><div class="ab-name">Image Forensics</div><div class="ab-sub">w=0.14</div></div>
      <div class="agent-box active"><div class="ab-icon">🎬</div><div class="ab-name">Video Forensics</div><div class="ab-sub">w=0.14</div></div>
      <div class="agent-box active"><div class="ab-icon">🔄</div><div class="ab-name">Context Agent</div><div class="ab-sub">w=0.12</div></div>
      <div class="agent-box active"><div class="ab-icon">🕸️</div><div class="ab-name">Network Agent</div><div class="ab-sub">w=0.10</div></div>
      <div class="agent-box active"><div class="ab-icon">🧠</div><div class="ab-name">Linguistic</div><div class="ab-sub">w=0.10</div></div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Fusion -->
  <div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="pipe-node fusion" style="max-width:360px;width:100%;">
      <div class="pipe-node-title">⚖️ Evidence Fusion</div>
      <div class="pipe-node-sub">Weighted ensemble + Bayesian inference + meta-model blend</div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Decision -->
  <div style="display:flex;justify-content:center;margin-bottom:8px;">
    <div class="pipe-node decide" style="max-width:360px;width:100%;">
      <div class="pipe-node-title">🎯 Decision Engine</div>
      <div class="pipe-node-sub">Risk band → action · requires_human_review → audit trail</div>
    </div>
  </div>
  <div style="text-align:center;color:var(--text3);font-size:18px;margin:4px 0;">↓</div>

  <!-- Outputs -->
  <div style="display:flex;gap:10px;justify-content:center;">
    <div class="pipe-node out-allow" style="flex:1;max-width:160px;"><div class="pipe-node-title">✅ Auto-Allow</div></div>
    <div class="pipe-node out-flag"  style="flex:1;max-width:160px;"><div class="pipe-node-title">🚩 Flag Review</div></div>
    <div class="pipe-node out-block" style="flex:1;max-width:160px;"><div class="pipe-node-title">🛑 Auto-Block</div></div>
  </div>
</div>

<!-- ROUTER -->
<section id="router">
<h3>🔀 Input Router — 3 Layers</h3>
<p>The router runs before any agent. It performs three passes on the raw input to compute a <strong>pipeline activation score (0–1)</strong> for each of the four processing pipelines (VISION, TEXT, VIDEO, URL). Any pipeline scoring ≥ 0.35 is activated.</p>

<div class="flow-steps">
  <div class="flow-step">
    <div class="flow-num">L1</div>
    <div class="flow-content">
      <div class="flow-title">Magic Bytes Detection <code>layer1magic.py</code></div>
      <div class="flow-desc">Reads the raw binary header of the file to identify its true MIME type — independent of filename or extension. A <code>.jpg</code> renamed to <code>.txt</code> is still detected as an image. This prevents file-type spoofing. Uses Python's <code>python-magic</code> library which wraps <code>libmagic</code>.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">L2</div>
    <div class="flow-content">
      <div class="flow-title">Content Sniffing <code>layer2sniff.py</code></div>
      <div class="flow-desc">For files where the MIME type is ambiguous (e.g. <code>text/plain</code>), the content sniffer inspects the text body to determine whether it's a URL, HTML page, JSON data, or human-written prose. Also detects social media URLs (Twitter, Facebook, Telegram) which trigger the URL credibility pipeline.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">L3</div>
    <div class="flow-content">
      <div class="flow-title">Pipeline Scoring Classifier <code>layer3classifier.py</code></div>
      <div class="flow-desc">A rule-based scorer that takes all signals from L1 and L2 and outputs a score per pipeline. Rules are additive — a screenshot of a tweet from Twitter scores high on both VISION (it's an image) and URL (it originates from a social platform). Threshold: <code>0.35</code>. Multiple pipelines can activate simultaneously.</div>
    </div>
  </div>
</div>

<div class="callout warn">
  <div class="callout-icon">⚠️</div>
  <div>The router's output is <em>supplemented</em> by the orchestrator's user-dialogue plan. If the router classifies a screenshot as VISION only, but the user declares it as <code>social_post_screenshot</code>, the orchestrator <em>adds</em> TEXT, URL, and NETWORK pipelines on top — it never removes what the router activated.</div>
</div>
</section>

<!-- PREPROCESSING -->
<section id="preprocessing">
<h3>⚙️ Preprocessing Layer</h3>
<p>Every input goes through a content-type-specific preprocessing pipeline before reaching the agents. The output is always a <strong><code>NormalizedFeatureObject</code></strong> — a unified data structure consumed by all agents regardless of input type.</p>

<div class="table-wrap">
<table>
  <thead><tr><th>Content Type</th><th>Preprocessing Steps</th><th>Key Libraries</th></tr></thead>
  <tbody>
    <tr>
      <td><strong>Image</strong></td>
      <td>OCR text extraction · EXIF metadata · ELA compression analysis · FFT spectral analysis · UI/screenshot detection</td>
      <td><code>Pillow</code> · <code>pytesseract</code> · <code>numpy</code></td>
    </tr>
    <tr>
      <td><strong>Video</strong></td>
      <td>Keyframe sampling · sharpness variance · luminosity flicker · face-edge anomaly detection · FFT on face patches · metadata extraction · audio transcription (stub → Whisper)</td>
      <td><code>OpenCV</code> · <code>numpy</code> · <code>openai-whisper</code></td>
    </tr>
    <tr>
      <td><strong>Document</strong></td>
      <td>Text extraction (PDF / DOCX / TXT) · heading and table layout parsing · author metadata · edit history</td>
      <td><code>PyMuPDF</code> · <code>pdfplumber</code> · <code>python-docx</code></td>
    </tr>
    <tr>
      <td><strong>URL</strong></td>
      <td>Page scraping · meta tag extraction · WHOIS domain query · social platform fingerprinting</td>
      <td><code>httpx</code> · <code>beautifulsoup4</code> · <code>python-whois</code></td>
    </tr>
  </tbody>
</table>
</div>
</section>

<!-- AGENTS -->
<section id="agents">
<h3>🤖 Agent Committee</h3>
<p>After preprocessing, the orchestrator submits tasks to Prefect's <code>ConcurrentTaskRunner</code>. All activated agents run <strong>in parallel</strong>, each receiving the same <code>NormalizedFeatureObject</code>. This means a 3-agent activation takes the same time as running 3 agents simultaneously — not 3× longer.</p>

<h4>Agent Weights in Evidence Fusion</h4>
<p>Each agent's risk score is multiplied by its weight and confidence before being blended into the final verdict. These weights reflect how reliable each signal is in the MENACRAFT threat model:</p>

<div class="card" style="margin:16px 0;">
  <div class="weight-bar"><div class="weight-label">Claim Verifier</div><div class="weight-track"><div class="weight-fill" style="width:100%;background:#2563eb;"></div></div><div class="weight-pct">22%</div></div>
  <div class="weight-bar"><div class="weight-label">Source Credibility</div><div class="weight-track"><div class="weight-fill" style="width:81.8%;background:#059669;"></div></div><div class="weight-pct">18%</div></div>
  <div class="weight-bar"><div class="weight-label">Image Forensics</div><div class="weight-track"><div class="weight-fill" style="width:63.6%;background:#7c3aed;"></div></div><div class="weight-pct">14%</div></div>
  <div class="weight-bar"><div class="weight-label">Video Forensics</div><div class="weight-track"><div class="weight-fill" style="width:63.6%;background:#7c3aed;"></div></div><div class="weight-pct">14%</div></div>
  <div class="weight-bar"><div class="weight-label">Context Agent</div><div class="weight-track"><div class="weight-fill" style="width:54.5%;background:#0891b2;"></div></div><div class="weight-pct">12%</div></div>
  <div class="weight-bar"><div class="weight-label">Linguistic Agent</div><div class="weight-track"><div class="weight-fill" style="width:45.5%;background:#d97706;"></div></div><div class="weight-pct">10%</div></div>
  <div class="weight-bar"><div class="weight-label">Network Agent</div><div class="weight-track"><div class="weight-fill" style="width:45.5%;background:#d97706;"></div></div><div class="weight-pct">10%</div></div>
  <div class="weight-bar" style="margin-bottom:0;"><div class="weight-label">Claim Extractor</div><div class="weight-track"><div class="weight-fill" style="width:0%;"></div></div><div class="weight-pct">0% *</div></div>
  <p style="font-size:11px;color:var(--text3);margin-top:8px;margin-bottom:0;">* Claim Extractor is informational only — its output feeds the Claim Verifier and Context Agent but does not directly contribute to the risk score.</p>
</div>
</section>

<!-- FUSION -->
<section id="fusion">
<h3>⚖️ Evidence Fusion — 3 Stages</h3>

<div class="flow-steps">
  <div class="flow-step">
    <div class="flow-num">S1</div>
    <div class="flow-content">
      <div class="flow-title">Weighted Ensemble</div>
      <div class="flow-desc">Each active agent's risk score is multiplied by its weight × confidence. Agents with confidence = 0 (i.e., not applicable for this content type) are excluded. The result is a weighted average risk score from <strong>0.0 to 1.0</strong>.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">S2</div>
    <div class="flow-content">
      <div class="flow-title">Bayesian Update</div>
      <div class="flow-desc">Starting from a neutral prior (log-odds = 0), each agent signal updates the log-odds in proportion to its evidence strength. This ensures that <em>multiple weak signals compound</em> — five small red flags together produce a higher risk than one large flag alone.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">S3</div>
    <div class="flow-content">
      <div class="flow-title">Meta-Model Blend (α = 0.60)</div>
      <div class="flow-desc">The final risk score is <code>α × ensemble_score + (1-α) × bayesian_score</code>. The blend weight α defaults to 0.60 — favouring the ensemble when signals agree, and the Bayesian estimate when they conflict. <code>meta_confidence</code> reflects reliability of the final estimate.</div>
    </div>
  </div>
</div>
</section>

<!-- DECISION -->
<section id="decision">
<h3>🎯 Decision Engine</h3>

<div class="table-wrap">
<table>
  <thead><tr><th>Risk Score</th><th>Band</th><th>Action</th><th>Human Review?</th><th>Meaning</th></tr></thead>
  <tbody>
    <tr><td><code>0.00 – 0.24</code></td><td><span class="badge green">GREEN</span></td><td>auto-allow</td><td>No</td><td>No significant disinformation signals found.</td></tr>
    <tr><td><code>0.25 – 0.49</code></td><td><span class="badge amber">AMBER</span></td><td>flag-review</td><td><strong>Yes</strong></td><td>Mixed signals — human reviewer should assess.</td></tr>
    <tr><td><code>0.50 – 0.74</code></td><td><span class="badge amber" style="background:#fff7ed;border-color:#fdba74;color:#ea580c;">ORANGE</span></td><td>flag-review</td><td><strong>Yes</strong></td><td>Multiple disinformation signals. Likely misleading.</td></tr>
    <tr><td><code>0.75 – 1.00</code></td><td><span class="badge red">RED</span></td><td>auto-block</td><td>No</td><td>Strong fabrication/deepfake/coordinated disinfo evidence.</td></tr>
  </tbody>
</table>
</div>
</section>
</section>

<hr>

<!-- TOOLS & WHY -->
<section id="tools-image">
<h2>🔧 Tools & Why We Chose Them</h2>

<h3>📸 Image Forensics Tools</h3>

<div class="why-grid">
  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">Pillow (PIL)</div>
      <div class="tool-layer">Core Image Library</div>
    </div>
    <div class="why-reason">
      <strong>Why Pillow?</strong> It is the most mature Python imaging library with zero native dependencies. We use it for ELA (re-compression at JPEG quality 92 to expose manipulation), EXIF extraction via <code>img._getexif()</code>, pixel-level diffing via <code>ImageChops.difference()</code>, and colour space conversion. It handles all formats we accept (JPEG, PNG, WebP, BMP, TIFF, GIF). <strong>Not chosen:</strong> OpenCV would add 50MB of binary dependencies for tasks Pillow handles natively.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">NumPy</div>
      <div class="tool-layer">Spectral Analysis</div>
    </div>
    <div class="why-reason">
      <strong>Why NumPy for FFT?</strong> GAN-generated and diffusion-generated images show anomalous periodicity in their frequency domain due to convolutional upsampling artifacts. <code>np.fft.fft2</code> + <code>np.fft.fftshift</code> exposes these as low-variance spectral signatures below our threshold of <code>48.0</code>. NumPy is already a transitive dependency of Pillow/OpenCV, so there is no additional cost.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">ExifTags (Pillow)</div>
      <div class="tool-layer">Metadata Forensics</div>
    </div>
    <div class="why-reason">
      <strong>Why not piexif?</strong> <code>piexif</code> is not in the project's <code>requirements.txt</code>. We use Pillow's built-in <code>ExifTags.TAGS</code> dictionary to decode all EXIF tag IDs to human-readable names without an additional dependency. We detect editing software (Photoshop, GIMP, Lightroom, Affinity, Snapseed), missing camera make/model, and timestamp mismatches with the declared submission date.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">pytesseract</div>
      <div class="tool-layer">OCR (optional)</div>
    </div>
    <div class="why-reason">
      <strong>Why optional OCR?</strong> For screenshots and memes, the critical content is the <em>text in the image</em> — not the pixel data. <code>pytesseract</code> wraps Tesseract 5 which supports Arabic, French, and English (crucial for MENA content). It's marked optional (<code>try/import</code>) so the pipeline degrades gracefully on machines without Tesseract installed, falling back to a structured image description that the LLM can still work with.
    </div>
  </div>
</div>
</section>

<section id="tools-video">
<h3>🎬 Video Forensics Tools</h3>

<div class="why-grid">
  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">OpenCV (cv2)</div>
      <div class="tool-layer">Frame Analysis</div>
    </div>
    <div class="why-reason">
      <strong>Why OpenCV?</strong> OpenCV's <code>VideoCapture</code> is the industry standard for decoding video frames without FFmpeg's complex CLI. We use it for uniform frame sampling (<code>np.linspace</code> indices), Laplacian sharpness variance computation (<code>cv2.Laplacian</code>), and Haar cascade face detection for face-region anomaly analysis. <code>opencv-python-headless</code> is used (no GUI dependencies) to minimise container size.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">Haar Cascade (OpenCV)</div>
      <div class="tool-layer">Face Detection</div>
    </div>
    <div class="why-reason">
      <strong>Why Haar and not a CNN?</strong> The project is dependency-constrained. Haar cascades ship bundled with OpenCV (<code>cv2.data.haarcascades</code>) — zero additional downloads. They're fast enough for our use case (16 frames sampled per video). The code includes a <strong>TODO stub</strong> for FaceForensics++ PyTorch integration: a trained CNN classifier for deepfake detection. When resources allow, swap the heuristic face-edge analysis for the trained model.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">openai-whisper</div>
      <div class="tool-layer">Audio Transcription (ASR)</div>
    </div>
    <div class="why-reason">
      <strong>Why Whisper?</strong> Whisper supports Arabic natively — critical for MENA content. It runs locally (no API calls, no data leaving the server), produces word-level timestamps useful for audio-visual sync checking, and is the most accurate open-source ASR model for multilingual content. Currently a stub in the video processor (the integration point is clearly marked with a comment) — the architecture is ready to plug in Whisper or faster-whisper without changing the agent interface.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">tempfile (stdlib)</div>
      <div class="tool-layer">Video I/O Safety</div>
    </div>
    <div class="why-reason">
      <strong>Why tempfile for video?</strong> OpenCV's <code>VideoCapture</code> requires a file path — it cannot read from a <code>bytes</code> buffer. We write to a secure temporary file using <code>tempfile.NamedTemporaryFile(delete=False)</code>, then guarantee cleanup in a <code>finally</code> block even if an exception occurs. The suffix is preserved from the original filename to ensure OpenCV's codec auto-detection works correctly.
    </div>
  </div>
</div>
</section>

<section id="tools-text">
<h3>📄 Text, Claims & Documents</h3>

<div class="why-grid">
  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">PyMuPDF (fitz)</div>
      <div class="tool-layer">PDF Extraction · Primary</div>
    </div>
    <div class="why-reason">
      <strong>Why PyMuPDF as primary?</strong> It is the fastest Python PDF library, preserves layout structure, and correctly handles Arabic right-to-left text. <code>page.get_text()</code> returns plain text per page while <code>page.get_images()</code> extracts embedded images for optional OCR. <strong>Fallback:</strong> <code>pdfplumber</code> is included as a secondary extractor for PDFs where PyMuPDF fails to extract structured text (common with certain encoding schemes).
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">python-docx</div>
      <div class="tool-layer">DOCX Extraction</div>
    </div>
    <div class="why-reason">
      <strong>Why python-docx?</strong> DOCX files contain rich metadata: author, revision history, tracked changes, and comment threads — all disinformation-relevant signals. <code>python-docx</code> exposes these programmatically. For the hackathon, we use a fallback DOCX reader (unzip + regex on the XML) that has zero additional dependencies, with <code>python-docx</code> as the upgrade path for production.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">httpx</div>
      <div class="tool-layer">URL Scraping · Async</div>
    </div>
    <div class="why-reason">
      <strong>Why httpx over requests?</strong> The entire orchestrator is async (Prefect + FastAPI). <code>httpx</code> is the async-native HTTP client — it supports <code>async with httpx.AsyncClient()</code> which integrates cleanly with <code>await</code>. Using <code>requests</code> in an async context would block the event loop. <code>httpx</code> also supports HTTP/2 and has a <code>timeout</code> parameter we use to prevent agent hangs on slow pages.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">sentence-transformers</div>
      <div class="tool-layer">RAG Embeddings</div>
    </div>
    <div class="why-reason">
      <strong>Why sentence-transformers for RAG?</strong> The Claim Verifier uses <code>all-MiniLM-L6-v2</code> to embed both the extracted claim and the knowledge-base chunks into the same 384-dimensional vector space. Cosine similarity then identifies supporting or contradicting evidence. MiniLM is chosen for its balance: fast enough to embed 20 claims in under a second on CPU, while maintaining semantic accuracy sufficient for fact-checking purposes.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">ChromaDB</div>
      <div class="tool-layer">Vector Store</div>
    </div>
    <div class="why-reason">
      <strong>Why ChromaDB?</strong> It is the simplest production-ready vector database with a Python-native API and no external server process. <code>chromadb.PersistentClient</code> stores vectors on disk in <code>./chroma_db/</code>. The project ships a pre-built <code>chroma.sqlite3</code> with an initial fact corpus. For production, swap to a hosted Chroma, Pinecone, or Weaviate instance without changing the <code>VectorStore</code> interface.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">Groq LLM API</div>
      <div class="tool-layer">Claim Extraction · NLI</div>
    </div>
    <div class="why-reason">
      <strong>Why Groq?</strong> Groq's inference hardware delivers LLaMA-3.3-70B at ~500 tokens/second — fast enough for real-time claim extraction within a request timeout. We use it for two tasks: (1) structured claim extraction from any text surface via a strict JSON schema prompt, and (2) NLI (Natural Language Inference) to determine whether retrieved knowledge-base chunks SUPPORT, CONTRADICT, or are INSUFFICIENT for each claim. The project also supports Anthropic Claude and Ollama as drop-in alternatives.
    </div>
  </div>
</div>
</section>

<section id="tools-infra">
<h3>🏗️ Infrastructure & Framework</h3>

<div class="why-grid">
  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">FastAPI</div>
      <div class="tool-layer">API Layer</div>
    </div>
    <div class="why-reason">
      <strong>Why FastAPI?</strong> FastAPI is async-native (built on Starlette + Uvicorn), which matches our <code>async/await</code> agent architecture. It generates OpenAPI documentation automatically (<code>/docs</code>), validates all request/response models via Pydantic, and has built-in <code>UploadFile</code> support for multipart form data — exactly what our file upload endpoints need. Performance benchmarks show it handles 10–100× more requests/sec than Flask for I/O-bound workloads like ours.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">Prefect</div>
      <div class="tool-layer">Orchestration</div>
    </div>
    <div class="why-reason">
      <strong>Why Prefect?</strong> Prefect's <code>@flow</code> and <code>@task</code> decorators give us automatic retry logic (<code>retries=2, retry_delay_seconds=5</code>), structured logging via <code>get_run_logger()</code>, and — critically — <code>ConcurrentTaskRunner</code> which runs all agent tasks truly in parallel using Python's <code>asyncio</code> event loop. Without Prefect, we'd need to write manual <code>asyncio.gather()</code> boilerplate and our own retry/logging infrastructure.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">Pydantic v2</div>
      <div class="tool-layer">Data Validation</div>
    </div>
    <div class="why-reason">
      <strong>Why Pydantic?</strong> <code>NormalizedFeatureObject</code> is the contract between preprocessing and agents. Pydantic enforces that every agent receives a correctly typed object — preventing the class of bugs where an agent crashes because a field is <code>None</code> when it expected a string. Pydantic v2 (Rust-based) is 5–50× faster than v1 at validation, which matters since we validate the NFO once per pipeline run.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">python-whois</div>
      <div class="tool-layer">Source Credibility</div>
    </div>
    <div class="why-reason">
      <strong>Why WHOIS?</strong> Domain age is one of the strongest signals for source credibility. Fake news sites are typically registered within days or weeks of a disinformation campaign. WHOIS data reveals: registration date, registrar, registrant country, and name servers. Domains registered in high-risk jurisdictions or using privacy shields where real outlets do not are flagged. <code>python-whois</code> is the most complete Python WHOIS parser with support for hundreds of TLD-specific response formats.
    </div>
  </div>

  <div class="why-row">
    <div class="why-tool">
      <div class="tool-name">beautifulsoup4</div>
      <div class="tool-layer">URL Scraping</div>
    </div>
    <div class="why-reason">
      <strong>Why BeautifulSoup?</strong> For URL inputs, we scrape the page and extract: <code>&lt;title&gt;</code>, <code>&lt;meta name="description"&gt;</code>, Open Graph tags (<code>og:title</code>, <code>og:image</code>), canonical URL, and the main article body text. BeautifulSoup handles malformed HTML gracefully — critical because many disinformation sites have broken markup. The extracted text then feeds the Claim Extractor.
    </div>
  </div>
</div>
</section>

<hr>

<!-- AGENT DETAILS -->
<section id="agent-details">
<h2>🤖 All 8 Agents — Detailed</h2>

<section id="agent-claim-extract">
<h3>📋 1. Claim Extractor <span class="badge blue">w = 0.00</span></h3>
<p>Extracts structured factual claims from any text surface. It runs first because its output (<code>ClaimExtractionResult</code>) is consumed by both the Claim Verifier and the Context Agent in the subsequent parallel step.</p>

<div class="card-grid">
  <div class="card-sm" style="--c:var(--accent);">
    <div class="card-sm-icon">🔤</div>
    <div class="card-sm-title">Text Selection Logic</div>
    <div class="card-sm-desc">Automatically picks the richest text surface: OCR text for images, page body for URLs, raw transcript for video, document body for PDFs. Falls back through each option gracefully.</div>
    <div class="card-sm-tags"><span class="tag accent">select_richest_text()</span></div>
  </div>
  <div class="card-sm" style="--c:var(--purple);">
    <div class="card-sm-icon">🤖</div>
    <div class="card-sm-title">Multi-Provider LLM</div>
    <div class="card-sm-desc">Supports Anthropic Claude, OpenAI-compatible endpoints (Groq, Ollama, vLLM), and a regex-based heuristic fallback. Each claim gets type, verifiability, entities, and red flags.</div>
    <div class="card-sm-tags"><span class="tag purple">llm → heuristic fallback</span></div>
  </div>
  <div class="card-sm" style="--c:var(--red);">
    <div class="card-sm-icon">🚩</div>
    <div class="card-sm-title">Red Flag Vocabulary</div>
    <div class="card-sm-desc">Seven standardised flag types: <code>absolute_language</code>, <code>urgency_trigger</code>, <code>appeal_to_fear</code>, <code>unverified_attribution</code>, <code>emotional_amplifier</code>, <code>vague_quantifier</code>, <code>conspiracy_framing</code>.</div>
    <div class="card-sm-tags"><span class="tag red">7 flag types</span></div>
  </div>
</div>
<p><strong>Why weight = 0?</strong> The Claim Extractor is purely informational — it extracts claims but makes no judgement about their truth. Assigning it a non-zero weight would punish documents that simply <em>contain</em> many claims, regardless of whether those claims are true or false. Its output flows into the Claim Verifier (w=0.22) which makes the actual truth judgement.</p>
</section>

<section id="agent-claim-verify">
<h3>✅ 2. Claim Verifier (RAG) <span class="badge blue">w = 0.22 — Highest</span></h3>
<p>The highest-weighted agent. Uses Retrieval-Augmented Generation (RAG) to cross-reference each extracted claim against a fact corpus stored in ChromaDB.</p>

<div class="flow-steps">
  <div class="flow-step">
    <div class="flow-num">①</div>
    <div class="flow-content">
      <div class="flow-title">Embed the claim</div>
      <div class="flow-desc">The claim text is encoded with <code>all-MiniLM-L6-v2</code> into a 384-dimensional vector. This captures semantic meaning, not just keyword overlap.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">②</div>
    <div class="flow-content">
      <div class="flow-title">Retrieve top-k evidence chunks</div>
      <div class="flow-desc">ChromaDB performs cosine similarity search and returns the 5 most similar knowledge-base chunks (articles, fact-checks, Wikipedia entries).</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">③</div>
    <div class="flow-content">
      <div class="flow-title">NLI verdict via LLM</div>
      <div class="flow-desc">A structured prompt asks the LLM: given this CLAIM and these EVIDENCE passages, is the claim SUPPORTED, CONTRADICTED, or INSUFFICIENT? Returns a confidence score and one-sentence explanation.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">④</div>
    <div class="flow-content">
      <div class="flow-title">Aggregate across all claims</div>
      <div class="flow-desc"><code>overall_support_score</code> and <code>overall_contradiction_score</code> are computed as confidence-weighted averages across all verified claims.</div>
    </div>
  </div>
</div>

<p><strong>Verifiability thresholds:</strong> HIGH verifiability claims require a similarity score > 0.65 to be marked SUPPORTED; LOW verifiability claims require 0.85 — because vague claims can spuriously match many documents.</p>
</section>

<section id="agent-source">
<h3>🏛️ 3. Source Credibility Agent <span class="badge green">w = 0.18</span></h3>
<p>Evaluates the trustworthiness of where the content came from. Operates on the domain/platform rather than the content itself.</p>

<div class="table-wrap">
<table>
  <thead><tr><th>Signal</th><th>How Evaluated</th><th>Risk Impact</th></tr></thead>
  <tbody>
    <tr><td><strong>Domain age</strong></td><td>WHOIS <code>creation_date</code> → days since registration</td><td>< 30 days → high risk</td></tr>
    <tr><td><strong>Known fake-news</strong></td><td>String match against curated registry (infowars, naturalnews, etc.)</td><td>Score → 0.05</td></tr>
    <tr><td><strong>Known satire</strong></td><td>String match against satire site list (The Onion, BabylonBee, etc.)</td><td>Score → 0.20, flag shown</td></tr>
    <tr><td><strong>Trusted outlet</strong></td><td>Match against reuters, apnews, bbc, aljazeera, etc.</td><td>Score → 0.90</td></tr>
    <tr><td><strong>Domain spoofing</strong></td><td>Checks if a trusted outlet's name appears mid-domain (e.g. <code>bbc-news.xyz</code>)</td><td>Score → 0.10</td></tr>
    <tr><td><strong>Suspicious TLD</strong></td><td>.tk, .ml, .ga, .cf, .gq, .xyz, .top, .click</td><td>Score → 0.25</td></tr>
    <tr><td><strong>HTTPS</strong></td><td>URL prefix check</td><td>No HTTPS → cap score at 0.45</td></tr>
    <tr><td><strong>Platform</strong></td><td>Known platform scores: Twitter 0.55, Telegram 0.35, WhatsApp 0.30</td><td>Closed channels flagged</td></tr>
  </tbody>
</table>
</div>
</section>

<section id="agent-image">
<h3>🔬 4. Image Forensics Agent <span class="badge purple">w = 0.14</span></h3>
<p>Five independent detectors run on every image. Each can independently set the anomaly flag.</p>

<div class="card-grid">
  <div class="card-sm" style="--c:#7c3aed;">
    <div class="card-sm-icon">📊</div>
    <div class="card-sm-title">ELA — Error Level Analysis</div>
    <div class="card-sm-desc">Re-compresses at quality 92 and measures per-pixel difference. Pasted or cloned regions have been compressed a different number of times, creating anomalous high-frequency residuals above the 28-unit threshold.</div>
    <div class="card-sm-tags"><span class="tag purple">Pillow · ImageChops</span></div>
  </div>
  <div class="card-sm" style="--c:#7c3aed;">
    <div class="card-sm-icon">🏷️</div>
    <div class="card-sm-title">EXIF Forensics</div>
    <div class="card-sm-desc">Detects missing EXIF (stripped by editors/re-uploaders), editing software tags (Photoshop, GIMP, Snapseed), missing camera make/model, and timestamp mismatches with claimed submission date.</div>
    <div class="card-sm-tags"><span class="tag purple">Pillow · ExifTags</span></div>
  </div>
  <div class="card-sm" style="--c:#7c3aed;">
    <div class="card-sm-icon">〰️</div>
    <div class="card-sm-title">FFT Spectral Analysis</div>
    <div class="card-sm-desc">GAN and diffusion model outputs show low spectral variance (< 48.0) in the FFT magnitude spectrum due to convolutional upsampling grids. Real camera photos show higher variance from natural scene frequencies.</div>
    <div class="card-sm-tags"><span class="tag purple">NumPy · fft2</span></div>
  </div>
  <div class="card-sm" style="--c:#7c3aed;">
    <div class="card-sm-icon">🖥️</div>
    <div class="card-sm-title">UI / Screenshot Detection</div>
    <div class="card-sm-desc">Screenshots and memes have reduced colour palettes (< 64 unique colours in a subsample), uniform horizontal borders, and unusual aspect ratios. These trigger the OCR + claims pipeline.</div>
    <div class="card-sm-tags"><span class="tag purple">NumPy · heuristic</span></div>
  </div>
  <div class="card-sm" style="--c:#7c3aed;">
    <div class="card-sm-icon">🔤</div>
    <div class="card-sm-title">OCR Text Extraction</div>
    <div class="card-sm-desc">Extracts embedded text for downstream claim extraction. Supports Arabic, French, and English via Tesseract. Optional — degrades gracefully without pytesseract installed.</div>
    <div class="card-sm-tags"><span class="tag purple">pytesseract · optional</span></div>
  </div>
</div>
</section>

<section id="agent-video">
<h3>🎬 5. Video Forensics Agent <span class="badge purple">w = 0.14</span></h3>

<div class="table-wrap">
<table>
  <thead><tr><th>Detector</th><th>What it Finds</th><th>Method</th></tr></thead>
  <tbody>
    <tr><td><strong>Sharpness Variance</strong></td><td>Inserted synthetic frames create sharp discontinuities in per-frame Laplacian variance</td><td><code>cv2.Laplacian</code></td></tr>
    <tr><td><strong>Temporal Flicker</strong></td><td>Luminosity jumps > 25 units between consecutive frames — GAN frames aren't generated frame-by-frame</td><td>Per-frame mean luminosity delta</td></tr>
    <tr><td><strong>Face-Edge Anomaly</strong></td><td>Face-swap boundaries produce elevated Canny edge ratios (> 0.18) in ROI margin zones</td><td>Haar cascade + <code>cv2.Canny</code></td></tr>
    <tr><td><strong>FFT on Face Patches</strong></td><td>GAN face regions show low spectral variance (< 45.0) from convolutional upsampling artifacts</td><td><code>np.fft.fft2</code> on 128×128 face crop</td></tr>
    <tr><td><strong>Metadata Forensics</strong></td><td>Non-standard FPS (re-encoded deepfakes change codec/FPS), null resolution, negative frame count</td><td><code>cv2.VideoCapture</code> properties</td></tr>
  </tbody>
</table>
</div>
</section>

<section id="agent-context">
<h3>🔄 6. Context Agent <span class="badge teal">w = 0.12</span></h3>
<p>Checks whether the claims extracted are <em>contextually coherent</em> — not just whether they're factually true. Uses Wikidata for knowledge-graph cross-referencing and temporal reasoning.</p>

<ul>
  <li><strong>Temporal coherence:</strong> Checks if claimed dates/events align with known timelines (e.g., "image from 2019 being used to represent a 2024 event").</li>
  <li><strong>Mixed tense detection:</strong> Content combining definitive past-event language ("confirmed", "revealed") with future predictions ("will happen", "soon") is flagged — a common disinformation pattern.</li>
  <li><strong>Contradictory term pairs:</strong> Co-occurrence of <code>always/never</code>, <code>confirmed/allegedly</code>, <code>fact/rumor</code> within the same text signals internal inconsistency.</li>
  <li><strong>Wikidata lookup:</strong> Named entities are searched via the Wikidata API to find known facts that support or contradict each claim.</li>
</ul>
</section>

<section id="agent-network">
<h3>🕸️ 7. Network Agent <span class="badge amber">w = 0.10</span></h3>
<p>Analyses distribution and propagation signals rather than the content itself. Detects <strong>coordinated inauthentic behaviour</strong>.</p>

<ul>
  <li><strong>Bot probability score</strong> (0–1): Computed from URL/domain graph features, templated phrasing repetition ratios, user-agent-style signals in metadata, and share count anomalies.</li>
  <li><strong>Suspicious TLD detection:</strong> Pre-compiled set of 20+ TLDs commonly used in spam/phishing campaigns.</li>
  <li><strong>Propagation pattern classification:</strong> organic / coordinated / viral / targeted — derived from spread velocity and account age signals.</li>
  <li><strong>LLM synthesis (Groq):</strong> Fuses all signals into a structured verdict with natural-language reasoning.</li>
</ul>
</section>

<section id="agent-ling">
<h3>🧠 8. Linguistic Agent <span class="badge amber">w = 0.10</span></h3>
<p>Analyses the <em>writing style</em> of the text for two axes: clickbait/emotional manipulation and AI-generated text detection.</p>

<div class="card-grid">
  <div class="card-sm" style="--c:var(--amber);">
    <div class="card-sm-icon">🎣</div>
    <div class="card-sm-title">Clickbait Detection</div>
    <div class="card-sm-desc">Matches against 13 clickbait phrase patterns ("you won't believe", "the truth about", "share before deleted") and 15 emotional amplifier words. Score = hits / 5.0, capped at 1.0.</div>
    <div class="card-sm-tags"><span class="tag amber">pattern matching</span></div>
  </div>
  <div class="card-sm" style="--c:var(--amber);">
    <div class="card-sm-icon">🤖</div>
    <div class="card-sm-title">AI Text Detection</div>
    <div class="card-sm-desc">Measures sentence length variance across the text. AI-generated text has unnaturally uniform sentence structure (low variance). Score = 1 - (variance / 50.0). Confirmed by LLM self-reflection pass (Groq).</div>
    <div class="card-sm-tags"><span class="tag amber">statistical + LLM</span></div>
  </div>
</div>

<p>The final linguistic risk = <code>clickbait_score × 0.55 + ai_generated_score × 0.45</code> — clickbait is weighted slightly higher because it's a more direct disinformation signal in the MENA context.</p>
</section>
</section>

<hr>

<!-- FRONTEND -->
<section id="frontend">
<h2>🖥️ Frontend — 4-Step Wizard</h2>

<p>The frontend (<code>truthguard-v3.html</code>) is a self-contained single-file application. It communicates with the orchestrator API at <code>localhost:8001</code> and degrades gracefully to local computation if the API is unreachable.</p>

<div class="flow-steps">
  <div class="flow-step">
    <div class="flow-num">1</div>
    <div class="flow-content">
      <div class="flow-title">Content Submission</div>
      <div class="flow-desc">Three input modes: file upload (drag & drop), URL, or pasted text. All types accepted — the type is <em>not assumed</em> at this stage. File is stored in memory and only sent to the API at Step 4.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">2</div>
    <div class="flow-content">
      <div class="flow-title">Content Nature Declaration</div>
      <div class="flow-desc">12 content types to choose from. Selecting "Social Post Screenshot" triggers contextual enrichment fields: platform, author handle, source URL, and a text field to type out the visible post text (for better OCR-independent claim extraction). The expected agent pipeline is shown next to each choice.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">3</div>
    <div class="flow-content">
      <div class="flow-title">Analysis Goal Selection</div>
      <div class="flow-desc">8 analysis goals — users select only what they need. This prevents unnecessary agent activation and makes the analysis faster. Each goal card shows which underlying agents it activates.</div>
    </div>
  </div>
  <div class="flow-step">
    <div class="flow-num">4</div>
    <div class="flow-content">
      <div class="flow-title">Agent Plan Review → Run</div>
      <div class="flow-desc">The orchestrator computes the activation plan (via <code>POST /analyse/plan</code>) and displays each agent as ACTIVE or SKIP with a written reason. The user sees exactly what will run before submitting. Then analysis runs with a live stage-by-stage loading indicator.</div>
    </div>
  </div>
</div>

<section id="dialogue">
<h3>🗣️ Why a Dialogue System?</h3>

<div class="callout info">
  <div class="callout-icon">🎯</div>
  <div>
    <strong>The core problem with file-type routing:</strong> MIME type tells you <em>format</em>, not <em>meaning</em>. A <code>image/jpeg</code> could be a raw photo (→ VISION only), a screenshot of a tweet (→ VISION + TEXT + URL + NETWORK), a meme (→ VISION + TEXT + CONTEXT), or a screenshot of a WhatsApp conversation (→ VISION + TEXT + CONTEXT). Routing by MIME alone would activate only VISION in all these cases — missing the most important analysis dimensions.
  </div>
</div>

<p>The dialogue system closes this gap by making content nature <strong>explicit</strong>. The orchestrator's <code>plan_agents()</code> function uses a <strong>content nature override map</strong> — when the user declares <code>social_post_screenshot</code>, the orchestrator ignores the router's image-only routing and activates 7 of 8 agents, regardless of file type.</p>

<div class="table-wrap">
<table>
  <thead><tr><th>Content Nature</th><th>Agents Activated</th><th>Why</th></tr></thead>
  <tbody>
    <tr>
      <td><strong>📸 Social Post Screenshot</strong></td>
      <td>All 7 (except video forensics)</td>
      <td>Pixel forensics (manipulation check) + OCR claims + source cred on visible URL + network/bot signals + linguistic manipulation</td>
    </tr>
    <tr>
      <td><strong>🖼️ Raw Photo</strong></td>
      <td>image_forensics only</td>
      <td>No text to extract, no URL to check — only pixel-level analysis is relevant</td>
    </tr>
    <tr>
      <td><strong>😂 Meme</strong></td>
      <td>image_forensics + claim_extract + claim_verify + context_agent + linguistic</td>
      <td>Memes often repurpose real images in wrong contexts + text claims need verification</td>
    </tr>
    <tr>
      <td><strong>📰 News Article</strong></td>
      <td>claim_extract + claim_verify + source_cred + linguistic + context_agent</td>
      <td>Text-heavy content — facts, source, and manipulation language are the relevant signals</td>
    </tr>
    <tr>
      <td><strong>🔬 Scientific Claim</strong></td>
      <td>claim_extract + claim_verify + context_agent</td>
      <td>Temporal accuracy (publication date, retraction status) and knowledge-base verification are most critical</td>
    </tr>
  </tbody>
</table>
</div>
</section>
</section>

<hr>

<!-- API REFERENCE -->
<section id="api">
<h2>🔌 API Reference</h2>

<h3>Orchestrator API · <code>localhost:8001</code></h3>

<div class="table-wrap">
<table>
  <thead><tr><th>Endpoint</th><th>Method</th><th>Description</th></tr></thead>
  <tbody>
    <tr><td><code>/health</code></td><td>GET</td><td>Service health check. Returns version and mode.</td></tr>
    <tr><td><code>/agents</code></td><td>GET</td><td>List all available agents with descriptions, weights, and trigger conditions.</td></tr>
    <tr><td><code>/analyse/plan</code></td><td>POST</td><td>Preview the agent activation plan without running it. Called by Step 4 of the wizard.</td></tr>
    <tr><td><code>/analyse</code></td><td>POST</td><td>Full analysis. Accepts file + dialogue answers as multipart form data. Returns <code>AnalyseResponse</code>.</td></tr>
  </tbody>
</table>
</div>

<h3>Preprocessing API · <code>localhost:8000</code></h3>

<div class="table-wrap">
<table>
  <thead><tr><th>Endpoint</th><th>Input</th><th>Returns</th></tr></thead>
  <tbody>
    <tr><td><code>POST /preprocess/image</code></td><td>Multipart image file</td><td><code>NormalizedFeatureObject</code></td></tr>
    <tr><td><code>POST /preprocess/url</code></td><td>JSON <code>{"url": "..."}</code></td><td><code>NormalizedFeatureObject</code></td></tr>
    <tr><td><code>POST /preprocess/document</code></td><td>Multipart PDF/DOCX/TXT</td><td><code>NormalizedFeatureObject</code></td></tr>
    <tr><td><code>POST /preprocess/video</code></td><td>Multipart video file</td><td><code>NormalizedFeatureObject</code></td></tr>
  </tbody>
</table>
</div>

<h3>Key Request Fields (<code>POST /analyse</code>)</h3>
<pre><code>POST /analyse
Content-Type: multipart/form-data

file            = &lt;binary file upload&gt;        # optional if URL mode
input_type      = "image"|"video"|"document"|"url"
content_nature  = "social_post_screenshot"    # see ContentNature enum
analysis_goals  = '["authenticity","source_credibility"]'  # JSON array
source_url      = "https://twitter.com/..."   # optional
post_text       = "Full text of the post..."  # optional, typed-out version
platform        = "Twitter"                   # optional
author_handle   = "@username"                 # optional</code></pre>
</section>

<!-- INSTALL -->
<section id="install">
<h2>📦 Installation</h2>

<h3>Minimal (no GPU, no OCR)</h3>
<pre><code>pip install fastapi uvicorn python-multipart httpx pydantic pillow pymupdf beautifulsoup4</code></pre>

<h3>Full (all features)</h3>
<pre><code># Core
pip install -r Preprocessing/requirements.txt

# OCR (requires Tesseract binary)
# Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra
pip install pytesseract

# Video
# Ubuntu: sudo apt install ffmpeg
pip install opencv-python-headless openai-whisper

# RAG (Claim Verifier)
pip install sentence-transformers chromadb

# Orchestration
pip install prefect

# LLM providers (choose one or more)
pip install anthropic  # Claude
pip install groq       # Groq (LLaMA)
# Ollama: install ollama binary separately</code></pre>

<h3>Project Structure</h3>
<pre><code>codecrafters-main/
├── Preprocessing/              # FastAPI preprocessing service (port 8000)
│   ├── main.py                 # 4 endpoints: /preprocess/{image,url,document,video}
│   └── app/
│       ├── models/feature_object.py    # NormalizedFeatureObject schema
│       └── pipeline/                   # Per-type processors
│           ├── image/processor_image.py
│           ├── video/processor_vid.py
│           ├── document/processor_doc.py
│           └── url/processor_url.py
├── Agents/                     # 8 agent modules
│   ├── orchestrator.py         # Prefect flow — wires everything
│   ├── evidence_fusion.py      # 3-stage fusion + DecisionEngine
│   ├── claim_extractor.py      # LLM claim extraction
│   ├── claim_verifier.py       # RAG + NLI verification
│   ├── agent_image_forensics.py
│   ├── agent_video_forensics.py
│   ├── context_agent.py
│   ├── source_cred_agent.py
│   ├── network_agent.py
│   └── linguistic_agent.py
├── Router/                     # 3-layer content router
│   ├── router.py               # Main entry: route(context) → RoutingDecision
│   ├── layer1magic.py          # MIME detection
│   ├── layer2sniff.py          # Content sniffing
│   ├── layer3classifier.py     # Pipeline scoring
│   └── models.py               # SubmissionContext, RoutingDecision, Pipeline
├── orchestrator_api.py         # NEW: User-dialogue orchestrator (port 8001)
├── chroma_db/                  # Pre-built vector store with initial fact corpus
├── truthguard-v3.html          # Frontend wizard UI
└── README.html                 # This document</code></pre>
</section>

<hr>

<!-- FOOTER -->
<div style="text-align:center;padding:32px 0 0;color:var(--text3);font-size:13px;">
  <p>TruthGuard · MENACRAFT Hackathon · Built with FastAPI · Prefect · Pillow · OpenCV · Whisper · ChromaDB</p>
  <p style="margin-top:6px;">
    <a href="http://localhost:8000/docs" style="color:var(--accent);text-decoration:none;">Preprocessing API Docs</a> ·
    <a href="http://localhost:8001/docs" style="color:var(--accent);text-decoration:none;">Orchestrator API Docs</a>
  </p>
</div>

</main>
</div>
</body>
</html>
