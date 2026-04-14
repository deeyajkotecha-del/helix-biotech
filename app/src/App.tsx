import { Routes, Route } from 'react-router-dom';
import {
  EvidencePage,
  AppLayout,
  CompaniesPage,
  DirectoryPage,
  EnrichmentPage,
  GlobalPage,
  ForecasterPage,
  DeckAnalyzerPage,
} from './components/evidence';

function App() {
  return (
    <Routes>
      {/* Main layout with sidebar navigation */}
      <Route element={<AppLayout />}>
        <Route path="/" element={<EvidencePage />} />
        <Route path="/search" element={<EvidencePage />} />
        <Route path="/extract" element={<EvidencePage />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/directory" element={<DirectoryPage />} />
        <Route path="/enrichment" element={<EnrichmentPage />} />
        <Route path="/global" element={<GlobalPage />} />
        <Route path="/forecaster" element={<ForecasterPage />} />
        <Route path="/deck-analyzer" element={<DeckAnalyzerPage />} />
      </Route>
    </Routes>
  );
}

export default App;
