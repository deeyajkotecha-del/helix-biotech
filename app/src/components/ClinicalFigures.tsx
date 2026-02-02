import { useState } from 'react';
import Citation from './Citation';

// Backend base URL for serving static figures
const FIGURES_BASE_URL = import.meta.env.DEV
  ? 'http://localhost:8000'
  : 'https://backend-production-ed24.up.railway.app';

interface ExtractedData {
  primary_endpoint?: string;
  treatment_result?: string;
  placebo_result?: string;
  p_value?: string;
  n_treatment?: number;
  n_placebo?: number;
  response_rate?: string;
  [key: string]: string | number | undefined | object;
}

interface ClinicalFigure {
  id: string;
  source: string;
  source_url?: string;
  slide_number: number;
  image_path: string;
  figure_type?: string;
  title?: string;
  description?: string;
  extracted_data?: ExtractedData;
  analysis?: string[];
  limitations?: string[];
  competitive_context?: string;
  trial?: string;
  citation_number?: number;
}

interface Props {
  figures: ClinicalFigure[];
  assetName: string;
  sectionName: string;
}

export default function ClinicalFigures({ figures, assetName, sectionName }: Props) {
  const [expandedFigure, setExpandedFigure] = useState<string | null>(null);
  const [selectedTrial, setSelectedTrial] = useState<string | null>(null);

  if (!figures || figures.length === 0) {
    return null;
  }

  // Group figures by trial
  const figuresByTrial = figures.reduce((acc, fig) => {
    const trial = fig.trial || 'Other';
    if (!acc[trial]) acc[trial] = [];
    acc[trial].push(fig);
    return acc;
  }, {} as Record<string, ClinicalFigure[]>);

  const trials = Object.keys(figuresByTrial);
  const activeTrial = selectedTrial || trials[0];
  const activeFigures = figuresByTrial[activeTrial] || [];

  const getFigureTypeIcon = (type?: string) => {
    switch (type) {
      case 'waterfall_plot':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        );
      case 'line_chart':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        );
      case 'kaplan_meier':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
    }
  };

  return (
    <div className="clinical-figures mt-6">
      <h5 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
        <svg className="w-5 h-5 text-biotech-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Clinical Evidence - {assetName}
      </h5>

      {/* Trial tabs */}
      {trials.length > 1 && (
        <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
          {trials.map(trial => (
            <button
              key={trial}
              onClick={() => setSelectedTrial(trial)}
              className={`px-3 py-1.5 text-sm font-medium rounded-full whitespace-nowrap transition-colors ${
                activeTrial === trial
                  ? 'bg-biotech-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {trial} ({figuresByTrial[trial].length})
            </button>
          ))}
        </div>
      )}

      {/* Figures grid */}
      <div className="grid md:grid-cols-2 gap-4">
        {activeFigures.map((figure) => (
          <div
            key={figure.id}
            className="clinical-figure-card border border-gray-200 rounded-lg overflow-hidden hover:border-biotech-300 transition-colors"
          >
            {/* Figure image */}
            <div
              className="relative cursor-pointer bg-gray-100"
              onClick={() => setExpandedFigure(expandedFigure === figure.id ? null : figure.id)}
            >
              <img
                src={`${FIGURES_BASE_URL}${figure.image_path}`}
                alt={figure.title || `Slide ${figure.slide_number}`}
                className="w-full h-48 object-contain"
                loading="lazy"
              />
              <div className="absolute top-2 left-2 flex items-center gap-1 px-2 py-1 bg-black/70 text-white text-xs rounded">
                {getFigureTypeIcon(figure.figure_type)}
                <span>{figure.figure_type?.replace('_', ' ') || 'Figure'}</span>
              </div>
              <div className="absolute top-2 right-2 px-2 py-1 bg-black/70 text-white text-xs rounded">
                Slide {figure.slide_number}
              </div>
              <div className="absolute bottom-2 right-2 p-1 bg-black/70 text-white rounded">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                </svg>
              </div>
            </div>

            {/* Figure info */}
            <div className="p-3">
              <h6 className="font-medium text-gray-900 text-sm mb-1">
                {figure.title || `Figure from ${figure.source}`}
              </h6>

              {/* Key data points */}
              {figure.extracted_data && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {figure.extracted_data.treatment_result && (
                    <span className="px-2 py-0.5 bg-biotech-100 text-biotech-700 text-xs font-medium rounded">
                      {figure.extracted_data.treatment_result}
                    </span>
                  )}
                  {figure.extracted_data.p_value && (
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                      p{figure.extracted_data.p_value}
                    </span>
                  )}
                  {figure.extracted_data.response_rate && (
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded">
                      {figure.extracted_data.response_rate}
                    </span>
                  )}
                </div>
              )}

              {/* Source link */}
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>{figure.source}</span>
                {figure.source_url && (
                  <a
                    href={figure.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-biotech-600 hover:underline"
                  >
                    View PDF
                  </a>
                )}
                {figure.citation_number && (
                  <Citation section={sectionName} number={figure.citation_number} />
                )}
              </div>
            </div>

            {/* Expanded analysis */}
            {expandedFigure === figure.id && figure.analysis && figure.analysis.length > 0 && (
              <div className="px-3 pb-3 border-t border-gray-100 pt-3">
                <div className="text-xs font-medium text-gray-500 uppercase mb-2">Satya Analysis</div>
                <ul className="space-y-1">
                  {figure.analysis.map((point, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="w-1.5 h-1.5 bg-biotech-500 rounded-full mt-1.5 flex-shrink-0"></span>
                      {point}
                    </li>
                  ))}
                </ul>

                {figure.competitive_context && (
                  <div className="mt-3 p-2 bg-amber-50 rounded text-xs text-amber-800">
                    <span className="font-medium">vs Competition:</span> {figure.competitive_context}
                  </div>
                )}

                {figure.limitations && figure.limitations.length > 0 && (
                  <div className="mt-2 text-xs text-gray-500">
                    <span className="font-medium">Limitations:</span> {figure.limitations.join(', ')}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Expanded modal */}
      {expandedFigure && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setExpandedFigure(null)}
        >
          <div className="max-w-5xl max-h-[90vh] overflow-auto bg-white rounded-lg" onClick={e => e.stopPropagation()}>
            {(() => {
              const fig = figures.find(f => f.id === expandedFigure);
              if (!fig) return null;
              return (
                <>
                  <img
                    src={`${FIGURES_BASE_URL}${fig.image_path}`}
                    alt={fig.title || 'Clinical figure'}
                    className="w-full"
                  />
                  <div className="p-4">
                    <h3 className="font-semibold text-lg mb-2">{fig.title}</h3>
                    {fig.description && <p className="text-gray-600 mb-3">{fig.description}</p>}
                    <div className="text-sm text-gray-500">
                      Source: {fig.source} (Slide {fig.slide_number})
                    </div>
                  </div>
                </>
              );
            })()}
            <button
              onClick={() => setExpandedFigure(null)}
              className="absolute top-4 right-4 p-2 bg-white rounded-full shadow-lg"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
