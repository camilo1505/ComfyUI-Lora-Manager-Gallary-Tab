import { state } from '../../state/index.js';
import { NSFW_LEVELS, getMatureBlurThreshold } from '../../utils/constants.js';
import { translate } from '../../utils/i18nHelpers.js';
import { modalManager } from '../../managers/ModalManager.js';

function getOutputFileName(output) {
    return output.filename || output.file_name || 'Unknown';
}

function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function getThumbnailUrl(relativePath) {
    return `/api/lm/outputs/thumbnail?path=${encodeURIComponent(relativePath)}&size=300`;
}

function getFullImageUrl(relativePath) {
    return `/outputs_static/${relativePath}`;
}

async function loadFullMetadata(relativePath) {
    try {
        const res = await fetch(`/api/lm/outputs/detail?path=${encodeURIComponent(relativePath)}`);
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

async function showCardModal(card) {
    const dataset = card.dataset;
    const relativePath = dataset.relative_path || '';

    if (!relativePath) return;

    const fullSrc = getFullImageUrl(relativePath);
    const fileName = dataset.file_name || 'Unknown';

    const content = `
        <div class="modal-content">
            <button class="close" onclick="modalManager.closeModal('modelModal')">&times;</button>
            <header class="modal-header">
                <div class="modal-header-row">
                    <div class="model-name-header">
                        <h2 class="model-name-content">${fileName}</h2>
                    </div>
                    <div class="modal-nav-controls" role="group">
                        <button class="modal-nav-btn" title="Previous"><i class="fas fa-chevron-left"></i></button>
                        <button class="modal-nav-btn" title="Next"><i class="fas fa-chevron-right"></i></button>
                    </div>
                </div>
            </header>
            <div class="modal-body output-modal-body">
                <img src="${fullSrc}" alt="${fileName}" class="output-modal-preview">
                <div class="output-modal-info">
                    <div class="info-section">
                        <div class="info-grid" id="outputDetailGrid">
                            <div class="info-item full-width">
                                <label>Prompt</label>
                                <div class="output-prompt-box" id="outputPromptBox"><span>Loading...</span></div>
                            </div>
                            <div class="info-item full-width">
                                <label>Negative Prompt</label>
                                <div class="output-prompt-box" id="outputNegPromptBox"><span>Loading...</span></div>
                            </div>
                        </div>
                    </div>
                    <div class="info-section" id="outputMetaSection">
                        <div class="info-grid" id="outputMetaGrid">
                            <div class="info-item"><label>Resolution</label><span id="detailResolution">${dataset.resolution || ''}</span></div>
                            <div class="info-item"><label>Sampler</label><span id="detailSampler">${dataset.sampler || ''}</span></div>
                            <div class="info-item"><label>CFG</label><span id="detailCfg">${dataset.cfg || ''}</span></div>
                            <div class="info-item"><label>Steps</label><span id="detailSteps">${dataset.steps || ''}</span></div>
                            <div class="info-item"><label>Seed</label><code id="detailSeed">${dataset.seed || ''}</code></div>
                            <div class="info-item"><label>Model</label><span id="detailCheckpoint">${dataset.checkpoint || ''}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    modalManager.showModal('modelModal', content, null, () => {});

    const fullData = await loadFullMetadata(relativePath);
    if (fullData) {
        const promptBox = document.getElementById('outputPromptBox');
        const negBox = document.getElementById('outputNegPromptBox');
        if (promptBox) {
            const prompt = fullData.prompt || '';
            promptBox.innerHTML = prompt
                ? `<span>${prompt.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>')}</span><i class="fas fa-copy output-copy-icon"></i>`
                : '<span>No prompt metadata</span>';
            promptBox.dataset.copy = prompt.replace(/"/g, '&quot;');
        }
        if (negBox) {
            const neg = fullData.negative_prompt || '';
            negBox.innerHTML = neg
                ? `<span>${neg.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</span><i class="fas fa-copy output-copy-icon"></i>`
                : '<span>No negative prompt metadata</span>';
            negBox.dataset.copy = neg.replace(/"/g, '&quot;');
        }
        const detailCfg = document.getElementById('detailCfg');
        if (detailCfg && fullData.cfg != null) detailCfg.textContent = fullData.cfg;
        const detailSteps = document.getElementById('detailSteps');
        if (detailSteps && fullData.steps != null) detailSteps.textContent = fullData.steps;
        const detailSeed = document.getElementById('detailSeed');
        if (detailSeed && fullData.seed != null) detailSeed.textContent = fullData.seed;
        const detailCheckpoint = document.getElementById('detailCheckpoint');
        if (detailCheckpoint && fullData.checkpoint) detailCheckpoint.textContent = fullData.checkpoint;
        const detailResolution = document.getElementById('detailResolution');
        if (detailResolution && fullData.resolution) detailResolution.textContent = fullData.resolution;
        const detailSampler = document.getElementById('detailSampler');
        if (detailSampler && fullData.sampler) detailSampler.textContent = fullData.sampler;

        setupCopyIcons();
    } else {
        const promptBox = document.getElementById('outputPromptBox');
        const negBox = document.getElementById('outputNegPromptBox');
        if (promptBox) promptBox.innerHTML = '<span>No prompt metadata</span>';
        if (negBox) negBox.innerHTML = '<span>No negative prompt metadata</span>';
    }
}

function setupCopyIcons() {
    document.querySelectorAll('.output-prompt-box[data-copy]').forEach(el => {
        el.addEventListener('click', () => {
            const val = el.dataset.copy;
            if (!val) return;
            navigator.clipboard.writeText(val);
            const icon = el.querySelector('.output-copy-icon');
            if (icon) {
                icon.className = 'fas fa-check output-copy-icon';
                setTimeout(() => { icon.className = 'fas fa-copy output-copy-icon'; }, 1500);
            }
        });
    });
}

export function setupOutputCardEventDelegation() {
    const grid = document.getElementById('modelGrid');
    if (!grid || grid.dataset.outputEventsSet) return;
    grid.dataset.outputEventsSet = '1';

    grid.addEventListener('click', (event) => {
        const card = event.target.closest('.model-card');
        if (!card || !card.classList.contains('output-card')) return;

        if (event.target.closest('.output-blur-toggle')) {
            event.stopPropagation();
            const preview = card.querySelector('.card-preview');
            const isBlurred = preview.classList.toggle('blurred');
            const icon = card.querySelector('.output-blur-toggle');
            icon.className = isBlurred ? 'fas fa-eye-slash output-blur-toggle' : 'fas fa-eye output-blur-toggle';
            const overlay = card.querySelector('.nsfw-overlay');
            if (overlay) overlay.style.display = isBlurred ? 'flex' : 'none';
            return;
        }

        if (event.target.closest('.show-content-btn')) {
            event.stopPropagation();
            const preview = card.querySelector('.card-preview');
            preview.classList.remove('blurred');
            const eyeIcon = card.querySelector('.output-blur-toggle');
            if (eyeIcon) eyeIcon.className = 'fas fa-eye output-blur-toggle';
            const overlay = card.querySelector('.nsfw-overlay');
            if (overlay) overlay.style.display = 'none';
            return;
        }

        if (event.target.closest('.fa-download')) {
            event.stopPropagation();
            const relativePath = card.dataset.relative_path || '';
            const filename = card.dataset.file_name || 'download.png';
            if (relativePath) {
                downloadFile(getFullImageUrl(relativePath), filename);
            }
            return;
        }

        if (!event.target.closest('.card-actions, .toggle-blur-btn, .show-content-btn, .nsfw-overlay')) {
            event.stopPropagation();
            if (state.bulkMode) {
                const path = card.dataset.filepath;
                if (state.selectedLoras.has(path)) {
                    state.selectedLoras.delete(path);
                    card.classList.remove('selected');
                } else {
                    state.selectedLoras.add(path);
                    card.classList.add('selected');
                }
            } else {
                showCardModal(card);
            }
            return;
        }
    });
}

export function createOutputCard(output) {
    const card = document.createElement('div');
    card.className = 'model-card output-card';
    card.draggable = true;
    card.dataset.filepath = output.file_path || '';
    card.dataset.relative_path = output.relative_path || '';
    card.dataset.file_name = output.filename || output.file_name || '';
    card.dataset.folder = output.folder || '';
    card.dataset.file_size = output.size || output.file_size || 0;
    card.dataset.resolution = output.resolution || '';
    card.dataset.sampler = output.sampler || '';
    card.dataset.cfg = String(output.cfg ?? '');
    card.dataset.steps = String(output.steps ?? '');
    card.dataset.seed = String(output.seed ?? '');
    card.dataset.has_metadata = output.has_metadata ? 'true' : 'false';
    card.dataset.checkpoint = output.checkpoint || '';

    const nsfwLevel = output.preview_nsfw_level !== undefined ? output.preview_nsfw_level : 0;
    card.dataset.nsfwLevel = nsfwLevel;

    const matureBlurThreshold = getMatureBlurThreshold(state.settings);
    const shouldBlur = state.settings.blur_mature_content && nsfwLevel >= matureBlurThreshold;
    if (shouldBlur) {
        card.classList.add('nsfw-content');
    }

    const relativePath = output.relative_path || '';
    const thumbUrl = getThumbnailUrl(relativePath);

    let nsfwText = translate('modelCard.nsfw.matureContent', {}, 'Mature Content');
    if (nsfwLevel >= NSFW_LEVELS.XXX) {
        nsfwText = translate('modelCard.nsfw.xxxRated', {}, 'XXX-rated Content');
    } else if (nsfwLevel >= NSFW_LEVELS.X) {
        nsfwText = translate('modelCard.nsfw.xRated', {}, 'X-rated Content');
    } else if (nsfwLevel >= NSFW_LEVELS.R) {
        nsfwText = translate('modelCard.nsfw.rRated', {}, 'R-rated Content');
    }

    const toggleBlurTitle = translate('modelCard.actions.toggleBlur', {}, 'Toggle blur');
    const showButtonText = translate('modelCard.actions.show', {}, 'Show');

    const hasMetadata = output.has_metadata;
    const metaIcon = hasMetadata ? 'fa-circle-check' : 'fa-circle-xmark';
    const metaTitle = hasMetadata
        ? translate('outputs.metadataAvailable', {}, 'Metadata available')
        : translate('outputs.metadataUnavailable', {}, 'Metadata unavailable');
    const metaIconClass = hasMetadata ? 'meta-available' : 'meta-unavailable';

    const resolution = output.resolution || '';
    const resolutionDisplay = resolution ? `Res | ${resolution}` : 'Res | ?';

    card.innerHTML = `
        <div class="card-preview ${shouldBlur ? 'blurred' : ''}">
            <img src="${thumbUrl}" alt="${getOutputFileName(output)}" loading="lazy"
                 onerror="this.onerror=null; this.src='/loras_static/images/no-preview.png'">
            <div class="card-header">
                <div class="card-header-info">
                    <span class="base-model-label output-resolution-label"
                          title="${resolutionDisplay}">
                        <span class="model-base-type">${resolutionDisplay}</span>
                    </span>
                    <span class="output-meta-badge" title="${metaTitle}">
                        <i class="fas ${metaIcon} ${metaIconClass}"></i>
                    </span>
                </div>
                <div class="card-actions">
                    <i class="far fa-heart output-action" title="Favorite"></i>
                    <i class="fas fa-download output-action" title="Download"></i>
                    <i class="fas fa-eye output-blur-toggle" title="Toggle blur"></i>
                </div>
            </div>
            ${shouldBlur ? `
                <div class="nsfw-overlay">
                    <div class="nsfw-warning">
                        <p>${nsfwText}</p>
                        <button class="show-content-btn">${showButtonText}</button>
                    </div>
                </div>
            ` : ''}
            <div class="card-footer">
                <div class="model-info">
                    <span class="model-name" title="${getOutputFileName(output).replace(/"/g, '&quot;')}">${getOutputFileName(output)}</span>
                    <div class="version-row output-params">
                        <span class="badge-version-unit">
                            ${output.sampler ? `<span class="param-badge" title="Sampler"><i class="fas fa-brush"></i> ${output.sampler}</span>` : ''}
                            ${output.cfg != null ? `<span class="param-badge" title="CFG"><i class="fas fa-sliders"></i> ${output.cfg}</span>` : ''}
                            ${output.steps != null ? `<span class="param-badge" title="Steps"><i class="fas fa-shoe-prints"></i> ${output.steps}</span>` : ''}
                            ${output.seed != null ? `<span class="param-badge" title="Seed"><i class="fas fa-dice"></i> ${output.seed}</span>` : ''}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    `;

    return card;
}
