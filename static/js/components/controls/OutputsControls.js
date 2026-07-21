import { setCurrentPageType, getCurrentPageState, state } from '../../state/index.js';
import { sidebarManager } from '../SidebarManager.js';
import { initSortDropdown } from './SortDropdown.js';
import { refreshVirtualScroll } from '../../utils/infiniteScroll.js';

function buildTreeFromFolders(folders) {
    const tree = {};
    for (const folder of folders) {
        const parts = folder.split('/');
        let node = tree;
        for (const part of parts) {
            if (!node[part]) node[part] = {};
            node = node[part];
        }
    }
    return tree;
}

function getSelectedFilePaths() {
    const cards = document.querySelectorAll('.model-card.output-card.selected');
    return Array.from(cards).map(c => ({
        path: c.dataset.filepath,
        name: c.dataset.file_name,
        preview: c.querySelector('img')?.src || '',
    }));
}

function downloadFile(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function setupBulkContextMenu() {
    const menu = document.getElementById('bulkContextMenu');
    if (!menu || menu.dataset.outputsReady) return;
    menu.dataset.outputsReady = '1';
    menu.innerHTML = `
        <div class="context-menu-item" data-action="download-selected"><i class="fas fa-download"></i> Download Selected</div>
        <div class="context-menu-item delete-item" data-action="delete-selected"><i class="fas fa-trash"></i> Delete Selected</div>
    `;
    menu.addEventListener('click', async (e) => {
        const item = e.target.closest('.context-menu-item');
        if (!item) return;
        e.stopPropagation();
        e.stopImmediatePropagation();
        e.preventDefault();
        const action = item.dataset.action;
        if (action === 'download-selected') {
            const items = getSelectedFilePaths();
            for (const it of items) {
                if (it.preview && !it.preview.includes('no-preview.png')) {
                    downloadFile(it.preview, it.name);
                    await new Promise(r => setTimeout(r, 200));
                }
            }
        }
        if (action === 'delete-selected') {
            const items = getSelectedFilePaths();
            if (!items.length) return;
            if (!confirm(`Delete ${items.length} selected image(s)?`)) return;
            let deleted = 0;
            for (const it of items) {
                try {
                    const res = await fetch(`/api/lm/outputs/delete?path=${encodeURIComponent(it.path)}`, { method: 'DELETE' });
                    if (res.ok) deleted++;
                } catch (err) { console.error('Delete failed:', it.name, err); }
            }
            if (deleted > 0) await refreshVirtualScroll();
        }
    });
}

export class OutputsControls {
    constructor(pageType) {
        setCurrentPageType(pageType);
        this.pageType = pageType;
        this.pageState = getCurrentPageState();

        this.pageState.pageSize = 100;
        this.pageState.isLoading = false;
        this.pageState.hasMore = true;

        this.sidebarManager = sidebarManager;

        this._initSort();
        this._initBulk();
        this._initRefresh();
        this._initContextMenu();

        window.pageControls = this;
    }

    async initialize() {
        await this._initSidebar();
    }

    _initSort() {
        const sortSelect = document.getElementById('sortSelect');
        if (sortSelect) {
            initSortDropdown(sortSelect);
            sortSelect.addEventListener('change', async () => {
                this.pageState.sortBy = sortSelect.value;
                await this._onRefresh();
            });
        }
    }

    _initBulk() {
        const bulkBtn = document.getElementById('bulkOperationsBtn');
        if (!bulkBtn) return;
        bulkBtn.addEventListener('click', () => {
            state.bulkMode = !state.bulkMode;
            document.body.classList.toggle('bulk-mode', state.bulkMode);
            bulkBtn.classList.toggle('active', state.bulkMode);
            if (!state.bulkMode) {
                document.querySelectorAll('.model-card.output-card.selected').forEach(c => c.classList.remove('selected'));
                state.selectedLoras.clear();
            }
        });
    }

    _initRefresh() {
        const refreshBtn = document.getElementById('refreshButton');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this._onRefresh());
        }
    }

    _initContextMenu() {
        setupBulkContextMenu();
    }

    async _initSidebar() {
        await this.sidebarManager.initialize(this);
    }

    async _onRefresh() {
        await refreshVirtualScroll();
    }

    async resetAndReload(updateFolders) {
        if (this.pageState.searchOptions) {
            this.pageState.searchOptions.recursive = this.sidebarManager.recursiveSearchEnabled;
        }
        this.pageState.activeFolder = this.sidebarManager.selectedPath || '';
        await refreshVirtualScroll();
    }

    getSidebarApiClient() {
        return {
            apiConfig: { config: { displayName: 'Outputs' } },
            async fetchUnifiedFolderTree() {
                const res = await fetch('/api/lm/outputs/list?page_size=1');
                const data = await res.json();
                const folders = data.folders || [];
                return { success: true, tree: buildTreeFromFolders(folders) };
            },
            async fetchModelFolders() {
                const res = await fetch('/api/lm/outputs/list?page_size=1');
                const data = await res.json();
                return { folders: data.folders || [] };
            },
            async loadMoreWithVirtualScroll() { await refreshVirtualScroll(); },
            async moveSingleModel() {},
            async moveBulkModels() { return []; },
        };
    }
}
