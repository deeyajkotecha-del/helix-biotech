import { useCitation } from '../context/CitationContext';

const API_BASE = 'https://backend-production-ed24.up.railway.app/api';

export default function SourceSidebar() {
  const { activeSource, activePdfPage, sidebarOpen, closeSidebar } = useCitation();

  if (!activeSource) {
    return null;
  }

  const pdfUrl = activeSource.pdf_path
    ? `${API_BASE}/sources/${activeSource.id}/pdf${activePdfPage ? `#page=${activePdfPage}` : ''}`
    : null;

  const formatAuthors = (authors: string[] | null) => {
    if (!authors || authors.length === 0) return 'Unknown authors';
    if (authors.length <= 3) return authors.join(', ');
    return `${authors.slice(0, 3).join(', ')} et al.`;
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const getSourceTypeLabel = (type: string) => {
    switch (type) {
      case 'journal_article': return 'Journal Article';
      case 'sec_filing': return 'SEC Filing';
      case 'conference_poster': return 'Conference Poster';
      case 'internal_document': return 'Internal Document';
      case 'presentation': return 'Presentation';
      default: return type;
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={`source-sidebar-backdrop ${sidebarOpen ? 'open' : ''}`}
        onClick={closeSidebar}
      />

      {/* Sidebar */}
      <div className={`source-sidebar ${sidebarOpen ? 'open' : ''}`}>
        {/* Header */}
        <div className="source-sidebar-header">
          <div className="flex-1 min-w-0">
            <span className="source-type-badge">
              {getSourceTypeLabel(activeSource.source_type)}
            </span>
            <h3 className="source-title">{activeSource.title}</h3>
            <p className="source-authors">
              {formatAuthors(activeSource.authors)}
              {activeSource.publication_date && (
                <span className="source-date"> ({formatDate(activeSource.publication_date)})</span>
              )}
            </p>
          </div>
          <button
            onClick={closeSidebar}
            className="source-close-btn"
            aria-label="Close sidebar"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Metadata */}
        <div className="source-metadata">
          {activeSource.journal_name && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Journal:</span> {activeSource.journal_name}
            </p>
          )}
          {activeSource.doi && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">DOI:</span>{' '}
              <a
                href={`https://doi.org/${activeSource.doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-biotech-600 hover:underline"
              >
                {activeSource.doi}
              </a>
            </p>
          )}
          {activeSource.pmid && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">PMID:</span>{' '}
              <a
                href={`https://pubmed.ncbi.nlm.nih.gov/${activeSource.pmid}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-biotech-600 hover:underline"
              >
                {activeSource.pmid}
              </a>
            </p>
          )}
          {activeSource.url && !activeSource.doi && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">URL:</span>{' '}
              <a
                href={activeSource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-biotech-600 hover:underline break-all"
              >
                {activeSource.url}
              </a>
            </p>
          )}
        </div>

        {/* Abstract */}
        {activeSource.abstract && (
          <div className="source-abstract">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Abstract</h4>
            <p className="text-sm text-gray-600 leading-relaxed">{activeSource.abstract}</p>
          </div>
        )}

        {/* PDF Viewer */}
        {pdfUrl ? (
          <div className="source-pdf-container">
            <object
              data={pdfUrl}
              type="application/pdf"
              className="source-pdf-viewer"
            >
              <div className="source-pdf-fallback">
                <p className="text-gray-600 mb-4">
                  Unable to display PDF. Your browser may not support embedded PDFs.
                </p>
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-biotech-600 text-white rounded hover:bg-biotech-700"
                >
                  Download PDF
                </a>
              </div>
            </object>
          </div>
        ) : (
          <div className="source-no-pdf">
            <svg className="w-12 h-12 text-gray-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-gray-500 text-sm">No PDF available for this source</p>
            {activeSource.url && (
              <a
                href={activeSource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-block text-biotech-600 hover:underline text-sm"
              >
                View original source
              </a>
            )}
          </div>
        )}
      </div>
    </>
  );
}
