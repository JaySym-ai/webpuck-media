// Render a real PR (title, state, author, date, labels, description from the GitHub API) as a page.
const fs = require('fs'); const path = require('path'); const { marked } = require('marked');
const [,, itemFile, repo, outFile] = process.argv;
const it = JSON.parse(fs.readFileSync(itemFile, 'utf8'));
const css = fs.readFileSync(path.join(__dirname, 'node_modules/github-markdown-css/github-markdown-light.css'), 'utf8');
const d = new Date(it.created_at);
const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });
const [owner, name] = repo.split('/');
const labels = it.labels.map(l => `<span class="lbl" style="background:#${l.color}">${l.name}</span>`).join(' ');
const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}
body{margin:0;background:#fff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:#1f2328}
.top{border-bottom:1px solid #d1d9e0;padding:18px 18px 14px;background:#f6f8fa}
.path{font-size:22px;color:#1f2328}.path span{color:#59636e}
.wrap{max-width:1012px;margin:0 auto;padding:20px 18px 60px}
h1.t{font-size:28px;font-weight:400;margin:0 0 10px;line-height:1.25}h1.t .n{color:#59636e;font-weight:300}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:15px;color:#59636e;margin-bottom:18px;padding-bottom:16px;border-bottom:1px solid #d1d9e0}
.state{display:inline-flex;align-items:center;gap:6px;background:#59636e;color:#fff;border-radius:2em;padding:5px 12px;font-weight:500;font-size:14px}
.meta b{color:#1f2328}
.lbl{font-size:12px;font-weight:500;border-radius:2em;padding:2px 9px;color:#fff}
.box{border:1px solid #d1d9e0;border-radius:6px}
.boxh{background:#f6f8fa;border-bottom:1px solid #d1d9e0;padding:10px 16px;font-size:14px;color:#59636e;border-radius:6px 6px 0 0}
.markdown-body{font-size:16px;padding:16px 20px}
.src{font:13px ui-monospace,monospace;color:#59636e;margin-top:8px}
</style></head><body>
<div class="top"><div class="path"><span>${owner}</span> / <b>${name}</b></div><div class="src">github.com/${repo}/pull/${it.number}</div></div>
<div class="wrap"><h1 class="t">${it.title} <span class="n">#${it.number}</span></h1>
<div class="meta"><span class="state">${it.draft ? 'Draft' : it.state}</span><span><b>${it.user.login}</b> opened this pull request on ${date}</span>${labels}</div>
<div class="box"><div class="boxh"><b>${it.user.login}</b> commented on ${date}</div><article class="markdown-body">${marked.parse(it.body)}</article></div></div></body></html>`;
fs.writeFileSync(outFile, html); console.log('wrote', outFile);
