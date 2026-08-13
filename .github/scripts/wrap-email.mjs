#!/usr/bin/env node
// Wrap a converted markdown->HTML fragment in a mobile-first, card-based email template.
// Usage: node wrap-email.mjs <fragment.html> <output.html> <dateLabel>
import { readFileSync, writeFileSync } from "node:fs";

const [, , fragmentPath, outputPath, dateLabel] = process.argv;
const fragment = readFileSync(fragmentPath, "utf8");

const iconFor = (html) => {
  const t = html.toLowerCase();
  if (t.includes("microbiota") || t.includes("細菌") || t.includes("iga")) {
    return { src: "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f9a0.png", alt: "microbiota", label: "MICROBIOME" };
  }
  if (t.includes("development") || t.includes("発生") || t.includes("組織") || t.includes("hdac")) {
    return { src: "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f52c.png", alt: "morphology", label: "MORPHOLOGY" };
  }
  return { src: "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f42d.png", alt: "mouse immunology", label: "MOUSE IMMUNOLOGY" };
};

const parts = fragment.split(/<hr\s*\/?\s*>/i).map(s => s.trim()).filter(Boolean);
const intro = parts.shift() || "";

const hero = `
  <div class="hero">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
      <tr>
        <td class="hero-copy">
          <div class="kicker">LIFE SCIENCE DAILY</div>
          <div class="date">${dateLabel || "TODAY"}</div>
          ${intro}
        </td>
        <td class="hero-art" width="92" valign="top">
          <img src="https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72/1f9ec.png" width="64" height="64" alt="DNA" style="display:block;border:0;" />
        </td>
      </tr>
    </table>
  </div>`;

const cards = parts.map((section, index) => {
  const icon = iconFor(section);
  return `
  <div class="article-card">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" class="article-head">
      <tr>
        <td width="58" valign="top">
          <div class="icon-wrap"><img src="${icon.src}" width="36" height="36" alt="${icon.alt}" style="display:block;border:0;" /></div>
        </td>
        <td valign="middle">
          <div class="article-no">PAPER ${index + 1}</div>
          <div class="topic-label">${icon.label}</div>
        </td>
      </tr>
    </table>
    <div class="article-body">${section}</div>
  </div>`;
}).join("\n");

const html = `<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { margin:0; padding:0; background:#f3f5f8; font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Yu Gothic",Meiryo,sans-serif; color:#172033; }
  .wrapper { max-width:680px; margin:0 auto; padding:18px 10px 28px; }
  .hero { background:#172033; border-radius:20px; padding:24px 22px; margin-bottom:14px; box-shadow:0 8px 24px rgba(23,32,51,.12); }
  .hero-copy { padding-right:12px; }
  .hero-art { text-align:right; }
  .kicker { color:#a8b7d8; font-size:11px; font-weight:800; letter-spacing:.16em; margin-bottom:4px; }
  .date { color:#ffffff; font-size:13px; font-weight:700; margin-bottom:14px; }
  .hero h1 { color:#ffffff; font-size:23px; line-height:1.35; margin:0 0 14px; }
  .hero p { color:#e6ebf5; font-size:14.5px; line-height:1.75; margin:0; }
  .hero strong { color:#ffffff; }
  .article-card { background:#ffffff; border-radius:18px; padding:20px 20px 22px; margin:0 0 14px; border:1px solid #e6eaf0; box-shadow:0 3px 12px rgba(23,32,51,.05); }
  .article-head { margin-bottom:8px; }
  .icon-wrap { width:48px; height:48px; border-radius:14px; background:#f4f6fa; text-align:center; vertical-align:middle; padding:6px; box-sizing:border-box; }
  .article-no { color:#8a95a8; font-size:10px; line-height:1.2; font-weight:800; letter-spacing:.14em; }
  .topic-label { color:#35415a; font-size:12px; line-height:1.3; font-weight:800; margin-top:4px; }
  .article-body h2 { font-size:19px; line-height:1.5; color:#111827; margin:10px 0 10px; padding:0; background:none; border:0; }
  .article-body h3 { font-size:12px; line-height:1.4; color:#59657a; margin:19px 0 7px; text-transform:none; letter-spacing:.02em; }
  .article-body h3::before { content:"▸ "; color:#667eea; }
  .article-body p { font-size:14.5px; line-height:1.82; margin:6px 0 12px; color:#334155; }
  .article-body ul { padding-left:20px; margin:8px 0 12px; }
  .article-body li { font-size:14.5px; line-height:1.75; margin:5px 0; color:#334155; }
  .article-body strong { color:#111827; }
  .article-body em { color:#667085; }
  .article-body a { color:#4f46e5; text-decoration:none; border-bottom:1px solid #c7c5f7; word-break:break-word; }
  .footer { text-align:center; font-size:11px; line-height:1.6; color:#9aa4b4; padding:10px 8px 0; }
  @media only screen and (max-width:520px) {
    .wrapper { padding:10px 8px 20px !important; }
    .hero { border-radius:16px !important; padding:20px 16px !important; }
    .hero h1 { font-size:20px !important; }
    .hero-art { width:66px !important; }
    .hero-art img { width:50px !important; height:50px !important; }
    .article-card { border-radius:15px !important; padding:17px 15px 19px !important; }
    .article-body h2 { font-size:17px !important; }
    .article-body p, .article-body li { font-size:14px !important; line-height:1.78 !important; }
  }
</style>
</head>
<body>
<div class="wrapper">
${hero}
${cards}
  <p class="footer">免疫学・機能形態学 毎朝ダイジェスト<br>ChatGPT → GitHub → Email</p>
</div>
</body>
</html>`;

writeFileSync(outputPath, html);
