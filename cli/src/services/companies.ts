/**
 * Companies Service
 *
 * Talks to your backend API to get XBI company data.
 * This service handles searching for companies and fetching their details.
 */

import axios from 'axios';
import { Company } from '../types';
import { getConfig } from '../config';

/**
 * Search for companies by name or ticker
 * Uses fuzzy matching on the backend
 */
export async function searchCompanies(query: string): Promise<Company[]> {
  const config = getConfig();

  try {
    // The backend API endpoint for searching companies
    const response = await axios.get<Company[]>(`${config.apiUrl}/api/companies/search`, {
      params: { q: query }
    });
    return response.data;
  } catch (error) {
    // If search endpoint doesn't exist, fallback to getting all and filtering
    const response = await axios.get<Company[]>(`${config.apiUrl}/api/companies`);
    const queryLower = query.toLowerCase();

    return response.data.filter(company =>
      company.ticker.toLowerCase().includes(queryLower) ||
      company.name.toLowerCase().includes(queryLower)
    );
  }
}

/**
 * Get a specific company by ticker
 */
export async function getCompanyByTicker(ticker: string): Promise<Company | null> {
  const config = getConfig();
  const tickerUpper = ticker.toUpperCase();

  try {
    // Try direct endpoint first
    const response = await axios.get<Company>(`${config.apiUrl}/api/companies/${tickerUpper}`);
    return response.data;
  } catch (error) {
    // Fallback: get all companies and find the one we want
    const response = await axios.get<Company[]>(`${config.apiUrl}/api/companies`);
    return response.data.find(c => c.ticker.toUpperCase() === tickerUpper) || null;
  }
}

/**
 * Get all XBI companies
 */
export async function getAllCompanies(): Promise<Company[]> {
  const config = getConfig();
  const response = await axios.get<Company[]>(`${config.apiUrl}/api/companies`);
  return response.data;
}
