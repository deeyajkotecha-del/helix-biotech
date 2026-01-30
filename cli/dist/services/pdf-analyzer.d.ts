/**
 * PDF Analyzer Service
 *
 * Extracts text content from PDFs and analyzes for
 * pipeline data, clinical results, and catalysts.
 */
export interface ExtractedDocument {
    documentId: string;
    title: string;
    filePath: string;
    textContent: string;
    pageCount: number;
    charCount: number;
    extractedAt: string;
    isScanned: boolean;
    metadata?: {
        author?: string;
        creator?: string;
        producer?: string;
        creationDate?: string;
    };
}
export interface PipelineAsset {
    name: string;
    codeNames: string[];
    target?: string;
    modality?: string;
    phase: string;
    indication: string;
    otherIndications?: string[];
    partner?: string;
    status: string;
    keyData?: string;
    nextCatalyst?: string;
}
export interface ClinicalResult {
    drug: string;
    trial: string;
    indication: string;
    endpoint: string;
    result: string;
    placebo?: string;
    pValue?: string;
    nPatients?: number;
    source: string;
    date: string;
}
export interface Catalyst {
    drug: string;
    event: string;
    expectedDate: string;
    type: 'data-readout' | 'regulatory' | 'conference' | 'other';
    notes?: string;
}
export interface AnalyzedDocument extends ExtractedDocument {
    pipelineAssets: PipelineAsset[];
    clinicalResults: ClinicalResult[];
    catalysts: Catalyst[];
    keyFindings: string[];
    financialData?: {
        cash?: string;
        runway?: string;
        guidance?: string;
    };
}
/**
 * Extract text from a PDF file
 */
export declare function extractPDFText(filePath: string): Promise<ExtractedDocument>;
/**
 * Extract text from all PDFs for a company
 */
export declare function extractAllPDFs(ticker: string, pdfFiles: string[]): Promise<ExtractedDocument[]>;
/**
 * Extract pipeline assets from text
 */
export declare function extractPipelineFromText(text: string): PipelineAsset[];
/**
 * Extract clinical results from text
 */
export declare function extractClinicalResultsFromText(text: string, source: string): ClinicalResult[];
/**
 * Extract catalysts from text
 */
export declare function extractCatalystsFromText(text: string): Catalyst[];
/**
 * Analyze an extracted document for structured data
 */
export declare function analyzeDocument(extracted: ExtractedDocument): AnalyzedDocument;
/**
 * Analyze all documents for a company
 */
export declare function analyzeAllDocuments(ticker: string, documents: ExtractedDocument[]): Promise<AnalyzedDocument[]>;
/**
 * Get cached extracted text for a document
 */
export declare function getCachedExtraction(ticker: string, documentId: string): string | null;
//# sourceMappingURL=pdf-analyzer.d.ts.map