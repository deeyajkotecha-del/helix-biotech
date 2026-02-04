import type { Company } from '../types';

interface Props {
  company: Company;
}

const stageLabels: Record<string, string> = {
  large_cap_diversified: 'Large Cap',
  commercial_stage: 'Commercial',
  late_clinical: 'Late Clinical',
  mid_clinical: 'Mid Clinical',
  early_clinical: 'Early Clinical',
  preclinical: 'Preclinical',
};

const modalityLabels: Record<string, string> = {
  small_molecule: 'Small Molecule',
  antibody_biologics: 'Antibody/Biologics',
  rna_therapeutics: 'RNA',
  cell_gene_therapy: 'Cell/Gene',
  radiopharmaceutical: 'Radiopharm',
  platform_diversified: 'Platform',
};

export default function CompanyCard({ company }: Props) {
  const stageLabel = company.development_stage ? stageLabels[company.development_stage] || company.development_stage : null;
  const modalityLabel = company.modality ? modalityLabels[company.modality] || company.modality : null;

  // Link to server-rendered HTML page with full clinical data
  const companyUrl = `/api/clinical/companies/${company.ticker}/html`;

  return (
    <a
      href={companyUrl}
      className="block bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden"
    >
      <div className="p-6">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="inline-block px-3 py-1 bg-biotech-100 text-biotech-700 font-bold rounded text-lg">
              {company.ticker}
            </span>
            {company.has_data && (
              <span className="inline-block px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded">
                Data
              </span>
            )}
          </div>
          {stageLabel && (
            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
              {stageLabel}
            </span>
          )}
        </div>

        <h3 className="text-lg font-semibold text-gray-800 mb-2">
          {company.name}
        </h3>

        {/* Tags for modality and therapeutic area */}
        <div className="flex flex-wrap gap-1 mb-3">
          {modalityLabel && (
            <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
              {company.modality_subtype || modalityLabel}
            </span>
          )}
          {company.therapeutic_subtype && (
            <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded">
              {company.therapeutic_subtype}
            </span>
          )}
        </div>

        {company.notes && (
          <p className="text-gray-600 text-sm mb-4 line-clamp-2">
            {company.notes}
          </p>
        )}

        {company.market_cap_mm && (
          <div className="text-sm text-gray-500">
            Market Cap: ${(company.market_cap_mm / 1000).toFixed(1)}B
          </div>
        )}

        <div className="mt-4 flex items-center text-biotech-600 text-sm font-medium">
          View Clinical Data
          <svg
            className="w-4 h-4 ml-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </div>
      </div>
    </a>
  );
}
