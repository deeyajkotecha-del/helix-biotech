"use strict";
/**
 * Ollama Provider
 *
 * Ollama lets you run AI models locally on your machine - completely free!
 *
 * Setup:
 * 1. Install Ollama: https://ollama.ai
 * 2. Pull a model: ollama pull llama3.2
 * 3. Run it: ollama serve (or it auto-starts)
 *
 * Then this provider will work automatically.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.OllamaProvider = void 0;
const axios_1 = __importDefault(require("axios"));
const config_1 = require("../../config");
const index_1 = require("./index");
class OllamaProvider {
    constructor() {
        this.name = 'Ollama (Local)';
    }
    async analyze(filingContent, ticker) {
        const config = (0, config_1.getConfig)();
        const prompt = (0, index_1.getAnalysisPrompt)(filingContent, ticker);
        try {
            // Ollama's API endpoint for generating completions
            const response = await axios_1.default.post(`${config.ollamaUrl}/api/generate`, {
                model: config.ollamaModel,
                prompt: prompt,
                stream: false, // We want the full response, not streaming
                options: {
                    temperature: 0.3, // Lower = more focused/deterministic
                    num_ctx: 8192, // Context window size
                }
            }, {
                timeout: 300000, // 5 minute timeout (analysis can take a while)
            });
            return (0, index_1.parseAnalysisResponse)(response.data.response, response.data.response);
        }
        catch (error) {
            if (axios_1.default.isAxiosError(error)) {
                if (error.code === 'ECONNREFUSED') {
                    throw new Error('Could not connect to Ollama. Make sure Ollama is running:\n' +
                        '  1. Install: https://ollama.ai\n' +
                        '  2. Start: ollama serve\n' +
                        '  3. Pull a model: ollama pull llama3.2');
                }
                if (error.response?.status === 404) {
                    throw new Error(`Model "${config.ollamaModel}" not found. Pull it first:\n` +
                        `  ollama pull ${config.ollamaModel}`);
                }
            }
            throw error;
        }
    }
}
exports.OllamaProvider = OllamaProvider;
//# sourceMappingURL=ollama.js.map