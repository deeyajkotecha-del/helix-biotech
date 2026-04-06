import { Routes, Route } from 'react-router-dom';
import { SearchPage } from './components/search';
import {
  EvidencePage,
  AppLayout,
  CompaniesPage,
  DirectoryPage,
  EnrichmentPage,
  GlobalPage,
  ForecasterPage
} from './components/evidence';

function App() {
  return (
    <Routes>
      {/* Main layout with sidebar navigation */}
      <Route element={<AppLayout />}>
        <Route path="/" element={<EvidencePage />} />
        <Route path="/extract" element={<EvidencePage />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/directory" element={<DirectoryPage />} />
        <Route path="/enrichment" element={<EnrichmentPage />} />
        <Route path="/global" element={<GlobalPage />} />
        <Route path="/forecaster" element={<ForecasterPage />} />
      </Route>

      {/* Legacy search route (no sidebar) */}
      <Route path="/search" element={<SearchPage />} />
    </Routes>
  );
}

export default App;
