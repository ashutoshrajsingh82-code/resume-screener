const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const test = require('node:test');
const { chromium } = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;

const root = path.resolve(__dirname, '..');
let browser;
const pageUrl = pathToFileURL(path.join(root, 'index.html')).href;
const frameworkAssets = [
    ['**/react.production.min.js', path.join(root, 'node_modules', 'react', 'umd', 'react.production.min.js')],
    ['**/react-dom.production.min.js', path.join(root, 'node_modules', 'react-dom', 'umd', 'react-dom.production.min.js')],
    ['**/babel.min.js', path.join(root, 'node_modules', '@babel', 'standalone', 'babel.min.js')],
];

test.before(async () => {
    browser = await chromium.launch({ channel: 'chrome', headless: true });
});

test.after(async () => {
    if (browser) await browser.close();
});

async function openDashboard(viewport) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    await routeLocalFramework(page);
    await page.goto(pageUrl, { waitUntil: 'domcontentloaded' });
    await page.locator('#page-title').waitFor({ state: 'visible', timeout: 20000 });
    return page;
}

async function routeLocalFramework(page) {
    for (const [pattern, file] of frameworkAssets) {
        await page.route(pattern, (route) => route.fulfill({
            status: 200,
            contentType: 'application/javascript; charset=utf-8',
            body: fs.readFileSync(file),
        }));
    }
}

for (const viewport of [
    { width: 1365, height: 900 },
    { width: 768, height: 1024 },
    { width: 375, height: 812 },
]) {
    test(`axe accessibility and responsive layout at ${viewport.width}px`, async () => {
        const page = await openDashboard(viewport);
        const results = await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
            .analyze();
        assert.deepEqual(results.violations.map(({ id, impact, help, nodes }) => ({ id, impact, help, targets: nodes.map((node) => node.target), snippets: nodes.map((node) => node.html) })), []);
        const dimensions = await page.evaluate(() => ({
            documentWidth: document.documentElement.scrollWidth,
            viewportWidth: document.documentElement.clientWidth,
        }));
        assert.ok(dimensions.documentWidth <= dimensions.viewportWidth, `horizontal overflow: ${JSON.stringify(dimensions)}`);
        await page.close();
    });
}

test('keyboard order reaches the job description and upload control with visible focus', async () => {
    const page = await openDashboard({ width: 1280, height: 900 });
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.className), 'brand');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Screening');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Results');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Check connection');
    await page.keyboard.press('Tab');
    assert.match(await page.evaluate(() => document.activeElement.textContent.trim()), /How results work/);
    await page.keyboard.press('Tab');
    assert.match(await page.evaluate(() => document.activeElement.textContent.trim()), /Privacy and responsible use/);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.textContent.trim()), 'Use example role');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'jd');
    await page.keyboard.press('Tab');
    assert.match(await page.evaluate(() => document.activeElement.textContent.trim()), /privacy details/);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'resume-files');
    const focusStyle = await page.locator('.dropzone').evaluate((element) => getComputedStyle(element).outlineStyle);
    assert.equal(focusStyle, 'solid');
    await page.close();
});

test('populated results controls remain accessible and clearing resumes is confirmed', async () => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const page = await context.newPage();
    await routeLocalFramework(page);
    await page.route('**/health', (route) => route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ model_loaded: true, max_upload_bytes: 10485760 }),
    }));
    await page.route('**/rank', (route) => route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
            ranked_resumes: [
                { rank: 1, filename: 'example_one.txt', score: 0.81, semantic_score: 0.8, skill_score: 0.82, raw_similarity: 0.5, matched_skills: ['python'], explicit_matched_skills: ['python'], implied_matched_skills: [], missing_skills: ['sql'] },
                { rank: 2, filename: 'example_two.txt', score: 0.62, semantic_score: 0.6, skill_score: 0.65, raw_similarity: 0.4, matched_skills: ['sql'], explicit_matched_skills: ['sql'], implied_matched_skills: [], missing_skills: ['python'] },
            ],
            jd_skills: ['python', 'sql'], skipped: [], effective_semantic_weight: 0.6,
        }),
    }));
    await page.goto(pageUrl, { waitUntil: 'domcontentloaded' });
    await page.locator('#page-title').waitFor({ state: 'visible', timeout: 20000 });
    await page.locator('.privacy-note summary').click();
    const privacyCopy = await page.locator('.privacy-note').innerText();
    assert.match(privacyCopy, /sends the selected file bytes and job description/i);
    assert.match(privacyCopy, /temporary storage/i);
    assert.match(privacyCopy, /must not make autonomous hiring decisions/i);
    await page.getByRole('button', { name: 'Use example role' }).click();
    await page.locator('#resume-files').setInputFiles(path.join(root, 'samples', 'resumes', 'strong_backend.txt'));
    await page.getByRole('button', { name: 'Run screening' }).click();
    await page.getByRole('heading', { name: 'Screening results' }).waitFor();
    await page.getByText('Screening complete', { exact: true }).waitFor();
    const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
    assert.deepEqual(results.violations.map(({ id, impact, help, nodes }) => ({ id, impact, help, targets: nodes.map((node) => node.target), snippets: nodes.map((node) => node.html) })), []);
    await page.once('dialog', (dialog) => dialog.accept());
    await page.getByRole('button', { name: 'Clear all resumes' }).click();
    await page.getByText('No resumes added yet.').waitFor();
    await page.once('dialog', (dialog) => dialog.accept());
    await page.getByRole('button', { name: 'Clear screening session' }).click();
    await page.locator('#jd').waitFor();
    assert.equal(await page.locator('#jd').inputValue(), '');
    await page.getByText('Results will appear here').waitFor();
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('#page-title').waitFor({ state: 'visible', timeout: 20000 });
    assert.equal(await page.locator('#jd').inputValue(), '');
    await page.getByText('No resumes added yet.').waitFor();
    await page.close();
});
