import { Routes, Route } from 'react-router-dom';
import { SearchPage } from './components/search';
import { EvidencePage } from './components/evidence';

function App() {
  return (
    <Routes>
      {/* Evidence / Open Evidence is the homepage */}
      <Route path="/" element={<EvidencePage />} />
      <Route path="/extract" element={<EvidencePage />} />
      <Route path="/extract/" element={<EvidencePage />} />

      {/* Legacy search route still available */}
      <Route path="/search" element={<SearchPage />} />
    </Routes>
  );
}

export default App;
