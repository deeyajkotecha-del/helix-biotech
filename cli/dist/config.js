"use strict";
/**
 * Configuration Module
 *
 * Loads settings from environment variables.
 * Copy .env.example to .env and customize as needed.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getConfig = getConfig;
exports.resetConfig = resetConfig;
const dotenv_1 = __importDefault(require("dotenv"));
const path_1 = __importDefault(require("path"));
// Load .env file from the CLI directory (not CWD)
// This ensures .env is found regardless of where the command is run from
const envPath = path_1.default.resolve(__dirname, '..', '.env');
dotenv_1.default.config({ path: envPath });
let cachedConfig = null;
/**
 * Get the application configuration
 * Reads from environment variables with sensible defaults
 */
function getConfig() {
    if (cachedConfig) {
        return cachedConfig;
    }
    cachedConfig = {
        // Your backend API URL
        apiUrl: process.env.HELIX_API_URL || 'https://backend-production-ed24.up.railway.app',
        // Which LLM to use: 'ollama' or 'claude'
        llmProvider: (process.env.LLM_PROVIDER || 'ollama'),
        // Ollama settings (local AI)
        ollamaUrl: process.env.OLLAMA_URL || 'http://localhost:11434',
        ollamaModel: process.env.OLLAMA_MODEL || 'llama3.2',
        // Claude settings (for later)
        claudeApiKey: process.env.ANTHROPIC_API_KEY,
        claudeModel: process.env.CLAUDE_MODEL || 'claude-3-haiku-20240307',
        // SEC EDGAR requires User-Agent format: "CompanyName contact@email.com"
        secUserAgent: process.env.SEC_USER_AGENT || 'Helix CLI contact@helix.dev',
    };
    return cachedConfig;
}
/**
 * Reset config cache (useful for testing)
 */
function resetConfig() {
    cachedConfig = null;
}
//# sourceMappingURL=config.js.map