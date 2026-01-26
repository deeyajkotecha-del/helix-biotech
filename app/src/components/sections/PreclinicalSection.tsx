import type { PreclinicalSection as PreclinicalData } from '../../types';

interface Props {
  data: PreclinicalData;
}

export default function PreclinicalSection({ data }: Props) {
  return (
    <div>
      <h3 className="section-title">Preclinical Data & Publications</h3>

      {/* Mechanism of Action */}
      {data.mechanism_of_action && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
          <h4 className="font-semibold text-purple-800 mb-2">Mechanism of Action</h4>
          <p className="text-purple-700">{data.mechanism_of_action}</p>
        </div>
      )}

      {/* Key Findings */}
      {data.key_findings.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2 text-biotech-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Key Findings
          </h4>
          <ul className="space-y-2">
            {data.key_findings.map((finding, index) => (
              <li key={index} className="flex items-start bg-gray-50 p-3 rounded">
                <span className="w-6 h-6 bg-biotech-100 text-biotech-700 rounded-full flex items-center justify-center text-xs font-medium mr-3 flex-shrink-0">
                  {index + 1}
                </span>
                <span className="text-gray-600">{finding}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* PubMed Articles */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
          <svg className="w-5 h-5 mr-2 text-biotech-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          PubMed Publications ({data.pubmed_articles.length})
        </h4>

        {data.pubmed_articles.length > 0 ? (
          <div className="space-y-4">
            {data.pubmed_articles.map((article) => (
              <div
                key={article.pmid}
                className="border border-gray-200 rounded-lg p-4 hover:border-biotech-300 transition-colors"
              >
                <h5 className="font-medium text-gray-800 mb-2 leading-snug">
                  {article.title}
                </h5>
                <div className="flex flex-wrap gap-2 text-xs text-gray-500 mb-2">
                  <span className="bg-gray-100 px-2 py-1 rounded">
                    {article.journal}
                  </span>
                  <span className="bg-gray-100 px-2 py-1 rounded">
                    {article.pub_date}
                  </span>
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
                    PMID: {article.pmid}
                  </span>
                </div>
                {article.authors.length > 0 && (
                  <p className="text-sm text-gray-500 mb-2">
                    {article.authors.slice(0, 3).join(', ')}
                    {article.authors.length > 3 && ' et al.'}
                  </p>
                )}
                {article.abstract && (
                  <details className="mt-2">
                    <summary className="text-sm text-biotech-600 cursor-pointer hover:text-biotech-700">
                      View Abstract
                    </summary>
                    <p className="text-sm text-gray-600 mt-2 pl-4 border-l-2 border-gray-200">
                      {article.abstract}
                    </p>
                  </details>
                )}
                {article.doi && (
                  <a
                    href={`https://doi.org/${article.doi}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-sm text-biotech-600 hover:text-biotech-700 mt-2"
                  >
                    View on DOI
                    <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-400 italic">No PubMed articles found</p>
        )}
      </div>

      {/* Conference Posters */}
      {data.conference_posters.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-800 mb-3">Conference Posters</h4>
          <div className="space-y-3">
            {data.conference_posters.map((poster, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <pre className="text-sm text-gray-600 whitespace-pre-wrap">
                  {JSON.stringify(poster, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
