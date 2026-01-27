/**
 * LLM Service
 *
 * Provides AI analysis of SEC filings using either:
 * - Ollama (local, free) - default
 * - Claude (Anthropic API) - requires API key
 *
 * Set LLM_PROVIDER=claude and ANTHROPIC_API_KEY in .env to use Claude.
 */
import { LLMProvider } from '../types';
/**
 * Build the analysis prompt for the LLM
 * This prompt is designed to extract structured biotech data from SEC filings
 */
export declare function buildAnalysisPrompt(filingContent: string, ticker: string): string;
/**
 * Get the configured LLM provider
 */
export declare function getLLMProvider(): LLMProvider;
//# sourceMappingURL=llm.d.ts.map