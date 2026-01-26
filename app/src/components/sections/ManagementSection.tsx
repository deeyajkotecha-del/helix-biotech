import type { ManagementSection as ManagementData } from '../../types';

interface Props {
  data: ManagementData;
}

export default function ManagementSection({ data }: Props) {
  return (
    <div>
      <h3 className="section-title">Management Team Assessment</h3>

      {/* CEO */}
      {data.ceo && (
        <div className="bg-gray-50 rounded-lg p-5 mb-6">
          <div className="flex items-start">
            <div className="w-12 h-12 bg-biotech-600 rounded-full flex items-center justify-center text-white font-bold text-lg mr-4">
              {data.ceo.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
            </div>
            <div>
              <h4 className="font-semibold text-lg text-gray-800">{data.ceo.name}</h4>
              <p className="text-biotech-600 font-medium">{data.ceo.title}</p>
              {data.ceo.background && (
                <p className="text-gray-600 mt-2 text-sm">{data.ceo.background}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Key Executives */}
      {data.key_executives.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-800 mb-3">Key Executives</h4>
          <div className="grid md:grid-cols-2 gap-4">
            {data.key_executives.map((exec, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 flex items-start"
              >
                <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-gray-600 font-medium text-sm mr-3">
                  {exec.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                </div>
                <div>
                  <p className="font-medium text-gray-800">{exec.name}</p>
                  <p className="text-gray-500 text-sm">{exec.title}</p>
                  {exec.background && (
                    <p className="text-gray-400 text-xs mt-1">{exec.background}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Changes */}
      {data.recent_changes.length > 0 && (
        <div className="mb-6">
          <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            Recent Changes
          </h4>
          <ul className="space-y-2">
            {data.recent_changes.map((change, index) => (
              <li key={index} className="flex items-start">
                <span className="w-2 h-2 bg-yellow-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-600">{change}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Board Highlights */}
      {data.board_highlights.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Board Highlights
          </h4>
          <ul className="space-y-2">
            {data.board_highlights.map((highlight, index) => (
              <li key={index} className="flex items-start">
                <span className="w-2 h-2 bg-biotech-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-600">{highlight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Empty State */}
      {!data.ceo &&
       data.key_executives.length === 0 &&
       data.recent_changes.length === 0 &&
       data.board_highlights.length === 0 && (
        <p className="text-gray-400 italic">No management data available</p>
      )}
    </div>
  );
}
