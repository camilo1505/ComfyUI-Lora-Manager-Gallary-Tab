// Controls components index file
import { PageControls } from './PageControls.js';
import { LorasControls } from './LorasControls.js';
import { CheckpointsControls } from './CheckpointsControls.js';
import { EmbeddingsControls } from './EmbeddingsControls.js';
import { OutputsControls } from './OutputsControls.js';

export { PageControls, LorasControls, CheckpointsControls, EmbeddingsControls, OutputsControls };

export function createPageControls(pageType) {
    if (pageType === 'loras') {
        return new LorasControls();
    } else if (pageType === 'checkpoints') {
        return new CheckpointsControls();
    } else if (pageType === 'embeddings') {
        return new EmbeddingsControls();
    } else if (pageType === 'outputs') {
        return new OutputsControls(pageType);
    } else {
        console.error(`Unknown page type: ${pageType}`);
        return null;
    }
}