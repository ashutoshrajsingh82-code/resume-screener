const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..', '..');
const apiBase = process.env.RESUME_SCREENER_API || 'http://127.0.0.1:8000';
const frontendBase = process.env.RESUME_SCREENER_FRONTEND || 'http://127.0.0.1:8010';
const pageUrl = `${frontendBase}/?api=${encodeURIComponent(apiBase)}`;

async function run() {
    const browser = await chromium.launch({ channel: 'chrome', headless: true });
    try {
        const health = await fetch(`${apiBase}/health`);
        assert.equal(health.status, 200, 'FastAPI health endpoint must be available');
        assert.equal((await health.json()).model_loaded, true, 'sentence-transformer model must be initialized');

        const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
        const page = await context.newPage();
        const rankResponses = [];
        page.on('response', async (response) => {
            if (response.url().endsWith('/rank')) rankResponses.push(await response.json());
        });

        await page.goto(pageUrl, { waitUntil: 'domcontentloaded' });
        await page.locator('.backend-status.online').waitFor({ timeout: 15000 });
        await page.getByRole('button', { name: 'Use example role' }).click();
        await page.locator('#resume-files').setInputFiles([
            path.join(root, 'samples', 'resumes', 'strong_backend.txt'),
            path.join(root, 'samples', 'resumes', 'mid_django.txt'),
            path.join(root, 'docs', 'test_dataset', 'resumes', 'extraction_failures', 'malformed.pdf'),
        ]);
        assert.equal(await page.locator('.file-row').count(), 3, 'three selected files should be listed');
        await page.getByRole('button', { name: 'Run screening' }).click();
        await page.getByText('Screening completed with issues', { exact: true }).waitFor({ timeout: 60000 });
        assert.equal(await page.locator('.candidate-row').count(), 2, 'valid resumes should retain results after one failure');
        assert.match(await page.locator('.success-banner').innerText(), /2 successfully screened.*1 failed.*3 selected/s);
        assert.equal(rankResponses.length, 1);

        const firstResponse = rankResponses[0];
        assert.equal(firstResponse.ranked_resumes.length, 2);
        assert.equal(firstResponse.skipped[0].filename, 'malformed.pdf');
        for (const candidate of firstResponse.ranked_resumes) {
            const row = page.locator('.candidate-row').filter({ has: page.getByRole('heading', { name: candidate.filename }) });
            assert.equal(await row.locator('.score-block strong').innerText(), `${(candidate.score * 100).toFixed(2)}%`);
            assert.equal(await row.locator('.candidate-metrics').getByText(`${(candidate.semantic_score * 100).toFixed(2)}%`, { exact: true }).count(), 1);
        }

        const explanation = page.locator('.candidate-explanation').first();
        const explanationSummary = explanation.locator('summary');
        await explanationSummary.focus();
        await explanationSummary.press('Enter');
        await page.waitForFunction(() => document.querySelector('.candidate-explanation')?.open === true);
        await explanation.getByText('Detected in extracted text', { exact: true }).waitFor();
        await page.getByRole('checkbox', { name: 'Compare strong_backend.txt' }).check();
        await page.getByRole('checkbox', { name: 'Compare mid_django.txt' }).check();
        await page.getByRole('heading', { name: 'Candidate comparison' }).waitFor();
        assert.equal(await page.locator('.compare-candidate').count(), 2);

        await page.locator('#weight').focus();
        await page.keyboard.press('Home');
        await page.waitForFunction(() => document.querySelectorAll('.candidate-row').length === 2);
        await page.waitForTimeout(700);
        assert.equal(rankResponses.length, 2, 'changing the weight should trigger a real backend recalculation');
        assert.equal(rankResponses[1].effective_semantic_weight, 0);
        assert.equal(await page.locator('.weight-formula').innerText().then((s) => /0% meaning similarity/.test(s)), true);

        page.once('dialog', (dialog) => dialog.accept());
        await page.getByRole('button', { name: 'Clear screening session' }).click();
        await page.getByText('Results will appear here').waitFor();
        assert.equal(await page.locator('#jd').inputValue(), '');
        assert.equal(await page.locator('.file-row').count(), 0);
        assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);

        await page.getByRole('button', { name: 'Use example role' }).click();
        await page.locator('#resume-files').setInputFiles(path.join(root, 'docs', 'test_dataset', 'resumes', 'extraction_failures', 'malformed.pdf'));
        await page.getByRole('button', { name: 'Run screening' }).click();
        await page.getByText('No resumes were successfully screened', { exact: true }).waitFor({ timeout: 60000 });
        await page.getByRole('heading', { name: 'No resumes could be ranked' }).waitFor();

        const offlinePage = await context.newPage();
        await offlinePage.goto(`${frontendBase}/?api=http%3A%2F%2F127.0.0.1%3A1`, { waitUntil: 'domcontentloaded' });
        await offlinePage.getByText('Backend unavailable', { exact: true }).waitFor({ timeout: 15000 });
        assert.equal(await offlinePage.getByRole('button', { name: 'Run screening' }).isDisabled(), true);

        await offlinePage.close();
        await page.close();
        await context.close();
        console.log('PASS: built frontend + live FastAPI/model upload, partial success, backend score display, explanations, comparison, weight recalculation, session cleanup, and offline state.');
    } finally {
        await browser.close();
    }
}

run().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
