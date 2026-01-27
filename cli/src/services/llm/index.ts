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
import { getConfig } from '../../config';
import { OllamaProvider } from './ollama';
import { ClaudeProvider } from './claude';
import { buildAnalysisPrompt } from './prompts';

// Re-export the prompt builder so other modules can use it for --debug mode
export { buildAnalysisPrompt } from './prompts';

/**
 * Get the configured LLM provider
 * Reads LLM_PROVIDER env var to decide which one to use
 */
export function getLLMProvider(): LLMProvider {
  const config = getConfig();

  console.log(`[LLM] Provider configured: ${config.llmProvider}`);

  switch (config.llmProvider) {
    case 'ollama':
      console.log('[LLM] Using Ollama provider');
      return new OllamaProvider();
    case 'claude':
      console.log('[LLM] Using Claude API provider');
      return new ClaudeProvider();
    default:
      console.log('[LLM] Defaulting to Ollama provider');
      return new OllamaProvider();
  }
}

/**
 * Get the name of the current LLM provider (for API responses)
 */
export function getLLMProviderName(): string {
  const config = getConfig();
  return config.llmProvider || 'ollama';
}

/**
 * Build the analysis prompt (wrapper for prompts.ts)
 * Used by LLM providers
 */
export function getAnalysisPrompt(filingContent: string, ticker: string): string {
  return buildAnalysisPrompt(filingContent, ticker);
}

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
export function parseAnalysisResponse(response: string, rawResponse: string): AnalysisResult {
  try {
    // Try to find JSON in the response (LLMs sometimes add extra text)
    const jsonMatch = response.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      throw new Error('No JSON found in response');
    }

    const parsed = JSON.parse(jsonMatch[0]);

    // Build the result, providing defaults for missing fields
    return {
      company: {
        name: parsed.company?.name || 'Unknown',
        ticker: parsed.company?.ticker || 'N/A',
        marketCap: parsed.company?.marketCap || null,
        employees: parsed.company?.employees || null,
      },
      pipeline: Array.isArray(parsed.pipeline) ? parsed.pipeline.map((p: any) => ({
        drug: p.drug || 'Unknown',
        phase: p.phase || 'Unknown',
        indication: p.indication || 'Unknown',
        status: p.status,
        catalyst: p.catalyst || null,
      })) : [],
      financials: {
        cash: parsed.financials?.cash || null,
        cashDate: parsed.financials?.cashDate || null,
        quarterlyBurnRate: parsed.financials?.quarterlyBurnRate || null,
        runwayMonths: parseRunwayMonths(parsed.financials?.runwayMonths),
        revenue: parsed.financials?.revenue || null,
        revenueSource: parsed.financials?.revenueSource || null,
      },
      fdaInteractions: Array.isArray(parsed.fdaInteractions) ? parsed.fdaInteractions : [],
      partnerships: Array.isArray(parsed.partnerships) ? parsed.partnerships.map((p: any) => ({
        partner: p.partner || 'Unknown',
        type: p.type || 'Unknown',
        value: p.value || null,
        details: p.details || '',
      })) : [],
      risks: Array.isArray(parsed.risks) ? parsed.risks : [],
      recentEvents: Array.isArray(parsed.recentEvents) ? parsed.recentEvents : [],
      analystSummary: parsed.analystSummary || 'No summary available',
      rawResponse,
    };
  } catch (error) {
    // If parsing fails, return a default result with the raw response
    // This lets the user see what went wrong
    return {
      company: { name: 'Parse Error', ticker: 'N/A', marketCap: null, employees: null },
      pipeline: [],
      financials: {
        cash: null,
        cashDate: null,
        quarterlyBurnRate: null,
        runwayMonths: null,
        revenue: null,
        revenueSource: null,
      },
      fdaInteractions: [],
      partnerships: [],
      risks: ['Failed to parse LLM response - see raw output with --debug flag'],
      recentEvents: [],
      analystSummary: `Parse error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      rawResponse,
    };
  }
}

/**
 * Helper to parse runway months from various formats
 * LLMs might return "24", 24, "24 months", ">36", etc.
 */
function parseRunwayMonths(value: any): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    // Extract first number from string
    const match = value.match(/\d+/);
    if (match) return parseInt(match[0], 10);
  }
  return null;
}
