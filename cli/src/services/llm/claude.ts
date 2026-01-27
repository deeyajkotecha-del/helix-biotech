/**
 * Claude Provider
 *
 * Uses Claude API for SEC filing analysis.
 * Much faster and more accurate than local Ollama models.
 */

import Anthropic from '@anthropic-ai/sdk';
import { LLMProvider, AnalysisResult } from '../../types';
import { getConfig } from '../../config';
import { getAnalysisPrompt, parseAnalysisResponse } from './index';

export class ClaudeProvider implements LLMProvider {
  name = 'Claude API';
  private client: Anthropic | null = null;

  private getClient(): Anthropic {
    if (!this.client) {
      const config = getConfig();
      if (!config.claudeApiKey) {
        throw new Error(
          'Claude API key not configured.\n' +
          'Set ANTHROPIC_API_KEY in your .env file or use Ollama instead:\n' +
          '  LLM_PROVIDER=ollama'
        );
      }
      this.client = new Anthropic({ apiKey: config.claudeApiKey });
    }
    return this.client;
  }

  async analyze(filingContent: string, ticker: string): Promise<AnalysisResult> {
    const config = getConfig();
    const client = this.getClient();

    console.log(`[Claude] Analyzing ${ticker} with model: ${config.claudeModel}`);
    console.log(`[Claude] Content length: ${filingContent.length} chars`);

    const prompt = getAnalysisPrompt(filingContent, ticker);

    try {
      console.log('[Claude] Sending request to Claude API...');
      const startTime = Date.now();

      const response = await client.messages.create({
        model: config.claudeModel,
        max_tokens: 4096,
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ]
      });

      const elapsed = Date.now() - startTime;
      console.log(`[Claude] Response received in ${(elapsed / 1000).toFixed(1)}s`);

      // Extract text from response
      const textContent = response.content.find(block => block.type === 'text');
      if (!textContent || textContent.type !== 'text') {
        throw new Error('No text response from Claude');
      }

      const rawResponse = textContent.text;
      console.log(`[Claude] Response length: ${rawResponse.length} chars`);

      // Parse the JSON response
      const analysis = parseAnalysisResponse(rawResponse, ticker);
      analysis.rawResponse = rawResponse;

      return analysis;
    } catch (error) {
      if (error instanceof Anthropic.APIError) {
        if (error.status === 401) {
          throw new Error('Invalid Claude API key. Check your ANTHROPIC_API_KEY in .env');
        }
        if (error.status === 429) {
          throw new Error('Claude API rate limit exceeded. Please wait and try again.');
        }
        throw new Error(`Claude API error: ${error.message}`);
      }
      throw error;
    }
  }
}
