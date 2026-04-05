<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TruthGuard — Smart Content Verification</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;1,300&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#080a0f;--bg2:#0d1018;--surface:#111520;--surface2:#161c2c;
  --border:#1e2438;--border2:#272f48;
  --accent:#7cf4c8;--accent2:#4de8b0;
  --accent-d:rgba(124,244,200,0.10);--accent-g:rgba(124,244,200,0.20);
  --red:#ff5c6a;--red-d:rgba(255,92,106,0.12);
  --amber:#ffbe3d;--amber-d:rgba(255,190,61,0.12);
  --orange:#ff8845;--orange-d:rgba(255,136,69,0.12);
  --green:#3cffa0;--green-d:rgba(60,255,160,0.12);
  --blue:#5b9eff;--blue-d:rgba(91,158,255,0.12);
  --purple:#c084fc;--purple-d:rgba(192,132,252,0.12);
  --pink:#f472b6;
  --text:#dde4f0;--text2:#7d8aaa;--text3:#3d4560;
  --font-h:'Syne',sans-serif;--font-b:'DM Sans',sans-serif;--font-m:'JetBrains Mono',monospace;
  --r:14px;--rs:9px;--shadow:0 12px 60px rgba(0,0,0,0.7);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--text);font-family:var(--font-b);font-size:15px;line-height:1.6;min-height:100vh;overflow-x:hidden;}
body::after{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.04) 2px,rgba(0,0,0,0.04) 4px);pointer-events:none;z-index:9999;}
.glow-orb{position:fixed;top:-200px;left:50%;transform:translateX(-50%);width:800px;height:500px;background:radial-gradient(ellipse,rgba(124,244,200,0.04) 0%,transparent 70%);pointer-events:none;}

/* NAV */
nav{position:sticky;top:0;z-index:200;background:rgba(8,10,15,0.90);backdrop-filter:blur(24px);border-bottom:1px solid var(--border);height:60px;display:flex;align-items:center;padding:0 28px;justify-content:space-between;}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none;}
.logo-mark{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,var(--accent),var(--blue));display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:900;color:#080a0f;font-family:var(--font-h);}
.logo-text{font-family:var(--font-h);font-size:17px;font-weight:800;letter-spacing:-.5px;color:var(--text);}
.logo-text span{color:var(--accent);}
.nav-right{display:flex;align-items:center;gap:12px;}
.api-badge{display:flex;align-items:center;gap:6px;font-family:var(--font-m);font-size:11px;padding:4px 10px;border-radius:6px;transition:all .3s;}
.api-badge.online{color:var(--green);background:var(--green-d);border:1px solid rgba(60,255,160,0.15);}
.api-badge.offline{color:var(--red);background:var(--red-d);border:1px solid rgba(255,92,106,0.2);}
.api-badge.checking{color:var(--text3);background:var(--surface2);border:1px solid var(--border);}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor;}
.dot.pulse{animation:blink 2s ease infinite;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
.nav-link-btn{padding:6px 14px;border-radius:var(--rs);border:none;background:none;color:var(--text2);font-family:var(--font-b);font-size:13px;cursor:pointer;transition:all .2s;}
.nav-link-btn:hover{color:var(--text);background:var(--surface);}

/* LAYOUT */
.container{max-width:1100px;margin:0 auto;padding:0 24px;position:relative;}

/* HERO */
.hero{padding:60px 0 44px;text-align:center;}
.eyebrow{display:inline-flex;align-items:center;gap:7px;font-family:var(--font-m);font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);background:var(--accent-d);border:1px solid rgba(124,244,200,0.18);padding:5px 13px;border-radius:100px;margin-bottom:22px;}
h1{font-family:var(--font-h);font-size:clamp(32px,4.5vw,58px);font-weight:800;letter-spacing:-2px;line-height:1.06;margin-bottom:16px;}
h1 .hi{color:var(--accent);}h1 .h2{color:var(--blue);}
.hero-sub{max-width:520px;margin:0 auto 36px;color:var(--text2);font-size:16px;line-height:1.75;font-weight:300;}

/* WIZARD */
.wizard{background:var(--surface);border:1px solid var(--border);border-radius:20px;overflow:hidden;box-shadow:var(--shadow);margin-bottom:60px;}
.wizard-progress{display:flex;align-items:center;padding:16px 28px;border-bottom:1px solid var(--border);gap:0;}
.prog-step{display:flex;align-items:center;gap:8px;flex:1;min-width:0;}
.prog-step:not(:last-child)::after{content:'';flex:1;height:1px;background:var(--border2);margin:0 8px;transition:background .4s;}
.prog-step.done::after{background:var(--accent);}
.prog-num{width:26px;height:26px;border-radius:50%;flex-shrink:0;border:2px solid var(--border2);display:flex;align-items:center;justify-content:center;font-family:var(--font-m);font-size:10px;color:var(--text3);transition:all .3s;}
.prog-step.active .prog-num{border-color:var(--accent);color:var(--accent);background:var(--accent-d);}
.prog-step.done .prog-num{border-color:var(--accent);background:var(--accent);color:#080a0f;font-weight:700;}
.prog-label{font-size:12px;font-weight:500;color:var(--text3);transition:color .3s;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.prog-step.active .prog-label{color:var(--accent);}
.prog-step.done .prog-label{color:var(--text2);}

.step-panel{display:none;animation:fadeIn .3s ease;}
.step-panel.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.step-header{padding:28px 28px 0;display:flex;align-items:flex-start;gap:14px;}
.step-icon{width:44px;height:44px;border-radius:12px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:20px;}
.step-title{font-family:var(--font-h);font-size:20px;font-weight:800;letter-spacing:-.5px;margin-bottom:4px;}
.step-sub{font-size:13px;color:var(--text2);line-height:1.5;}
.step-body{padding:22px 28px 28px;}

/* CHOICE GRIDS */
.choice-grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));}
.choice-grid.cols2{grid-template-columns:repeat(auto-fill,minmax(260px,1fr));}
.choice-card{border:1.5px solid var(--border);border-radius:var(--r);padding:14px 16px;cursor:pointer;transition:all .2s;position:relative;background:var(--bg2);user-select:none;display:flex;align-items:flex-start;gap:12px;}
.choice-card:hover{border-color:var(--border2);transform:translateY(-1px);}
.choice-card.selected{border-color:var(--c,var(--accent));background:rgba(124,244,200,0.05);}
.choice-card.selected::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--c,var(--accent));border-radius:14px 14px 0 0;}
.card-icon{font-size:22px;flex-shrink:0;margin-top:1px;}
.card-body{flex:1;min-width:0;}
.card-title{font-family:var(--font-h);font-size:13px;font-weight:700;letter-spacing:-.2px;margin-bottom:3px;}
.card-desc{font-size:12px;color:var(--text2);line-height:1.45;}
.card-check{width:18px;height:18px;border-radius:5px;flex-shrink:0;border:2px solid var(--border2);display:flex;align-items:center;justify-content:center;font-size:9px;transition:all .2s;margin-top:2px;}
.choice-card.selected .card-check{background:var(--c,var(--accent));border-color:var(--c,var(--accent));color:#080a0f;}

/* UPLOAD */
.upload-zone{border:2px dashed var(--border2);border-radius:var(--r);padding:50px 32px;text-align:center;cursor:pointer;transition:all .25s;position:relative;background:var(--bg);}
.upload-zone:hover,.upload-zone.over{border-color:var(--accent);background:var(--accent-d);}
.upload-zone input{position:absolute;inset:0;opacity:0;cursor:pointer;z-index:1;}
.upload-icon-wrap{width:56px;height:56px;border-radius:14px;margin:0 auto 14px;border:1px solid var(--border2);background:var(--surface2);display:flex;align-items:center;justify-content:center;font-size:24px;transition:all .25s;}
.upload-zone:hover .upload-icon-wrap,.upload-zone.over .upload-icon-wrap{background:var(--accent-d);border-color:var(--accent);}
.upload-title{font-family:var(--font-h);font-size:16px;font-weight:700;margin-bottom:6px;}
.upload-sub{font-size:13px;color:var(--text2);}
.upload-sub strong{color:var(--accent);}
.file-pill{display:inline-flex;align-items:center;gap:8px;margin-top:12px;font-family:var(--font-m);font-size:12px;color:var(--accent);background:var(--accent-d);border:1px solid rgba(124,244,200,0.2);padding:5px 12px;border-radius:8px;}

/* INPUTS */
.field-label{font-family:var(--font-m);font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--text3);margin-bottom:6px;display:block;}
.text-input,.url-input,.textarea{width:100%;background:var(--bg);border:1px solid var(--border2);border-radius:var(--rs);padding:12px 16px;color:var(--text);font-family:var(--font-m);font-size:13px;outline:none;transition:border .2s;}
.text-input::placeholder,.url-input::placeholder,.textarea::placeholder{color:var(--text3);}
.text-input:focus,.url-input:focus,.textarea:focus{border-color:var(--accent);}
.textarea{resize:vertical;min-height:100px;font-family:var(--font-b);font-size:14px;line-height:1.6;}
.field-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;}
.field-row .text-input{flex:1;min-width:160px;}

/* ALERTS */
.alert{display:flex;gap:10px;padding:11px 14px;border-radius:var(--rs);font-size:13px;line-height:1.5;margin-bottom:16px;}
.alert.amber{background:var(--amber-d);border:1px solid rgba(255,190,61,0.2);color:var(--amber);}
.alert.blue{background:var(--blue-d);border:1px solid rgba(91,158,255,0.2);color:var(--blue);}
.alert.accent{background:var(--accent-d);border:1px solid rgba(124,244,200,0.2);color:var(--accent);}
.alert.red{background:var(--red-d);border:1px solid rgba(255,92,106,0.2);color:var(--red);}

/* PLAN */
.plan-grid{display:flex;flex-direction:column;gap:8px;}
.agent-row{display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:var(--rs);border:1px solid var(--border);background:var(--bg2);transition:all .3s;}
.agent-row.active{border-color:var(--accent);background:var(--accent-d);}
.agent-row.inactive{opacity:0.35;}
.agent-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.agent-row.active .agent-dot{background:var(--accent);box-shadow:0 0 8px var(--accent);}
.agent-row.inactive .agent-dot{background:var(--text3);}
.agent-info{flex:1;}
.agent-name{font-family:var(--font-h);font-size:13px;font-weight:700;letter-spacing:-.2px;}
.agent-desc{font-size:12px;color:var(--text2);}
.agent-weight{font-family:var(--font-m);font-size:10px;color:var(--text3);}
.agent-badge{font-family:var(--font-m);font-size:9px;letter-spacing:1px;text-transform:uppercase;padding:3px 8px;border-radius:4px;}
.badge-active{background:var(--accent-d);color:var(--accent);border:1px solid rgba(124,244,200,0.2);}
.badge-skip{background:var(--surface2);color:var(--text3);border:1px solid var(--border);}
.reason-list{margin-top:16px;padding:14px 16px;border-radius:var(--rs);background:var(--bg);border:1px solid var(--border);}
.reason-title{font-family:var(--font-m);font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--text3);margin-bottom:10px;}
.reason-item{display:flex;gap:8px;font-size:12px;color:var(--text2);padding:4px 0;border-bottom:1px solid var(--border);line-height:1.5;}
.reason-item:last-child{border-bottom:none;}
.reason-item::before{content:'→';color:var(--accent);flex-shrink:0;}

/* FOOTER BAR */
.wizard-footer{padding:18px 28px;border-top:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;}
.footer-info{font-size:13px;color:var(--text2);}
.footer-info strong{color:var(--accent);font-family:var(--font-m);}
.btn-row{display:flex;gap:10px;}
.btn{display:flex;align-items:center;gap:7px;padding:11px 22px;border-radius:var(--rs);font-family:var(--font-h);font-size:14px;font-weight:700;cursor:pointer;transition:all .2s;border:none;white-space:nowrap;}
.btn-ghost{background:var(--surface2);color:var(--text2);border:1px solid var(--border2);}
.btn-ghost:hover{color:var(--text);border-color:var(--text3);}
.btn-primary{background:var(--accent);color:#080a0f;}
.btn-primary:hover{background:var(--accent2);transform:translateY(-1px);box-shadow:0 4px 20px rgba(124,244,200,0.3);}
.btn-primary:disabled{opacity:.4;cursor:not-allowed;transform:none;box-shadow:none;}

/* LOADING */
#loading-panel{display:none;}
#loading-panel.show{display:block;}
.loading-inner{padding:60px 28px;text-align:center;}
.loader-ring{width:52px;height:52px;border-radius:50%;border:3px solid var(--border2);border-top-color:var(--accent);animation:spin .7s linear infinite;margin:0 auto 20px;}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-title{font-family:var(--font-h);font-size:18px;font-weight:800;margin-bottom:6px;}
.loading-sub{font-size:13px;color:var(--text2);margin-bottom:28px;}
.stage-list{display:flex;flex-direction:column;gap:6px;max-width:400px;margin:0 auto;}
.stage-item{display:flex;align-items:center;gap:10px;font-family:var(--font-m);font-size:11px;padding:8px 14px;border-radius:var(--rs);background:var(--bg2);border:1px solid var(--border);color:var(--text3);transition:all .3s;}
.stage-item.running{color:var(--accent);border-color:rgba(124,244,200,0.2);background:var(--accent-d);}
.stage-item.done{color:var(--green);border-color:rgba(60,255,160,0.15);}
.stage-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;background:currentColor;}
.stage-item.running .stage-dot{animation:blink .8s ease infinite;}

/* ERROR PANEL */
#error-panel{display:none;padding:52px 28px;text-align:center;}
#error-panel.show{display:block;}
.error-icon{font-size:52px;margin-bottom:18px;}
.error-title{font-family:var(--font-h);font-size:22px;font-weight:800;color:var(--red);margin-bottom:8px;letter-spacing:-.5px;}
.error-msg{font-size:14px;color:var(--text2);max-width:500px;margin:0 auto 20px;line-height:1.7;}
.error-detail{font-family:var(--font-m);font-size:11px;color:var(--text3);background:var(--bg2);border:1px solid var(--border);border-radius:var(--rs);padding:13px 16px;max-width:500px;margin:0 auto 24px;text-align:left;word-break:break-all;line-height:1.7;}
.error-detail strong{color:var(--red);display:block;margin-bottom:4px;}

/* RESULTS */
#results-panel{display:none;}
#results-panel.show{display:block;}
.res-header{padding:24px 28px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;}
.res-title{font-family:var(--font-h);font-size:18px;font-weight:800;letter-spacing:-.5px;}
.btn-restart{padding:7px 16px;border-radius:var(--rs);background:var(--surface2);border:1px solid var(--border2);color:var(--text2);font-size:13px;cursor:pointer;transition:all .2s;}
.btn-restart:hover{color:var(--text);border-color:var(--text3);}

/* VERDICT */
.verdict{margin:24px 28px 20px;padding:24px 28px;border-radius:16px;display:flex;align-items:center;gap:20px;flex-wrap:wrap;}
.verdict.GREEN{background:var(--green-d);border:1px solid rgba(60,255,160,0.25);}
.verdict.AMBER{background:var(--amber-d);border:1px solid rgba(255,190,61,0.25);}
.verdict.ORANGE{background:var(--orange-d);border:1px solid rgba(255,136,69,0.25);}
.verdict.RED{background:var(--red-d);border:1px solid rgba(255,92,106,0.25);}
.verdict-emoji{font-size:44px;flex-shrink:0;}
.verdict-main{flex:1;min-width:200px;}
.verdict-label{font-family:var(--font-h);font-size:26px;font-weight:800;letter-spacing:-1px;margin-bottom:3px;}
.verdict.GREEN .verdict-label{color:var(--green);}
.verdict.AMBER .verdict-label{color:var(--amber);}
.verdict.ORANGE .verdict-label{color:var(--orange);}
.verdict.RED .verdict-label{color:var(--red);}
.verdict-explain{font-size:13px;color:var(--text2);line-height:1.5;}
.verdict-scores{display:flex;gap:24px;flex-wrap:wrap;}
.score-block{text-align:center;}
.score-num{font-family:var(--font-h);font-size:26px;font-weight:800;line-height:1;}
.score-lbl{font-family:var(--font-m);font-size:9px;letter-spacing:1px;text-transform:uppercase;color:var(--text2);margin-top:2px;}

/* CHIPS */
.pipeline-chips{padding:0 28px 16px;display:flex;gap:8px;flex-wrap:wrap;}
.chip{display:flex;align-items:center;gap:6px;font-family:var(--font-m);font-size:10px;letter-spacing:.5px;padding:4px 10px;border-radius:6px;}
.chip.VISION{background:var(--blue-d);color:var(--blue);border:1px solid rgba(91,158,255,0.2);}
.chip.TEXT{background:var(--accent-d);color:var(--accent);border:1px solid rgba(124,244,200,0.2);}
.chip.VIDEO{background:var(--purple-d);color:var(--purple);border:1px solid rgba(192,132,252,0.2);}
.chip.URL{background:var(--orange-d);color:var(--orange);border:1px solid rgba(255,136,69,0.2);}

/* AGENT CARDS */
.agents-grid{padding:0 28px;display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));margin-bottom:20px;}
.agent-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--r);overflow:hidden;}
.agent-card-head{padding:13px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;}
.agent-card-icon{width:30px;height:30px;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:15px;}
.agent-card-title{font-family:var(--font-h);font-size:13px;font-weight:700;flex:1;}
.risk-badge{font-family:var(--font-m);font-size:9px;letter-spacing:1px;text-transform:uppercase;padding:3px 8px;border-radius:4px;font-weight:600;}
.rb-HIGH{background:var(--red-d);color:var(--red);border:1px solid rgba(255,92,106,0.2);}
.rb-MEDIUM{background:var(--amber-d);color:var(--amber);border:1px solid rgba(255,190,61,0.2);}
.rb-LOW{background:var(--green-d);color:var(--green);border:1px solid rgba(60,255,160,0.2);}
.agent-card-body{padding:14px 16px;}
.bar-wrap{margin-bottom:12px;}
.bar-label{display:flex;justify-content:space-between;font-size:11px;color:var(--text2);margin-bottom:5px;}
.bar-label strong{color:var(--text);}
.bar-track{height:5px;background:var(--border2);border-radius:3px;overflow:hidden;}
.bar-fill{height:100%;border-radius:3px;transition:width 1.2s cubic-bezier(.4,0,.2,1);}
.bar-fill.GREEN{background:var(--green);}
.bar-fill.AMBER{background:var(--amber);}
.bar-fill.ORANGE{background:var(--orange);}
.bar-fill.RED{background:var(--red);}
.finding{display:flex;gap:8px;font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:6px;align-items:flex-start;}
.finding-bullet{width:5px;height:5px;border-radius:50%;flex-shrink:0;margin-top:5px;}
.finding-bullet.red{background:var(--red);box-shadow:0 0 5px var(--red);}
.finding-bullet.amber{background:var(--amber);box-shadow:0 0 5px var(--amber);}
.finding-bullet.green{background:var(--green);}
.finding-bullet.blue{background:var(--blue);}

/* AUDIT */
.audit-wrap{margin:0 28px 28px;}
.audit-toggle{display:flex;align-items:center;gap:8px;padding:12px 16px;border-radius:var(--rs) var(--rs) 0 0;background:var(--bg2);border:1px solid var(--border);cursor:pointer;font-family:var(--font-h);font-size:13px;font-weight:700;}
.audit-toggle:hover{background:var(--surface);}
.chevron{margin-left:auto;color:var(--text2);font-size:11px;transition:transform .2s;}
.audit-toggle.open .chevron{transform:rotate(180deg);}
.audit-entries{display:none;border:1px solid var(--border);border-top:none;border-radius:0 0 var(--rs) var(--rs);overflow:hidden;}
.audit-entries.show{display:block;}
.audit-row{display:grid;grid-template-columns:28px 1fr;gap:0 10px;padding:9px 16px;border-bottom:1px solid var(--border);align-items:start;}
.audit-row:last-child{border-bottom:none;}
.audit-n{font-family:var(--font-m);font-size:10px;color:var(--text3);padding-top:1px;}
.audit-t{font-family:var(--font-m);font-size:11px;color:var(--text2);line-height:1.5;}
.audit-t em{color:var(--accent);font-style:normal;font-weight:500;}

/* HOW IT WORKS */
.how-section{padding:40px 0 60px;}
.section-eyebrow{font-family:var(--font-m);font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--text3);margin-bottom:10px;}
.section-title{font-family:var(--font-h);font-size:28px;font-weight:800;letter-spacing:-1px;margin-bottom:32px;}
.flow-grid{display:grid;gap:1px;background:var(--border);border:1px solid var(--border);border-radius:16px;overflow:hidden;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));}
.flow-step{background:var(--surface);padding:24px 20px;}
.flow-n{font-family:var(--font-m);font-size:10px;letter-spacing:1px;color:var(--text3);margin-bottom:10px;}
.flow-icon{font-size:26px;margin-bottom:10px;}
.flow-title{font-family:var(--font-h);font-size:13px;font-weight:700;margin-bottom:4px;}
.flow-desc{font-size:12px;color:var(--text2);line-height:1.5;}

footer{border-top:1px solid var(--border);padding:28px 0;text-align:center;color:var(--text3);font-size:12px;position:relative;z-index:1;}
footer a{color:var(--text2);text-decoration:none;}
footer a:hover{color:var(--accent);}
.sep{height:1px;background:var(--border);margin:18px 0;}
.tag-label{font-family:var(--font-m);font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--text3);margin-bottom:10px;}

@media(max-width:600px){
  nav{padding:0 16px;}
  .container,.hero{padding:0 16px;}
  h1{font-size:28px;}
  .wizard-progress{padding:12px 16px;}
  .prog-label{display:none;}
  .step-header,.step-body,.wizard-footer{padding-left:16px;padding-right:16px;}
  .agents-grid,.pipeline-chips,.audit-wrap,.verdict{padding-left:16px;padding-right:16px;margin-left:0;margin-right:0;}
  .verdict{margin:16px 16px 12px;}
  .choice-grid{grid-template-columns:1fr;}
  .agents-grid{grid-template-columns:1fr;}
  .verdict-scores{gap:16px;}
}
</style>
</head>
<body>
<div class="glow-orb"></div>

<nav>
  <a class="logo" href="#">
    <div class="logo-mark">TG</div>
    <span class="logo-text">Truth<span>Guard</span></span>
  </a>
  <div class="nav-right">
    <div class="api-badge checking" id="api-badge">
      <div class="dot"></div>
      <span id="api-badge-text">checking…</span>
    </div>
    <button class="nav-link-btn" onclick="document.getElementById('how').scrollIntoView({behavior:'smooth'})">How it works</button>
    <a class="nav-link-btn" href="http://localhost:8001/docs" target="_blank">API ↗</a>
  </div>
</nav>

<section class="hero">
  <div class="container">
    <div class="eyebrow">🔬 Orchestrator-Driven · Agent Committee v3</div>
    <h1>The system <span class="hi">asks</span> before<br>it <span class="h2">analyses</span></h1>
    <p class="hero-sub">TruthGuard doesn't guess. It asks you what the content <em>is</em> and what you need to know — then activates exactly the right agents.</p>
  </div>
</section>

<div class="container">
<div class="wizard" id="wizard">

  <div class="wizard-progress" id="progress-bar">
    <div class="prog-step active" id="ps-1"><div class="prog-num">1</div><div class="prog-label">Upload</div></div>
    <div class="prog-step" id="ps-2"><div class="prog-num">2</div><div class="prog-label">Content Type</div></div>
    <div class="prog-step" id="ps-3"><div class="prog-num">3</div><div class="prog-label">Goals</div></div>
    <div class="prog-step" id="ps-4"><div class="prog-num">4</div><div class="prog-label">Agent Plan</div></div>
  </div>

  <!-- STEP 1 -->
  <div class="step-panel active" id="step-1">
    <div class="step-header">
      <div class="step-icon" style="background:var(--accent-d);border:1px solid rgba(124,244,200,0.2);">📥</div>
      <div><div class="step-title">Submit your content</div><div class="step-sub">File, URL, or typed text — we route it correctly in the next step.</div></div>
    </div>
    <div class="step-body">
      <div style="display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap;">
        <button class="btn btn-primary" style="padding:7px 16px;font-size:13px;" onclick="setInputTab(this,'file')" id="tab-file">📎 File</button>
        <button class="btn btn-ghost"   style="padding:7px 16px;font-size:13px;" onclick="setInputTab(this,'url')"  id="tab-url">🔗 URL</button>
        <button class="btn btn-ghost"   style="padding:7px 16px;font-size:13px;" onclick="setInputTab(this,'text')" id="tab-text">✍️ Text</button>
      </div>
      <div id="input-file">
        <div class="upload-zone" id="dropzone">
          <input type="file" id="file-input" onchange="onFile()">
          <div class="upload-icon-wrap">📂</div>
          <div class="upload-title">Drop any file here</div>
          <p class="upload-sub">Image, Video, Document, Screenshot · <strong>all types accepted</strong></p>
          <div id="file-pill" style="display:none;" class="file-pill">📎 <span id="file-name-label"></span></div>
        </div>
      </div>
      <div id="input-url" style="display:none;">
        <label class="field-label">Page or article URL</label>
        <input class="url-input" id="url-val" type="url" placeholder="https://example.com/article-to-verify">
      </div>
      <div id="input-text" style="display:none;">
        <label class="field-label">Post or article text</label>
        <textarea class="textarea" id="text-val" placeholder="Paste the full text of the post, article, or claim you want to verify…"></textarea>
      </div>
    </div>
    <div class="wizard-footer">
      <div class="footer-info">Step 1 of 4 — what are we analysing?</div>
      <div class="btn-row"><button class="btn btn-primary" onclick="goStep(2)">Continue →</button></div>
    </div>
  </div>

  <!-- STEP 2 -->
  <div class="step-panel" id="step-2">
    <div class="step-header">
      <div class="step-icon" style="background:var(--blue-d);border:1px solid rgba(91,158,255,0.2);">🔍</div>
      <div><div class="step-title">What is this content?</div><div class="step-sub">This tells the orchestrator which agents to activate. A screenshot of a tweet is <strong>not</strong> treated as "just an image."</div></div>
    </div>
    <div class="step-body">
      <div class="choice-grid" id="nature-grid"></div>
      <div class="sep"></div>
      <div id="enrichment-fields" style="display:none;">
        <div class="alert accent" style="margin-bottom:14px;"><span>💡</span><span>Providing more context helps the orchestrator activate the right agents. These fields are optional.</span></div>
        <div class="field-row">
          <div style="flex:1;min-width:180px;"><label class="field-label">Platform (e.g. Twitter, Telegram)</label><input class="text-input" id="platform-val" placeholder="Twitter / Facebook / Telegram…"></div>
          <div style="flex:1;min-width:180px;"><label class="field-label">Author / handle</label><input class="text-input" id="author-val" placeholder="@username"></div>
        </div>
        <div style="margin-top:10px;"><label class="field-label">Source URL (where this was originally posted)</label><input class="url-input" id="source-url-val" placeholder="https://twitter.com/…"></div>
        <div style="margin-top:10px;" id="post-text-field">
          <label class="field-label">Post text (type it out for better claim extraction)</label>
          <textarea class="textarea" id="post-text-val" style="min-height:80px;" placeholder="Optional: type the visible text in the screenshot for better claim extraction…"></textarea>
        </div>
      </div>
    </div>
    <div class="wizard-footer">
      <div class="footer-info" id="nature-footer">Select what this content is</div>
      <div class="btn-row">
        <button class="btn btn-ghost" onclick="goStep(1)">← Back</button>
        <button class="btn btn-primary" onclick="goStep(3)" id="btn-step2" disabled>Continue →</button>
      </div>
    </div>
  </div>

  <!-- STEP 3 -->
  <div class="step-panel" id="step-3">
    <div class="step-header">
      <div class="step-icon" style="background:var(--purple-d);border:1px solid rgba(192,132,252,0.2);">🎯</div>
      <div><div class="step-title">What do you need to know?</div><div class="step-sub">Select one or more analysis goals. The orchestrator will activate the minimum set of agents needed.</div></div>
    </div>
    <div class="step-body"><div class="choice-grid cols2" id="goals-grid"></div></div>
    <div class="wizard-footer">
      <div class="footer-info" id="goals-footer"><strong id="goal-count">0</strong> goals selected</div>
      <div class="btn-row">
        <button class="btn btn-ghost" onclick="goStep(2)">← Back</button>
        <button class="btn btn-primary" onclick="buildPlan()" id="btn-step3" disabled>Build Agent Plan →</button>
      </div>
    </div>
  </div>

  <!-- STEP 4 -->
  <div class="step-panel" id="step-4">
    <div class="step-header">
      <div class="step-icon" style="background:var(--amber-d);border:1px solid rgba(255,190,61,0.2);">🤖</div>
      <div><div class="step-title">Your agent activation plan</div><div class="step-sub">The orchestrator computed this plan based on your answers. Review it, then run the analysis.</div></div>
    </div>
    <div class="step-body">
      <div class="plan-grid" id="plan-grid"></div>
      <div class="reason-list" id="reason-list"><div class="reason-title">Why these agents?</div><div id="reasons-body"></div></div>
    </div>
    <div class="wizard-footer">
      <div class="footer-info"><strong id="active-count">0</strong> agents · <strong id="pipeline-count">0</strong> pipelines</div>
      <div class="btn-row">
        <button class="btn btn-ghost" onclick="goStep(3)">← Back</button>
        <button class="btn btn-primary" onclick="runAnalysis()" id="btn-run">⚡ Run Analysis</button>
      </div>
    </div>
  </div>

  <!-- LOADING -->
  <div id="loading-panel">
    <div class="loading-inner">
      <div class="loader-ring"></div>
      <div class="loading-title">Running agent committee…</div>
      <div class="loading-sub">Activated agents processing in parallel</div>
      <div class="stage-list" id="stage-list"></div>
    </div>
  </div>

  <!-- ERROR -->
  <div id="error-panel">
    <div class="error-icon">🔌</div>
    <div class="error-title" id="error-title">API Unreachable</div>
    <div class="error-msg" id="error-msg">The orchestrator API at <code>localhost:8001</code> did not respond. Make sure <code>orchestrator_api.py</code> is running before submitting a request.</div>
    <div class="error-detail" id="error-detail"></div>
    <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
      <button class="btn btn-ghost" onclick="retryFromPlan()">← Back to Plan</button>
      <button class="btn btn-primary" onclick="restart()">↺ Start Over</button>
    </div>
  </div>

  <!-- RESULTS -->
  <div id="results-panel">
    <div class="res-header">
      <div class="res-title">Analysis Complete</div>
      <button class="btn-restart" onclick="restart()">← New Analysis</button>
    </div>
    <div id="verdict-wrap"></div>
    <div class="pipeline-chips" id="pipeline-chips"></div>
    <div class="agents-grid" id="agents-grid"></div>
    <div class="audit-wrap">
      <div class="audit-toggle" id="audit-toggle" onclick="toggleAudit()">
        <span>🔍</span> Orchestrator Audit Trail
        <span class="chevron">▼</span>
      </div>
      <div class="audit-entries" id="audit-entries"></div>
    </div>
  </div>

</div>
</div>

<section class="how-section" id="how">
  <div class="container">
    <div class="section-eyebrow">Architecture · v3</div>
    <div class="section-title">Dialogue-driven orchestration</div>
    <div class="flow-grid">
      <div class="flow-step"><div class="flow-n">01</div><div class="flow-icon">📥</div><div class="flow-title">Content Submission</div><div class="flow-desc">File, URL, or text. Any type accepted — type is not assumed, it's asked.</div></div>
      <div class="flow-step"><div class="flow-n">02</div><div class="flow-icon">🗣️</div><div class="flow-title">Content Nature Dialogue</div><div class="flow-desc">You tell us if it's a tweet screenshot, meme, article, etc. A screenshot ≠ just an image.</div></div>
      <div class="flow-step"><div class="flow-n">03</div><div class="flow-icon">🎯</div><div class="flow-title">Goal Selection</div><div class="flow-desc">Authenticity? Source credibility? Claim verification? You pick — we don't run all agents by default.</div></div>
      <div class="flow-step"><div class="flow-n">04</div><div class="flow-icon">🧮</div><div class="flow-title">Plan Computation</div><div class="flow-desc">Orchestrator maps your answers → minimal agent set with full transparency on why each agent fires.</div></div>
      <div class="flow-step"><div class="flow-n">05</div><div class="flow-icon">⚙️</div><div class="flow-title">Parallel Agent Run</div><div class="flow-desc">Only activated agents run. 8 max, fewer if not needed. Prefect ConcurrentTaskRunner.</div></div>
      <div class="flow-step"><div class="flow-n">06</div><div class="flow-icon">⚖️</div><div class="flow-title">Evidence Fusion</div><div class="flow-desc">Bayesian + weighted ensemble fusion → risk score → band → action. Full audit trail returned.</div></div>
    </div>
  </div>
</section>

<footer>
  <div class="container">
    TruthGuard · MENACRAFT · Orchestrator API v3.0 running on <a href="http://localhost:8001" target="_blank">localhost:8001</a> ·
    <a href="http://localhost:8001/docs" target="_blank">Swagger UI</a>
  </div>
</footer>

<script>
const API = 'http://localhost:8001';

let state = {
  step:1, inputTab:'file', file:null, urlVal:'', textVal:'',
  nature:null, goals:new Set(),
  platform:'', author:'', sourceUrl:'', postText:'',
  plan:null, result:null,
};

/* ── API health check ── */
async function checkApiHealth() {
  const badge   = document.getElementById('api-badge');
  const badgeText = document.getElementById('api-badge-text');
  try {
    const r = await fetch(API + '/health', { signal: AbortSignal.timeout(3000) });
    if (r.ok) {
      badge.className = 'api-badge online';
      badge.querySelector('.dot').classList.add('pulse');
      badgeText.textContent = 'API v3.0';
      return true;
    }
  } catch {}
  badge.className = 'api-badge offline';
  badgeText.textContent = 'API offline';
  return false;
}
checkApiHealth();
setInterval(checkApiHealth, 15000);

/* ── Data ── */
const NATURES = [
  {id:'social_post_screenshot',icon:'📸',label:'Social Post Screenshot',desc:'Screenshot of a tweet, Facebook post, Telegram message, etc.',color:'--pink',triggers:'VISION + TEXT + URL + NETWORK'},
  {id:'raw_image',icon:'🖼️',label:'Photo / Image',desc:'Original photo, graphic, or illustration — not a screenshot.',color:'--blue',triggers:'VISION'},
  {id:'meme',icon:'😂',label:'Meme',desc:'Image with embedded text. Check context + claims in the text.',color:'--orange',triggers:'VISION + TEXT + CONTEXT'},
  {id:'chat_screenshot',icon:'💬',label:'Chat Screenshot',desc:'WhatsApp, Signal, DM thread, etc.',color:'--accent',triggers:'VISION + TEXT + CONTEXT'},
  {id:'news_article',icon:'📰',label:'News Article',desc:'Published article, blog post, or news site content.',color:'--amber',triggers:'TEXT + SOURCE + URL'},
  {id:'scientific_claim',icon:'🔬',label:'Scientific Claim',desc:'Paper, study, statistic, or technical assertion.',color:'--green',triggers:'TEXT + CLAIM VERIFY + CONTEXT'},
  {id:'government_document',icon:'🏛️',label:'Government / Official Doc',desc:'Government statement, legal document, official announcement.',color:'--blue',triggers:'TEXT + SOURCE + CLAIM'},
  {id:'video_clip',icon:'🎬',label:'Video Clip',desc:'Video file or clip — includes audio transcription.',color:'--purple',triggers:'VIDEO + TEXT + CONTEXT'},
  {id:'advertisement',icon:'📢',label:'Advertisement',desc:'Paid ad, sponsored content, or promotional material.',color:'--pink',triggers:'TEXT + CLAIM + SOURCE'},
  {id:'url_link',icon:'🔗',label:'URL / Link',desc:'Just a link — we scrape the page and analyse the content.',color:'--orange',triggers:'URL + TEXT + SOURCE'},
  {id:'audio_clip',icon:'🎵',label:'Audio Clip',desc:'Voice message, podcast excerpt, or audio recording.',color:'--accent',triggers:'TEXT (ASR) + LINGUISTIC'},
  {id:'unknown',icon:'❓',label:'Not Sure',desc:'Let the system auto-detect based on file type.',color:'--text2',triggers:'AUTO'},
];

const GOALS = [
  {id:'authenticity',icon:'🔬',label:'Content Authenticity',desc:'Is this real, AI-generated, or manipulated? Pixel/ELA/EXIF forensics.',color:'--accent',agent:'image_forensics + linguistic'},
  {id:'contextual_consistency',icon:'🔄',label:'Contextual Consistency',desc:'Is this image/video being used in a misleading context? Reverse-check.',color:'--blue',agent:'context_agent'},
  {id:'source_credibility',icon:'🏛️',label:'Source Credibility',desc:'Can we trust where this came from? WHOIS, domain age, fake-news DB.',color:'--amber',agent:'source_cred'},
  {id:'claim_verification',icon:'📋',label:'Claim Verification',desc:'Are the factual claims in this content verifiable? RAG knowledge-base.',color:'--purple',agent:'claim_extract + claim_verify'},
  {id:'network_analysis',icon:'🕸️',label:'Network & Bot Analysis',desc:'Is this being spread by bots? Coordinated inauthentic behaviour?',color:'--red',agent:'network_agent'},
  {id:'linguistic_analysis',icon:'🧠',label:'Linguistic Analysis',desc:'Is the text AI-written? Clickbait? Emotionally manipulative?',color:'--green',agent:'linguistic'},
  {id:'deepfake_detection',icon:'👤',label:'Deepfake Detection',desc:'Face-swap or GAN-generated video/image detection.',color:'--pink',agent:'video_forensics + image_forensics'},
  {id:'metadata_forensics',icon:'🗃️',label:'Metadata Forensics',desc:'EXIF data, codec info, edit history, hidden steganography.',color:'--orange',agent:'image_forensics'},
];

const AGENT_META = {
  image_forensics: {name:'Image Forensics',icon:'🔬',desc:'ELA · FFT · EXIF anomaly detection',weight:0.14},
  video_forensics: {name:'Video Forensics',icon:'🎬',desc:'Deepfake · keyframe · codec analysis',weight:0.14},
  claim_extract:   {name:'Claim Extractor',icon:'📋',desc:'OCR → factual claim extraction',weight:0.00},
  claim_verify:    {name:'Claim Verifier (RAG)',icon:'✅',desc:'Knowledge-base cross-reference',weight:0.22},
  source_cred:     {name:'Source Credibility',icon:'🏛️',desc:'WHOIS · domain age · fake-news DB',weight:0.18},
  context_agent:   {name:'Context Agent',icon:'🔄',desc:'Temporal coherence · knowledge graph',weight:0.12},
  network_agent:   {name:'Network Agent',icon:'🕸️',desc:'Bot probability · propagation pattern',weight:0.10},
  linguistic:      {name:'Linguistic Agent',icon:'🧠',desc:'Clickbait · AI-written text · manipulation',weight:0.10},
};

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
  buildNatureGrid(); buildGoalsGrid(); setupDropzone();
});

function buildNatureGrid() {
  document.getElementById('nature-grid').innerHTML = NATURES.map(n => `
    <div class="choice-card" data-nature="${n.id}" onclick="selectNature(this,'${n.id}')" style="--c:var(${n.color})">
      <div class="card-icon">${n.icon}</div>
      <div class="card-body">
        <div class="card-title">${n.label}</div>
        <div class="card-desc">${n.desc}</div>
        <div style="margin-top:6px;font-family:var(--font-m);font-size:9px;color:var(${n.color});letter-spacing:.5px;">${n.triggers}</div>
      </div>
      <div class="card-check"></div>
    </div>`).join('');
}

function buildGoalsGrid() {
  document.getElementById('goals-grid').innerHTML = GOALS.map(g => `
    <div class="choice-card" data-goal="${g.id}" onclick="toggleGoal(this,'${g.id}')" style="--c:var(${g.color})">
      <div class="card-icon">${g.icon}</div>
      <div class="card-body">
        <div class="card-title">${g.label}</div>
        <div class="card-desc">${g.desc}</div>
        <div style="margin-top:6px;font-family:var(--font-m);font-size:9px;color:var(--text3);letter-spacing:.3px;">Agents: ${g.agent}</div>
      </div>
      <div class="card-check"></div>
    </div>`).join('');
}

/* ── Tabs & dropzone ── */
function setInputTab(btn, tab) {
  state.inputTab = tab;
  ['file','url','text'].forEach(t => {
    document.getElementById('input-'+t).style.display = t===tab ? 'block' : 'none';
    const b = document.getElementById('tab-'+t);
    b.className = t===tab ? 'btn btn-primary' : 'btn btn-ghost';
    b.style.padding = '7px 16px'; b.style.fontSize = '13px';
  });
}
function setupDropzone() {
  const dz = document.getElementById('dropzone');
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('over'));
  dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('over'); if(e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });
}
function onFile() { const f=document.getElementById('file-input').files[0]; if(f) setFile(f); }
function setFile(f) {
  state.file=f;
  document.getElementById('file-name-label').textContent = f.name+' ('+(f.size/1024).toFixed(1)+' KB)';
  document.getElementById('file-pill').style.display='inline-flex';
}

/* ── Step nav ── */
function goStep(n) {
  if (n>1) {
    if (state.inputTab==='file' && !state.file) { alert('Please upload a file first.'); return; }
    if (state.inputTab==='url'  && !document.getElementById('url-val').value.trim()) { alert('Please enter a URL.'); return; }
    if (state.inputTab==='text' && !document.getElementById('text-val').value.trim()) { alert('Please enter some text.'); return; }
  }
  if (n>2 && !state.nature) { alert('Please select what kind of content this is.'); return; }
  if (n>3 && state.goals.size===0) { alert('Please select at least one analysis goal.'); return; }

  state.urlVal    = document.getElementById('url-val').value.trim();
  state.textVal   = document.getElementById('text-val').value.trim();
  state.platform  = document.getElementById('platform-val').value.trim();
  state.author    = document.getElementById('author-val').value.trim();
  state.sourceUrl = document.getElementById('source-url-val').value.trim();
  state.postText  = document.getElementById('post-text-val').value.trim();
  state.step = n;

  for (let i=1;i<=4;i++) {
    const ps=document.getElementById('ps-'+i);
    ps.classList.remove('active','done');
    if (i<n) { ps.classList.add('done'); ps.querySelector('.prog-num').textContent='✓'; }
    else if (i===n) { ps.classList.add('active'); ps.querySelector('.prog-num').textContent=i; }
    else ps.querySelector('.prog-num').textContent=i;
  }
  document.querySelectorAll('.step-panel').forEach(p=>p.classList.remove('active'));
  const sp=document.getElementById('step-'+n);
  if (sp) sp.classList.add('active');
}

function selectNature(card, id) {
  document.querySelectorAll('[data-nature]').forEach(c=>{c.classList.remove('selected');c.querySelector('.card-check').textContent='';});
  card.classList.add('selected'); card.querySelector('.card-check').textContent='✓';
  state.nature=id;
  document.getElementById('btn-step2').disabled=false;
  const n=NATURES.find(x=>x.id===id);
  document.getElementById('nature-footer').textContent=`"${n.label}" — activates: ${n.triggers}`;
  const needsEnrich=['social_post_screenshot','meme','chat_screenshot','news_article','url_link','advertisement'].includes(id);
  document.getElementById('enrichment-fields').style.display=needsEnrich?'block':'none';
  const needsText=['social_post_screenshot','meme','chat_screenshot'].includes(id);
  document.getElementById('post-text-field').style.display=needsText?'block':'none';
}

function toggleGoal(card, id) {
  if (state.goals.has(id)) { state.goals.delete(id); card.classList.remove('selected'); card.querySelector('.card-check').textContent=''; }
  else { state.goals.add(id); card.classList.add('selected'); card.querySelector('.card-check').textContent='✓'; }
  const cnt=state.goals.size;
  document.getElementById('goals-footer').innerHTML=`<strong id="goal-count">${cnt}</strong> goal${cnt!==1?'s':''} selected`;
  document.getElementById('btn-step3').disabled=cnt===0;
}

/* ── Build plan — API only, no local fallback ── */
async function buildPlan() {
  state.platform  = document.getElementById('platform-val').value.trim();
  state.author    = document.getElementById('author-val').value.trim();
  state.sourceUrl = document.getElementById('source-url-val').value.trim();
  state.postText  = document.getElementById('post-text-val').value.trim();

  const inputType = state.inputTab==='url' ? 'url'
    : state.file ? detectInputType(state.file.name) : 'document';

  const fd = new FormData();
  fd.append('input_type', inputType);
  fd.append('content_nature', state.nature);
  fd.append('analysis_goals', JSON.stringify([...state.goals]));
  if (state.sourceUrl) fd.append('source_url', state.sourceUrl);
  if (state.postText)  fd.append('post_text',  state.postText);

  // Disable button while fetching
  const btn = document.getElementById('btn-step3');
  btn.disabled = true;
  btn.textContent = 'Contacting API…';

  try {
    const r = await fetch(API + '/analyse/plan', { method:'POST', body:fd });
    if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`);
    state.plan = await r.json();
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Build Agent Plan →';
    showError(
      'Cannot Reach Orchestrator',
      'The plan could not be fetched because the API at <code>localhost:8001</code> is not responding.',
      `POST /analyse/plan failed\n${err.message}\n\nFix: run  python orchestrator_api.py`
    );
    return;
  }

  btn.disabled = false;
  btn.textContent = 'Build Agent Plan →';
  renderPlan(state.plan);
  goStep(4);
}

function detectInputType(filename) {
  const ext=(filename||'').split('.').pop().toLowerCase();
  if (['jpg','jpeg','png','webp','gif','bmp','tiff'].includes(ext)) return 'image';
  if (['mp4','mov','avi','webm','mkv','3gp'].includes(ext)) return 'video';
  if (['pdf','docx','doc','txt','md'].includes(ext)) return 'document';
  return 'image';
}

/* ── Render plan ── */
function renderPlan(plan) {
  document.getElementById('plan-grid').innerHTML = Object.entries(AGENT_META).map(([id,m]) => {
    const active=plan[id];
    return `<div class="agent-row ${active?'active':'inactive'}">
      <div class="agent-dot"></div>
      <div style="font-size:18px;flex-shrink:0;">${m.icon}</div>
      <div class="agent-info"><div class="agent-name">${m.name}</div><div class="agent-desc">${m.desc}</div></div>
      <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
        <span class="agent-badge ${active?'badge-active':'badge-skip'}">${active?'ACTIVE':'SKIP'}</span>
        ${m.weight>0?`<span class="agent-weight">weight: ${m.weight}</span>`:''}
      </div>
    </div>`;
  }).join('');

  document.getElementById('reasons-body').innerHTML=(plan.reasons||[]).map(r=>`<div class="reason-item">${r}</div>`).join('');

  const activeCount=Object.entries(AGENT_META).filter(([id])=>plan[id]).length;
  document.getElementById('active-count').textContent=activeCount;
  const pipes=new Set();
  if(plan.image_forensics) pipes.add('VISION');
  if(plan.video_forensics) pipes.add('VIDEO');
  if(plan.claim_extract||plan.claim_verify||plan.linguistic) pipes.add('TEXT');
  if(plan.source_cred||plan.network_agent) pipes.add('URL');
  document.getElementById('pipeline-count').textContent=pipes.size;
}

/* ── Run analysis — API only, hard error on failure ── */
async function runAnalysis() {
  const stages=buildStages();
  document.getElementById('stage-list').innerHTML=stages.map((s,i)=>`
    <div class="stage-item" id="stage-${i}"><div class="stage-dot"></div> ${s.label}</div>`).join('');

  document.querySelectorAll('.step-panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('error-panel').classList.remove('show');
  document.getElementById('results-panel').classList.remove('show');
  document.getElementById('loading-panel').classList.add('show');

  const timer=animateStages(stages.length);

  const inputType=state.inputTab==='url' ? 'url'
    : state.file ? detectInputType(state.file.name) : 'document';

  const fd=new FormData();
  fd.append('input_type', inputType);
  fd.append('content_nature', state.nature);
  fd.append('analysis_goals', JSON.stringify([...state.goals]));
  if (state.sourceUrl) fd.append('source_url', state.sourceUrl);
  if (state.postText)  fd.append('post_text',  state.postText);
  if (state.platform)  fd.append('platform',   state.platform);
  if (state.author)    fd.append('author_handle', state.author);
  if (state.file)      fd.append('file', state.file);
  if (state.urlVal)    fd.append('source_url',  state.urlVal);

  let result;
  try {
    const r = await fetch(API + '/analyse', { method:'POST', body:fd });
    if (!r.ok) {
      const body = await r.text();
      throw new Error(`HTTP ${r.status} — ${body}`);
    }
    result = await r.json();
  } catch (err) {
    clearInterval(timer);
    document.getElementById('loading-panel').classList.remove('show');
    showError(
      'Analysis Failed',
      'The orchestrator returned an error or could not be reached. Check that the API and all agent dependencies are running.',
      `POST /analyse failed\n${err.message}`
    );
    return;
  }

  clearInterval(timer);
  document.querySelectorAll('.stage-item').forEach(el=>{
    el.classList.remove('running'); el.classList.add('done');
    el.querySelector('.stage-dot').textContent='';
  });
  await new Promise(r=>setTimeout(r,400));

  document.getElementById('loading-panel').classList.remove('show');
  state.result=result;
  renderResults(result);
  document.getElementById('results-panel').classList.add('show');
  document.getElementById('results-panel').scrollIntoView({behavior:'smooth',block:'start'});
}

function buildStages() {
  const p=state.plan||{};
  const stages=[{label:'Routing input through preprocessing pipeline'}];
  if(p.claim_extract)  stages.push({label:'Claim Extractor: extracting factual statements'});
  if(p.image_forensics)stages.push({label:'Image Forensics: ELA · FFT · EXIF analysis'});
  if(p.video_forensics)stages.push({label:'Video Forensics: deepfake · keyframe analysis'});
  if(p.source_cred)    stages.push({label:'Source Credibility: WHOIS · domain reputation'});
  if(p.network_agent)  stages.push({label:'Network Agent: bot probability · propagation'});
  if(p.linguistic)     stages.push({label:'Linguistic Agent: clickbait · AI-text detection'});
  if(p.claim_verify)   stages.push({label:'Claim Verifier: RAG knowledge-base lookup'});
  if(p.context_agent)  stages.push({label:'Context Agent: temporal · knowledge-graph check'});
  stages.push({label:'Evidence fusion: Bayesian + weighted ensemble'});
  stages.push({label:'Decision engine: action · band · confidence'});
  return stages;
}

function animateStages(count) {
  let i=0;
  return setInterval(()=>{
    if(i>0){const prev=document.getElementById('stage-'+(i-1));if(prev){prev.classList.remove('running');prev.classList.add('done');}}
    const cur=document.getElementById('stage-'+i);if(cur)cur.classList.add('running');
    i++; if(i>=count) clearInterval(arguments.callee);
  },900);
}

/* ── Error panel ── */
function showError(title, msg, detail) {
  document.getElementById('loading-panel').classList.remove('show');
  document.querySelectorAll('.step-panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('error-title').textContent = title;
  document.getElementById('error-msg').innerHTML = msg;
  document.getElementById('error-detail').innerHTML = `<strong>Details</strong>${detail.replace(/\n/g,'<br>')}`;
  document.getElementById('error-panel').classList.add('show');
}

function retryFromPlan() {
  document.getElementById('error-panel').classList.remove('show');
  goStep(4);
}

/* ── Render results ── */
function renderResults(res) {
  renderVerdict(res);
  renderChips(res.active_pipelines||[]);
  renderAgentCards(res.agent_results||{});
  renderAuditTrail(res);
}

function renderVerdict(res) {
  const emojis={GREEN:'✅',AMBER:'⚠️',ORANGE:'🚨',RED:'🛑'};
  document.getElementById('verdict-wrap').innerHTML=`
    <div class="verdict ${res.risk_band}">
      <div class="verdict-emoji">${emojis[res.risk_band]||'❓'}</div>
      <div class="verdict-main">
        <div class="verdict-label">${res.label}</div>
        <div class="verdict-explain">${res.explanation}</div>
      </div>
      <div class="verdict-scores">
        <div class="score-block"><div class="score-num">${Math.round(res.risk_score*100)}%</div><div class="score-lbl">Risk Score</div></div>
        <div class="score-block"><div class="score-num">${Math.round(res.confidence*100)}%</div><div class="score-lbl">Confidence</div></div>
        <div class="score-block"><div class="score-num" style="font-size:14px;margin-top:4px;">${(res.action||'').replace('-','‑')}</div><div class="score-lbl">Action</div></div>
        <div class="score-block"><div class="score-num" style="font-size:14px;margin-top:4px;">${res.processing_time_ms}ms</div><div class="score-lbl">Run Time</div></div>
      </div>
    </div>`;
}

function renderChips(pipelines) {
  const icons={VISION:'🔭',TEXT:'📝',VIDEO:'🎬',URL:'🔗'};
  document.getElementById('pipeline-chips').innerHTML=`<div class="tag-label">Active Pipelines</div>`+
    pipelines.map(p=>`<div class="chip ${p}">${icons[p]||''} ${p}</div>`).join('');
}

function renderAgentCards(results) {
  const cards=[];
  for (const [id,res] of Object.entries(results)) {
    const m=AGENT_META[id]; if(!m) continue;
    cards.push(buildAgentCard(id,m,res));
  }
  if (results.claim_extract && results.claim_verify) cards.push(buildClaimCard(results.claim_extract,results.claim_verify));
  document.getElementById('agents-grid').innerHTML=cards.join('');
}

function riskToColor(s){return s<0.25?'GREEN':s<0.5?'AMBER':s<0.75?'ORANGE':'RED';}
function riskToLabel(s){return s<0.25?'LOW':s<0.5?'MEDIUM':'HIGH';}

function buildAgentCard(id, m, res) {
  if (id==='claim_extract'||id==='claim_verify') return '';
  const risk = res.risk_score ?? res.bot_probability
    ?? (1-(res.overall_score ?? res.overall_consistency_score ?? 0.5))
    ?? ((res.clickbait_score||0)*0.55+(res.ai_generated_score||0)*0.45) ?? 0.5;
  const color=riskToColor(risk), level=riskToLabel(risk);
  const findings=[];
  if(res.anomalies?.length)     res.anomalies.forEach(a=>findings.push({t:'red',text:a}));
  if(res.red_flags?.length)     res.red_flags.forEach(f=>findings.push({t:'amber',text:f}));
  if(res.temporal_issues?.length) res.temporal_issues.forEach(t=>findings.push({t:'amber',text:t}));
  if(res.exif_consistent===false) findings.push({t:'red',text:'EXIF metadata inconsistency detected'});
  if(res.exif_consistent===true)  findings.push({t:'green',text:'EXIF metadata consistent with source'});
  if(res.is_screenshot) findings.push({t:'blue',text:'UI fingerprint: screenshot border detected — activating OCR claim pipeline'});
  if(res.deepfake_probability!==undefined) findings.push({t:res.deepfake_probability>0.5?'red':'green',text:`Deepfake probability: ${Math.round(res.deepfake_probability*100)}%`});
  if(res.domain) findings.push({t:res.overall_score>0.6?'green':'amber',text:`Domain: ${res.domain} · ${res.domain_age_days}d old · SSL: ${res.has_ssl?'yes':'NO'}`});
  if(res.bot_probability!==undefined) findings.push({t:res.bot_probability>0.5?'red':'green',text:`Bot probability: ${Math.round(res.bot_probability*100)}% · Pattern: ${res.propagation_pattern}`});
  if(res.clickbait_score!==undefined) findings.push({t:res.clickbait_score>0.5?'red':'green',text:`Clickbait score: ${Math.round(res.clickbait_score*100)}% · AI-gen: ${Math.round(res.ai_generated_score*100)}%`});
  if(!findings.length) findings.push({t:'green',text:'No anomalies detected by this agent'});
  return `<div class="agent-card">
    <div class="agent-card-head">
      <div class="agent-card-icon" style="background:var(--surface2);">${m.icon}</div>
      <div class="agent-card-title">${m.name}</div>
      <span class="risk-badge rb-${level}">${level}</span>
    </div>
    <div class="agent-card-body">
      <div class="bar-wrap">
        <div class="bar-label"><span>Risk</span><strong>${Math.round(risk*100)}%</strong></div>
        <div class="bar-track"><div class="bar-fill ${color}" style="width:${Math.round(risk*100)}%"></div></div>
      </div>
      ${findings.slice(0,4).map(f=>`<div class="finding"><div class="finding-bullet ${f.t}"></div><span>${f.text}</span></div>`).join('')}
    </div>
  </div>`;
}

function buildClaimCard(extract, verify) {
  const statusColors={VERIFIED:'green',UNVERIFIED:'amber',CONTRADICTED:'red',PARTIALLY_VERIFIED:'blue'};
  const statusLabel={VERIFIED:'✅ Verified',UNVERIFIED:'❓ Unverified',CONTRADICTED:'❌ Contradicted',PARTIALLY_VERIFIED:'⚡ Partially verified'};
  if (!extract.claims||extract.claims.length===0) {
    return `<div class="agent-card" style="grid-column:1/-1">
      <div class="agent-card-head">
        <div class="agent-card-icon" style="background:var(--surface2);">📋</div>
        <div class="agent-card-title">Claim Extraction & Verification</div>
        <span class="risk-badge rb-LOW">NO CLAIMS</span>
      </div>
      <div class="agent-card-body">
        <div style="color:var(--text2);font-size:13px;line-height:1.6;padding:8px 0;">
          ${extract.note||'No text was found to extract claims from.'}
        </div>
      </div>
    </div>`;
  }
  const items=(verify.verifications||[]).map(v=>`
    <div style="padding:12px 14px;border-radius:10px;margin-bottom:8px;border:1px solid var(--border);background:var(--bg);">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:700;color:var(--${statusColors[v.status]});">${statusLabel[v.status]||v.status}</span>
        <span style="font-family:var(--font-m);font-size:10px;color:var(--text3);">confidence: ${Math.round((v.support_score||v.confidence||0)*100)}%</span>
      </div>
      <div style="font-size:13px;color:var(--text);line-height:1.55;">"${v.claim_text}"</div>
      ${v.explanation?`<div style="font-size:11px;color:var(--text2);margin-top:6px;">${v.explanation}</div>`:''}
    </div>`).join('');
  const verifiedCount=verify.verified_count||0, total=verify.verifications?.length||0;
  const badgeColor=verifiedCount===total?'LOW':verifiedCount===0?'HIGH':'MEDIUM';
  const extractLabel=extract.extraction_method==='llm'?'Groq LLM':extract.extraction_method==='heuristic'?'heuristic':'extraction';
  return `<div class="agent-card" style="grid-column:1/-1">
    <div class="agent-card-head">
      <div class="agent-card-icon" style="background:var(--surface2);">📋</div>
      <div class="agent-card-title">
        Claim Extraction & Verification
        <span style="font-size:11px;font-weight:400;color:var(--text2);margin-left:8px;">via ${extractLabel} · ${extract.total_claims} claim${extract.total_claims!==1?'s':''} found</span>
      </div>
      <span class="risk-badge rb-${badgeColor}">${verifiedCount}/${total} verified</span>
    </div>
    <div class="agent-card-body">${items||'<div style="color:var(--text2);font-size:13px;">No claims to verify.</div>'}</div>
  </div>`;
}

function renderAuditTrail(res) {
  const audit=res.audit_trail||{};
  const notes=[
    `input_type = <em>${audit.input_type||'—'}</em>`,
    `content_nature = <em>${audit.content_nature||'—'}</em>  ← user-declared`,
    `analysis_goals = <em>[${(audit.analysis_goals||[]).join(', ')}]</em>`,
    `agents_activated = <em>[${(audit.agents_activated||[]).join(', ')}]</em>`,
    ...(res.routing_notes||[]).map(n=>`orchestrator: <em>${n}</em>`),
    `risk_score = <em>${res.risk_score}</em>   risk_band = <em>${res.risk_band}</em>`,
    `confidence = <em>${res.confidence}</em>   action = <em>${res.action}</em>`,
    `requires_human_review = <em>${res.requires_human_review}</em>`,
    `processing_time = <em>${res.processing_time_ms}ms</em>`,
  ];
  document.getElementById('audit-entries').innerHTML=notes.map((n,i)=>`
    <div class="audit-row">
      <div class="audit-n">${String(i+1).padStart(2,'0')}</div>
      <div class="audit-t">${n}</div>
    </div>`).join('');
}

function toggleAudit() {
  document.getElementById('audit-toggle').classList.toggle('open');
  document.getElementById('audit-entries').classList.toggle('show');
}

/* ── Restart ── */
function restart() {
  state={step:1,inputTab:'file',file:null,urlVal:'',textVal:'',nature:null,goals:new Set(),platform:'',author:'',sourceUrl:'',postText:'',plan:null,result:null};
  document.getElementById('file-input').value='';
  document.getElementById('file-pill').style.display='none';
  ['url-val','text-val','platform-val','author-val','source-url-val','post-text-val'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('enrichment-fields').style.display='none';
  document.querySelectorAll('.choice-card').forEach(c=>{c.classList.remove('selected');c.querySelector('.card-check').textContent='';});
  ['results-panel','error-panel','loading-panel'].forEach(id=>document.getElementById(id).classList.remove('show'));
  buildNatureGrid(); buildGoalsGrid();
  setInputTab(document.getElementById('tab-file'),'file');
  for(let i=1;i<=4;i++){const ps=document.getElementById('ps-'+i);ps.classList.remove('active','done');ps.querySelector('.prog-num').textContent=i;}
  goStep(1);
  window.scrollTo({top:0,behavior:'smooth'});
}
</script>
</body>
</html>