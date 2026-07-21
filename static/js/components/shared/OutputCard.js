import { state, getCurrentPageState } from '../../state/index.js';
import { NSFW_LEVELS, getMatureBlurThreshold } from '../../utils/constants.js';
import { translate } from '../../utils/i18nHelpers.js';

function getOutputFileName(output) {
    return output.file_name || 'Unknown';
}

export function setupOutputCardEventDelegation() {
}

export function createOutputCard(output) {
    const card = document.createElement('div');
    card.className = 'model-card output-card';
    card.draggable = true;
    card.dataset.filepath = output.file_path || '';
    card.dataset.file_name = output.file_name || '';
    card.dataset.folder = output.folder || '';
    card.dataset.file_size = output.file_size || 0;
    card.dataset.resolution = output.resolution || '';
    card.dataset.sampler = output.sampler || '';
    card.dataset.cfg = String(output.cfg ?? '');
    card.dataset.steps = String(output.steps ?? '');
    card.dataset.seed = String(output.seed ?? '');
    card.dataset.has_metadata = output.has_metadata ? 'true' : 'false';

    const nsfwLevel = output.preview_nsfw_level !== undefined ? output.preview_nsfw_level : 0;
    card.dataset.nsfwLevel = nsfwLevel;

    const matureBlurThreshold = getMatureBlurThreshold(state.settings);
    const shouldBlur = state.settings.blur_mature_content && nsfwLevel >= matureBlurThreshold;
    if (shouldBlur) {
        card.classList.add('nsfw-content');
    }

    const previewUrl = output.preview_url || '/loras_static/images/no-preview.png';

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
            <img src="${previewUrl}" alt="${getOutputFileName(output)}"
                 onerror="this.onerror=null; this.src='/loras_static/images/no-preview.png'">
            <div class="card-header">
                ${shouldBlur ?
            `<button class="toggle-blur-btn" title="${toggleBlurTitle}">
                      <i class="fas fa-eye"></i>
                  </button>` : ''}
                <div class="card-header-info">
                    <span class="base-model-label output-resolution-label ${shouldBlur ? 'with-toggle' : ''}"
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
                    <i class="fas fa-eye-slash output-action" title="Mark as sensitive"></i>
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
