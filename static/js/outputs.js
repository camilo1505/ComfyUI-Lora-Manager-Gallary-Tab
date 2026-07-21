import { appCore } from './core.js';
import { state } from './state/index.js';
import { updateCardsForBulkMode } from './components/shared/ModelCard.js';
import { createPageControls } from './components/controls/index.js';
import { confirmDelete, closeDeleteModal, confirmExclude, closeExcludeModal } from './utils/modalUtils.js';
import { ModelDuplicatesManager } from './components/ModelDuplicatesManager.js';

export class OutputsPageManager {
    constructor() {
        state.bulkMode = false;
        state.selectedLoras = new Set();

        const pageType = document.body.dataset.page || 'outputs';
        this.pageControls = createPageControls(pageType);

        this.duplicatesManager = new ModelDuplicatesManager(this);

        this._exposeRequiredGlobalFunctions();
    }

    _exposeRequiredGlobalFunctions() {
        window.confirmDelete = confirmDelete;
        window.closeDeleteModal = closeDeleteModal;
        window.confirmExclude = confirmExclude;
        window.closeExcludeModal = closeExcludeModal;

        window.modelDuplicatesManager = this.duplicatesManager;
    }

    async initialize() {
        updateCardsForBulkMode(state.bulkMode);
        appCore.initializePageFeatures();
    }
}

export async function initializeOutputsPage() {
    await appCore.initialize();

    const outputsPage = new OutputsPageManager();
    await outputsPage.initialize();

    return outputsPage;
}

document.addEventListener('DOMContentLoaded', initializeOutputsPage);
