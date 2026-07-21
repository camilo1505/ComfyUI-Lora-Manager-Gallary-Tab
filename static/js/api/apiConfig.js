import { state } from '../state/index.js';

/**
 * API Configuration
 * Centralized configuration for all model types and their endpoints
 */

// Model type definitions
export const MODEL_TYPES = {
    LORA: 'loras',
    CHECKPOINT: 'checkpoints',
    EMBEDDING: 'embeddings',
    OUTPUTS: 'outputs'
};

// Base API configuration for each model type
export const MODEL_CONFIG = {
    [MODEL_TYPES.LORA]: {
        displayName: 'LoRA',
        singularName: 'lora',
        defaultPageSize: 100,
        supportsLetterFilter: true,
        supportsBulkOperations: true,
        supportsMove: true,
        templateName: 'loras.html'
    },
    [MODEL_TYPES.CHECKPOINT]: {
        displayName: 'Checkpoint',
        singularName: 'checkpoint',
        defaultPageSize: 100,
        supportsLetterFilter: false,
        supportsBulkOperations: true,
        supportsMove: true,
        templateName: 'checkpoints.html'
    },
    [MODEL_TYPES.EMBEDDING]: {
        displayName: 'Embedding',
        singularName: 'embedding',
        defaultPageSize: 100,
        supportsLetterFilter: true,
        supportsBulkOperations: true,
        supportsMove: true,
        templateName: 'embeddings.html'
    },
    [MODEL_TYPES.OUTPUTS]: {
        displayName: 'Outputs',
        singularName: 'output',
        defaultPageSize: 100,
        supportsLetterFilter: true,
        supportsBulkOperations: true,
        supportsMove: true,
        templateName: 'outputs.html'
    }
};

/**
 * Generate API endpoints for a given model type
 * @param {string} modelType - The model type (e.g., 'loras', 'checkpoints')
 * @returns {Object} Object containing all API endpoints for the model type
 */
export function getApiEndpoints(modelType) {
    if (!Object.values(MODEL_TYPES).includes(modelType)) {
        throw new Error(`Invalid model type: ${modelType}`);
    }

    const apiPrefix = modelType;

    return {
        // Base CRUD operations
        list: `/api/lm/${apiPrefix}/list`,
        excluded: `/api/lm/${apiPrefix}/excluded`,
        delete: `/api/lm/${apiPrefix}/delete`,
        exclude: `/api/lm/${apiPrefix}/exclude`,
        unexclude: `/api/lm/${apiPrefix}/unexclude`,
        rename: `/api/lm/${apiPrefix}/rename`,
        save: `/api/lm/${apiPrefix}/save-metadata`,
        cancelTask: `/api/lm/${apiPrefix}/cancel-task`,

        // Bulk operations
        bulkDelete: `/api/lm/${apiPrefix}/bulk-delete`,

        // Tag operations
        addTags: `/api/lm/${apiPrefix}/add-tags`,

        // Move operations (now common for all model types that support move)
        moveModel: `/api/lm/${apiPrefix}/move_model`,
        moveBulk: `/api/lm/${apiPrefix}/move_models_bulk`,

        // CivitAI integration
        fetchCivitai: `/api/lm/${apiPrefix}/fetch-civitai`,
        fetchAllCivitai: `/api/lm/${apiPrefix}/fetch-all-civitai`,
        relinkCivitai: `/api/lm/${apiPrefix}/relink-civitai`,
        civitaiVersions: `/api/lm/${apiPrefix}/civitai/versions`,
        refreshUpdates: `/api/lm/${apiPrefix}/updates/refresh`,
        fetchMissingLicenses: `/api/lm/${apiPrefix}/updates/fetch-missing-license`,
        modelUpdateStatus: `/api/lm/${apiPrefix}/updates/status`,
        modelUpdateVersions: `/api/lm/${apiPrefix}/updates/versions`,
        ignoreModelUpdate: `/api/lm/${apiPrefix}/updates/ignore`,
        ignoreVersionUpdate: `/api/lm/${apiPrefix}/updates/ignore-version`,

        // Preview management
        replacePreview: `/api/lm/${apiPrefix}/replace-preview`,
        setPreviewFromUrl: `/api/lm/${apiPrefix}/set-preview-from-url`,

        // Query operations
        scan: `/api/lm/${apiPrefix}/scan`,
        topTags: `/api/lm/${apiPrefix}/top-tags`,
        searchTags: `/api/lm/${apiPrefix}/search-tags`,
        baseModels: `/api/lm/${apiPrefix}/base-models`,
        modelTypes: `/api/lm/${apiPrefix}/model-types`,
        roots: `/api/lm/${apiPrefix}/roots`,
        folders: `/api/lm/${apiPrefix}/folders`,
        folderTree: `/api/lm/${apiPrefix}/folder-tree`,
        unifiedFolderTree: `/api/lm/${apiPrefix}/unified-folder-tree`,
        duplicates: `/api/lm/${apiPrefix}/find-duplicates`,
        conflicts: `/api/lm/${apiPrefix}/find-filename-conflicts`,
        verify: `/api/lm/${apiPrefix}/verify-duplicates`,
        metadata: `/api/lm/${apiPrefix}/metadata`,
        modelDescription: `/api/lm/${apiPrefix}/model-description`,

        // Auto-organize operations
        autoOrganize: `/api/lm/${apiPrefix}/auto-organize`,
        autoOrganizeProgress: `/api/lm/${apiPrefix}/auto-organize-progress`,

        // Model-specific endpoints (will be merged with specific configs)
        specific: {}
    };
}

/**
 * Model-specific endpoint configurations
 */
export const MODEL_SPECIFIC_ENDPOINTS = {
    [MODEL_TYPES.LORA]: {
        letterCounts: `/api/lm/${MODEL_TYPES.LORA}/letter-counts`,
        notes: `/api/lm/${MODEL_TYPES.LORA}/get-notes`,
        triggerWords: `/api/lm/${MODEL_TYPES.LORA}/get-trigger-words`,
        previewUrl: `/api/lm/${MODEL_TYPES.LORA}/preview-url`,
        civitaiUrl: `/api/lm/${MODEL_TYPES.LORA}/civitai-url`,
        metadata: `/api/lm/${MODEL_TYPES.LORA}/metadata`,
        getTriggerWordsPost: `/api/lm/${MODEL_TYPES.LORA}/get_trigger_words`,
        civitaiModelByVersion: `/api/lm/${MODEL_TYPES.LORA}/civitai/model/version`,
        civitaiModelByHash: `/api/lm/${MODEL_TYPES.LORA}/civitai/model/hash`,
    },
    [MODEL_TYPES.CHECKPOINT]: {
        info: `/api/lm/${MODEL_TYPES.CHECKPOINT}/info`,
        checkpoints_roots: `/api/lm/${MODEL_TYPES.CHECKPOINT}/checkpoints_roots`,
        unet_roots: `/api/lm/${MODEL_TYPES.CHECKPOINT}/unet_roots`,
        metadata: `/api/lm/${MODEL_TYPES.CHECKPOINT}/metadata`,
    },
    [MODEL_TYPES.EMBEDDING]: {
        metadata: `/api/lm/${MODEL_TYPES.EMBEDDING}/metadata`,
    },
    [MODEL_TYPES.OUTPUTS]: {
        letterCounts: `/api/lm/${MODEL_TYPES.LORA}/letter-counts`,
        notes: `/api/lm/${MODEL_TYPES.LORA}/get-notes`,
        triggerWords: `/api/lm/${MODEL_TYPES.LORA}/get-trigger-words`,
        previewUrl: `/api/lm/${MODEL_TYPES.LORA}/preview-url`,
        civitaiUrl: `/api/lm/${MODEL_TYPES.LORA}/civitai-url`,
        metadata: `/api/lm/${MODEL_TYPES.LORA}/metadata`,
        getTriggerWordsPost: `/api/lm/${MODEL_TYPES.LORA}/get_trigger_words`,
        civitaiModelByVersion: `/api/lm/${MODEL_TYPES.LORA}/civitai/model/version`,
        civitaiModelByHash: `/api/lm/${MODEL_TYPES.LORA}/civitai/model/hash`,
    }
};

/**
 * Get complete API configuration for a model type
 * @param {string} modelType - The model type
 * @returns {Object} Complete API configuration
 */
export function getCompleteApiConfig(modelType) {
    const baseEndpoints = getApiEndpoints(modelType);
    const specificEndpoints = MODEL_SPECIFIC_ENDPOINTS[modelType] || {};
    const config = MODEL_CONFIG[modelType];

    return {
        modelType,
        config,
        endpoints: {
            ...baseEndpoints,
            specific: specificEndpoints
        }
    };
}

/**
 * Validate if a model type is supported
 * @param {string} modelType - The model type to validate
 * @returns {boolean} True if valid, false otherwise
 */
export function isValidModelType(modelType) {
    return Object.values(MODEL_TYPES).includes(modelType);
}

/**
 * Get model type from current page or explicit parameter
 * @param {string} [explicitType] - Explicitly provided model type
 * @returns {string} The model type
 */
export function getCurrentModelType(explicitType = null) {
    if (explicitType && isValidModelType(explicitType)) {
        return explicitType;
    }

    return state.currentPageType || MODEL_TYPES.LORA;
}

// Download API endpoints (shared across all model types)
export const DOWNLOAD_ENDPOINTS = {
    download: '/api/lm/download-model',
    downloadGet: '/api/lm/download-model-get',
    cancelGet: '/api/lm/cancel-download-get',
    progress: '/api/lm/download-progress',
    exampleImages: '/api/lm/force-download-example-images' // New endpoint for downloading example images
};

// Hugging Face API endpoints
export const HF_ENDPOINTS = {
    repoFiles: '/api/lm/hf-repo-files',
    download: '/api/lm/download-hf-model',
};

// WebSocket endpoints
export const WS_ENDPOINTS = {
    fetchProgress: '/ws/fetch-progress'
};
