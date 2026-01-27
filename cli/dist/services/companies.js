"use strict";
/**
 * Companies Service
 *
 * Talks to your backend API to get XBI company data.
 * This service handles searching for companies and fetching their details.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.searchCompanies = searchCompanies;
exports.getCompanyByTicker = getCompanyByTicker;
exports.getAllCompanies = getAllCompanies;
const axios_1 = __importDefault(require("axios"));
const config_1 = require("../config");
/**
 * Search for companies by name or ticker
 * Uses fuzzy matching on the backend
 */
async function searchCompanies(query) {
    const config = (0, config_1.getConfig)();
    try {
        // The backend API endpoint for searching companies
        const response = await axios_1.default.get(`${config.apiUrl}/api/companies/search`, {
            params: { q: query }
        });
        return response.data;
    }
    catch (error) {
        // If search endpoint doesn't exist, fallback to getting all and filtering
        const response = await axios_1.default.get(`${config.apiUrl}/api/companies`);
        const queryLower = query.toLowerCase();
        return response.data.filter(company => company.ticker.toLowerCase().includes(queryLower) ||
            company.name.toLowerCase().includes(queryLower));
    }
}
/**
 * Get a specific company by ticker
 */
async function getCompanyByTicker(ticker) {
    const config = (0, config_1.getConfig)();
    const tickerUpper = ticker.toUpperCase();
    try {
        // Try direct endpoint first
        const response = await axios_1.default.get(`${config.apiUrl}/api/companies/${tickerUpper}`);
        return response.data;
    }
    catch (error) {
        // Fallback: get all companies and find the one we want
        const response = await axios_1.default.get(`${config.apiUrl}/api/companies`);
        return response.data.find(c => c.ticker.toUpperCase() === tickerUpper) || null;
    }
}
/**
 * Get all XBI companies
 */
async function getAllCompanies() {
    const config = (0, config_1.getConfig)();
    const response = await axios_1.default.get(`${config.apiUrl}/api/companies`);
    return response.data;
}
//# sourceMappingURL=companies.js.map