/* Shared upload validation and state transitions for the browser UI and Node tests. */
(function (root, factory) {
    const workflow = factory();
    if (typeof module !== 'undefined' && module.exports) module.exports = workflow;
    if (root) root.ResumeUploadWorkflow = workflow;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    const DEFAULT_MAX_FILE_BYTES = 10 * 1024 * 1024;
    const TYPES = {
        pdf: ['application/pdf', 'application/x-pdf'],
        docx: ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        txt: ['text/plain'],
    };

    function fileId(file) {
        return `${file.name}|${file.size}|${file.lastModified || 0}`;
    }

    function limitLabel(bytes) {
        if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(bytes % (1024 * 1024) ? 1 : 0)} MB`;
        if (bytes >= 1024) return `${Math.ceil(bytes / 1024)} KB`;
        return `${bytes} bytes`;
    }

    function validateResumeFile(file, maxBytes = DEFAULT_MAX_FILE_BYTES) {
        const errors = [];
        const name = typeof file.name === 'string' ? file.name : '';
        const extension = name.includes('.') ? name.split('.').pop().toLowerCase() : '';
        if (!Object.prototype.hasOwnProperty.call(TYPES, extension)) {
            errors.push('Unsupported file type. Choose a PDF, DOCX, or TXT resume.');
            return errors;
        }
        if (!name || name.length > 255 || /[<>:"|?*\\/\u0000-\u001f]/.test(name) || name === '.' || name === '..') {
            errors.push('This filename is not allowed. Rename the file and select it again.');
        }
        const mime = (file.type || '').split(';')[0].trim().toLowerCase();
        if (mime && mime !== 'application/octet-stream' && !TYPES[extension].includes(mime)) {
            errors.push(`The file type (${mime}) does not match its .${extension} extension.`);
        }
        if (!Number.isFinite(file.size) || file.size <= 0) errors.push('This file is empty. Select a non-empty resume.');
        else if (file.size > maxBytes) errors.push(`This file is larger than the ${limitLabel(maxBytes)} limit.`);
        return errors;
    }

    function addResumeFiles(existing, incoming, maxBytes = DEFAULT_MAX_FILE_BYTES) {
        const items = [...existing];
        const errors = [];
        const seenIds = new Set(items.map((item) => item.id));
        const seenNames = new Set(items.map((item) => item.file.name.toLocaleLowerCase()));
        let duplicates = 0;
        for (const file of Array.from(incoming || [])) {
            const id = fileId(file);
            const normalizedName = String(file.name || '').toLocaleLowerCase();
            if (seenIds.has(id) || seenNames.has(normalizedName)) {
                duplicates += 1;
                continue;
            }
            seenIds.add(id);
            seenNames.add(normalizedName);
            const fileErrors = validateResumeFile(file, maxBytes);
            items.push({ id, file, errors: fileErrors, status: fileErrors.length ? 'invalid' : 'ready' });
            errors.push(...fileErrors.map((message) => `${file.name || 'Selected file'}: ${message}`));
        }
        return { items, added: items.length - existing.length, errors, duplicates };
    }

    function removeResumeFile(items, id) {
        return items.filter((item) => item.id !== id);
    }

    function canSubmit(jdText, items, backendReady, isLoading, maxBytes = DEFAULT_MAX_FILE_BYTES) {
        return Boolean(jdText && jdText.trim() && items.some((item) => validateResumeFile(item.file, maxBytes).length === 0) && backendReady && !isLoading);
    }

    const initialScreeningState = {
        isLoading: false,
        results: null,
        error: null,
        selected: 0,
        successful: 0,
        failed: 0,
    };

    function screeningReducer(state, action) {
        switch (action.type) {
            case 'inputs-changed':
                return { ...initialScreeningState, selected: action.selected, failed: action.invalid || 0 };
            case 'start':
                if (state.isLoading) return state;
                return { ...state, isLoading: true, error: null, results: null, selected: action.selected, successful: 0, failed: action.invalid || 0 };
            case 'success':
                return { ...state, isLoading: false, error: null, results: action.results, selected: action.selected, successful: action.successful, failed: Math.max(0, action.selected - action.successful) };
            case 'failure':
                return { ...state, isLoading: false, results: null, error: action.error, selected: action.selected, successful: 0, failed: action.selected };
            default:
                return state;
        }
    }

    function fileSizeLabel(bytes) {
        if (!Number.isFinite(bytes) || bytes <= 0) return '0 bytes';
        if (bytes < 1024) return `${bytes} bytes`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10 * 1024 ? 1 : 0)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function formatScorePercent(score) {
        return `${(score * 100).toFixed(2)}%`;
    }

    function sortRankedResumes(items, sortBy = 'rank') {
        return [...items].sort((a, b) => {
            if (sortBy === 'filename') return a.filename.localeCompare(b.filename);
            if (sortBy === 'rank') return a.rank - b.rank;
            const field = sortBy === 'score' ? 'score' : sortBy === 'semantic' ? 'semantic_score' : 'skill_score';
            if (a[field] === null) return b[field] === null ? 0 : 1;
            if (b[field] === null) return -1;
            return b[field] - a[field];
        });
    }

    return { DEFAULT_MAX_FILE_BYTES, TYPES, fileId, validateResumeFile, addResumeFiles, removeResumeFile, canSubmit, initialScreeningState, screeningReducer, fileSizeLabel, formatScorePercent, sortRankedResumes };
});
