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
import { LLMProvider, AnalysisResult } from '../../types';
export declare class OllamaProvider implements LLMProvider {
    name: string;
    analyze(filingContent: string, ticker: string): Promise<AnalysisResult>;
}
//# sourceMappingURL=ollama.d.ts.map