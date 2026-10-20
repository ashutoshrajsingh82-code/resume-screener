const fs = require('node:fs');
const path = require('node:path');
const babel = require('@babel/standalone');

const root = path.resolve(__dirname, '..');
const output = path.join(root, 'dist');
const indexPath = path.join(root, 'index.html');
const html = fs.readFileSync(indexPath, 'utf8');
const jsxMatch = html.match(/<script type="text\/babel">([\s\S]*?)<\/script>/i);

if (!jsxMatch) {
    throw new Error('Could not find the application JSX script in index.html.');
}

const appJs = babel.transform(jsxMatch[1], {
    filename: 'resume-screener.jsx',
    presets: ['react'],
    sourceType: 'script',
}).code;

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(path.join(output, 'app.js'), appJs);
fs.copyFileSync(path.join(root, 'style.css'), path.join(output, 'style.css'));
fs.copyFileSync(path.join(root, 'upload_workflow.js'), path.join(output, 'upload_workflow.js'));
fs.copyFileSync(path.join(root, 'node_modules/react/umd/react.production.min.js'), path.join(output, 'react.production.min.js'));
fs.copyFileSync(path.join(root, 'node_modules/react-dom/umd/react-dom.production.min.js'), path.join(output, 'react-dom.production.min.js'));

const productionHtml = html
    .replace(/\s*<script src="https:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/react\/18\.3\.1\/umd\/react\.production\.min\.js"><\/script>/, '')
    .replace(/\s*<script src="https:\/\/cdnjs\.cloudflare\.com\/ajax\/libs\/react-dom\/18\.3\.1\/umd\/react-dom\.production\.min\.js"><\/script>/, '')
    .replace(/\s*<script src="https:\/\/cdn\.jsdelivr\.net\/npm\/@babel\/standalone@7\.26\.4\/babel\.min\.js"><\/script>/, '')
    .replace('<script src="upload_workflow.js"></script>', '<script src="react.production.min.js"></script>\n    <script src="react-dom.production.min.js"></script>\n    <script src="upload_workflow.js"></script>')
    .replace(jsxMatch[0], '<script src="app.js" defer></script>');

fs.writeFileSync(path.join(output, 'index.html'), productionHtml);
console.log(`Production frontend written to ${path.relative(root, output)}.`);
