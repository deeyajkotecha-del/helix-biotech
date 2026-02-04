import { useState, useEffect } from 'react';
import { companiesApi } from '../services/api';
import type { Company } from '../types';
import CompanyCard from './CompanyCard';

interface TaxonomyTier {
  id: string;
  name: string;
  description: string;
}

interface TaxonomyCategory {
  description: string;
  tiers: TaxonomyTier[];
}

type Taxonomy = Record<string, TaxonomyCategory>;

interface Filters {
  development_stage: string;
  modality: string;
  therapeutic_area: string;
}

export default function Dashboard() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [filters, setFilters] = useState<Filters>({
    development_stage: '',
    modality: '',
    therapeutic_area: '',
  });

  useEffect(() => {
    loadTaxonomy();
    loadCompanies();
  }, []);

  useEffect(() => {
    loadCompanies();
  }, [filters]);

  const loadTaxonomy = async () => {
    try {
      const data = await companiesApi.getTaxonomy();
      setTaxonomy(data);
    } catch (err) {
      console.error('Error loading taxonomy:', err);
    }
  };

  const loadCompanies = async () => {
    try {
      setLoading(true);
      const activeFilters = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== '')
      );
      const data = await companiesApi.list(activeFilters);
      setCompanies(data);
      setError(null);
    } catch (err) {
      setError('Failed to load companies. Make sure the backend is running.');
      console.error('Error loading companies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({ development_stage: '', modality: '', therapeutic_area: '' });
  };

  const hasActiveFilters = Object.values(filters).some(v => v !== '');

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="text-center">
          <div className="loading-spinner mx-auto mb-4"></div>
          <p className="text-gray-600">Loading companies...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <h3 className="text-red-800 font-semibold mb-2">Error</h3>
        <p className="text-red-600">{error}</p>
        <button
          onClick={loadCompanies}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          Tracked Biotech Companies
        </h2>
        <p className="text-gray-600">
          Select a company to view comprehensive investment analysis
        </p>
      </div>

      {/* Taxonomy Filters */}
      {taxonomy && (
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Development Stage
              </label>
              <select
                value={filters.development_stage}
                onChange={(e) => handleFilterChange('development_stage', e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-biotech-500 focus:ring-biotech-500 text-sm"
              >
                <option value="">All Stages</option>
                {taxonomy.development_stage?.tiers?.map((tier) => (
                  <option key={tier.id} value={tier.id}>{tier.name}</option>
                ))}
              </select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Modality
              </label>
              <select
                value={filters.modality}
                onChange={(e) => handleFilterChange('modality', e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-biotech-500 focus:ring-biotech-500 text-sm"
              >
                <option value="">All Modalities</option>
                {taxonomy.modality?.tiers?.map((tier) => (
                  <option key={tier.id} value={tier.id}>{tier.name}</option>
                ))}
              </select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Therapeutic Area
              </label>
              <select
                value={filters.therapeutic_area}
                onChange={(e) => handleFilterChange('therapeutic_area', e.target.value)}
                className="w-full rounded-md border-gray-300 shadow-sm focus:border-biotech-500 focus:ring-biotech-500 text-sm"
              >
                <option value="">All Areas</option>
                {taxonomy.therapeutic_area?.tiers?.map((tier) => (
                  <option key={tier.id} value={tier.id}>{tier.name}</option>
                ))}
              </select>
            </div>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md"
              >
                Clear filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* Results count */}
      <div className="mb-4 text-sm text-gray-600">
        Showing {companies.length} {companies.length === 1 ? 'company' : 'companies'}
        {hasActiveFilters && ' (filtered)'}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {companies.map((company) => (
          <CompanyCard key={company.ticker} company={company} />
        ))}
      </div>

      {companies.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          {hasActiveFilters
            ? 'No companies match the selected filters.'
            : 'No companies found. Check the backend configuration.'}
        </div>
      )}
    </div>
  );
}
