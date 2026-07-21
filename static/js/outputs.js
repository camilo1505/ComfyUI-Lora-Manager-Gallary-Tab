import { appCore } from './core.js';
import { state } from './state/index.js';
import { createPageControls } from './components/controls/index.js';

export class OutputsPageManager {
    constructor() {
        state.bulkMode = false;
        state.selectedLoras = new Set();

        const pageType = document.body.dataset.page || 'outputs';
        this.pageControls = createPageControls(pageType);
    }

    async initialize() {
        appCore.initializePageFeatures();
    }
}

export async function initializeOutputsPage() {
    await appCore.initialize();

    const outputsPage = new OutputsPageManager();
    await outputsPage.pageControls.initialize();
    await outputsPage.initialize();

    return outputsPage;
}

document.addEventListener('DOMContentLoaded', initializeOutputsPage);
