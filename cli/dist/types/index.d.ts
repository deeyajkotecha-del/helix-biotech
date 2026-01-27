/**
 * Type definitions for the Helix CLI
 */
export interface Company {
    ticker: string;
    name: string;
    description?: string;
    sector?: string;
    lead_asset?: string;
    indication?: string;
    stage?: string;
    weight?: number;
    website?: string;
}
export interface Filing {
    accessionNumber: string;
    filingDate: string;
    reportDate: string;
    form: string;
    primaryDocument: string;
    fileUrl: string;
}
export interface SECSubmission {
    cik: string;
    entityType: string;
    name: string;
    tickers: string[];
    filings: {
        recent: {
            accessionNumber: string[];
            filingDate: string[];
            reportDate: string[];
            form: string[];
            primaryDocument: string[];
        };
    };
}
export interface AnalyzedCompany {
    name: string;
    ticker: string;
    marketCap: string | null;
    employees: number | null;
}
export interface PipelineItem {
    drug: string;
    phase: string;
    indication: string;
    status?: string;
    catalyst?: string | null;
}
export interface Financials {
    cash: string | null;
    cashDate: string | null;
    quarterlyBurnRate: string | null;
    runwayMonths: number | null;
    revenue: string | null;
    revenueSource: string | null;
}
export interface Partnership {
    partner: string;
    type: string;
    value: string | null;
    details: string;
}
export interface AnalysisResult {
    company: AnalyzedCompany;
    pipeline: PipelineItem[];
    financials: Financials;
    fdaInteractions: string[];
    partnerships: Partnership[];
    risks: string[];
    recentEvents: string[];
    analystSummary: string;
    rawResponse?: string;
}
export interface LLMProvider {
    name: string;
    analyze(filingContent: string, ticker: string): Promise<AnalysisResult>;
}
export interface Config {
    apiUrl: string;
    llmProvider: 'ollama' | 'claude';
    ollamaUrl: string;
    ollamaModel: string;
    claudeApiKey?: string;
    claudeModel: string;
    secUserAgent: string;
}
//# sourceMappingURL=index.d.ts.map