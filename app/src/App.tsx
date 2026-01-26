import { Routes, Route } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import ReportView from './components/ReportView';

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-biotech-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold">Biotech Investor Insights Portal</h1>
          <p className="text-biotech-200 text-sm">
            Comprehensive investment analysis powered by PubMed & ClinicalTrials.gov
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/report/:ticker" element={<ReportView />} />
        </Routes>
      </main>

      <footer className="bg-gray-100 border-t mt-8">
        <div className="max-w-7xl mx-auto px-4 py-4 text-center text-sm text-gray-600">
          Data sources: PubMed (NCBI), ClinicalTrials.gov, SEC Filings
        </div>
      </footer>
    </div>
  );
}

export default App;
