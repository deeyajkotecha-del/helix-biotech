/**
 * PDF Analyzer Service
 *
 * Extracts text content from PDFs and analyzes for
 * pipeline data, clinical results, and catalysts.
 */

import * as fs from 'fs';
import * as path from 'path';
import { getExtractedDir, ensureDir } from './pdf-downloader';

// pdf-parse requires CommonJS import
// eslint-disable-next-line @typescript-eslint/no-var-requires
const pdfParse = require('pdf-parse');

// ============================================
// Types
// ============================================

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

// ============================================
// Text Extraction
// ============================================

/**
 * Extract text from a PDF file
 */
export async function extractPDFText(filePath: string): Promise<ExtractedDocument> {
  const documentId = path.basename(filePath, '.pdf');

  try {
    console.log(`[PDF Analyzer] Extracting text from: ${path.basename(filePath)}`);

    const dataBuffer = fs.readFileSync(filePath);
    const data = await pdfParse(dataBuffer);

    const textContent = data.text || '';
    const isScanned = textContent.length < 100 || (textContent.length / data.numpages < 50);

    if (isScanned) {
      console.warn(`[PDF Analyzer] Warning: ${path.basename(filePath)} appears to be scanned (low text content)`);
    }

    console.log(`[PDF Analyzer] Extracted ${textContent.length} chars from ${data.numpages} pages`);

    return {
      documentId,
      title: data.info?.Title || documentId,
      filePath,
      textContent,
      pageCount: data.numpages,
      charCount: textContent.length,
      extractedAt: new Date().toISOString(),
      isScanned,
      metadata: {
        author: data.info?.Author,
        creator: data.info?.Creator,
        producer: data.info?.Producer,
        creationDate: data.info?.CreationDate,
      },
    };
  } catch (error: any) {
    console.error(`[PDF Analyzer] Error extracting ${path.basename(filePath)}:`, error.message);
    return {
      documentId,
      title: documentId,
      filePath,
      textContent: '',
      pageCount: 0,
      charCount: 0,
      extractedAt: new Date().toISOString(),
      isScanned: true,
      metadata: {},
    };
  }
}

/**
 * Extract text from all PDFs for a company
 */
export async function extractAllPDFs(
  ticker: string,
  pdfFiles: string[]
): Promise<ExtractedDocument[]> {
  const results: ExtractedDocument[] = [];

  for (const filePath of pdfFiles) {
    const extracted = await extractPDFText(filePath);
    results.push(extracted);

    // Save extracted text
    const extractedDir = getExtractedDir(ticker);
    ensureDir(extractedDir);

    const textFile = path.join(extractedDir, `${extracted.documentId}.txt`);
    fs.writeFileSync(textFile, extracted.textContent);

    const metaFile = path.join(extractedDir, `${extracted.documentId}.meta.json`);
    fs.writeFileSync(metaFile, JSON.stringify({
      documentId: extracted.documentId,
      title: extracted.title,
      pageCount: extracted.pageCount,
      charCount: extracted.charCount,
      isScanned: extracted.isScanned,
      extractedAt: extracted.extractedAt,
      metadata: extracted.metadata,
    }, null, 2));
  }

  return results;
}

// ============================================
// Pattern Matching for Data Extraction
// ============================================

const PHASE_PATTERNS = [
  /phase\s*([123](?:\/[123])?[ab]?)/gi,
  /phase\s*([IVX]+)(?:\s*[ab])?/gi,
  /p([123])(?:\/([123]))?/gi,
];

const DRUG_NAME_PATTERNS = [
  /ARO-[A-Z0-9]+/g,
  /[A-Z]{2,5}-[0-9]{3,5}/g,
];

const EFFICACY_PATTERNS = [
  /(\d+(?:\.\d+)?)\s*%\s*(?:reduction|decrease|improvement|response|remission)/gi,
  /(?:reduction|decrease|improvement)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%/gi,
  /ORR\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*%/gi,
  /p\s*[=<]\s*(0\.\d+)/gi,
];

/**
 * Extract pipeline assets from text
 */
export function extractPipelineFromText(text: string): PipelineAsset[] {
  const assets: PipelineAsset[] = [];
  const seenNames = new Set<string>();

  // Find drug names
  for (const pattern of DRUG_NAME_PATTERNS) {
    const matches = text.match(pattern) || [];
    for (const match of matches) {
      if (!seenNames.has(match)) {
        seenNames.add(match);

        // Find context around the drug mention
        const contextPattern = new RegExp(`${match}[^.]*(?:phase|indication|target|partner)[^.]*`, 'gi');
        const contextMatch = text.match(contextPattern);

        let phase = 'Unknown';
        let indication = 'Unknown';

        if (contextMatch) {
          const context = contextMatch[0];

          // Extract phase
          for (const phasePattern of PHASE_PATTERNS) {
            const phaseMatch = context.match(phasePattern);
            if (phaseMatch) {
              phase = `Phase ${phaseMatch[1]}`;
              break;
            }
          }

          // Extract indication from context
          const indicationPatterns = [
            /(?:for|in|treating)\s+([A-Za-z\s]+?)(?:\.|,|and|with)/i,
          ];
          for (const indPattern of indicationPatterns) {
            const indMatch = context.match(indPattern);
            if (indMatch) {
              indication = indMatch[1].trim();
              break;
            }
          }
        }

        assets.push({
          name: match,
          codeNames: [match],
          phase,
          indication,
          status: 'Active',
        });
      }
    }
  }

  return assets;
}

/**
 * Extract clinical results from text
 */
export function extractClinicalResultsFromText(text: string, source: string): ClinicalResult[] {
  const results: ClinicalResult[] = [];

  // Find efficacy data
  for (const pattern of EFFICACY_PATTERNS) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      // Get surrounding context
      const idx = match.index || 0;
      const context = text.slice(Math.max(0, idx - 200), Math.min(text.length, idx + 200));

      // Find drug name in context
      let drug = 'Unknown';
      for (const namePattern of DRUG_NAME_PATTERNS) {
        const nameMatch = context.match(namePattern);
        if (nameMatch) {
          drug = nameMatch[0];
          break;
        }
      }

      results.push({
        drug,
        trial: 'See source',
        indication: 'See source',
        endpoint: match[0],
        result: match[1] + '%',
        source,
        date: new Date().toISOString().slice(0, 10),
      });
    }
  }

  return results;
}

/**
 * Extract catalysts from text
 */
export function extractCatalystsFromText(text: string): Catalyst[] {
  const catalysts: Catalyst[] = [];

  const catalystPatterns = [
    /expected\s+(?:in\s+)?(?:Q[1-4]\s+)?(\d{4})/gi,
    /(?:data|results|readout)\s+(?:expected|anticipated)\s+(?:in\s+)?(?:Q[1-4]\s+)?(\d{4})/gi,
    /(?:Q[1-4])\s+(\d{4})/gi,
  ];

  for (const pattern of catalystPatterns) {
    const matches = text.matchAll(pattern);
    for (const match of matches) {
      const idx = match.index || 0;
      const context = text.slice(Math.max(0, idx - 150), Math.min(text.length, idx + 150));

      // Find drug name
      let drug = 'Unknown';
      for (const namePattern of DRUG_NAME_PATTERNS) {
        const nameMatch = context.match(namePattern);
        if (nameMatch) {
          drug = nameMatch[0];
          break;
        }
      }

      catalysts.push({
        drug,
        event: 'Data readout',
        expectedDate: match[0],
        type: 'data-readout',
      });
    }
  }

  return catalysts;
}

// ============================================
// Full Document Analysis
// ============================================

/**
 * Analyze an extracted document for structured data
 */
export function analyzeDocument(extracted: ExtractedDocument): AnalyzedDocument {
  const text = extracted.textContent;

  return {
    ...extracted,
    pipelineAssets: extractPipelineFromText(text),
    clinicalResults: extractClinicalResultsFromText(text, extracted.title),
    catalysts: extractCatalystsFromText(text),
    keyFindings: [], // Would use Claude API for this
  };
}

/**
 * Analyze all documents for a company
 */
export async function analyzeAllDocuments(
  ticker: string,
  documents: ExtractedDocument[]
): Promise<AnalyzedDocument[]> {
  console.log(`[PDF Analyzer] Analyzing ${documents.length} documents for ${ticker}`);

  return documents.map(doc => analyzeDocument(doc));
}

/**
 * Get cached extracted text for a document
 */
export function getCachedExtraction(ticker: string, documentId: string): string | null {
  const extractedDir = getExtractedDir(ticker);
  const textFile = path.join(extractedDir, `${documentId}.txt`);

  if (fs.existsSync(textFile)) {
    return fs.readFileSync(textFile, 'utf-8');
  }

  return null;
}
