import { Link } from 'react-router-dom';
import type { Company } from '../types';

interface Props {
  company: Company;
}

export default function CompanyCard({ company }: Props) {
  return (
    <Link
      to={`/report/${company.ticker}`}
      className="block bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-200 overflow-hidden"
    >
      <div className="p-6">
        <div className="flex items-start justify-between mb-3">
          <div>
            <span className="inline-block px-3 py-1 bg-biotech-100 text-biotech-700 font-bold rounded text-lg">
              {company.ticker}
            </span>
          </div>
          {company.sector && (
            <span className="badge badge-info">{company.sector}</span>
          )}
        </div>

        <h3 className="text-lg font-semibold text-gray-800 mb-2">
          {company.name}
        </h3>

        {company.description && (
          <p className="text-gray-600 text-sm mb-4 line-clamp-2">
            {company.description}
          </p>
        )}

        {company.lead_asset && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <p className="text-sm text-gray-500">Lead Asset</p>
            <p className="font-medium text-biotech-700">{company.lead_asset}</p>
          </div>
        )}

        <div className="mt-4 flex items-center text-biotech-600 text-sm font-medium">
          View Full Report
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
    </Link>
  );
}
