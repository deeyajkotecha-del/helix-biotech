/**
 * Claude Provider
 *
 * Uses Claude API for SEC filing analysis.
 * Much faster and more accurate than local Ollama models.
 */
import { LLMProvider, AnalysisResult } from '../../types';
export declare class ClaudeProvider implements LLMProvider {
    name: string;
    private client;
    private getClient;
    analyze(filingContent: string, ticker: string): Promise<AnalysisResult>;
}
//# sourceMappingURL=claude.d.ts.map