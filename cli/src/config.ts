/**
 * Configuration Module
 *
 * Loads settings from environment variables.
 * Copy .env.example to .env and customize as needed.
 */

import dotenv from 'dotenv';
import path from 'path';
import { Config } from './types';

// Load .env file from the CLI directory (not CWD)
// This ensures .env is found regardless of where the command is run from
const envPath = path.resolve(__dirname, '..', '.env');
dotenv.config({ path: envPath });

let cachedConfig: Config | null = null;

/**
 * Get the application configuration
 * Reads from environment variables with sensible defaults
 */
export function getConfig(): Config {
  if (cachedConfig) {
    return cachedConfig;
  }

  cachedConfig = {
    // Your backend API URL
    apiUrl: process.env.HELIX_API_URL || 'https://backend-production-ed24.up.railway.app',

    // Which LLM to use: 'ollama' or 'claude'
    llmProvider: (process.env.LLM_PROVIDER || 'ollama') as 'ollama' | 'claude',

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
export function resetConfig(): void {
  cachedConfig = null;
}
