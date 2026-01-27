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

import axios from 'axios';
import { LLMProvider, AnalysisResult } from '../../types';
import { getConfig } from '../../config';
import { getAnalysisPrompt, parseAnalysisResponse } from './index';

export class OllamaProvider implements LLMProvider {
  name = 'Ollama (Local)';

  async analyze(filingContent: string, ticker: string): Promise<AnalysisResult> {
    const config = getConfig();
    const prompt = getAnalysisPrompt(filingContent, ticker);

    try {
      // Ollama's API endpoint for generating completions
      const response = await axios.post<{ response: string }>(
        `${config.ollamaUrl}/api/generate`,
        {
          model: config.ollamaModel,
          prompt: prompt,
          stream: false,  // We want the full response, not streaming
          options: {
            temperature: 0.3,  // Lower = more focused/deterministic
            num_ctx: 8192,     // Context window size
          }
        },
        {
          timeout: 300000,  // 5 minute timeout (analysis can take a while)
        }
      );

      return parseAnalysisResponse(response.data.response, response.data.response);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED') {
          throw new Error(
            'Could not connect to Ollama. Make sure Ollama is running:\n' +
            '  1. Install: https://ollama.ai\n' +
            '  2. Start: ollama serve\n' +
            '  3. Pull a model: ollama pull llama3.2'
          );
        }
        if (error.response?.status === 404) {
          throw new Error(
            `Model "${config.ollamaModel}" not found. Pull it first:\n` +
            `  ollama pull ${config.ollamaModel}`
          );
        }
      }
      throw error;
    }
  }
}
