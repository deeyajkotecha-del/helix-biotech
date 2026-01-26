import { useState, useEffect } from 'react';
import { companiesApi } from '../services/api';
import type { Company } from '../types';
import CompanyCard from './CompanyCard';

export default function Dashboard() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      setLoading(true);
      const data = await companiesApi.list();
      setCompanies(data);
      setError(null);
    } catch (err) {
      setError('Failed to load companies. Make sure the backend is running.');
      console.error('Error loading companies:', err);
    } finally {
      setLoading(false);
    }
  };

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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {companies.map((company) => (
          <CompanyCard key={company.ticker} company={company} />
        ))}
      </div>

      {companies.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No companies found. Check the backend configuration.
        </div>
      )}
    </div>
  );
}
