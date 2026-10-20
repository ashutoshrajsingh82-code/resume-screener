const test = require('node:test');
const assert = require('node:assert/strict');
const workflow = require('../../upload_workflow.js');

function file(name, size, type = '', lastModified = 1) {
    return { name, size, type, lastModified };
}

test('selects several supported files and deduplicates by filename', () => {
    const added = workflow.addResumeFiles([], [
        file('first.txt', 30, 'text/plain'),
        file('second.pdf', 40, 'application/pdf'),
        file('FIRST.txt', 31, 'text/plain', 2),
    ]);
    assert.equal(added.items.length, 2);
    assert.equal(added.duplicates, 1);
    assert.deepEqual(added.items.map((item) => item.status), ['ready', 'ready']);
});

test('individual removal leaves other selected files intact', () => {
    const added = workflow.addResumeFiles([], [file('first.txt', 30), file('second.docx', 40)]);
    const remaining = workflow.removeResumeFile(added.items, added.items[0].id);
    assert.equal(remaining.length, 1);
    assert.equal(remaining[0].file.name, 'second.docx');
});

test('validates extensions and MIME types where provided', () => {
    assert.match(workflow.validateResumeFile(file('resume.exe', 20))[0], /Unsupported file type/);
    assert.match(workflow.validateResumeFile(file('resume.pdf', 20, 'text/plain'))[0], /does not match/);
    assert.match(workflow.validateResumeFile(file('bad:name.txt', 20))[0], /filename is not allowed/);
    assert.deepEqual(workflow.validateResumeFile(file('resume.pdf', 20, 'application/octet-stream')), []);
});

test('rejects empty and oversized files with actionable messages', () => {
    assert.match(workflow.validateResumeFile(file('empty.txt', 0))[0], /empty/);
    assert.match(workflow.validateResumeFile(file('large.txt', workflow.DEFAULT_MAX_FILE_BYTES + 1))[0], /10 MB limit/);
});

test('does not allow invalid or busy submissions', () => {
    const invalid = workflow.addResumeFiles([], [file('bad.doc', 20)]).items;
    const valid = workflow.addResumeFiles([], [file('good.txt', 20)]).items;
    assert.equal(workflow.canSubmit('role', invalid, true, false), false);
    assert.equal(workflow.canSubmit('', valid, true, false), false);
    assert.equal(workflow.canSubmit('role', valid, false, false), false);
    assert.equal(workflow.canSubmit('role', valid, true, true), false);
    assert.equal(workflow.canSubmit('role', valid, true, false), true);
});

test('reports indeterminate processing and counts partial success', () => {
    const started = workflow.screeningReducer(workflow.initialScreeningState, { type: 'start', selected: 3, invalid: 1 });
    assert.equal(started.isLoading, true);
    assert.equal(workflow.screeningReducer(started, { type: 'start', selected: 3 }).isLoading, true);
    const done = workflow.screeningReducer(started, { type: 'success', results: { ranked_resumes: [{}] }, selected: 3, successful: 1 });
    assert.equal(done.isLoading, false);
    assert.equal(done.successful, 1);
    assert.equal(done.failed, 2);
});

test('recovers from a request error when a new screening attempt starts', () => {
    const failed = workflow.screeningReducer(workflow.initialScreeningState, { type: 'failure', selected: 2, error: 'Backend unavailable' });
    assert.equal(failed.error, 'Backend unavailable');
    assert.equal(failed.failed, 2);
    const retry = workflow.screeningReducer(failed, { type: 'start', selected: 2, invalid: 0 });
    assert.equal(retry.isLoading, true);
    assert.equal(retry.error, null);
});

test('formats backend scores consistently and sorts without mutating returned scores', () => {
    const returned = [
        { filename: 'semantic.txt', rank: 1, score: 0.7543, semantic_score: 0.91, skill_score: 0.5 },
        { filename: 'skills.txt', rank: 2, score: 0.7012, semantic_score: 0.61, skill_score: 1 },
    ];
    const originalScores = returned.map((item) => item.score);
    assert.equal(workflow.formatScorePercent(returned[0].score), '75.43%');
    assert.deepEqual(workflow.sortRankedResumes(returned, 'skill').map((item) => item.filename), ['skills.txt', 'semantic.txt']);
    assert.deepEqual(returned.map((item) => item.score), originalScores);
    assert.deepEqual(returned.map((item) => item.rank), [1, 2]);
});
