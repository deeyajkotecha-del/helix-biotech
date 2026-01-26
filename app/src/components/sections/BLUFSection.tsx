import type { BLUFSection as BLUFData } from '../../types';

interface Props {
  data: BLUFData;
}

export default function BLUFSection({ data }: Props) {
  const getRecommendationStyle = (rec?: string) => {
    if (!rec) return 'badge-neutral';
    const lower = rec.toLowerCase();
    if (lower.includes('bullish')) return 'badge-success';
    if (lower.includes('bearish')) return 'badge-danger';
    return 'badge-warning';
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title mb-0 border-0 pb-0">
          Bottom Line Up Front (BLUF)
        </h3>
        {data.recommendation && (
          <span className={`badge ${getRecommendationStyle(data.recommendation)} text-sm px-3 py-1`}>
            {data.recommendation}
          </span>
        )}
      </div>

      {/* Executive Summary */}
      <div className="bg-biotech-50 rounded-lg p-4 mb-6">
        <h4 className="font-semibold text-biotech-800 mb-2">Executive Summary</h4>
        <p className="text-gray-700">{data.summary}</p>
      </div>

      {/* Investment Thesis */}
      <div className="mb-6">
        <h4 className="font-semibold text-gray-800 mb-2">Investment Thesis</h4>
        <p className="text-gray-600">{data.investment_thesis}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Key Catalysts */}
        <div>
          <h4 className="font-semibold text-green-700 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            Key Catalysts
          </h4>
          {data.key_catalysts.length > 0 ? (
            <ul className="space-y-2">
              {data.key_catalysts.map((catalyst, index) => (
                <li key={index} className="flex items-start">
                  <span className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <span className="text-gray-600">{catalyst}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">No catalysts identified</p>
          )}
        </div>

        {/* Key Risks */}
        <div>
          <h4 className="font-semibold text-red-700 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Key Risks
          </h4>
          {data.key_risks.length > 0 ? (
            <ul className="space-y-2">
              {data.key_risks.map((risk, index) => (
                <li key={index} className="flex items-start">
                  <span className="w-2 h-2 bg-red-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  <span className="text-gray-600">{risk}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 italic">No risks identified</p>
          )}
        </div>
      </div>
    </div>
  );
}
