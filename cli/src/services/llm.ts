/**
 * LLM Service
 *
 * Provides AI analysis of SEC filings using either:
 * - Ollama (local, free) - default
 * - Claude (Anthropic API) - requires API key
 *
 * Set LLM_PROVIDER=claude and ANTHROPIC_API_KEY in .env to use Claude.
 */

import axios from 'axios';
import { getConfig } from '../config';
import { AnalysisResult, LLMProvider } from '../types';

// Request timeout for LLM calls (2 minutes - these can be slow)
const LLM_TIMEOUT = 120000;

/**
 * Build the analysis prompt for the LLM
 * This prompt is designed to extract structured biotech data from SEC filings
 */
export function buildAnalysisPrompt(filingContent: string, ticker: string): string {
  return `You are a biotech equity analyst. Analyze this SEC filing for ${ticker} and extract key information.

FILING CONTENT:
${filingContent}

Extract the following in JSON format:

{
  "company": {
    "name": "Company legal name",
    "ticker": "${ticker}",
    "marketCap": "Market cap if mentioned, or null",
    "employees": number or null
  },
  "pipeline": [
    {
      "drug": "Drug name or code",
      "phase": "Preclinical | Phase 1 | Phase 2 | Phase 3 | NDA/BLA Filed | Approved",
      "indication": "Disease or condition",
      "status": "Brief status update",
      "catalyst": "Next expected milestone or null"
    }
  ],
  "financials": {
    "cash": "Cash position (e.g., '$2.1B')",
    "cashDate": "As of date for cash position",
    "quarterlyBurnRate": "Quarterly operating expenses/burn",
    "runwayMonths": number (estimated months of cash runway) or null,
    "revenue": "Revenue if any",
    "revenueSource": "Source of revenue (product sales, royalties, etc.)"
  },
  "fdaInteractions": ["Approvals", "CRLs", "Breakthrough designations", "Fast track", etc.],
  "partnerships": [
    {
      "partner": "Partner company",
      "type": "licensing | collaboration | acquisition | supply",
      "value": "Deal value or null",
      "details": "Brief description"
    }
  ],
  "risks": ["Top 3-5 key risks from the filing"],
  "recentEvents": ["Material events from the reporting period"],
  "analystSummary": "2-3 sentence investment thesis summarizing the opportunity and key considerations"
}

IMPORTANT:
- Return ONLY valid JSON, no markdown or explanation
- Use null for unknown values, not empty strings
- Focus on the most important/material information
- For pipeline, include all drugs mentioned with their most advanced phase
- Calculate runway as cash / quarterly burn rate if both are available`;
}

/**
 * Parse JSON from LLM response, handling common issues
 */
function parseAnalysisResponse(response: string, ticker: string): AnalysisResult {
  // Try to extract JSON from the response
  let jsonStr = response;

  // Remove markdown code blocks if present
  const jsonMatch = response.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (jsonMatch) {
    jsonStr = jsonMatch[1];
  }

  // Try to find JSON object in response
  const objectMatch = jsonStr.match(/\{[\s\S]*\}/);
  if (objectMatch) {
    jsonStr = objectMatch[0];
  }

  try {
    const parsed = JSON.parse(jsonStr);

    // Ensure required fields exist with defaults
    return {
      company: parsed.company || { name: ticker, ticker, marketCap: null, employees: null },
      pipeline: parsed.pipeline || [],
      financials: parsed.financials || {
        cash: null,
        cashDate: null,
        quarterlyBurnRate: null,
        runwayMonths: null,
        revenue: null,
        revenueSource: null,
      },
      fdaInteractions: parsed.fdaInteractions || [],
      partnerships: parsed.partnerships || [],
      risks: parsed.risks || [],
      recentEvents: parsed.recentEvents || [],
      analystSummary: parsed.analystSummary || 'Analysis could not be completed.',
      rawResponse: response,
    };
  } catch (error) {
    // Return a minimal result with the raw response for debugging
    return {
      company: { name: ticker, ticker, marketCap: null, employees: null },
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
      risks: ['Failed to parse LLM response'],
      recentEvents: [],
      analystSummary: 'Analysis parsing failed. Use --debug to see raw response.',
      rawResponse: response,
    };
  }
}

/**
 * Ollama LLM Provider (local, free)
 */
class OllamaProvider implements LLMProvider {
  name: string;
  private url: string;
  private model: string;

  constructor() {
    const config = getConfig();
    this.url = config.ollamaUrl;
    this.model = config.ollamaModel;
    this.name = `Ollama (${this.model})`;
  }

  async analyze(filingContent: string, ticker: string): Promise<AnalysisResult> {
    const prompt = buildAnalysisPrompt(filingContent, ticker);

    try {
      const response = await axios.post(
        `${this.url}/api/generate`,
        {
          model: this.model,
          prompt,
          stream: false,
          options: {
            temperature: 0.1,
            num_predict: 4096,
          },
        },
        {
          timeout: LLM_TIMEOUT,
          headers: { 'Content-Type': 'application/json' },
        }
      );

      const llmResponse = response.data.response || '';
      return parseAnalysisResponse(llmResponse, ticker);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED') {
          throw new Error(`Ollama not running. Start it with: ollama serve`);
        }
        if (error.code === 'ECONNABORTED') {
          throw new Error(`Ollama request timed out after ${LLM_TIMEOUT / 1000}s`);
        }
        throw new Error(`Ollama error: ${error.message}`);
      }
      throw error;
    }
  }
}

/**
 * Claude LLM Provider (Anthropic API)
 */
class ClaudeProvider implements LLMProvider {
  name: string;
  private apiKey: string;
  private model: string;

  constructor() {
    const config = getConfig();
    if (!config.claudeApiKey) {
      throw new Error('ANTHROPIC_API_KEY not set. Add it to your .env file.');
    }
    this.apiKey = config.claudeApiKey;
    this.model = config.claudeModel;
    this.name = `Claude (${this.model})`;
  }

  async analyze(filingContent: string, ticker: string): Promise<AnalysisResult> {
    const prompt = buildAnalysisPrompt(filingContent, ticker);

    try {
      const response = await axios.post(
        'https://api.anthropic.com/v1/messages',
        {
          model: this.model,
          max_tokens: 4096,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        },
        {
          timeout: LLM_TIMEOUT,
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': this.apiKey,
            'anthropic-version': '2023-06-01',
          },
        }
      );

      const llmResponse = response.data.content?.[0]?.text || '';
      return parseAnalysisResponse(llmResponse, ticker);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 401) {
          throw new Error('Invalid Anthropic API key. Check your ANTHROPIC_API_KEY.');
        }
        if (error.code === 'ECONNABORTED') {
          throw new Error(`Claude request timed out after ${LLM_TIMEOUT / 1000}s`);
        }
        throw new Error(`Claude API error: ${error.message}`);
      }
      throw error;
    }
  }
}

/**
 * Get the configured LLM provider
 */
export function getLLMProvider(): LLMProvider {
  const config = getConfig();

  if (config.llmProvider === 'claude') {
    return new ClaudeProvider();
  }

  return new OllamaProvider();
}
