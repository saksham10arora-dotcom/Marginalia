// vitest setup: renderer.js reads `window.marked` (populated in a real
// browser by the classic-script load of vendor/marked.min.js, see
// manifest.json). Vitest runs under Node with no `window` global by default,
// so this stubs one and populates it from the real npm `marked` package
// (which Node CAN resolve, unlike a bare specifier in an unbundled browser)
// before any test file imports renderer.js.
import { marked } from 'marked';

globalThis.window = globalThis.window || {};
globalThis.window.marked = marked;
