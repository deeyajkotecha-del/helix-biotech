/**
 * LLM Provider Abstraction
 *
 * This module lets you switch between different AI providers (Ollama, Claude)
 * without changing any other code. Set LLM_PROVIDER env var to switch.
 *
 * Why an abstraction?
 * - Start with free Ollama (runs locally on your machine)
 * - Switch to Claude API when you're ready for production
 * - Could add OpenAI, Gemini, etc. later
 */
import { LLMProvider, AnalysisResult } from '../../types';
export { buildAnalysisPrompt } from './prompts';
/**
 * Get the configured LLM provider
 * Reads LLM_PROVIDER env var to decide which one to use
 */
export declare function getLLMProvider(): LLMProvider;
/**
 * Get the name of the current LLM provider (for API responses)
 */
export declare function getLLMProviderName(): string;
/**
 * Build the analysis prompt (wrapper for prompts.ts)
 * Used by LLM providers
 */
export declare function getAnalysisPrompt(filingContent: string, ticker: string): string;
/**
 * Parse the LLM response into our AnalysisResult structure
 *
 * This handles the new biotech-specific format with:
 * - company info
 * - pipeline drugs
 * - financials (cash, burn rate, runway)
 * - FDA interactions
 * - partnerships
 * - risks
 * - recent events
 * - analyst summary
 */
export declare function parseAnalysisResponse(response: string, rawResponse: string): AnalysisResult;
//# sourceMappingURL=index.d.ts.map