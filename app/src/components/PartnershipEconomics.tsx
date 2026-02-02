import type { Partnership } from '../types';
import Citation from './Citation';

interface Props {
  partnerships: Partnership[];
  sectionName: string;
}

function formatCurrency(amount?: number): string {
  if (!amount) return '-';
  if (amount >= 1000000000) {
    return `$${(amount / 1000000000).toFixed(1)}B`;
  }
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(0)}M`;
  }
  return `$${amount.toLocaleString()}`;
}

export default function PartnershipEconomics({ partnerships, sectionName }: Props) {
  if (!partnerships || partnerships.length === 0) {
    return null;
  }

  const activePartnerships = partnerships.filter(p => p.status === 'Active');

  return (
    <div className="partnership-economics mt-8">
      <h4 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-biotech-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
        Partnership Economics
      </h4>

      <div className="space-y-4">
        {activePartnerships.map((partnership, idx) => (
          <div key={idx} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-biotech-50 to-white px-4 py-3 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h5 className="font-semibold text-gray-900">{partnership.partner}</h5>
                  <p className="text-sm text-gray-600">
                    Est. {partnership.established}
                    {partnership.programs && partnership.programs.length > 0 && (
                      <span> • {partnership.programs.length} program{partnership.programs.length > 1 ? 's' : ''}</span>
                    )}
                  </p>
                </div>
                <span className="badge bg-green-100 text-green-700 text-xs">
                  {partnership.status}
                </span>
              </div>
            </div>

            {/* Financial Terms */}
            {partnership.financial_terms && (
              <div className="p-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="text-center p-3 bg-gray-50 rounded">
                    <div className="text-xs text-gray-500 mb-1">Upfront</div>
                    <div className="font-semibold text-gray-900">
                      {formatCurrency(partnership.financial_terms.upfront)}
                    </div>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded">
                    <div className="text-xs text-gray-500 mb-1">Dev Milestones</div>
                    <div className="font-semibold text-gray-900">
                      {formatCurrency(partnership.financial_terms.development_milestones_potential)}
                    </div>
                  </div>
                  <div className="text-center p-3 bg-gray-50 rounded">
                    <div className="text-xs text-gray-500 mb-1">Commercial</div>
                    <div className="font-semibold text-gray-900">
                      {formatCurrency(partnership.financial_terms.commercial_milestones_potential)}
                    </div>
                  </div>
                  <div className="text-center p-3 bg-biotech-50 rounded">
                    <div className="text-xs text-biotech-600 mb-1">Total Deal Value</div>
                    <div className="font-bold text-biotech-700">
                      {formatCurrency(partnership.financial_terms.total_deal_value)}
                    </div>
                  </div>
                </div>

                {/* Progress bar for received */}
                {partnership.financial_terms.received_to_date && partnership.financial_terms.total_deal_value && (
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-600 mb-1">
                      <span>Received to Date</span>
                      <span>{formatCurrency(partnership.financial_terms.received_to_date)} / {formatCurrency(partnership.financial_terms.total_deal_value)}</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-biotech-500 rounded-full"
                        style={{
                          width: `${Math.min(100, (partnership.financial_terms.received_to_date / partnership.financial_terms.total_deal_value) * 100)}%`
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Royalties */}
                {partnership.financial_terms.royalties && (
                  <div className="text-sm text-gray-600 mb-3">
                    <span className="font-medium">Royalties:</span> {partnership.financial_terms.royalties}
                  </div>
                )}
              </div>
            )}

            {/* Programs */}
            {partnership.programs && partnership.programs.length > 0 && (
              <div className="px-4 pb-3">
                <div className="text-xs text-gray-500 mb-2">Programs Covered</div>
                <div className="flex flex-wrap gap-2">
                  {partnership.programs.map((prog, pidx) => (
                    <span key={pidx} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                      {prog}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Responsibilities */}
            {partnership.responsibilities && (
              <div className="px-4 pb-3 border-t border-gray-100 pt-3">
                <div className="grid md:grid-cols-2 gap-3 text-sm">
                  {partnership.responsibilities.arwr && (
                    <div>
                      <span className="text-gray-500">ARWR:</span>{' '}
                      <span className="text-gray-700">{partnership.responsibilities.arwr}</span>
                    </div>
                  )}
                  {partnership.responsibilities.partner && (
                    <div>
                      <span className="text-gray-500">{partnership.partner}:</span>{' '}
                      <span className="text-gray-700">{partnership.responsibilities.partner}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Key Terms */}
            {partnership.key_terms && (
              <div className="px-4 pb-4 text-xs text-gray-500 italic">
                {partnership.key_terms}
                {partnership.citation_number && (
                  <Citation section={sectionName} number={partnership.citation_number} />
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Summary Stats */}
      {activePartnerships.length > 1 && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-biotech-700">
                {activePartnerships.length}
              </div>
              <div className="text-xs text-gray-500">Active Partners</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-biotech-700">
                {formatCurrency(
                  activePartnerships.reduce((sum, p) => sum + (p.financial_terms?.total_deal_value || 0), 0)
                )}
              </div>
              <div className="text-xs text-gray-500">Total Deal Value</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-600">
                {formatCurrency(
                  activePartnerships.reduce((sum, p) => sum + (p.financial_terms?.received_to_date || 0), 0)
                )}
              </div>
              <div className="text-xs text-gray-500">Received to Date</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
