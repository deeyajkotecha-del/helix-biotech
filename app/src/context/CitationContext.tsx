import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Source, CitationWithSource, CitationContextValue } from '../types';
import { citationsApi } from '../services/api';

const CitationContext = createContext<CitationContextValue | undefined>(undefined);

interface CitationProviderProps {
  children: ReactNode;
  ticker: string;
}

export function CitationProvider({ children, ticker }: CitationProviderProps) {
  const [citations, setCitations] = useState<CitationWithSource[]>([]);
  const [activeSource, setActiveSource] = useState<Source | null>(null);
  const [activePdfPage, setActivePdfPage] = useState<number | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const loadCitations = useCallback(async (reportTicker: string) => {
    if (loaded) return;
    try {
      const response = await citationsApi.getReportCitations(reportTicker);
      setCitations(response.citations);
      setLoaded(true);
    } catch (err) {
      console.error('Error loading citations:', err);
    }
  }, [loaded]);

  // Load citations when ticker is available
  if (ticker && !loaded) {
    loadCitations(ticker);
  }

  const openSource = useCallback((citation: CitationWithSource) => {
    setActiveSource(citation.source);
    setActivePdfPage(citation.pdf_page);
    setSidebarOpen(true);
  }, []);

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false);
    // Delay clearing source to allow animation
    setTimeout(() => {
      setActiveSource(null);
      setActivePdfPage(null);
    }, 300);
  }, []);

  const getCitationByNumber = useCallback((section: string, number: number) => {
    return citations.find(
      c => c.section_name === section && c.citation_number === number
    );
  }, [citations]);

  const value: CitationContextValue = {
    citations,
    activeSource,
    activePdfPage,
    sidebarOpen,
    loadCitations,
    openSource,
    closeSidebar,
    getCitationByNumber,
  };

  return (
    <CitationContext.Provider value={value}>
      {children}
    </CitationContext.Provider>
  );
}

export function useCitation() {
  const context = useContext(CitationContext);
  if (context === undefined) {
    throw new Error('useCitation must be used within a CitationProvider');
  }
  return context;
}

export default CitationContext;
