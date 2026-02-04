import axios from 'axios';
import type { Company, Report } from '../types';

const API_BASE = 'https://backend-production-ed24.up.railway.app/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const companiesApi = {
  list: async (filters?: {
    development_stage?: string;
    modality?: string;
    therapeutic_area?: string;
    thesis_type?: string;
    priority?: string;
    has_data?: boolean;
  }): Promise<Company[]> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const queryString = params.toString();
    const url = `/clinical/companies${queryString ? `?${queryString}` : ''}`;
    const response = await api.get<{ companies: Company[]; count: number }>(url);
    return response.data.companies;
  },

  getTaxonomy: async () => {
    const response = await api.get('/clinical/taxonomy');
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

export default api;
