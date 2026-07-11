#!/usr/bin/env node
// Wrap a converted markdown->HTML fragment in a styled email template.
// Usage: node wrap-email.mjs <fragment.html> <output.html> <dateLabel>
import { readFileSync, writeFileSync } from "node:fs";

const [, , fragmentPath, outputPath, dateLabel] = process.argv;
const fragment = readFileSync(fragmentPath, "utf8");

const html = `<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { margin:0; padding:0; background:#eef1f6; font-family:-apple-system,BlinkMacSystemFont,"Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif; color:#1f2937; }
  .wrapper { max-width:640px; margin:0 auto; padding:20px 12px; }
  .eyebrow { font-size:12px; color:#4f46e5; font-weight:700; letter-spacing:.08em; margin:0 0 10px; padding-left:4px; }
  .card { background:#ffffff; border-radius:14px; padding:30px 28px; box-shadow:0 1px 4px rgba(15,23,42,0.08); }
  .card h1 { font-size:21px; margin:0 0 14px; color:#111827; padding-bottom:14px; border-bottom:3px solid #4f46e5; }
  .card h2 { font-size:16.5px; color:#111827; margin:26px 0 8px; padding:10px 12px; background:#eef2ff; border-left:4px solid #4f46e5; border-radius:6px; }
  .card h2:first-of-type { margin-top:6px; }
  .card h3 { font-size:13.5px; color:#4f46e5; margin:16px 0 4px; }
  .card p { font-size:14.5px; line-height:1.8; margin:6px 0 12px; }
  .card ul { padding-left:20px; margin:6px 0 12px; }
  .card li { font-size:14.5px; line-height:1.75; margin:5px 0; }
  .card strong { color:#111827; }
  .card em { color:#6b7280; }
  .card a { color:#4f46e5; text-decoration:none; border-bottom:1px solid rgba(79,70,229,.35); word-break:break-all; }
  .card hr { border:none; border-top:1px solid #e5e7eb; margin:26px 0; }
  .footer { text-align:center; font-size:11px; color:#9ca3af; padding:16px 4px 0; }
</style>
</head>
<body>
<div class="wrapper">
  <p class="eyebrow">LIFE SCIENCE DAILY DIGEST${dateLabel ? " ・ " + dateLabel : ""}</p>
  <div class="card">
${fragment}
  </div>
  <p class="footer">免疫学・機能形態学 毎朝ダイジェスト ／ Claude + GitHub Actions 自動配信</p>
</div>
</body>
</html>
`;

writeFileSync(outputPath, html);
