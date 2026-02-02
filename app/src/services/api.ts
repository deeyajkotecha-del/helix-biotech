import axios from 'axios';
import type { Company, Report, Source, CitationWithSource, ReportCitationsResponse } from '../types';

// Use local backend for development, production URL for deployed app
const API_BASE = import.meta.env.DEV
  ? 'http://localhost:8000/api'
  : 'https://backend-production-ed24.up.railway.app/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const companiesApi = {
  list: async (): Promise<Company[]> => {
    const response = await api.get<Company[]>('/companies');
    return response.data;
  },

  get: async (ticker: string): Promise<Company> => {
    const response = await api.get<Company>(`/companies/${ticker}`);
    return response.data;
  },

  refresh: async (ticker: string): Promise<{ status: string; message: string }> => {
    const response = await api.post(`/companies/${ticker}/refresh`);
    return response.data;
  },
};

export const reportsApi = {
  get: async (ticker: string): Promise<Report> => {
    const response = await api.get<Report>(`/reports/${ticker}`);
    return response.data;
  },

  generate: async (ticker: string, forceRefresh = false): Promise<Report> => {
    const response = await api.post<Report>(
      `/reports/${ticker}/generate`,
      null,
      { params: { force_refresh: forceRefresh } }
    );
    return response.data;
  },

  getSection: async (ticker: string, sectionName: string) => {
    const response = await api.get(`/reports/${ticker}/section/${sectionName}`);
    return response.data;
  },

  listAvailable: async () => {
    const response = await api.get('/reports');
    return response.data;
  },
};

export const sourcesApi = {
  list: async (params?: { skip?: number; limit?: number; source_type?: string; search?: string }) => {
    const response = await api.get<{ sources: Source[]; total: number; skip: number; limit: number }>('/sources', { params });
    return response.data;
  },

  get: async (id: number): Promise<Source> => {
    const response = await api.get<Source>(`/sources/${id}`);
    return response.data;
  },

  getPdfUrl: (id: number): string => {
    return `${API_BASE}/sources/${id}/pdf`;
  },
};

export const citationsApi = {
  getReportCitations: async (ticker: string, section?: string): Promise<ReportCitationsResponse> => {
    const response = await api.get<ReportCitationsResponse>(`/citations/report/${ticker}`, {
      params: section ? { section } : undefined,
    });
    return response.data;
  },

  get: async (id: number): Promise<CitationWithSource> => {
    const response = await api.get<CitationWithSource>(`/citations/${id}`);
    return response.data;
  },
};

export default api;
