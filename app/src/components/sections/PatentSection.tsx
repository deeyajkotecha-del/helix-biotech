import type { PatentLegalSection as PatentData } from '../../types';

interface Props {
  data: PatentData;
}

export default function PatentSection({ data }: Props) {
  return (
    <div>
      <h3 className="section-title">Patent & Legal Review</h3>

      {/* Nearest Patent Expiry */}
      {data.nearest_expiry && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-amber-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="font-medium text-amber-800">Patent Status</span>
          </div>
          <p className="text-amber-700 mt-2">{data.nearest_expiry}</p>
        </div>
      )}

      {/* Key Patents */}
      {data.key_patents.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-800 mb-3">Key Patents</h4>
          <div className="space-y-3">
            {data.key_patents.map((patent, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <p className="font-medium text-gray-800">{patent.title}</p>
                {patent.patent_number && (
                  <p className="text-sm text-gray-500 mt-1">
                    Patent #: {patent.patent_number}
                  </p>
                )}
                {patent.expiry_date && (
                  <p className="text-sm text-gray-500">
                    Expiry: {patent.expiry_date}
                  </p>
                )}
                {patent.status && (
                  <span className="badge badge-info mt-2">{patent.status}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Litigation */}
      {data.litigation.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-red-700 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Active Litigation
          </h4>
          <ul className="space-y-2">
            {data.litigation.map((item, index) => (
              <li key={index} className="flex items-start">
                <span className="w-2 h-2 bg-red-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-600">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Regulatory Notes */}
      {data.regulatory_notes.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Regulatory Notes
          </h4>
          <ul className="space-y-2">
            {data.regulatory_notes.map((note, index) => (
              <li key={index} className="flex items-start">
                <span className="w-2 h-2 bg-biotech-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-600">{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty State */}
      {data.key_patents.length === 0 &&
       data.litigation.length === 0 &&
       data.regulatory_notes.length === 0 &&
       !data.nearest_expiry && (
        <p className="text-gray-400 italic">No patent or legal data available</p>
      )}
    </div>
  );
}
