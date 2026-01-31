/**
 * Serve Command
 *
 * Start an HTTP server for browser-based access to the analysis API.
 *
 * Examples:
 *   helix serve                 # Start on default port 3001
 *   helix serve --port 8080     # Start on custom port
 */

import { Command } from 'commander';
import chalk from 'chalk';
import express, { Request, Response } from 'express';
import cors from 'cors';
import * as fs from 'fs';
import * as path from 'path';
import { getFilings, getFilingForAnalysis } from '../services/sec-edgar';
import { getCompanyByTicker, searchCompanies, getAllCompanies } from '../services/companies';
import { getLLMProvider } from '../services/llm';
import { getConfig } from '../config';
import { AnalysisResult, PipelineItem, Company } from '../types';
import { getLandscapeData, generateLandscapeCSV, LandscapeData } from '../services/landscape';
import { searchTrialsByCondition } from '../services/trials';
import { extractMoleculesFromTrials, MoleculeSummary } from '../services/molecules';
import { getFullTrialData, compareTrials, FullTrialData, FormattedOutcome, FormattedSafety, FormattedAE } from '../services/trial-results';
import { getDrugPatentProfile, getPatentsByCondition } from '../services/patents';
import { DrugPatentProfile, OrangeBookPatent, OrangeBookExclusivity } from '../types/schema';
import { pharmaRouter } from '../services/pharma-routes';
import { generateTargetReport, getTrialAnalytics, getPublicationAnalytics, ExtendedReportData } from '../services/target-report';
import { generateExcel, generateCSV } from '../services/export';
import { getTargetAnalysis, TargetAnalysis } from '../data/target-analysis';
import { getARWRProfile, getARWRPipeline, getARWRCatalysts, getARWRPresentations, ARWR_PROFILE } from '../data/companies/arwr';
import { scrapeIRDocuments, isTickerSupported, getSupportedTickers } from '../services/ir-scraper';
import { FEATURED_COMPANIES, CompanyData, Catalyst } from '../types/company';
import { getNextCatalyst, getPastCatalysts, getUpcomingCatalysts, formatCatalystDateShort, getCatalystDisplayText } from '../utils/catalyst-utils';
import { downloadAllDocuments, getDownloadedDocuments } from '../services/pdf-downloader';
import { findKOLsCached, KOL, findEmailBySearch } from '../services/kol-finder';

// Cache directory for analysis results
const CACHE_DIR = path.resolve(__dirname, '..', '..', 'cache');

// Rate limiting: track timestamps of Claude API calls
const apiCallTimestamps: number[] = [];
const RATE_LIMIT_MAX_CALLS = 10;
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour

interface ServeOptions {
  port: string;
}

export function registerServeCommand(program: Command): void {
  program
    .command('serve')
    .description('Start HTTP server for browser-based API access')
    .option('-p, --port <port>', 'Port to listen on', '3001')
    .action(async (options: ServeOptions) => {
      // Use PORT env var (for Railway/Docker) or command line option
      const port = parseInt(process.env.PORT || options.port, 10);
      startServer(port);
    });
}

function startServer(port: number): void {
  const app = express();

  // Log configuration at startup
  const config = getConfig();
  console.log('');
  console.log(chalk.yellow('Configuration:'));
  console.log(chalk.gray(`  LLM_PROVIDER: ${config.llmProvider}`));
  console.log(chalk.gray(`  CLAUDE_MODEL: ${config.claudeModel}`));
  console.log(chalk.gray(`  ANTHROPIC_API_KEY: ${config.claudeApiKey ? '***' + config.claudeApiKey.slice(-4) : 'NOT SET'}`));

  // Enable CORS for browser access
  app.use(cors());
  app.use(express.json());

  // Ensure cache directory exists
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
    console.log(chalk.gray(`  Created cache directory: ${CACHE_DIR}`));
  }

  // Mount pharma intelligence routes
  app.use(pharmaRouter);

  // Homepage - Satya Bio (Professional SaaS Landing Page)
  app.get('/', (_req: Request, res: Response) => {
    const today = new Date();
    const lastUpdated = today.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Satya Bio | Biotech Intelligence for the Buy Side</title>
  <meta name="description" content="Competitive landscapes, catalyst tracking, and pipeline analytics — built for investment professionals.">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy: #1a2b3c;
      --navy-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --accent-light: #fef5f3;
      --bg: #fafaf8;
      --surface: #ffffff;
      --surface-alt: #f5f5f3;
      --border: #e5e5e0;
      --border-light: #eeeeea;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
      --highlight: #fef3c7;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

    /* Mesh gradient overlay */
    .hero-gradient {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background:
        radial-gradient(ellipse 80% 50% at 20% 40%, rgba(254,245,243,0.8) 0%, transparent 50%),
        radial-gradient(ellipse 60% 40% at 80% 60%, rgba(224,122,95,0.15) 0%, transparent 50%),
        radial-gradient(ellipse 50% 30% at 50% 20%, rgba(254,243,199,0.5) 0%, transparent 50%),
        linear-gradient(180deg, var(--bg) 0%, #f5f0eb 100%);
      pointer-events: none;
      z-index: 0;
    }

    /* Floating circles - BOLD and visible */
    .hero-bg {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      overflow: hidden;
      pointer-events: none;
      z-index: 1;
    }
    .circle {
      position: absolute;
      border-radius: 50%;
      filter: blur(1px);
    }
    .circle-1 {
      width: 500px; height: 500px;
      background: linear-gradient(135deg, rgba(254,243,199,0.6) 0%, rgba(253,230,138,0.5) 100%);
      top: -200px; right: -5%;
      opacity: 0.7;
      animation: float1 30s ease-in-out infinite;
    }
    .circle-2 {
      width: 350px; height: 350px;
      background: linear-gradient(135deg, rgba(254,205,193,0.6) 0%, rgba(224,122,95,0.35) 100%);
      bottom: -10%; left: -5%;
      opacity: 0.6;
      animation: float2 25s ease-in-out infinite;
    }
    .circle-3 {
      width: 200px; height: 200px;
      background: linear-gradient(135deg, rgba(224,242,254,0.7) 0%, rgba(186,230,253,0.5) 100%);
      top: 30%; right: 15%;
      opacity: 0.65;
      animation: float3 20s ease-in-out infinite;
    }
    .circle-4 {
      width: 280px; height: 280px;
      background: linear-gradient(135deg, rgba(224,122,95,0.25) 0%, rgba(254,205,193,0.4) 100%);
      top: 60%; left: 20%;
      opacity: 0.5;
      animation: float4 35s ease-in-out infinite;
    }
    .circle-5 {
      width: 150px; height: 150px;
      background: linear-gradient(135deg, rgba(254,243,199,0.7) 0%, rgba(253,230,138,0.4) 100%);
      top: 10%; left: 10%;
      opacity: 0.55;
      animation: float5 28s ease-in-out infinite;
    }
    @keyframes float1 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      25% { transform: translate(30px, -20px) scale(1.02); }
      50% { transform: translate(-20px, 30px) scale(0.98); }
      75% { transform: translate(20px, 20px) scale(1.01); }
    }
    @keyframes float2 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      33% { transform: translate(-25px, -30px) scale(1.03); }
      66% { transform: translate(35px, 15px) scale(0.97); }
    }
    @keyframes float3 {
      0%, 100% { transform: translate(0, 0); }
      50% { transform: translate(-40px, 25px); }
    }
    @keyframes float4 {
      0%, 100% { transform: translate(0, 0) scale(1); }
      40% { transform: translate(20px, -35px) scale(1.02); }
      80% { transform: translate(-30px, 20px) scale(0.98); }
    }
    @keyframes float5 {
      0%, 100% { transform: translate(0, 0); }
      30% { transform: translate(25px, 20px); }
      70% { transform: translate(-15px, -25px); }
    }

    /* Floating ticker pills */
    .floating-tickers {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      pointer-events: none;
      z-index: 1;
      overflow: hidden;
    }
    .ticker-pill {
      position: absolute;
      padding: 6px 14px;
      background: rgba(255,255,255,0.85);
      border: 1px solid rgba(224,122,95,0.3);
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 700;
      color: var(--navy);
      box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      backdrop-filter: blur(4px);
    }
    .ticker-pill:nth-child(1) { top: 20%; left: 8%; animation: tickerFloat1 40s ease-in-out infinite; }
    .ticker-pill:nth-child(2) { top: 65%; left: 5%; animation: tickerFloat2 35s ease-in-out infinite; }
    .ticker-pill:nth-child(3) { top: 25%; right: 6%; animation: tickerFloat3 45s ease-in-out infinite; }
    .ticker-pill:nth-child(4) { top: 70%; right: 8%; animation: tickerFloat4 38s ease-in-out infinite; }
    .ticker-pill:nth-child(5) { top: 45%; left: 3%; animation: tickerFloat5 42s ease-in-out infinite; }
    @keyframes tickerFloat1 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(15px, 25px); } }
    @keyframes tickerFloat2 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(20px, -20px); } }
    @keyframes tickerFloat3 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-25px, 15px); } }
    @keyframes tickerFloat4 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(-15px, -25px); } }
    @keyframes tickerFloat5 { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(10px, -15px); } }

    /* Header */
    .header { position: sticky; top: 0; z-index: 100; background: rgba(250,250,248,0.95); backdrop-filter: blur(12px); border-bottom: 1px solid var(--border-light); padding: 0 32px; height: 68px; }
    .header-inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.4rem; font-weight: 800; color: var(--navy); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover { color: var(--navy); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-primary { padding: 10px 20px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; font-size: 0.9rem; transition: all 0.2s; }
    .btn-primary:hover { background: var(--accent-hover); transform: translateY(-1px); }

    /* Hero - Striking */
    .hero { background: transparent; padding: 110px 32px 90px; text-align: center; position: relative; overflow: hidden; min-height: 70vh; display: flex; align-items: center; justify-content: center; }
    .hero-content { position: relative; z-index: 2; max-width: 900px; margin: 0 auto; }
    .hero h1 {
      font-family: 'Fraunces', serif;
      font-size: 4.5rem;
      font-weight: 800;
      color: var(--navy);
      margin-bottom: 24px;
      letter-spacing: -0.04em;
      line-height: 1.05;
      text-shadow: 0 2px 4px rgba(26,43,60,0.08);
    }
    .hero-subtitle { color: var(--text-secondary); font-size: 1.35rem; margin-bottom: 48px; line-height: 1.6; max-width: 650px; margin-left: auto; margin-right: auto; }

    /* Hero Search - Glowing */
    .hero-search { max-width: 580px; margin: 0 auto 28px; position: relative; }
    .hero-search input {
      width: 100%;
      padding: 20px 28px 20px 56px;
      border: 2px solid var(--border);
      border-radius: 16px;
      font-size: 1.1rem;
      font-family: inherit;
      background: white;
      box-shadow: 0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04);
      outline: none;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .hero-search input:focus {
      border-color: var(--accent);
      box-shadow: 0 12px 48px rgba(0,0,0,0.12), 0 0 0 4px rgba(224,122,95,0.15);
      transform: translateY(-2px);
    }
    .hero-search input::placeholder { color: var(--text-muted); }
    .hero-search-icon { position: absolute; left: 22px; top: 50%; transform: translateY(-50%); width: 22px; height: 22px; color: var(--text-muted); transition: color 0.2s; }
    .hero-search:focus-within .hero-search-icon { color: var(--accent); }
    .hero-updated { font-size: 0.85rem; color: var(--text-muted); margin-top: 20px; }
    .hero-updated span { background: rgba(224,122,95,0.12); color: var(--accent); padding: 4px 12px; border-radius: 12px; font-weight: 600; }

    /* Live Preview Cards - Striking */
    .preview-section { padding: 96px 32px; background: linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%); }
    .preview-inner { max-width: 1180px; margin: 0 auto; }
    .preview-header { text-align: center; margin-bottom: 56px; }
    .preview-header h2 { font-family: 'Fraunces', serif; font-size: 2.2rem; color: var(--navy); margin-bottom: 12px; font-weight: 700; }
    .preview-header p { color: var(--text-muted); font-size: 1.05rem; }
    .preview-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
    @media (max-width: 900px) { .preview-grid { grid-template-columns: 1fr; } }

    .preview-card {
      background: linear-gradient(135deg, #ffffff 0%, #fefdfb 50%, #faf8f6 100%);
      border: 1px solid var(--border);
      border-left: 4px solid var(--accent);
      border-radius: 20px;
      padding: 36px;
      transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 4px 16px rgba(0,0,0,0.06), 0 1px 4px rgba(0,0,0,0.04);
      position: relative;
      overflow: hidden;
    }
    .preview-card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 100%;
      background: linear-gradient(180deg, rgba(224,122,95,0.03) 0%, transparent 40%);
      pointer-events: none;
    }
    .preview-card:hover {
      border-color: var(--accent);
      box-shadow: 0 24px 64px rgba(0,0,0,0.14), 0 8px 24px rgba(224,122,95,0.1);
      transform: translateY(-8px) scale(1.01);
    }
    .preview-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; position: relative; z-index: 1; }
    .preview-card h3 { font-family: 'Fraunces', serif; font-size: 1.3rem; font-weight: 700; color: var(--navy); }

    /* Vibrant badges with pulse */
    .preview-badge {
      padding: 6px 14px;
      background: linear-gradient(135deg, var(--accent) 0%, #d06a4f 100%);
      color: white;
      font-size: 0.7rem;
      font-weight: 700;
      border-radius: 14px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      box-shadow: 0 2px 8px rgba(224,122,95,0.4);
      animation: badgePulse 3s ease-in-out infinite;
    }
    @keyframes badgePulse {
      0%, 100% { box-shadow: 0 2px 8px rgba(224,122,95,0.4); }
      50% { box-shadow: 0 4px 16px rgba(224,122,95,0.6); }
    }

    .preview-stats { margin-bottom: 28px; position: relative; z-index: 1; }
    .preview-stat { display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--border-light); }
    .preview-stat:last-child { border-bottom: none; }
    .preview-stat-label { color: var(--text-secondary); font-size: 0.9rem; }
    .preview-stat-value {
      font-family: 'Fraunces', serif;
      font-weight: 800;
      font-size: 2rem;
      color: var(--navy);
      letter-spacing: -0.02em;
    }
    .preview-stat-value.highlight { color: var(--accent); }

    .preview-items { margin-bottom: 28px; position: relative; z-index: 1; }
    .preview-item { padding: 14px 0; border-bottom: 1px solid var(--border-light); font-size: 0.9rem; color: var(--text-secondary); }
    .preview-item:last-child { border-bottom: none; }
    .preview-item strong { color: var(--navy); font-weight: 700; }

    .preview-link {
      display: block;
      text-align: center;
      padding: 16px;
      background: linear-gradient(135deg, var(--navy) 0%, #243848 100%);
      color: white;
      text-decoration: none;
      border-radius: 12px;
      font-size: 0.95rem;
      font-weight: 600;
      transition: all 0.25s;
      box-shadow: 0 6px 20px rgba(26,43,60,0.25);
      position: relative;
      z-index: 1;
    }
    .preview-link:hover {
      background: linear-gradient(135deg, var(--navy-light) 0%, #2d4a5e 100%);
      transform: translateY(-3px);
      box-shadow: 0 10px 28px rgba(26,43,60,0.3);
    }

    /* Value Props - Premium */
    .value-section { padding: 88px 32px; background: var(--bg); }
    .value-inner { max-width: 920px; margin: 0 auto; }
    .value-header { text-align: center; margin-bottom: 56px; }
    .value-header h2 { font-family: 'Fraunces', serif; font-size: 2.2rem; color: var(--navy); margin-bottom: 14px; font-weight: 700; }
    .value-header p { color: var(--text-secondary); font-size: 1.1rem; }
    .value-list { display: flex; flex-direction: column; gap: 18px; }
    .value-item { display: flex; align-items: flex-start; gap: 18px; padding: 24px 28px; background: var(--surface); border: 1px solid var(--border-light); border-radius: 14px; transition: all 0.25s; box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
    .value-item:hover { border-color: var(--accent); box-shadow: 0 8px 24px rgba(0,0,0,0.08); transform: translateX(4px); }
    .value-dot { width: 10px; height: 10px; background: var(--accent); border-radius: 50%; flex-shrink: 0; margin-top: 8px; }
    .value-text { flex: 1; }
    .value-text h4 { font-size: 1.05rem; font-weight: 600; color: var(--navy); margin-bottom: 6px; }
    .value-text p { font-size: 0.92rem; color: var(--text-secondary); margin: 0; line-height: 1.5; }

    /* At a Glance - Premium Dark Navy */
    .glance-section { background: linear-gradient(135deg, var(--navy) 0%, #243848 100%); padding: 72px 32px; }
    .glance-inner { max-width: 1000px; margin: 0 auto; text-align: center; }
    .glance-title { font-family: 'Fraunces', serif; font-size: 1.3rem; color: rgba(255,255,255,0.7); margin-bottom: 40px; font-weight: 500; letter-spacing: 0.02em; }
    .glance-stats { display: flex; justify-content: center; gap: 100px; flex-wrap: wrap; }
    .glance-stat { text-align: center; }
    .glance-value { font-family: 'Fraunces', serif; font-size: 3.5rem; font-weight: 800; color: white; margin-bottom: 8px; letter-spacing: -0.02em; }
    .glance-label { font-size: 0.95rem; color: rgba(255,255,255,0.6); font-weight: 500; }
    .glance-meta { margin-top: 40px; display: flex; justify-content: center; gap: 32px; flex-wrap: wrap; }
    .glance-meta-item { display: flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.5); font-size: 0.85rem; }
    .glance-meta-item svg { width: 14px; height: 14px; }

    /* CTA Section */
    .cta-section { padding: 80px 32px; background: var(--surface-alt); }
    .cta-inner { max-width: 600px; margin: 0 auto; text-align: center; }
    .cta-inner h2 { font-family: 'Fraunces', serif; font-size: 2rem; color: var(--navy); margin-bottom: 12px; }
    .cta-inner p { color: var(--text-secondary); font-size: 1rem; margin-bottom: 32px; }
    .cta-form { display: flex; gap: 12px; max-width: 480px; margin: 0 auto 16px; }
    .cta-form input { flex: 1; padding: 14px 18px; border: 2px solid var(--border); border-radius: 10px; font-size: 1rem; font-family: inherit; outline: none; transition: border-color 0.2s; }
    .cta-form input:focus { border-color: var(--accent); }
    .cta-form button { padding: 14px 28px; background: var(--accent); color: white; border: none; border-radius: 10px; font-size: 1rem; font-weight: 700; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
    .cta-form button:hover { background: var(--accent-hover); }
    .cta-note { font-size: 0.85rem; color: var(--text-muted); }

    /* Company Logos Section */
    .logos-section { padding: 48px 32px; background: var(--surface); border-top: 1px solid var(--border-light); }
    .logos-inner { max-width: 1000px; margin: 0 auto; text-align: center; }
    .logos-title { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 24px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
    .logos-row {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 40px;
      flex-wrap: wrap;
    }
    .logo-item {
      padding: 10px 20px;
      background: var(--bg);
      border: 1px solid var(--border-light);
      border-radius: 10px;
      font-weight: 700;
      font-size: 0.9rem;
      color: var(--navy);
      transition: all 0.2s;
    }
    .logo-item:hover { border-color: var(--accent); background: var(--accent-light); }
    .logo-item span { color: var(--text-muted); font-weight: 500; font-size: 0.75rem; margin-left: 8px; }

    /* Footer */
    .footer { background: var(--navy); color: rgba(255,255,255,0.6); padding: 48px 32px; text-align: center; }
    .footer p { font-size: 0.9rem; }

    /* Mobile */
    @media (max-width: 768px) {
      .nav-links { display: none; }
      .hero { padding: 80px 20px 60px; min-height: 60vh; }
      .hero h1 { font-size: 2.6rem; }
      .hero-subtitle { font-size: 1rem; margin-bottom: 36px; }
      .hero-search input { padding: 16px 20px 16px 48px; font-size: 0.95rem; }
      .floating-tickers { display: none; }
      .preview-section, .value-section, .cta-section { padding: 56px 20px; }
      .preview-card { padding: 24px; border-left-width: 3px; }
      .preview-stat-value { font-size: 1.5rem; }
      .glance-section { padding: 56px 20px; }
      .glance-stats { gap: 48px; }
      .glance-value { font-size: 2.5rem; }
      .cta-form { flex-direction: column; }
      .value-item { padding: 20px; }
      .logos-section { padding: 40px 20px; }
      .logos-row { gap: 16px; }
      .logo-item { padding: 8px 14px; font-size: 0.8rem; }
      .logo-item span { display: none; }
    }
  </style>
</head>
<body>
  <!-- Header -->
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
        <a href="#cta" class="btn-primary">Request Access</a>
      </div>
    </div>
  </header>

  <!-- Hero -->
  <section class="hero">
    <div class="hero-gradient"></div>
    <div class="hero-bg">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
      <div class="circle circle-4"></div>
      <div class="circle circle-5"></div>
    </div>
    <div class="floating-tickers">
      <div class="ticker-pill">ARWR</div>
      <div class="ticker-pill">VKTX</div>
      <div class="ticker-pill">ALNY</div>
      <div class="ticker-pill">RCKT</div>
      <div class="ticker-pill">IONS</div>
    </div>
    <div class="hero-content">
      <h1>Biotech Intelligence<br>for the Buy Side</h1>
      <p class="hero-subtitle">Competitive landscapes, catalyst tracking, and pipeline analytics — built for investment professionals</p>
      <div class="hero-search">
        <svg class="hero-search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <input type="text" placeholder="Search targets, companies, or therapeutic areas..." onfocus="window.location.href='/companies'">
      </div>
      <div class="hero-updated">Data updated <span>${lastUpdated}</span></div>
    </div>
  </section>

  <!-- Live Preview Cards -->
  <section class="preview-section">
    <div class="preview-inner">
      <div class="preview-header">
        <h2>See What We Track</h2>
        <p>Real data, updated daily</p>
      </div>
      <div class="preview-grid">
        <!-- GLP-1 Landscape -->
        <div class="preview-card">
          <div class="preview-card-header">
            <h3>GLP-1 Landscape</h3>
            <span class="preview-badge">Hot Target</span>
          </div>
          <div class="preview-stats">
            <div class="preview-stat">
              <span class="preview-stat-label">Assets in development</span>
              <span class="preview-stat-value">25</span>
            </div>
            <div class="preview-stat">
              <span class="preview-stat-label">Approved</span>
              <span class="preview-stat-value">6</span>
            </div>
            <div class="preview-stat">
              <span class="preview-stat-label">Phase 3</span>
              <span class="preview-stat-value">7</span>
            </div>
            <div class="preview-stat">
              <span class="preview-stat-label">Disclosed deal value</span>
              <span class="preview-stat-value highlight">$22.8B</span>
            </div>
          </div>
          <a href="/api/report/target/GLP-1/html" class="preview-link">View Report</a>
        </div>

        <!-- Upcoming Catalysts -->
        <div class="preview-card">
          <div class="preview-card-header">
            <h3>Upcoming Catalysts</h3>
            <span class="preview-badge">Live</span>
          </div>
          <div class="preview-items">
            <div class="preview-item"><strong>RCKT:</strong> KRESLADI PDUFA — Mar 28, 2026</div>
            <div class="preview-item"><strong>XENE:</strong> X-TOLE2 Phase 3 data — Q1 2026</div>
            <div class="preview-item"><strong>VKTX:</strong> Oral VK2735 Phase 2 data — H1 2026</div>
            <div class="preview-item"><strong>RVMD:</strong> RMC-6236 PDAC Phase 3 — H2 2026</div>
          </div>
          <a href="/companies" class="preview-link">View All Catalysts</a>
        </div>

        <!-- Recent Deals -->
        <div class="preview-card">
          <div class="preview-card-header">
            <h3>Recent Deal Activity</h3>
            <span class="preview-badge">2024-25</span>
          </div>
          <div class="preview-items">
            <div class="preview-item"><strong>AZ / CSPC:</strong> $4.7B — GLP-1 portfolio</div>
            <div class="preview-item"><strong>Roche / Zealand:</strong> $5.3B — Petrelintide</div>
            <div class="preview-item"><strong>Pfizer / Metsera:</strong> $4.9B — Obesity portfolio</div>
            <div class="preview-item"><strong>Novo / Akero:</strong> $620M — MASH (EFX)</div>
          </div>
          <a href="/api/report/target/GLP-1/html" class="preview-link">View Deal Tracker</a>
        </div>
      </div>
    </div>
  </section>

  <!-- Value Props -->
  <section class="value-section">
    <div class="value-inner">
      <div class="value-header">
        <h2>What takes hours, done in minutes</h2>
        <p>Stop piecing together data from SEC filings, clinicaltrials.gov, and company IR pages</p>
      </div>
      <div class="value-list">
        <div class="value-item">
          <div class="value-dot"></div>
          <div class="value-text">
            <h4>Track every asset targeting GLP-1 across all clinical stages</h4>
            <p>Complete competitive landscapes with deal terms, trial data, and regulatory milestones</p>
          </div>
        </div>
        <div class="value-item">
          <div class="value-dot"></div>
          <div class="value-text">
            <h4>Monitor 60+ biotech pipelines with real-time catalyst updates</h4>
            <p>PDUFA dates, Phase 3 readouts, and key events automatically tracked</p>
          </div>
        </div>
        <div class="value-item">
          <div class="value-dot"></div>
          <div class="value-text">
            <h4>Compare competitive landscapes across therapeutic areas</h4>
            <p>Side-by-side analysis of clinical data, deal valuations, and market positioning</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Satya Bio At A Glance -->
  <section class="glance-section">
    <div class="glance-inner">
      <div class="glance-title">Satya Bio At A Glance</div>
      <div class="glance-stats">
        <div class="glance-stat">
          <div class="glance-value">60+</div>
          <div class="glance-label">public biotechs</div>
        </div>
        <div class="glance-stat">
          <div class="glance-value">200+</div>
          <div class="glance-label">pipeline assets</div>
        </div>
        <div class="glance-stat">
          <div class="glance-value">$30B+</div>
          <div class="glance-label">deal value tracked</div>
        </div>
      </div>
      <div class="glance-meta">
        <div class="glance-meta-item">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          Updated ${lastUpdated}
        </div>
        <div class="glance-meta-item">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          Primary source verified
        </div>
      </div>
    </div>
  </section>

  <!-- Company Logos -->
  <section class="logos-section">
    <div class="logos-inner">
      <div class="logos-title">Companies We Track</div>
      <div class="logos-row">
        <div class="logo-item">ARWR<span>RNAi</span></div>
        <div class="logo-item">ALNY<span>RNAi</span></div>
        <div class="logo-item">VKTX<span>GLP-1</span></div>
        <div class="logo-item">IONS<span>ASO</span></div>
        <div class="logo-item">RCKT<span>Gene Therapy</span></div>
        <div class="logo-item">NTLA<span>CRISPR</span></div>
        <div class="logo-item">RVMD<span>KRAS</span></div>
        <div class="logo-item">MRNA<span>mRNA</span></div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="cta-section" id="cta">
    <div class="cta-inner">
      <h2>Request Access</h2>
      <p>Currently in private beta with select funds</p>
      <form class="cta-form" onsubmit="event.preventDefault(); const email = this.querySelector('input').value; if(email) { window.location.href = 'mailto:hello@satyabio.com?subject=Beta%20Access%20Request&body=Email:%20' + encodeURIComponent(email); }">
        <input type="email" placeholder="work@fund.com" required>
        <button type="submit">Request Access</button>
      </form>
      <p class="cta-note">We'll be in touch within 24 hours</p>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
  </footer>
</body>
</html>`);
  });

  // Research Listing Page
  app.get('/research', (_req: Request, res: Response) => {
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Research | Satya Bio</title>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a2b3c;
      --primary-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --highlight: #fef08a;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

    /* Header */
    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 72px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 800; color: var(--primary); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.95rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: var(--primary); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-ghost { padding: 10px 18px; color: var(--text-secondary); font-weight: 600; text-decoration: none; }
    .btn-primary { padding: 10px 22px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; }
    .btn-primary:hover { background: var(--accent-hover); }

    /* Hero */
    .hero { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); padding: 80px 32px; text-align: center; }
    .hero h1 { font-family: 'Fraunces', serif; font-size: 3rem; font-weight: 700; color: white; margin-bottom: 16px; }
    .hero p { color: rgba(255,255,255,0.8); font-size: 1.2rem; max-width: 600px; margin: 0 auto; }

    /* Reports Grid */
    .reports { padding: 64px 32px; }
    .reports-inner { max-width: 1000px; margin: 0 auto; }
    .reports-header { margin-bottom: 48px; }
    .reports-header h2 { font-family: 'Fraunces', serif; font-size: 1.75rem; color: var(--primary); margin-bottom: 8px; }
    .reports-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }
    .report-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; transition: all 0.25s; text-decoration: none; color: inherit; display: block; }
    .report-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.1); }
    .report-card-image { height: 180px; background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); display: flex; align-items: center; justify-content: center; }
    .report-card-image span { font-size: 3rem; }
    .report-card-content { padding: 24px; }
    .report-badge { display: inline-block; padding: 4px 12px; background: var(--highlight); color: var(--primary); font-size: 0.75rem; font-weight: 700; border-radius: 4px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
    .report-card h3 { font-family: 'Fraunces', serif; font-size: 1.25rem; color: var(--primary); margin-bottom: 8px; line-height: 1.3; }
    .report-card p { color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 16px; }
    .report-meta { display: flex; gap: 16px; font-size: 0.8rem; color: var(--text-muted); }

    /* Footer */
    .footer { background: var(--primary); color: rgba(255,255,255,0.7); padding: 48px 32px; text-align: center; }
    .footer p { font-size: 0.9rem; }

    @media (max-width: 768px) {
      .nav-links { display: none; }
      .hero h1 { font-size: 2rem; }
      .reports { padding: 40px 20px; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research" class="active">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
                <a href="mailto:hello@satyabio.com?subject=Early%20Access%20Request&body=I'd%20like%20to%20request%20early%20access%20to%20Satya%20Bio." class="btn-primary">Get Started</a>
      </div>
    </div>
  </header>

  <section class="hero">
    <h1>Research & Insights</h1>
    <p>Deep-dive analysis on biotech deal trends, competitive landscapes, and investment opportunities.</p>
  </section>

  <section class="reports">
    <div class="reports-inner">
      <div class="reports-header">
        <h2>Latest Reports</h2>
      </div>
      <div class="reports-grid">
        <a href="/research/2025-licensing-deals" class="report-card">
          <div class="report-card-content">
            <span class="report-badge">Deal Intelligence</span>
            <h3>2024–2025 Biopharma Licensing Deals: A Comprehensive Analysis</h3>
            <p>Analysis of 389 licensing deals across therapeutic areas, modalities, and development stages.</p>
            <div class="report-meta">
              <span>Jan 2026</span>
              <span>•</span>
              <span>389 deals analyzed</span>
            </div>
          </div>
        </a>

        <a href="/api/report/target/TL1A/html" class="report-card">
          <div class="report-card-content">
            <span class="report-badge">Target Landscape</span>
            <h3>TL1A Inhibitors: The Next Blockbuster IBD Target</h3>
            <p>Complete competitive landscape with $18.5B+ in committed capital across 9 clinical-stage assets.</p>
            <div class="report-meta">
              <span>Jan 2026</span>
              <span>•</span>
              <span>9 assets tracked</span>
            </div>
          </div>
        </a>

        <a href="/api/report/target/B7-H3/html" class="report-card">
          <div class="report-card-content">
            <span class="report-badge">Target Landscape</span>
            <h3>B7-H3 ADCs: Racing to First Approval</h3>
            <p>23 assets in development with $28B+ in total deal value. Phase 3 data readouts expected 2026.</p>
            <div class="report-meta">
              <span>Jan 2026</span>
              <span>•</span>
              <span>23 assets tracked</span>
            </div>
          </div>
        </a>

        <a href="#" class="report-card" style="opacity: 0.6; pointer-events: none;">
          <div class="report-card-content">
            <span class="report-badge">Coming Soon</span>
            <h3>Big Pharma M&A Playbook 2026</h3>
            <p>Which therapeutic areas are attracting acquisition interest and at what valuations.</p>
            <div class="report-meta">
              <span>Feb 2026</span>
            </div>
          </div>
        </a>
      </div>
    </div>
  </section>

  <footer class="footer">
    <p>© 2026 Satya Bio. Institutional-grade biotech intelligence.</p>
  </footer>
</body>
</html>`);
  });

  // Companies Marketplace Page (Visual Cards with Sections) - Complete list of ~60 companies
  app.get('/companies', (_req: Request, res: Response) => {
    const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

    // Helper to get next catalyst for a company
    const getNextCatalystDisplay = (ticker: string): string => {
      const company = FEATURED_COMPANIES.find(c => c.ticker === ticker);
      if (!company) return '';
      const nextCatalyst = getNextCatalyst(company.catalysts);
      if (!nextCatalyst) return '';
      return getCatalystDisplayText(nextCatalyst);
    };

    // Company card generator function
    const companyCard = (ticker: string, name: string, platform: string, description: string, marketCap: string, pipeline: string, phase3: string, approved: string, catalyst: string, tags: string[]) => `
        <div class="company-card">
          <div class="card-header">
            <div>
              <div class="card-ticker-row">
                <span class="card-ticker">${ticker}</span>
                <span class="card-name">${name}</span>
              </div>
            </div>
            <span class="platform-badge">${platform}</span>
          </div>
          <p class="card-description">${description}</p>
          <div class="stats-row">
            <div class="stat"><span class="stat-value">${marketCap}</span><span class="stat-label">Market Cap</span></div>
            <div class="stat"><span class="stat-value">${pipeline}</span><span class="stat-label">Pipeline</span></div>
            <div class="stat"><span class="stat-value">${phase3}</span><span class="stat-label">Phase 3</span></div>
            ${approved ? `<div class="stat"><span class="stat-value">${approved}</span><span class="stat-label">Approved</span></div>` : ''}
          </div>
          <div class="catalyst-box">
            <div class="catalyst-label">Next Catalyst</div>
            <div class="catalyst-text">${catalyst}</div>
          </div>
          <div class="tags-row">
            ${tags.map(t => `<span class="tag">${t}</span>`).join('')}
          </div>
          <a href="/api/company/${ticker}/html" class="view-btn">View Company</a>
        </div>`;

    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Companies | Satya Bio</title>
  <meta name="description" content="Browse 60+ biotech companies by category, stage, and therapeutic area.">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy: #1a2b3c;
      --navy-light: #2d4a6f;
      --accent: #e07a5f;
      --accent-light: #fef5f3;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
      --catalyst-bg: #fef9c3;
      --catalyst-border: #fde047;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }

    /* Header */
    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 64px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-size: 1.25rem; font-weight: 700; color: var(--navy); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 28px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; }
    .nav-links a:hover, .nav-links a.active { color: var(--navy); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-ghost { padding: 8px 16px; color: var(--text-secondary); font-weight: 500; text-decoration: none; font-size: 0.9rem; }
    .btn-primary { padding: 8px 18px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 6px; font-size: 0.9rem; }

    /* Main Container */
    .main { max-width: 1400px; margin: 0 auto; padding: 32px; }

    /* Page Title */
    .page-header { margin-bottom: 24px; }
    .page-title { font-size: 1.75rem; font-weight: 700; color: var(--navy); margin-bottom: 8px; }
    .page-subtitle { color: var(--text-secondary); font-size: 0.95rem; }

    /* Search Bar */
    .search-container { margin-bottom: 24px; }
    .search-wrapper { position: relative; max-width: 600px; }
    .search-input {
      width: 100%;
      padding: 16px 20px 16px 52px;
      border: 2px solid var(--border);
      border-radius: 14px;
      font-size: 1rem;
      font-family: inherit;
      background: white;
      box-shadow: 0 4px 16px rgba(0,0,0,0.05);
      outline: none;
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .search-input:focus {
      border-color: var(--accent);
      box-shadow: 0 8px 32px rgba(0,0,0,0.08), 0 0 0 4px rgba(224,122,95,0.12);
    }
    .search-input::placeholder { color: var(--text-muted); }
    .search-icon {
      position: absolute;
      left: 18px;
      top: 50%;
      transform: translateY(-50%);
      width: 20px;
      height: 20px;
      color: var(--text-muted);
      transition: color 0.2s;
    }
    .search-wrapper:focus-within .search-icon { color: var(--accent); }
    .search-clear {
      position: absolute;
      right: 16px;
      top: 50%;
      transform: translateY(-50%);
      width: 24px;
      height: 24px;
      border: none;
      background: var(--border);
      border-radius: 50%;
      cursor: pointer;
      display: none;
      align-items: center;
      justify-content: center;
      color: var(--text-secondary);
      font-size: 14px;
      transition: all 0.15s;
    }
    .search-clear:hover { background: var(--accent); color: white; }
    .search-clear.visible { display: flex; }
    .search-results-info {
      margin-top: 12px;
      font-size: 0.9rem;
      color: var(--text-secondary);
    }
    .search-results-info strong { color: var(--navy); }
    .no-results {
      text-align: center;
      padding: 48px 24px;
      color: var(--text-secondary);
    }
    .no-results h3 { font-size: 1.1rem; color: var(--navy); margin-bottom: 8px; }

    /* Sticky Category Navigation */
    .category-nav { position: sticky; top: 64px; background: var(--bg); padding: 16px 0; z-index: 50; border-bottom: 1px solid var(--border); margin-bottom: 32px; }
    .category-pills { display: flex; gap: 10px; flex-wrap: wrap; }
    .category-pill { padding: 8px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: 20px; font-size: 0.85rem; font-weight: 500; color: var(--text-secondary); cursor: pointer; transition: all 0.15s; text-decoration: none; white-space: nowrap; }
    .category-pill:hover { border-color: var(--navy); color: var(--navy); }
    .category-pill.active { background: var(--navy); border-color: var(--navy); color: white; }
    /* Category pills - text only */

    /* Section */
    .section { margin-bottom: 48px; scroll-margin-top: 140px; }
    .section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid var(--border); }
    /* Section styling - clean, no emojis */
    .section-title { font-size: 1.25rem; font-weight: 700; color: var(--navy); }
    .section-count { background: var(--navy); color: white; font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
    .subsection-title { font-size: 0.9rem; font-weight: 600; color: var(--text-muted); margin: 24px 0 16px 0; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Company Cards Grid */
    .cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }

    /* Company Card */
    .company-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: all 0.2s; }
    .company-card:hover { border-color: var(--accent); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }

    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .card-ticker-row { display: flex; align-items: center; gap: 8px; }
    .card-ticker { font-size: 1rem; font-weight: 700; color: var(--navy); }
    .card-name { font-size: 0.8rem; color: var(--text-secondary); }
    .platform-badge { padding: 3px 8px; background: var(--accent-light); color: var(--accent); font-size: 0.65rem; font-weight: 600; border-radius: 10px; text-transform: uppercase; letter-spacing: 0.3px; }

    .card-description { color: var(--text-secondary); font-size: 0.8rem; line-height: 1.5; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

    /* Stats Row */
    .stats-row { display: flex; gap: 12px; margin-bottom: 12px; padding: 10px 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
    .stat { display: flex; flex-direction: column; }
    .stat-value { font-weight: 700; font-size: 0.85rem; color: var(--navy); }
    .stat-label { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px; }

    /* Catalyst Box */
    .catalyst-box { background: var(--catalyst-bg); border: 1px solid var(--catalyst-border); border-radius: 6px; padding: 8px 12px; margin-bottom: 12px; }
    .catalyst-label { font-size: 0.65rem; font-weight: 600; color: #92400e; text-transform: uppercase; letter-spacing: 0.3px; margin-bottom: 2px; }
    .catalyst-text { font-size: 0.8rem; color: #78350f; font-weight: 500; }

    /* Tags */
    .tags-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
    .tag { padding: 4px 10px; background: #f3f4f6; color: var(--text-secondary); font-size: 0.75rem; border-radius: 12px; }

    /* View Button */
    .view-btn { display: block; width: 100%; padding: 10px 16px; background: var(--navy); color: white; text-align: center; text-decoration: none; border-radius: 8px; font-size: 0.85rem; font-weight: 600; transition: background 0.15s; }
    .view-btn:hover { background: var(--navy-light); }

    /* Footer */
    .footer { background: var(--navy); color: rgba(255,255,255,0.7); padding: 32px; text-align: center; margin-top: 64px; }
    .footer p { font-size: 0.85rem; }

    /* Mobile */
    @media (max-width: 768px) {
      .nav-links { display: none; }
      .main { padding: 20px 16px; }
      .cards-grid { grid-template-columns: 1fr; }
      .category-pills { overflow-x: auto; flex-wrap: nowrap; padding-bottom: 8px; }
      .category-nav { top: 64px; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies" class="active">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
                <a href="mailto:hello@satyabio.com?subject=Early%20Access%20Request&body=I'd%20like%20to%20request%20early%20access%20to%20Satya%20Bio." class="btn-primary">Get Started</a>
      </div>
    </div>
  </header>

  <main class="main">
    <div class="page-header">
      <h1 class="page-title">Companies</h1>
      <p class="page-subtitle">Explore biotech companies with real-time catalyst tracking and deep research</p>
    </div>

    <!-- Search Bar -->
    <div class="search-container">
      <div class="search-wrapper">
        <svg class="search-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <input type="text" class="search-input" id="companySearch" placeholder="Search companies by name, ticker, or therapeutic area..." autocomplete="off">
        <button class="search-clear" id="searchClear" title="Clear search">&times;</button>
      </div>
      <div class="search-results-info" id="searchResultsInfo" style="display: none;"></div>
    </div>

    <!-- No Results Message -->
    <div class="no-results" id="noResults" style="display: none;">
      <h3>No companies found</h3>
      <p>Try a different search term</p>
    </div>

    <!-- Sticky Category Navigation -->
    <nav class="category-nav" id="categoryNav">
      <div class="category-pills">
        <a href="#largecap" class="category-pill active">Large-Cap (8)</a>
        <a href="#platform" class="category-pill">Platform (10)</a>
        <a href="#commercial" class="category-pill">Commercial (41)</a>
        <a href="#oncology" class="category-pill">Oncology (33)</a>
        <a href="#ii" class="category-pill">I&I (17)</a>
        <a href="#rare" class="category-pill">Rare Disease (14)</a>
        <a href="#neuro" class="category-pill">Neuro (6)</a>
        <a href="#metabolic" class="category-pill">Metabolic/CV (7)</a>
        <a href="#nephro" class="category-pill">Nephrology (2)</a>
        <a href="#vaccines" class="category-pill">Vaccines (4)</a>
        <a href="#tools" class="category-pill">Tools (3)</a>
      </div>
    </nav>

    <!-- ==================== LARGE-CAP BIOPHARMA (8) ==================== -->
    <section id="largecap" class="section">
      <div class="section-header">
        <h2 class="section-title">Large-Cap BioPharma</h2>
        <span class="section-count">8</span>
      </div>
      <div class="cards-grid">
        ${companyCard('GILD', 'Gilead Sciences', 'Small Molecule', 'HIV, Oncology, Liver. Key products: Biktarvy, Trodelvy, Livdelzi.', '$95B+', '50+', '15+', '25+', 'Lenacapavir HIV data (2026)', ['HIV', 'Oncology', 'Liver'])}
        ${companyCard('AMGN', 'Amgen', 'Biologics', 'Oncology, I&I, Bone. Key products: Repatha, Prolia, Lumakras.', '$150B+', '40+', '10+', '20+', 'MariTide obesity Ph3 (2026)', ['Oncology', 'I&I', 'Bone'])}
        ${companyCard('VRTX', 'Vertex Pharmaceuticals', 'Small Molecule', 'Rare Disease (CF), Pain, Gene Therapy. Key products: Trikafta, JOURNAVX, Casgevy.', '$120B+', '20+', '5', '5', 'VX-548 pain Ph3 (2026)', ['Rare Disease', 'Pain', 'Gene Therapy'])}
        ${companyCard('BMRN', 'BioMarin Pharmaceutical', 'Enzyme', 'Rare Disease. Key products: Voxzogo, Palynziq, Roctavian.', '$12B', '10+', '2', '7', 'Roctavian expansion (2026)', ['Rare Disease', 'Enzyme'])}
        ${companyCard('REGN', 'Regeneron Pharmaceuticals', 'Antibody', 'I&I, Ophthalmology, Oncology. Key products: Dupixent, EYLEA HD, Libtayo.', '$90B+', '35+', '10+', '8', 'Dupixent COPD Ph3 (2026)', ['I&I', 'Ophthalmology', 'Oncology'])}
        ${companyCard('BIIB', 'Biogen', 'Antibody', 'Neuropsychiatry. Key products: Leqembi, Spinraza, Tysabri.', '$25B', '20+', '5', '8', 'Leqembi expansion (2026)', ['Neuropsychiatry', 'MS', 'SMA'])}
        ${companyCard('ABBV', 'AbbVie', 'Small Molecule', 'I&I, Oncology, Neuro. Key products: Humira, Skyrizi, Rinvoq.', '$300B+', '50+', '15+', '30+', 'Skyrizi/Rinvoq growth (2026)', ['I&I', 'Oncology', 'Neuro'])}
        ${companyCard('ALNY', 'Alnylam Pharmaceuticals', 'RNAi', 'Rare Disease (RNAi). Key products: Amvuttra, Onpattro, Givlaari.', '$28.5B', '12', '3', '5', getNextCatalystDisplay('ALNY') || 'Vutrisiran ATTR-CM (2026)', ['Rare Disease', 'RNAi', 'Cardiometabolic'])}
      </div>
    </section>

    <!-- ==================== PLATFORM (10) ==================== -->
    <section id="platform" class="section">
      <div class="section-header">
        <h2 class="section-title">Platform</h2>
        <span class="section-count">10</span>
      </div>
      <div class="cards-grid">
        ${companyCard('MRNA', 'Moderna', 'mRNA', 'Vaccines, Oncology, Rare. COVID/RSV vaccines platform.', '$15B', '45+', '8', '2', 'mRNA-1283 COVID (2026)', ['Vaccines', 'Oncology', 'Rare Disease'])}
        ${companyCard('IONS', 'Ionis Pharmaceuticals', 'Antisense', 'Neuro, Cardio, Rare. Key products: SPINRAZA, WAINUA.', '$7.8B', '40+', '5', '4', getNextCatalystDisplay('IONS') || 'Olezarsen sNDA (2026)', ['Neuro', 'Cardio', 'Rare'])}
        ${companyCard('ARWR', 'Arrowhead Pharmaceuticals', 'RNAi', 'Liver, Cardio, Pulmonary. Key product: Plozasiran.', '$4.2B', '15', '3', '1', getNextCatalystDisplay('ARWR') || 'ARO-INHBE obesity (2026)', ['Liver', 'Cardio', 'Pulmonary'])}
        ${companyCard('CRSP', 'CRISPR Therapeutics', 'Gene Editing', 'Rare Disease (Gene Editing). Key product: Casgevy.', '$3.5B', '8', '2', '1', 'CTX112 CAR-T (2026)', ['Rare Disease', 'Gene Editing', 'Hematology'])}
        ${companyCard('RNA', 'Avidity Biosciences', 'AOC', 'Neuromuscular, Cardio. Lead: del-desiran (Ph3).', '$3.0B', '5', '2', '', 'del-desiran DM1 Ph3 (2026)', ['Neuromuscular', 'Cardio', 'AOC'])}
        ${companyCard('BEAM', 'Beam Therapeutics', 'Base Editing', 'Rare Disease (Gene Editing). Lead: BEAM-101 (Ph1/2).', '$3.1B', '5', '1', '', 'BEAM-302 AATD (2026)', ['Gene Editing', 'Sickle Cell', 'Liver'])}
        ${companyCard('NTLA', 'Intellia Therapeutics', 'CRISPR', 'Rare Disease (Gene Editing). Lead: NTLA-2001 (Ph3).', '$2.8B', '6', '2', '', 'NTLA-2001 ATTR Ph3 (2026)', ['Gene Editing', 'ATTR', 'HAE'])}
        ${companyCard('SANA', 'Sana Biotechnology', 'Cell Therapy', 'Cell Engineering platform for hypoimmune cells.', '$1.2B', '4', '1', '', 'SC291 Ph1 (2026)', ['Cell Therapy', 'Hypoimmune', 'Platform'])}
        ${companyCard('PRME', 'Prime Medicine', 'Gene Editing', 'Prime Editing platform. Lead: PM359 (Ph1).', '$0.8B', '3', '0', '', 'PM359 IND (2026)', ['Gene Editing', 'Rare Disease', 'Platform'])}
        ${companyCard('RGNX', 'Regenxbio', 'Gene Therapy', 'AAV gene therapy platform. Multiple programs.', '$0.6B', '8', '2', '', 'RGX-314 wet AMD (2026)', ['Gene Therapy', 'Ophthalmology', 'Platform'])}
      </div>
    </section>

    <!-- ==================== COMMERCIAL SPECIALTY (41) ==================== -->
    <section id="commercial" class="section">
      <div class="section-header">
        <h2 class="section-title">Commercial Specialty</h2>
        <span class="section-count">41</span>
      </div>
      <div class="cards-grid">
        ${companyCard('MIRM', 'Mirum Pharmaceuticals', 'Small Molecule', 'Rare - Liver. Key product: Livmarli.', '$4.5B', '4', '2', '3', 'Volixibat PSC (2026)', ['Rare Disease', 'Liver', 'Cholestasis'])}
        ${companyCard('ALKS', 'Alkermes', 'Small Molecule', 'Neuropsychiatry. Key products: Vivitrol, Aristada.', '$5.0B', '6', '2', '4', 'ALKS 2680 narcolepsy (2026)', ['Neuropsychiatry', 'Addiction', 'Schizophrenia'])}
        ${companyCard('FOLD', 'Amicus Therapeutics', 'Enzyme', 'Rare - Lysosomal. Key products: Galafold, Pombiliti.', '$3.2B', '4', '1', '2', 'Pombiliti expansion (2026)', ['Rare Disease', 'Lysosomal', 'Metabolic'])}
        ${companyCard('HALO', 'Halozyme Therapeutics', 'Drug Delivery', 'Drug Delivery. ENHANZE royalties.', '$7.2B', '20+', 'N/A', '8', 'New ENHANZE deals (2026)', ['Drug Delivery', 'Royalties', 'Platform'])}
        ${companyCard('KRYS', 'Krystal Biotech', 'Gene Therapy', 'Rare - Dermatology. Key product: Vyjuvek.', '$7B', '6', '2', '1', 'KB408 AATD (2026)', ['Rare Disease', 'Dermatology', 'Gene Therapy'])}
        ${companyCard('CYTK', 'Cytokinetics', 'Small Molecule', 'Cardiovascular. Key product: Myqorzo.', '$5.5B', '3', '2', '1', 'Aficamten HCM (2026)', ['Cardiovascular', 'HCM', 'Heart Failure'])}
        ${companyCard('GRAL', 'Grail', 'Diagnostics', 'Dx - Oncology. Key product: Galleri.', '$2.0B', '2', 'N/A', '1', 'Galleri Medicare (2026)', ['Diagnostics', 'Oncology', 'Screening'])}
        ${companyCard('INCY', 'Incyte', 'Small Molecule', 'Oncology, I&I. Key products: Jakafi, Opzelura.', '$14B', '20+', '5', '4', 'Povorcitinib AD (2026)', ['Oncology', 'I&I', 'Dermatology'])}
        ${companyCard('PTCT', 'PTC Therapeutics', 'Small Molecule', 'Rare Disease. Key products: Translarna, Evrysdi royalties.', '$2.5B', '6', '2', '3', 'Sepiapterin Ph3 (2026)', ['Rare Disease', 'Neuromuscular', 'PKU'])}
        ${companyCard('EXEL', 'Exelixis', 'Small Molecule', 'Oncology. Key product: Cabometyx.', '$8B', '10+', '4', '2', 'Zanzalintinib Ph3 (2026)', ['Oncology', 'Kidney Cancer', 'Liver Cancer'])}
        ${companyCard('EXAS', 'Exact Sciences', 'Diagnostics', 'Dx - Oncology. Key products: Cologuard, Oncotype DX.', '$19.4B', '5', 'N/A', '3', 'Cologuard Plus (2026)', ['Diagnostics', 'Oncology', 'Screening'])}
        ${companyCard('NTRA', 'Natera', 'Diagnostics', 'Dx - Oncology, Prenatal. Key products: Signatera, Panorama.', '$33B', '8', 'N/A', '4', 'Signatera expansion (2026)', ['Diagnostics', 'Oncology', 'Prenatal'])}
        ${companyCard('TGTX', 'TG Therapeutics', 'Antibody', 'I&I (MS). Key product: Briumvi.', '$4.5B', '3', '1', '1', 'Briumvi growth (2026)', ['I&I', 'MS', 'Autoimmune'])}
        ${companyCard('UTHR', 'United Therapeutics', 'Biologics', 'Rare - PAH. Key product: Tyvaso DPI.', '$14B', '8', '2', '5', 'Tyvaso DPI expansion (2026)', ['Rare Disease', 'PAH', 'Pulmonary'])}
        ${companyCard('TVTX', 'Travere Therapeutics', 'Small Molecule', 'Rare - Nephrology. Key product: Filspari.', '$3.0B', '3', '1', '2', 'Filspari FSGS (2026)', ['Rare Disease', 'Nephrology', 'IgAN'])}
        ${companyCard('MDGL', 'Madrigal Pharmaceuticals', 'Small Molecule', 'Metabolic - MASH. Key product: Rezdiffra.', '$6.8B', '1', '1', '1', 'Rezdiffra launch (2026)', ['Metabolic', 'MASH', 'Liver'])}
        ${companyCard('NBIX', 'Neurocrine Biosciences', 'Small Molecule', 'Neuropsychiatry. Key product: Ingrezza.', '$14B', '12', '3', '2', 'NBI-1065845 MDD (2026)', ['Neuropsychiatry', 'Movement Disorders', 'Psychiatry'])}
        ${companyCard('ACAD', 'Acadia Pharmaceuticals', 'Small Molecule', 'Neuropsychiatry. Key products: Nuplazid, Daybue.', '$4.5B', '4', '2', '2', 'Daybue growth (2026)', ['Neuropsychiatry', 'Rett Syndrome', 'Parkinson'])}
        ${companyCard('ADMA', 'ADMA Biologics', 'Biologics', 'I&I (Immunoglobulins). Key product: ASCENIV.', '$3.0B', '2', 'N/A', '1', 'ASCENIV expansion (2026)', ['I&I', 'Immunoglobulins', 'Plasma'])}
        ${companyCard('INSM', 'Insmed', 'Biologics', 'Rare - Pulmonary. Key products: Arikayce, Brinsupri.', '$34.7B', '6', '3', '2', 'Brensocatib launch (2026)', ['Rare Disease', 'Pulmonary', 'Anti-infective'])}
        ${companyCard('APLS', 'Apellis Pharmaceuticals', 'Small Molecule', 'Ophthalmology. Key product: Syfovre.', '$5.0B', '4', '2', '1', 'Syfovre growth (2026)', ['Ophthalmology', 'AMD', 'Complement'])}
        ${companyCard('RARE', 'Ultragenyx Pharmaceutical', 'Biologics', 'Rare Disease. Key products: Crysvita, Evkeeza.', '$4.5B', '15+', '3', '4', 'GTX-102 Angelman (2026)', ['Rare Disease', 'Metabolic', 'Gene Therapy'])}
        ${companyCard('CPRX', 'Catalyst Pharmaceuticals', 'Small Molecule', 'Neuropsychiatry. Key product: Firdapse.', '$2.5B', '2', '1', '1', 'Firdapse SMA (2026)', ['Neuropsychiatry', 'LEMS', 'Rare Disease'])}
        ${companyCard('VCYT', 'Veracyte', 'Diagnostics', 'Dx - Oncology. Key products: Decipher, Afirma.', '$2.0B', '4', 'N/A', '3', 'Prosigna expansion (2026)', ['Diagnostics', 'Oncology', 'Genomics'])}
        ${companyCard('NVAX', 'Novavax', 'Vaccine', 'Vaccines. COVID vaccine.', '$1.2B', '5', '2', '1', 'CIC flu combo (2026)', ['Vaccines', 'COVID', 'Influenza'])}
        ${companyCard('ARDX', 'Ardelyx', 'Small Molecule', 'Nephrology, GI. Key products: Ibsrela, Xphozah.', '$1.5B', '3', '1', '2', 'Xphozah growth (2026)', ['Nephrology', 'GI', 'Hyperphosphatemia'])}
        ${companyCard('AGIO', 'Agios Pharmaceuticals', 'Small Molecule', 'Rare - Hematology. Key product: Pyrukynd.', '$3.0B', '3', '1', '1', 'Pyrukynd expansion (2026)', ['Rare Disease', 'Hematology', 'PK Deficiency'])}
        ${companyCard('DVAX', 'Dynavax Technologies', 'Vaccine', 'Vaccines. Key product: Heplisav-B.', '$1.5B', '3', '1', '1', 'Heplisav-B growth (2026)', ['Vaccines', 'Hepatitis B', 'Adjuvant'])}
        ${companyCard('VCEL', 'Vericel', 'Regenerative', 'Regenerative. Key products: MACI, Epicel.', '$2.5B', '3', '1', '2', 'NexoBrid launch (2026)', ['Regenerative', 'Orthopedics', 'Burn'])}
        ${companyCard('MNKD', 'MannKind', 'Inhalation', 'Diabetes, Pulmonary. Key products: Afrezza, Tyvaso DPI.', '$1.0B', '3', '1', '2', 'V-Go growth (2026)', ['Diabetes', 'Pulmonary', 'Inhalation'])}
        ${companyCard('BCRX', 'BioCryst Pharmaceuticals', 'Small Molecule', 'Rare Disease. Key product: Orladeyo.', '$3.5B', '4', '1', '1', 'Orladeyo HAE (2026)', ['Rare Disease', 'HAE', 'Oral'])}
        ${companyCard('CDNA', 'CareDx', 'Diagnostics', 'Dx - Transplant. Key product: AlloSure.', '$0.8B', '3', 'N/A', '2', 'AlloSure expansion (2026)', ['Diagnostics', 'Transplant', 'Rejection'])}
        ${companyCard('IOVA', 'Iovance Biotherapeutics', 'Cell Therapy', 'Oncology. Key product: Amtagvi.', '$4.0B', '3', '2', '1', 'Amtagvi lung (2026)', ['Oncology', 'Cell Therapy', 'TIL'])}
        ${companyCard('SPRY', 'ARS Pharmaceuticals', 'Small Molecule', 'Allergy. Key product: Neffy.', '$1.5B', '2', '1', '1', 'Neffy launch (2026)', ['Allergy', 'Anaphylaxis', 'Epinephrine'])}
        ${companyCard('GERN', 'Geron', 'Small Molecule', 'Oncology. Key product: Rytelo.', '$4.0B', '2', '1', '1', 'Rytelo launch (2026)', ['Oncology', 'MDS', 'Telomerase'])}
        ${companyCard('EBS', 'Emergent BioSolutions', 'Biologics', 'Vaccines/Biodefense. Biodefense products.', '$0.5B', '5', '1', '3', 'ACAM2000 (2026)', ['Vaccines', 'Biodefense', 'Anthrax'])}
        ${companyCard('RIGL', 'Rigel Pharmaceuticals', 'Small Molecule', 'I&I. Key product: Rezlidhia.', '$0.3B', '3', '1', '1', 'Rezlidhia growth (2026)', ['I&I', 'Hematology', 'Kinase'])}
        ${companyCard('MYGN', 'Myriad Genetics', 'Diagnostics', 'Dx - Oncology. Key product: BRACAnalysis.', '$1.5B', '5', 'N/A', '4', 'Precise expansion (2026)', ['Diagnostics', 'Oncology', 'Hereditary Cancer'])}
        ${companyCard('SRPT', 'Sarepta Therapeutics', 'Gene Therapy', 'Rare - DMD. Key product: Elevidys.', '$9.5B', '15+', '3', '5', 'Elevidys confirmatory (2026)', ['Rare Disease', 'DMD', 'Gene Therapy'])}
        ${companyCard('MDXG', 'MiMedx Group', 'Regenerative', 'Regenerative. Key products: AmnioFix, EpiFix.', '$1.0B', '2', 'N/A', '2', 'Wound care growth (2026)', ['Regenerative', 'Wound Care', 'Amniotic'])}
        ${companyCard('IRWD', 'Ironwood Pharmaceuticals', 'Small Molecule', 'GI. Linzess royalties.', '$1.2B', '2', '1', '1', 'Linzess royalties (2026)', ['GI', 'IBS', 'Royalties'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - ONCOLOGY (33) ==================== -->
    <section id="oncology" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - Oncology</h2>
        <span class="section-count">33</span>
      </div>
      <div class="cards-grid">
        ${companyCard('RVMD', 'Revolution Medicines', 'Small Molecule', 'Oncology (RAS). Lead: Daraxonrasib (Ph3).', '$8.5B', '4', '2', '', 'RMC-6236 PDAC Ph3 (2026)', ['Oncology', 'KRAS', 'Pancreatic'])}
        ${companyCard('CELC', 'Celcuity', 'Small Molecule', 'Oncology (HER2). Lead: Gedatolisib (Ph3).', '$0.8B', '2', '1', '', 'Gedatolisib breast (2026)', ['Oncology', 'HER2', 'Breast Cancer'])}
        ${companyCard('CGON', 'CG Oncology', 'Oncolytic', 'Oncology (Oncolytic). Lead: CG0070 (Ph3).', '$1.0B', '2', '1', '', 'CG0070 bladder Ph3 (2026)', ['Oncology', 'Oncolytic Virus', 'Bladder Cancer'])}
        ${companyCard('ACLX', 'Arcellx', 'Cell Therapy', 'Oncology (CAR-T). Lead: Anitocabtagene (Ph2).', '$3.0B', '3', '1', '', 'Anito myeloma (2026)', ['Oncology', 'CAR-T', 'Multiple Myeloma'])}
        ${companyCard('NUVL', 'Nuvalent', 'Small Molecule', 'Oncology (TKI). Lead: NVL-520 (Ph2).', '$5.0B', '3', '1', '', 'NVL-520 ROS1 (2026)', ['Oncology', 'TKI', 'Lung Cancer'])}
        ${companyCard('SMMT', 'Summit Therapeutics', 'Antibody', 'Oncology (PD-1). Lead: Ivonescimab (Ph3).', '$8.0B', '2', '2', '', 'Ivonescimab NSCLC (2026)', ['Oncology', 'PD-1', 'Lung Cancer'])}
        ${companyCard('IDYA', 'Ideaya Biosciences', 'Small Molecule', 'Oncology (Synth Lethality). Lead: Darovasertib (Ph3).', '$2.8B', '6', '2', '', 'Darovasertib melanoma (2026)', ['Oncology', 'Melanoma', 'Synthetic Lethality'])}
        ${companyCard('SNDX', 'Syndax Pharmaceuticals', 'Small Molecule', 'Oncology (Menin). Lead: Revumenib (BLA).', '$2.5B', '4', '1', '', 'Revumenib AML (2026)', ['Oncology', 'Menin', 'AML'])}
        ${companyCard('IBRX', 'ImmunityBio', 'Biologics', 'Oncology (IL-15). Key product: Anktiva.', '$1.0B', '5', '2', '1', 'Anktiva bladder (2026)', ['Oncology', 'IL-15', 'Bladder Cancer'])}
        ${companyCard('IMNM', 'Immunome', 'Antibody', 'Oncology (Antibodies). Lead: IMM-1-104 (Ph1).', '$0.3B', '2', '0', '', 'IMM-1-104 solid (2026)', ['Oncology', 'Antibody', 'Solid Tumors'])}
        ${companyCard('TNGX', 'Tango Therapeutics', 'Small Molecule', 'Oncology (Synth Lethality). Lead: TNG908 (Ph2).', '$1.0B', '3', '1', '', 'TNG908 MTAP (2026)', ['Oncology', 'Synthetic Lethality', 'MTAP'])}
        ${companyCard('JANX', 'Janux Therapeutics', 'Bispecific', 'Oncology (T-cell Engager). Lead: JANX007 (Ph1).', '$2.0B', '3', '0', '', 'JANX007 prostate (2026)', ['Oncology', 'Bispecific', 'Prostate Cancer'])}
        ${companyCard('CRVS', 'Corvus Pharmaceuticals', 'Antibody', 'Oncology (IO). Lead: Mupadolimab (Ph2).', '$0.2B', '2', '1', '', 'Mupadolimab solid (2026)', ['Oncology', 'IO', 'Solid Tumors'])}
        ${companyCard('RCUS', 'Arcus Biosciences', 'Antibody', 'Oncology (IO). Lead: Domvanalimab (Ph3).', '$2.7B', '6', '3', '', 'Domvanalimab NSCLC (2026)', ['Oncology', 'TIGIT', 'Lung Cancer'])}
        ${companyCard('ORIC', 'Oric Pharmaceuticals', 'Small Molecule', 'Oncology. Lead: ORIC-114 (Ph2).', '$0.5B', '3', '1', '', 'ORIC-114 EGFR (2026)', ['Oncology', 'EGFR', 'Lung Cancer'])}
        ${companyCard('DAWN', 'Day One Biopharmaceuticals', 'Small Molecule', 'Oncology (Pediatric). Key product: Tovorafenib.', '$2.5B', '2', '1', '1', 'Tovorafenib expansion (2026)', ['Oncology', 'Pediatric', 'RAF'])}
        ${companyCard('PGEN', 'Precigen', 'Gene Therapy', 'Oncology (Gene Therapy). Lead: PRGN-3005 (Ph1).', '$0.2B', '4', '1', '', 'PRGN-3005 ovarian (2026)', ['Oncology', 'Gene Therapy', 'Ovarian Cancer'])}
        ${companyCard('NRIX', 'Nurix Therapeutics', 'Degrader', 'Oncology (Degrader). Lead: NX-2127 (Ph1).', '$1.0B', '4', '0', '', 'NX-2127 BTK (2026)', ['Oncology', 'Degrader', 'B-cell'])}
        ${companyCard('CTMX', 'CytomX Therapeutics', 'Probody', 'Oncology (Probody). Lead: CX-904 (Ph1).', '$0.3B', '3', '0', '', 'CX-904 solid (2026)', ['Oncology', 'Probody', 'Solid Tumors'])}
        ${companyCard('KURA', 'Kura Oncology', 'Small Molecule', 'Oncology (Menin). Lead: Ziftomenib (Ph3).', '$2.0B', '3', '1', '', 'Ziftomenib NPM1 (2026)', ['Oncology', 'Menin', 'AML'])}
        ${companyCard('RLAY', 'Relay Therapeutics', 'Small Molecule', 'Oncology (PI3Ka). Lead: Zovegalisib (Ph3).', '$1.8B', '4', '1', '', 'RLY-2608 breast (2026)', ['Oncology', 'PI3K', 'Breast Cancer'])}
        ${companyCard('GLUE', 'Monte Rosa Therapeutics', 'Degrader', 'Oncology (Degrader). Lead: MRT-2359 (Ph1).', '$0.4B', '3', '0', '', 'MRT-2359 GSPT1 (2026)', ['Oncology', 'Degrader', 'Solid Tumors'])}
        ${companyCard('ERAS', 'Erasca', 'Small Molecule', 'Oncology (RAS). Lead: Naporafenib (Ph2).', '$0.3B', '3', '1', '', 'Naporafenib combo (2026)', ['Oncology', 'RAS', 'Solid Tumors'])}
        ${companyCard('XNCR', 'Xencor', 'Bispecific', 'Oncology (Bispecific). Lead: Vudalimab (Ph2).', '$1.5B', '8', '2', '', 'Vudalimab NSCLC (2026)', ['Oncology', 'Bispecific', 'Lung Cancer'])}
        ${companyCard('OLMA', 'Olema Pharmaceuticals', 'Small Molecule', 'Oncology (ER). Lead: Palazestrant (Ph3).', '$1.0B', '2', '1', '', 'Palazestrant breast (2026)', ['Oncology', 'ER Degrader', 'Breast Cancer'])}
        ${companyCard('REPL', 'Replimune Group', 'Oncolytic', 'Oncology (Oncolytic). Lead: RP1 (Ph2).', '$0.5B', '3', '1', '', 'RP1 melanoma (2026)', ['Oncology', 'Oncolytic Virus', 'Melanoma'])}
        ${companyCard('BCAX', 'Bicara Therapeutics', 'Bispecific', 'Oncology (Bispecific). Lead: BCA101 (Ph2).', '$0.4B', '2', '1', '', 'BCA101 HNSCC (2026)', ['Oncology', 'Bispecific', 'Head & Neck'])}
        ${companyCard('CMPX', 'Compass Therapeutics', 'Antibody', 'Oncology (IO). Lead: CTX-009 (Ph2).', '$0.2B', '3', '1', '', 'CTX-009 biliary (2026)', ['Oncology', 'IO', 'Biliary Cancer'])}
        ${companyCard('VSTM', 'Verastem', 'Small Molecule', 'Oncology (RAF/MEK). Lead: Avutometinib (Ph3).', '$0.8B', '2', '2', '', 'Avutometinib ovarian (2026)', ['Oncology', 'RAF/MEK', 'Ovarian Cancer'])}
        ${companyCard('CGEM', 'Cullinan Therapeutics', 'Antibody', 'Oncology. Lead: CLN-978 (Ph1).', '$0.5B', '4', '0', '', 'CLN-978 B-cell (2026)', ['Oncology', 'T-cell Engager', 'B-cell'])}
        ${companyCard('AVBP', 'Arrivent Biopharma', 'Small Molecule', 'Oncology. Lead: ARRY-440 (Ph2).', '$0.3B', '2', '1', '', 'Furmonertinib NSCLC (2026)', ['Oncology', 'EGFR', 'Lung Cancer'])}
        ${companyCard('IMRX', 'Immuneering', 'Small Molecule', 'Oncology. Lead: IMM-1-104 (Ph1).', '$0.1B', '2', '0', '', 'IMM-6-415 RAS (2026)', ['Oncology', 'RAS', 'Solid Tumors'])}
        ${companyCard('TYRA', 'Tyra Biosciences', 'Small Molecule', 'Oncology (TKI). Lead: TYRA-300 (Ph2).', '$0.8B', '3', '1', '', 'TYRA-300 bladder (2026)', ['Oncology', 'FGFR', 'Bladder Cancer'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - I&I (17) ==================== -->
    <section id="ii" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - I&I</h2>
        <span class="section-count">17</span>
      </div>
      <div class="cards-grid">
        ${companyCard('PTGX', 'Protagonist Therapeutics', 'Peptide', 'I&I, Hematology. Lead: Rusfertide (Ph3).', '$5.3B', '4', '2', '', 'Rusfertide PV (2026)', ['I&I', 'Hematology', 'PV'])}
        ${companyCard('ARQT', 'Arcutis Biotherapeutics', 'Small Molecule', 'I&I (Dermatology). Lead: Roflumilast (Ph3).', '$0.8B', '3', '2', '2', 'Roflumilast scalp (2026)', ['I&I', 'Dermatology', 'Psoriasis'])}
        ${companyCard('KYMR', 'Kymera Therapeutics', 'Degrader', 'I&I (Degrader). Lead: KT-474 (Ph2).', '$2.0B', '4', '1', '', 'KT-474 atopic derm (2026)', ['I&I', 'Degrader', 'IRAK4'])}
        ${companyCard('IMVT', 'Immunovant', 'Antibody', 'I&I (FcRn). Lead: IMVT-1402 (Ph3).', '$5.0B', '3', '2', '', 'IMVT-1402 MG (2026)', ['I&I', 'FcRn', 'Autoimmune'])}
        ${companyCard('APGE', 'Apogee Therapeutics', 'Antibody', 'I&I (Dermatology). Lead: APG777 (Ph2).', '$3.0B', '2', '1', '', 'APG777 atopic derm (2026)', ['I&I', 'Dermatology', 'Atopic Derm'])}
        ${companyCard('VRDN', 'Viridian Therapeutics', 'Antibody', 'I&I (Thyroid Eye). Lead: VRDN-003 (Ph3).', '$2.5B', '3', '2', '', 'VRDN-003 TED (2026)', ['I&I', 'Thyroid Eye', 'IGF-1R'])}
        ${companyCard('DNTH', 'Dianthus Therapeutics', 'Antibody', 'I&I (Complement). Lead: DNTH103 (Ph2).', '$1.0B', '2', '1', '', 'DNTH103 gMG (2026)', ['I&I', 'Complement', 'Myasthenia Gravis'])}
        ${companyCard('IRON', 'Disc Medicine', 'Antibody', 'Hematology. Lead: Bitopertin (Ph3).', '$3.0B', '4', '2', '', 'Bitopertin EPP (2026)', ['Hematology', 'Iron Disorders', 'Porphyria'])}
        ${companyCard('CLDX', 'Celldex Therapeutics', 'Antibody', 'I&I (KIT). Lead: Barzolvolimab (Ph3).', '$3.5B', '3', '2', '', 'Barzolvolimab CSU (2026)', ['I&I', 'KIT', 'Urticaria'])}
        ${companyCard('RAPT', 'RAPT Therapeutics', 'Small Molecule', 'I&I. Lead: Zelnecirnon (Ph2).', '$0.3B', '2', '1', '', 'Zelnecirnon atopic (2026)', ['I&I', 'CCR4', 'Atopic Derm'])}
        ${companyCard('SYRE', 'Spyre Therapeutics', 'Antibody', 'I&I (IBD). Lead: SPY001 (Ph2).', '$2.0B', '2', '1', '', 'SPY001 UC (2026)', ['I&I', 'IBD', 'IL-18'])}
        ${companyCard('ANAB', 'Anaptysbio', 'Antibody', 'I&I (PD-1 Agonist). Lead: Rosnilimab (Ph3).', '$1.5B', '3', '2', '', 'Rosnilimab alopecia (2026)', ['I&I', 'PD-1 Agonist', 'Alopecia'])}
        ${companyCard('ORKA', 'Oruka Therapeutics', 'Antibody', 'I&I (Dermatology). Lead: ORKA-001 (Ph2).', '$0.8B', '2', '1', '', 'ORKA-001 psoriasis (2026)', ['I&I', 'Dermatology', 'IL-13'])}
        ${companyCard('UPB', 'Upstream Bio', 'Antibody', 'I&I (Pulmonary). Lead: UPB-101 (Ph2).', '$0.5B', '2', '1', '', 'UPB-101 asthma (2026)', ['I&I', 'Pulmonary', 'TSLP'])}
        ${companyCard('ANNX', 'Annexon Biosciences', 'Antibody', 'I&I (Complement). Lead: ANX005 (Ph3).', '$0.8B', '3', '2', '', 'ANX005 HD (2026)', ['I&I', 'Complement', 'Huntington'])}
        ${companyCard('INBX', 'Inhibrx Biosciences', 'Antibody', 'I&I. Lead: INBRX-101 (Ph2).', '$0.6B', '3', '1', '', 'INBRX-101 AATD (2026)', ['I&I', 'AATD', 'Rare Disease'])}
        ${companyCard('KROS', 'Keros Therapeutics', 'Antibody', 'I&I (Hematology). Lead: KER-050 (Ph2).', '$1.0B', '3', '1', '', 'KER-050 MDS (2026)', ['I&I', 'Hematology', 'MDS'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - RARE DISEASE (14) ==================== -->
    <section id="rare" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - Rare Disease</h2>
        <span class="section-count">14</span>
      </div>
      <div class="cards-grid">
        ${companyCard('BBIO', 'BridgeBio Pharma', 'Small Molecule', 'Rare Disease, Cardio. Key product: Acoramidis (Approved).', '$8.0B', '8', '3', '1', 'Acoramidis ATTR-CM (2026)', ['Rare Disease', 'Cardio', 'ATTR'])}
        ${companyCard('ROIV', 'Roivant Sciences', 'Holding', 'Multiple (Holding Co). Multiple Vants.', '$10.0B', '15+', '5', '3', 'IMVT-1402 Ph3 (2026)', ['Platform', 'Multiple', 'Holding Co'])}
        ${companyCard('SRRK', 'Scholar Rock Holding', 'Antibody', 'Rare - Neuromuscular. Lead: Apitegromab (Ph3).', '$2.0B', '3', '2', '', 'Apitegromab SMA (2026)', ['Rare Disease', 'Neuromuscular', 'SMA'])}
        ${companyCard('RYTM', 'Rhythm Pharmaceuticals', 'Small Molecule', 'Rare - Metabolic (Obesity). Key product: Setmelanotide.', '$2.5B', '3', '1', '1', 'Setmelanotide expansion (2026)', ['Rare Disease', 'Obesity', 'MC4R'])}
        ${companyCard('COGT', 'Cogent Biosciences', 'Small Molecule', 'Rare - Mast Cell. Lead: Bezuclastinib (Ph3).', '$2.0B', '2', '2', '', 'Bezuclastinib GIST (2026)', ['Rare Disease', 'Mast Cell', 'KIT'])}
        ${companyCard('DYN', 'Dyne Therapeutics', 'AOC', 'Rare - Neuromuscular. Lead: DYNE-101 (Ph2).', '$2.0B', '3', '1', '', 'DYNE-101 DM1 (2026)', ['Rare Disease', 'Neuromuscular', 'AOC'])}
        ${companyCard('QURE', 'uniQure', 'Gene Therapy', 'Rare - Gene Therapy. Lead: AMT-130 (Ph1/2).', '$1.0B', '4', '1', '1', 'AMT-130 HD (2026)', ['Rare Disease', 'Gene Therapy', 'Huntington'])}
        ${companyCard('SLNO', 'Soleno Therapeutics', 'Small Molecule', 'Rare - PWS. Lead: DCCR (Ph3).', '$1.5B', '2', '1', '', 'DCCR Prader-Willi (2026)', ['Rare Disease', 'PWS', 'Metabolic'])}
        ${companyCard('TSHA', 'Taysha Gene Therapies', 'Gene Therapy', 'Rare - Gene Therapy. Lead: TSHA-120 (Ph1/2).', '$0.3B', '4', '1', '', 'TSHA-120 GAN (2026)', ['Rare Disease', 'Gene Therapy', 'GAN'])}
        ${companyCard('KALV', 'KalVista Pharmaceuticals', 'Small Molecule', 'Rare - HAE. Key product: Sebetralstat (Approved).', '$2.0B', '3', '1', '1', 'Sebetralstat launch (2026)', ['Rare Disease', 'HAE', 'Oral'])}
        ${companyCard('PVLA', 'Palvella Therapeutics', 'Small Molecule', 'Rare - Dermatology. Lead: PV-10 (Ph3).', '$0.2B', '2', '1', '', 'QTORIN EB (2026)', ['Rare Disease', 'Dermatology', 'EB'])}
        ${companyCard('FDMT', '4D Molecular Therapeutics', 'Gene Therapy', 'Rare - Ophthalmology (Gene Therapy). Lead: 4D-150 (Ph2).', '$0.5B', '4', '1', '', '4D-150 wet AMD (2026)', ['Rare Disease', 'Gene Therapy', 'Ophthalmology'])}
        ${companyCard('LXEO', 'Lexeo Therapeutics', 'Gene Therapy', 'Rare - Gene Therapy. Lead: LX1001 (Ph1/2).', '$0.3B', '3', '0', '', 'LX1001 cardiac (2026)', ['Rare Disease', 'Gene Therapy', 'Cardiac'])}
        ${companyCard('SVRA', 'Savara', 'Biologics', 'Rare - Pulmonary. Lead: Molgramostim (Ph3).', '$0.8B', '2', '1', '', 'Molgramostim aPAP (2026)', ['Rare Disease', 'Pulmonary', 'aPAP'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - NEUROPSYCHIATRY (6) ==================== -->
    <section id="neuro" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - Neuropsychiatry</h2>
        <span class="section-count">6</span>
      </div>
      <div class="cards-grid">
        ${companyCard('PRAX', 'Praxis Precision Medicines', 'Small Molecule', 'Neuropsychiatry (Epilepsy). Lead: Ulixacaltamide (Ph3).', '$0.8B', '3', '1', '', 'Ulixacaltamide epilepsy (2026)', ['Neuropsychiatry', 'Epilepsy', 'Ion Channel'])}
        ${companyCard('DNLI', 'Denali Therapeutics', 'Biologics', 'Neuropsychiatry (Neurodegeneration). Lead: Tividenofusp alfa (BLA).', '$4.2B', '8', '2', '', 'DNL310 Hunter (2026)', ['Neuropsychiatry', 'Neurodegeneration', 'Lysosomal'])}
        ${companyCard('STOK', 'Stoke Therapeutics', 'Antisense', 'Neuropsychiatry (Genetic). Lead: STK-001 (Ph2).', '$1.0B', '3', '1', '', 'STK-001 Dravet (2026)', ['Neuropsychiatry', 'Genetic', 'Antisense'])}
        ${companyCard('BHVN', 'Biohaven', 'Small Molecule', 'Neuropsychiatry (Multiple). Lead: Troriluzole (Ph3).', '$1.0B', '6', '3', '', 'BHV-7000 epilepsy (2026)', ['Neuropsychiatry', 'Psychiatry', 'Neurology'])}
        ${companyCard('AVXL', 'Anavex Life Sciences', 'Small Molecule', 'Neuropsychiatry (Alzheimers). Lead: Blarcamesine (Ph3).', '$0.5B', '3', '2', '', 'Blarcamesine Alzheimers (2026)', ['Neuropsychiatry', 'Alzheimer', 'Sigma-1'])}
        ${companyCard('PRTA', 'Prothena', 'Antibody', 'Neuropsychiatry (Amyloid). Lead: Birtamimab (Ph3).', '$2.5B', '5', '2', '', 'Birtamimab AL amyloid (2026)', ['Neuropsychiatry', 'Amyloid', 'AL Amyloidosis'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - METABOLIC/CV (7) ==================== -->
    <section id="metabolic" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - Metabolic/CV</h2>
        <span class="section-count">7</span>
      </div>
      <div class="cards-grid">
        ${companyCard('VKTX', 'Viking Therapeutics', 'Small Molecule', 'Metabolic (Obesity). Lead: VK2735 (Ph3).', '$6.2B', '3', '2', '', getNextCatalystDisplay('VKTX') || 'VK2735 obesity Ph3 (2026)', ['Metabolic', 'Obesity', 'GLP-1'])}
        ${companyCard('MLYS', 'Mineralys Therapeutics', 'Small Molecule', 'Cardiovascular (HTN). Lead: Lorundrostat (Ph2).', '$1.5B', '2', '1', '', 'Lorundrostat HTN (2026)', ['Cardiovascular', 'HTN', 'Aldosterone'])}
        ${companyCard('SION', 'Sionna Therapeutics', 'Small Molecule', 'Cardiovascular. Lead: SIO-2007 (Ph1).', '$0.3B', '2', '0', '', 'SIO-2007 lipids (2026)', ['Cardiovascular', 'Lipids', 'PCSK9'])}
        ${companyCard('ALT', 'Altimmune', 'Biologics', 'Metabolic (Obesity). Lead: Pemvidutide (Ph2).', '$1.0B', '2', '1', '', 'Pemvidutide obesity (2026)', ['Metabolic', 'Obesity', 'GLP-1/Glucagon'])}
        ${companyCard('GOSS', 'Gossamer Bio', 'Small Molecule', 'I&I, Oncology. Lead: Seralutinib (Ph3).', '$0.5B', '3', '2', '', 'Seralutinib PAH (2026)', ['I&I', 'Oncology', 'PAH'])}
        ${companyCard('AKBA', 'Akebia Therapeutics', 'Small Molecule', 'Nephrology (Anemia). Key product: Vadadustat.', '$0.2B', '2', '1', '', 'Vadadustat anemia (2026)', ['Nephrology', 'Anemia', 'HIF-PHI'])}
        ${companyCard('RZLT', 'Rezolute', 'Antibody', 'Metabolic (Hypoglycemia). Lead: RZ358 (Ph3).', '$0.5B', '2', '1', '', 'RZ358 CHI (2026)', ['Metabolic', 'Hypoglycemia', 'Insulin'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - NEPHROLOGY (2) ==================== -->
    <section id="nephro" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - Nephrology</h2>
        <span class="section-count">2</span>
      </div>
      <div class="cards-grid">
        ${companyCard('VERA', 'Vera Therapeutics', 'Biologics', 'Nephrology (IgAN). Lead: Atacicept (Ph3).', '$3.0B', '2', '2', '', 'Atacicept IgAN (2026)', ['Nephrology', 'IgAN', 'BAFF/APRIL'])}
        ${companyCard('KOD', 'Kodiak Sciences', 'Biologics', 'Ophthalmology (Retinal). Lead: Tarcocimab (Ph3).', '$0.5B', '2', '1', '', 'Tarcocimab wet AMD (2026)', ['Ophthalmology', 'Retinal', 'Anti-VEGF'])}
      </div>
    </section>

    <!-- ==================== CLINICAL - VACCINES (4) ==================== -->
    <section id="vaccines" class="section">
      <div class="section-header">
        <h2 class="section-title">Clinical - Vaccines</h2>
        <span class="section-count">4</span>
      </div>
      <div class="cards-grid">
        ${companyCard('VIR', 'Vir Biotechnology', 'Antibody', 'Infectious Disease. Lead: Elebsiran (Ph2).', '$1.5B', '6', '2', '', 'Elebsiran HBV (2026)', ['Infectious Disease', 'HBV', 'siRNA'])}
        ${companyCard('IVVD', 'Invivyd', 'Antibody', 'Infectious Disease. Lead: VYD222 (Ph2).', '$0.3B', '2', '1', '', 'VYD222 COVID (2026)', ['Infectious Disease', 'COVID', 'Antibody'])}
        ${companyCard('ABUS', 'Arbutus Biopharma', 'Antisense', 'Infectious Disease (HBV). Lead: Imdusiran (Ph2).', '$0.2B', '3', '1', '', 'Imdusiran HBV (2026)', ['Infectious Disease', 'HBV', 'siRNA'])}
        ${companyCard('PCVX', 'Vaxcyte', 'Vaccine', 'Vaccines. Lead: VAX-31 (Ph3).', '$4.3B', '5', '2', '', 'VAX-31 pneumo (2026)', ['Vaccines', 'Pneumococcal', 'Conjugate'])}
      </div>
    </section>

    <!-- ==================== TOOLS & BIOPROCESSING (3) ==================== -->
    <section id="tools" class="section">
      <div class="section-header">
        <h2 class="section-title">Tools & Bioprocessing</h2>
        <span class="section-count">3</span>
      </div>
      <div class="cards-grid">
        ${companyCard('TWST', 'Twist Bioscience', 'Platform', 'Synthetic Biology. Synthetic DNA platform.', '$2.0B', 'N/A', 'N/A', '', 'Biopharma growth (2026)', ['Synthetic Biology', 'DNA', 'Platform'])}
        ${companyCard('RXRX', 'Recursion Pharmaceuticals', 'AI Platform', 'AI Drug Discovery. AI platform.', '$3.0B', '10+', '2', '', 'REC-994 NF2 (2026)', ['AI', 'Drug Discovery', 'Platform'])}
        ${companyCard('ABSI', 'Absci', 'AI Platform', 'AI Drug Discovery. AI antibody platform.', '$0.5B', '3', '0', '', 'ABS-101 Ph1 (2026)', ['AI', 'Antibody', 'Platform'])}
      </div>
    </section>
  </main>

  <footer class="footer">
    <p>© 2026 Satya Bio. Institutional-grade biotech intelligence.</p>
  </footer>

  <script>
    // Smooth scroll for category pills
    document.querySelectorAll('.category-pill').forEach(pill => {
      pill.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href').substring(1);
        const target = document.getElementById(targetId);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth' });
        }
      });
    });

    // Scroll spy for active pill
    const sections = document.querySelectorAll('.section');
    const pills = document.querySelectorAll('.category-pill');

    function updateActivePill() {
      let current = '';
      sections.forEach(section => {
        const sectionTop = section.offsetTop;
        if (window.pageYOffset >= sectionTop - 200) {
          current = section.getAttribute('id');
        }
      });

      pills.forEach(pill => {
        pill.classList.remove('active');
        if (pill.getAttribute('href') === '#' + current) {
          pill.classList.add('active');
        }
      });
    }

    window.addEventListener('scroll', updateActivePill);
    updateActivePill();

    // Search functionality
    const searchInput = document.getElementById('companySearch');
    const searchClear = document.getElementById('searchClear');
    const searchResultsInfo = document.getElementById('searchResultsInfo');
    const noResults = document.getElementById('noResults');
    const categoryNav = document.getElementById('categoryNav');
    const allSections = document.querySelectorAll('.section');
    const allCards = document.querySelectorAll('.company-card');

    // Store original parent for each card
    allCards.forEach(card => {
      card.dataset.originalParent = card.parentElement.className;
    });

    function performSearch(query) {
      const q = query.toLowerCase().trim();

      if (!q) {
        // Reset to normal view
        allSections.forEach(s => s.style.display = '');
        allCards.forEach(card => card.style.display = '');
        categoryNav.style.display = '';
        searchResultsInfo.style.display = 'none';
        noResults.style.display = 'none';
        searchClear.classList.remove('visible');
        return;
      }

      searchClear.classList.add('visible');

      let matchCount = 0;

      allCards.forEach(card => {
        const ticker = card.querySelector('.card-ticker')?.textContent?.toLowerCase() || '';
        const name = card.querySelector('.card-name')?.textContent?.toLowerCase() || '';
        const platform = card.querySelector('.platform-badge')?.textContent?.toLowerCase() || '';
        const description = card.querySelector('.card-description')?.textContent?.toLowerCase() || '';
        const tags = Array.from(card.querySelectorAll('.tag')).map(t => t.textContent.toLowerCase()).join(' ');

        const searchText = ticker + ' ' + name + ' ' + platform + ' ' + description + ' ' + tags;

        if (searchText.includes(q)) {
          card.style.display = '';
          matchCount++;
        } else {
          card.style.display = 'none';
        }
      });

      // Hide sections with no visible cards
      allSections.forEach(section => {
        const visibleCards = section.querySelectorAll('.company-card:not([style*="display: none"])');
        if (visibleCards.length === 0) {
          section.style.display = 'none';
        } else {
          section.style.display = '';
        }
      });

      // Hide category nav during search
      categoryNav.style.display = 'none';

      // Show results info
      if (matchCount > 0) {
        searchResultsInfo.innerHTML = '<strong>' + matchCount + '</strong> ' + (matchCount === 1 ? 'company' : 'companies') + ' matching "<strong>' + escapeHtml(query) + '</strong>"';
        searchResultsInfo.style.display = 'block';
        noResults.style.display = 'none';
      } else {
        searchResultsInfo.style.display = 'none';
        noResults.querySelector('p').textContent = 'No companies found for "' + query + '". Try a different search term.';
        noResults.style.display = 'block';
      }
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Debounce search
    let searchTimeout;
    searchInput.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => performSearch(this.value), 150);
    });

    searchClear.addEventListener('click', function() {
      searchInput.value = '';
      performSearch('');
      searchInput.focus();
    });

    // Clear search on Escape
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        searchInput.value = '';
        performSearch('');
        searchInput.blur();
      }
    });
  </script>
</body>
</html>`);
  });

  // Targets Marketplace Page
  app.get('/targets', (_req: Request, res: Response) => {
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Explore Drug Targets | Satya Bio</title>
  <meta name="description" content="Deep-dive research on validated and emerging therapeutic targets with competitive landscapes, clinical data, and deal activity.">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a2b3c;
      --primary-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --accent-light: #fef5f3;
      --highlight: #fef08a;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --border-light: #eeeeea;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
      --success: #10b981;
      --info: #3b82f6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

    /* Header */
    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 72px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 800; color: var(--primary); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.95rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: var(--primary); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-ghost { padding: 10px 18px; color: var(--text-secondary); font-weight: 600; text-decoration: none; }
    .btn-primary { padding: 10px 22px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; transition: all 0.2s; }
    .btn-primary:hover { background: var(--accent-hover); }

    /* Hero with floating circles */
    .hero { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); padding: 80px 32px; text-align: center; position: relative; overflow: hidden; }
    .hero-bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }
    .circle { position: absolute; border-radius: 50%; opacity: 0.15; animation: float 20s ease-in-out infinite; }
    .circle-1 { width: 300px; height: 300px; background: linear-gradient(135deg, #fef08a 0%, #fde68a 100%); top: -100px; right: 10%; animation-delay: 0s; }
    .circle-2 { width: 200px; height: 200px; background: linear-gradient(135deg, #fef5f3 0%, #fecaca 100%); bottom: -50px; left: 5%; animation-delay: -5s; }
    .circle-3 { width: 150px; height: 150px; background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); top: 20%; right: 5%; animation-delay: -10s; }
    @keyframes float {
      0%, 100% { transform: translate(0, 0) rotate(0deg); }
      25% { transform: translate(20px, -20px) rotate(5deg); }
      50% { transform: translate(-10px, 20px) rotate(-5deg); }
      75% { transform: translate(-20px, -10px) rotate(3deg); }
    }
    .hero-content { position: relative; z-index: 1; }
    .hero h1 { font-family: 'Fraunces', serif; font-size: 3rem; font-weight: 700; color: white; margin-bottom: 16px; }
    .hero p { color: rgba(255,255,255,0.85); font-size: 1.2rem; max-width: 700px; margin: 0 auto 32px; }

    /* Search Box */
    .search-container { max-width: 600px; margin: 0 auto; }
    .search-box { display: flex; background: var(--surface); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.15); }
    .search-box input { flex: 1; padding: 16px 24px; font-size: 1rem; border: none; outline: none; font-family: inherit; }
    .search-box input::placeholder { color: var(--text-muted); }
    .search-box button { padding: 16px 28px; background: var(--accent); color: white; border: none; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    .search-box button:hover { background: var(--accent-hover); }

    /* Main Layout */
    .main { max-width: 1400px; margin: 0 auto; padding: 40px 32px; display: grid; grid-template-columns: 280px 1fr; gap: 40px; }
    @media (max-width: 968px) { .main { grid-template-columns: 1fr; } }

    /* Sidebar Filters */
    .sidebar { position: sticky; top: 112px; height: fit-content; }
    .filter-section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    .filter-section h3 { font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 16px; }
    .filter-options { display: flex; flex-direction: column; gap: 8px; }
    .filter-option { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border-light); border-radius: 8px; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }
    .filter-option:hover { border-color: var(--accent); background: var(--accent-light); }
    .filter-option.active { border-color: var(--accent); background: var(--accent-light); }
    .filter-option input { display: none; }
    .filter-checkbox { width: 18px; height: 18px; border: 2px solid var(--border); border-radius: 4px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; flex-shrink: 0; }
    .filter-option.active .filter-checkbox { background: var(--accent); border-color: var(--accent); }
    .filter-option.active .filter-checkbox::after { content: '✓'; color: white; font-size: 12px; font-weight: 700; }
    .filter-count { margin-left: auto; font-size: 0.8rem; color: var(--text-muted); background: var(--border-light); padding: 2px 8px; border-radius: 10px; }

    /* Targets Grid */
    .targets-section h2 { font-family: 'Fraunces', serif; font-size: 1.5rem; color: var(--primary); margin-bottom: 8px; }
    .targets-meta { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 24px; }
    .targets-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }

    /* Target Card */
    .target-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; transition: all 0.25s; display: flex; flex-direction: column; }
    .target-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.08); border-color: var(--accent); }
    .target-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
    .target-name { font-family: 'Fraunces', serif; font-size: 1.4rem; font-weight: 700; color: var(--primary); }
    .target-fullname { font-size: 0.95rem; color: var(--text-secondary); margin-bottom: 8px; }
    .area-badge { display: inline-block; padding: 4px 12px; background: var(--accent-light); color: var(--accent); font-size: 0.75rem; font-weight: 700; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.3px; }
    .area-badge.oncology { background: #fef2f2; color: #dc2626; }
    .area-badge.metabolic { background: #fefce8; color: #ca8a04; }
    .area-badge.immunology { background: #f0fdf4; color: #16a34a; }
    .area-badge.cardiovascular { background: #eff6ff; color: #2563eb; }
    .target-desc { color: var(--text-secondary); font-size: 0.9rem; margin: 16px 0; flex: 1; line-height: 1.5; }
    .target-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding-top: 16px; border-top: 1px solid var(--border-light); margin-bottom: 16px; }
    .stat { text-align: center; }
    .stat-value { font-size: 1rem; font-weight: 700; color: var(--primary); }
    .stat-label { font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px; }
    .target-highlight { background: var(--highlight); padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; margin-bottom: 16px; }
    .highlight-label { font-weight: 600; color: var(--primary); }
    .view-btn { display: block; width: 100%; padding: 12px; background: var(--primary); color: white; text-align: center; text-decoration: none; border-radius: 10px; font-weight: 600; font-size: 0.95rem; transition: all 0.2s; }
    .view-btn:hover { background: var(--primary-light); transform: translateY(-1px); }

    /* Market Status */
    .market-status { display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 14px; }
    .status-approved { background: #dcfce7; color: #16a34a; }
    .status-race { background: #ffedd5; color: #c2410c; }
    .status-early { background: #f3f4f6; color: #6b7280; }

    /* Competitor Section - Fixed Layout */
    .competitor-section { margin: 10px 0; padding: 10px; background: var(--bg); border-radius: 8px; }
    .competitor-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; min-height: 28px; }
    .competitor-row:last-child { margin-bottom: 0; }
    .competitor-label { flex: 0 0 85px; font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; color: var(--text-muted); }
    .competitor-info { flex: 1; min-width: 0; display: flex; align-items: center; gap: 6px; }
    .competitor-text { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.75rem; color: var(--text); }
    .competitor-text .company { font-weight: 600; color: var(--primary); }
    .competitor-text .ticker { color: var(--accent); font-weight: 600; }
    .stage-pill { flex: 0 0 auto; font-size: 0.6rem; font-weight: 600; padding: 2px 7px; border-radius: 8px; white-space: nowrap; }
    .stage-pill-approved { background: #dcfce7; color: #16a34a; }
    .stage-pill-phase3 { background: #dbeafe; color: #2563eb; }
    .stage-pill-phase2 { background: #fef9c3; color: #ca8a04; }
    .stage-pill-phase1 { background: #f3f4f6; color: #6b7280; }

    /* Target Footer */
    .target-footer { margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border-light); }
    .companies-count { font-size: 0.75rem; color: var(--text-muted); margin-bottom: 6px; }
    .companies-count strong { color: var(--primary); }
    .target-card .view-btn { margin-top: 10px; }

    /* Footer */
    .footer { background: var(--primary); color: rgba(255,255,255,0.7); padding: 48px 32px; text-align: center; margin-top: 64px; }
    .footer p { font-size: 0.9rem; }

    /* Mobile */
    @media (max-width: 768px) {
      .nav-links { display: none; }
      .hero { padding: 60px 20px; }
      .hero h1 { font-size: 2rem; }
      .main { padding: 24px 20px; }
      .sidebar { display: none; }
      .targets-grid { grid-template-columns: 1fr; }
      .target-stats { grid-template-columns: repeat(2, 1fr); }
      .competitor-label { flex: 0 0 70px; font-size: 0.55rem; }
      .competitor-text { font-size: 0.7rem; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets" class="active">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
                <a href="mailto:hello@satyabio.com?subject=Early%20Access%20Request&body=I'd%20like%20to%20request%20early%20access%20to%20Satya%20Bio." class="btn-primary">Get Started</a>
      </div>
    </div>
  </header>

  <section class="hero">
    <div class="hero-bg">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>
    <div class="hero-content">
      <h1>Explore Drug Targets</h1>
      <p>Deep-dive research on validated and emerging therapeutic targets with competitive landscapes, clinical data, and deal activity.</p>
      <div class="search-container">
        <form class="search-box" onsubmit="event.preventDefault(); filterTargets();">
          <input type="text" id="target-search" placeholder="Search by target name, gene, or therapeutic area...">
          <button type="submit">Search</button>
        </form>
      </div>
    </div>
  </section>

  <div class="main">
    <aside class="sidebar">
      <div class="filter-section">
        <h3>By Therapeutic Area</h3>
        <div class="filter-options">
          <label class="filter-option" data-filter="oncology" onclick="toggleFilter(this)">
            <input type="checkbox" value="oncology">
            <span class="filter-checkbox"></span>
            Oncology
            <span class="filter-count">8</span>
          </label>
          <label class="filter-option" data-filter="immunology" onclick="toggleFilter(this)">
            <input type="checkbox" value="immunology">
            <span class="filter-checkbox"></span>
            Immunology
            <span class="filter-count">5</span>
          </label>
          <label class="filter-option" data-filter="cardiovascular" onclick="toggleFilter(this)">
            <input type="checkbox" value="cardiovascular">
            <span class="filter-checkbox"></span>
            Cardiovascular
            <span class="filter-count">1</span>
          </label>
          <label class="filter-option" data-filter="neuropsychiatry" onclick="toggleFilter(this)">
            <input type="checkbox" value="neuropsychiatry">
            <span class="filter-checkbox"></span>
            Neuropsychiatry
            <span class="filter-count">2</span>
          </label>
          <label class="filter-option" data-filter="metabolic" onclick="toggleFilter(this)">
            <input type="checkbox" value="metabolic">
            <span class="filter-checkbox"></span>
            Metabolic
            <span class="filter-count">1</span>
          </label>
          <label class="filter-option" data-filter="rare" onclick="toggleFilter(this)">
            <input type="checkbox" value="rare">
            <span class="filter-checkbox"></span>
            Rare Disease
            <span class="filter-count">2</span>
          </label>
        </div>
      </div>
    </aside>

    <section class="targets-section">
      <h2>Target Landscape</h2>
      <p class="targets-meta" id="targets-count">Showing 15 targets</p>

      <div class="targets-grid" id="targets-grid">
        <!-- KRAS G12C -->
        <div class="target-card" data-category="oncology">
          <div class="target-header">
            <div><div class="target-name">KRAS G12C</div></div>
            <span class="area-badge oncology">Oncology</span>
          </div>
          <div class="market-status status-approved">Approved Drug Exists</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Market Leader</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Amgen</span> (<span class="ticker">AMGN</span>) - Lumakras</span><span class="stage-pill stage-pill-approved">Approved</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Challenger</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Revolution</span> (<span class="ticker">RVMD</span>) - Elironrasib</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>8+</strong> companies pursuing</div>
            <p class="target-desc">Amgen, Mirati approved. Next-gen focus on combos.</p>
          </div>
        </div>

        <!-- RAS(ON) Multi -->
        <div class="target-card" data-category="oncology">
          <div class="target-header">
            <div><div class="target-name">RAS(ON) Multi</div></div>
            <span class="area-badge oncology">Oncology</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Revolution</span> (<span class="ticker">RVMD</span>) - Daraxonrasib</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Mirati/BMS</span> - MRTX1133</span><span class="stage-pill stage-pill-phase1">Phase 1</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>4</strong> companies pursuing</div>
            <p class="target-desc">First multi-RAS inhibitor; BTD granted.</p>
          </div>
        </div>

        <!-- Menin-MLL -->
        <div class="target-card" data-category="oncology">
          <div class="target-header">
            <div><div class="target-name">Menin-MLL</div></div>
            <span class="area-badge oncology">Oncology</span>
          </div>
          <div class="market-status status-approved">Approved Drug Exists</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Market Leader</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Syndax</span> (<span class="ticker">SNDX</span>) - Revuforj</span><span class="stage-pill stage-pill-approved">Approved</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Challenger</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Kura</span> (<span class="ticker">KURA</span>) - Ziftomenib</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>3</strong> companies pursuing</div>
            <p class="target-desc">First-in-class for KMT2A AML.</p>
          </div>
        </div>

        <!-- TIGIT -->
        <div class="target-card" data-category="oncology">
          <div class="target-header">
            <div><div class="target-name">TIGIT</div></div>
            <span class="area-badge oncology">Oncology</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Arcus/Gilead</span> (<span class="ticker">RCUS</span>) - Domvanalimab</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Merck</span> (<span class="ticker">MRK</span>) - Vibostolimab</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>10+</strong> companies pursuing</div>
            <p class="target-desc">Crowded checkpoint. Fc design matters.</p>
          </div>
        </div>

        <!-- B7-H3 -->
        <div class="target-card" data-category="oncology">
          <div class="target-header">
            <div><div class="target-name">B7-H3</div></div>
            <span class="area-badge oncology">Oncology</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">MacroGenics</span> (<span class="ticker">MGNX</span>) - Vobramitamab duo</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Multiple</span> - ADCs, CAR-T</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>23</strong> assets in development</div>
            <p class="target-desc">Highly expressed in solid tumors with limited normal tissue.</p>
            <a href="/api/report/target/B7-H3/html" class="view-btn">View Full Landscape →</a>
          </div>
        </div>

        <!-- TL1A -->
        <div class="target-card" data-category="immunology">
          <div class="target-header">
            <div><div class="target-name">TL1A</div></div>
            <span class="area-badge immunology">I&I</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Spyre</span> (<span class="ticker">SYRE</span>) - SPY002</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Prometheus</span> - PRA023</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>9</strong> assets in development</div>
            <p class="target-desc">Hot IBD target with anti-fibrotic potential.</p>
            <a href="/api/report/target/TL1A/html" class="view-btn">View Full Landscape →</a>
          </div>
        </div>

        <!-- FcRn -->
        <div class="target-card" data-category="immunology">
          <div class="target-header">
            <div><div class="target-name">FcRn</div></div>
            <span class="area-badge immunology">I&I</span>
          </div>
          <div class="market-status status-approved">Approved Drug Exists</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Market Leader</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">argenx</span> (<span class="ticker">ARGX</span>) - VYVGART</span><span class="stage-pill stage-pill-approved">Approved</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Challenger</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Immunovant</span> (<span class="ticker">IMVT</span>) - IMVT-1402</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>5</strong> companies pursuing</div>
            <p class="target-desc">$4B+ market. MG, CIDP, ITP.</p>
          </div>
        </div>

        <!-- IL-4Ra -->
        <div class="target-card" data-category="immunology">
          <div class="target-header">
            <div><div class="target-name">IL-4Ra / IL-13</div></div>
            <span class="area-badge immunology">I&I</span>
          </div>
          <div class="market-status status-approved">Approved Drug Exists</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Market Leader</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Regeneron</span> (<span class="ticker">REGN</span>) - Dupixent</span><span class="stage-pill stage-pill-approved">Approved</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Challenger</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Apogee</span> (<span class="ticker">APGE</span>) - APG777</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>4</strong> companies pursuing</div>
            <p class="target-desc">$13B+ blockbuster. Q12W dosing goal.</p>
          </div>
        </div>

        <!-- KIT mast cell -->
        <div class="target-card" data-category="immunology">
          <div class="target-header">
            <div><div class="target-name">KIT (mast cell)</div></div>
            <span class="area-badge immunology">I&I</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Celldex</span> (<span class="ticker">CLDX</span>) - Barzolvolimab</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Allakos</span> - Various</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>3</strong> companies pursuing</div>
            <p class="target-desc">Mast cell depletion for urticaria.</p>
          </div>
        </div>

        <!-- GLP-1 -->
        <div class="target-card" data-category="metabolic">
          <div class="target-header">
            <div><div class="target-name">GLP-1/GIP dual</div></div>
            <span class="area-badge metabolic">Metabolic</span>
          </div>
          <div class="market-status status-approved">Approved Drug Exists</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Market Leader</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Eli Lilly</span> (<span class="ticker">LLY</span>) - Mounjaro</span><span class="stage-pill stage-pill-approved">Approved</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Challenger</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Viking</span> (<span class="ticker">VKTX</span>) - VK2735</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>10+</strong> companies pursuing</div>
            <p class="target-desc">$50B+ market. Oral formulation key.</p>
            <a href="/api/report/target/GLP-1/html" class="view-btn">View Report</a>
          </div>
        </div>

        <!-- Aldosterone -->
        <div class="target-card" data-category="cardiovascular">
          <div class="target-header">
            <div><div class="target-name">Aldosterone synth</div></div>
            <span class="area-badge cardiovascular">Cardiovascular</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Mineralys</span> (<span class="ticker">MLYS</span>) - Lorundrostat</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Alnylam</span> (<span class="ticker">ALNY</span>) - Zilebesiran</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>3</strong> companies pursuing</div>
            <p class="target-desc">CYP11B2 for resistant HTN.</p>
          </div>
        </div>

        <!-- DMD -->
        <div class="target-card" data-category="rare">
          <div class="target-header">
            <div><div class="target-name">DMD gene therapy</div></div>
            <span class="area-badge" style="background:#faf5ff;color:#7c3aed;">Rare Disease</span>
          </div>
          <div class="market-status status-approved">Approved Drug Exists</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Market Leader</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Sarepta</span> (<span class="ticker">SRPT</span>) - Elevidys</span><span class="stage-pill stage-pill-approved">Approved</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Challenger</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Solid Bio</span> - SGT-003</span><span class="stage-pill stage-pill-phase1">Phase 1/2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>4</strong> companies pursuing</div>
            <p class="target-desc">First DMD gene therapy approved.</p>
          </div>
        </div>

        <!-- Hepcidin -->
        <div class="target-card" data-category="rare">
          <div class="target-header">
            <div><div class="target-name">Hepcidin mimetic</div></div>
            <span class="area-badge" style="background:#faf5ff;color:#7c3aed;">Rare Disease</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Protagonist</span> (<span class="ticker">PTGX</span>) - Rusfertide</span><span class="stage-pill stage-pill-phase3">NDA Filed</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Disc Med</span> (<span class="ticker">IRON</span>) - Various</span><span class="stage-pill stage-pill-phase2">Phase 2</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>2</strong> companies pursuing</div>
            <p class="target-desc">First-in-class for PV. Takeda partner.</p>
          </div>
        </div>

        <!-- Nav1.6 -->
        <div class="target-card" data-category="neuropsychiatry">
          <div class="target-header">
            <div><div class="target-name">Nav1.6 / SCN8A</div></div>
            <span class="area-badge" style="background:#fef3c7;color:#92400e;">Neuro</span>
          </div>
          <div class="market-status status-early">Early Stage</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Praxis</span> (<span class="ticker">PRAX</span>) - Relutrigine</span><span class="stage-pill stage-pill-phase2">Phase 2/3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text">None significant</span><span class="stage-pill stage-pill-phase1">-</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>1</strong> company pursuing</div>
            <p class="target-desc">BTD for SCN8A epilepsy. Low competition.</p>
          </div>
        </div>

        <!-- T-type Ca2+ -->
        <div class="target-card" data-category="neuropsychiatry">
          <div class="target-header">
            <div><div class="target-name">T-type Ca2+ channel</div></div>
            <span class="area-badge" style="background:#fef3c7;color:#92400e;">Neuro</span>
          </div>
          <div class="market-status status-race">Race to First</div>
          <div class="competitor-section">
            <div class="competitor-row">
              <span class="competitor-label">Frontrunner</span>
              <span class="competitor-info"><span class="competitor-text"><span class="company">Praxis</span> (<span class="ticker">PRAX</span>) - Ulixacaltamide</span><span class="stage-pill stage-pill-phase3">Phase 3</span></span>
            </div>
            <div class="competitor-row">
              <span class="competitor-label">Fast Follower</span>
              <span class="competitor-info"><span class="competitor-text">None significant</span><span class="stage-pill stage-pill-phase1">-</span></span>
            </div>
          </div>
          <div class="target-footer">
            <div class="companies-count"><strong>1</strong> company pursuing</div>
            <p class="target-desc">BTD for essential tremor.</p>
          </div>
        </div>
      </div>
    </section>
  </div>

  <footer class="footer">
    <p>© 2026 Satya Bio. Institutional-grade biotech intelligence.</p>
  </footer>

  <script>
    const activeFilters = new Set();
    function toggleFilter(el) {
      el.classList.toggle('active');
      const f = el.dataset.filter;
      if (el.classList.contains('active')) activeFilters.add(f);
      else activeFilters.delete(f);
      applyFilters();
    }
    function applyFilters() {
      const cards = document.querySelectorAll('.target-card');
      const q = document.getElementById('target-search').value.toLowerCase();
      let count = 0;
      cards.forEach(card => {
        const cats = (card.dataset.category || '').split(' ');
        const text = card.textContent.toLowerCase();
        const matchSearch = !q || text.includes(q);
        const matchFilter = activeFilters.size === 0 || [...activeFilters].some(f => cats.includes(f));
        if (matchSearch && matchFilter) { card.style.display = 'flex'; count++; }
        else card.style.display = 'none';
      });
      document.getElementById('targets-count').textContent = 'Showing ' + count + ' targets';
    }
    function filterTargets() { applyFilters(); }
    document.getElementById('target-search').addEventListener('input', applyFilters);
  </script>
</body>
</html>`);
  });

  // KOL Finder Page
  app.get('/kols', (_req: Request, res: Response) => {
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>KOL Finder | Satya Bio</title>
  <meta name="description" content="Find Key Opinion Leaders by target, disease, or therapeutic area.">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a2b3c;
      --primary-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --accent-light: #fef5f3;
      --highlight: #fef08a;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --border-light: #eeeeea;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
      --success: #10b981;
      --info: #3b82f6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

    /* Header */
    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 72px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1400px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 800; color: var(--primary); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.95rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: var(--primary); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-ghost { padding: 10px 18px; color: var(--text-secondary); font-weight: 600; text-decoration: none; }
    .btn-primary { padding: 10px 22px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; transition: all 0.2s; }
    .btn-primary:hover { background: var(--accent-hover); }

    /* Hero */
    .hero { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); padding: 60px 32px 80px; text-align: center; position: relative; overflow: hidden; }
    .hero-bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }
    .circle { position: absolute; border-radius: 50%; opacity: 0.1; }
    .circle-1 { width: 300px; height: 300px; background: linear-gradient(135deg, #fef08a 0%, #fde68a 100%); top: -100px; right: 10%; }
    .circle-2 { width: 200px; height: 200px; background: linear-gradient(135deg, #fef5f3 0%, #fecaca 100%); bottom: -80px; left: 5%; }
    .hero-content { position: relative; z-index: 1; }
    .hero h1 { font-family: 'Fraunces', serif; font-size: 2.8rem; font-weight: 700; color: white; margin-bottom: 12px; }
    .hero p { color: rgba(255,255,255,0.85); font-size: 1.15rem; max-width: 700px; margin: 0 auto 32px; }

    /* Search Box */
    .search-container { max-width: 700px; margin: 0 auto; }
    .search-box { display: flex; background: var(--surface); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.15); }
    .search-box input { flex: 1; padding: 18px 24px; font-size: 1.05rem; border: none; outline: none; font-family: inherit; }
    .search-box input::placeholder { color: var(--text-muted); }
    .search-box button { padding: 18px 32px; background: var(--accent); color: white; border: none; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    .search-box button:hover { background: var(--accent-hover); }
    .search-box button:disabled { background: var(--text-muted); cursor: not-allowed; }
    .search-hint { color: rgba(255,255,255,0.6); font-size: 0.85rem; margin-top: 12px; }
    .search-hint span { background: rgba(255,255,255,0.15); padding: 3px 10px; border-radius: 12px; margin: 0 4px; cursor: pointer; transition: background 0.2s; }
    .search-hint span:hover { background: rgba(255,255,255,0.25); }

    /* Main Layout */
    .main { max-width: 1400px; margin: 0 auto; padding: 40px 32px; display: grid; grid-template-columns: 260px 1fr; gap: 40px; }
    @media (max-width: 968px) { .main { grid-template-columns: 1fr; } }

    /* Sidebar Filters */
    .sidebar { position: sticky; top: 112px; height: fit-content; }
    .filter-section { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    .filter-section h3 { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 16px; }
    .filter-options { display: flex; flex-direction: column; gap: 6px; }
    .filter-option { display: flex; align-items: center; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border-light); border-radius: 8px; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }
    .filter-option:hover { border-color: var(--accent); background: var(--accent-light); }
    .filter-option.active { border-color: var(--accent); background: var(--accent-light); }
    .filter-option input[type="radio"] { margin-right: 10px; accent-color: var(--accent); }
    select.filter-select { width: 100%; padding: 12px; font-size: 0.9rem; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); cursor: pointer; font-family: inherit; }
    select.filter-select:focus { outline: none; border-color: var(--accent); }

    /* Results Section */
    .results-section h2 { font-family: 'Fraunces', serif; font-size: 1.5rem; color: var(--primary); margin-bottom: 8px; }
    .results-meta { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 24px; display: flex; align-items: center; gap: 16px; }
    .search-time { background: var(--border-light); padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; }

    /* Loading State */
    .loading { text-align: center; padding: 60px; color: var(--text-muted); }
    .loading-spinner { width: 40px; height: 40px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px; }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Empty State */
    .empty-state { text-align: center; padding: 80px 40px; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; }
    .empty-state h3 { font-family: 'Fraunces', serif; font-size: 1.3rem; color: var(--primary); margin-bottom: 12px; }
    .empty-state p { color: var(--text-muted); max-width: 400px; margin: 0 auto; }

    /* Results Table */
    .results-table { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; }
    .table-wrapper { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    thead { background: var(--bg); }
    th { padding: 14px 16px; text-align: left; font-weight: 600; color: var(--text-secondary); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); white-space: nowrap; }
    td { padding: 16px; border-bottom: 1px solid var(--border-light); vertical-align: top; }
    tr:last-child td { border-bottom: none; }
    tr:hover { background: var(--bg); }

    .kol-name { font-weight: 600; color: var(--primary); cursor: pointer; }
    .kol-name:hover { color: var(--accent); text-decoration: underline; }
    .institution { color: var(--text-secondary); font-size: 0.85rem; max-width: 250px; }
    .country-badge { display: inline-block; padding: 3px 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; font-size: 0.8rem; font-weight: 600; }
    .country-US { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
    .country-CN { background: #fef2f2; border-color: #fecaca; color: #b91c1c; }
    .country-UK { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
    .country-DE { background: #fefce8; border-color: #fef08a; color: #a16207; }
    .country-FR { background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }
    .country-JP { background: #fdf2f8; border-color: #fbcfe8; color: #be185d; }
    .email-link { color: var(--accent); text-decoration: none; font-size: 0.85rem; }
    .email-link:hover { text-decoration: underline; }
    .email-none { color: var(--text-muted); }
    .count-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 28px; padding: 4px 8px; background: var(--bg); border-radius: 8px; font-weight: 600; font-size: 0.85rem; }
    .count-high { background: #dcfce7; color: #166534; }
    .role-badge { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .role-pi { background: #dbeafe; color: #1e40af; }
    .role-author { background: #fef3c7; color: #92400e; }
    .role-both { background: #dcfce7; color: #166534; }

    /* Find Email Button */
    .find-email-btn { padding: 4px 12px; background: var(--accent); color: white; border: none; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
    .find-email-btn:hover { background: var(--accent-hover); }
    .email-searching { color: var(--accent); font-style: italic; }

    /* Expanded Details */
    .kol-details { display: none; background: var(--bg); padding: 20px; border-top: 1px solid var(--border-light); }
    .kol-details.show { display: block; }
    .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 768px) { .details-grid { grid-template-columns: 1fr; } }
    .details-section h4 { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 12px; }
    .details-list { list-style: none; }
    .details-list li { padding: 8px 0; border-bottom: 1px solid var(--border-light); font-size: 0.85rem; color: var(--text-secondary); }
    .details-list li:last-child { border-bottom: none; }
    .details-list a { color: var(--accent); text-decoration: none; }
    .details-list a:hover { text-decoration: underline; }

    /* Footer */
    .footer { background: var(--surface); border-top: 1px solid var(--border); padding: 24px 32px; text-align: center; color: var(--text-muted); font-size: 0.85rem; margin-top: 60px; }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols" class="active">KOL Finder</a>
        <a href="/research">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
        <a href="#" class="btn-primary">Get Started</a>
      </div>
    </div>
  </header>

  <section class="hero">
    <div class="hero-bg">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>
    <div class="hero-content">
      <h1>KOL Finder</h1>
      <p>Find Key Opinion Leaders by target, disease, or therapeutic area. Powered by PubMed and ClinicalTrials.gov.</p>
      <div class="search-container">
        <form class="search-box" id="search-form" onsubmit="searchKOLs(event)">
          <input type="text" id="search-input" placeholder="Search by target, disease, or drug name..." autocomplete="off">
          <button type="submit" id="search-btn">Search</button>
        </form>
        <div class="search-hint">
          Try: <span onclick="setSearch('TL1A')">TL1A</span>
          <span onclick="setSearch('ulcerative colitis')">ulcerative colitis</span>
          <span onclick="setSearch('KRAS G12C')">KRAS G12C</span>
          <span onclick="setSearch('CAR-T')">CAR-T</span>
        </div>
      </div>
    </div>
  </section>

  <main class="main">
    <aside class="sidebar">
      <div class="filter-section">
        <h3>Min. Publications</h3>
        <select class="filter-select" id="filter-pubs" onchange="applyFilters()">
          <option value="0">Any</option>
          <option value="3">3+</option>
          <option value="5">5+</option>
          <option value="10">10+</option>
        </select>
      </div>
      <div class="filter-section">
        <h3>Role</h3>
        <div class="filter-options">
          <label class="filter-option">
            <input type="radio" name="role" value="all" checked onchange="applyFilters()"> All
          </label>
          <label class="filter-option">
            <input type="radio" name="role" value="pi" onchange="applyFilters()"> Clinical Trial PI
          </label>
          <label class="filter-option">
            <input type="radio" name="role" value="author" onchange="applyFilters()"> Publication Author
          </label>
        </div>
      </div>
    </aside>

    <section class="results-section">
      <h2>Results</h2>
      <div class="results-meta" id="results-meta">
        <span id="results-count">Enter a search term to find KOLs</span>
      </div>

      <div id="results-container">
        <div class="empty-state">
          <h3>Search for Key Opinion Leaders</h3>
          <p>Enter a target, disease, or drug name to find researchers and clinical trial investigators in that field.</p>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    Satya Bio - Biotech Intelligence for the Buy Side
  </footer>

  <script>
    let allKOLs = [];
    let currentQuery = '';

    function setSearch(term) {
      document.getElementById('search-input').value = term;
      searchKOLs(new Event('submit'));
    }

    async function searchKOLs(e) {
      e.preventDefault();
      const query = document.getElementById('search-input').value.trim();
      if (!query) return;

      currentQuery = query;
      const btn = document.getElementById('search-btn');
      const container = document.getElementById('results-container');

      btn.disabled = true;
      btn.textContent = 'Searching...';
      container.innerHTML = '<div class="loading"><div class="loading-spinner"></div><p>Searching PubMed and ClinicalTrials.gov...</p></div>';

      try {
        const minPubs = document.getElementById('filter-pubs').value;
        const role = document.querySelector('input[name="role"]:checked').value;

        const params = new URLSearchParams({
          q: query,
          minPubs: minPubs,
          role: role
        });

        const response = await fetch('/api/kols?' + params);
        const data = await response.json();

        allKOLs = data.kols || [];
        renderResults(data);
      } catch (error) {
        container.innerHTML = '<div class="empty-state"><h3>Error</h3><p>Failed to search. Please try again.</p></div>';
      } finally {
        btn.disabled = false;
        btn.textContent = 'Search';
      }
    }

    function applyFilters() {
      if (!currentQuery) return;
      searchKOLs(new Event('submit'));
    }

    function renderResults(data) {
      const container = document.getElementById('results-container');
      const meta = document.getElementById('results-meta');

      if (!data.kols || data.kols.length === 0) {
        container.innerHTML = '<div class="empty-state"><h3>No KOLs Found</h3><p>Try a different search term or adjust your filters.</p></div>';
        meta.innerHTML = '<span id="results-count">No results found</span>';
        return;
      }

      const searchTime = data.searchTime ? (data.searchTime / 1000).toFixed(1) : '?';
      meta.innerHTML = \`
        <span id="results-count">Found <strong>\${data.kols.length}</strong> KOLs for "\${escapeHtml(data.query)}"</span>
        <span class="search-time">\${searchTime}s</span>
      \`;

      let html = '<div class="results-table"><div class="table-wrapper"><table>';
      html += '<thead><tr><th>Name</th><th>Institution</th><th>Email</th><th>Pubs</th><th>Trials</th><th>Role</th></tr></thead>';
      html += '<tbody>';

      data.kols.forEach((kol, idx) => {
        const pubClass = kol.publicationCount >= 5 ? 'count-high' : '';
        const trialClass = kol.trialCount >= 3 ? 'count-high' : '';

        let roleClass = 'role-author';
        let roleText = 'Author';
        if (kol.role === 'PI + Author') {
          roleClass = 'role-both';
          roleText = 'PI + Author';
        } else if (kol.role === 'PI') {
          roleClass = 'role-pi';
          roleText = 'PI';
        }

        const emailCell = kol.email
          ? '<a href="mailto:' + escapeHtml(kol.email) + '" class="email-link">' + escapeHtml(kol.email) + '</a>'
          : '<button class="find-email-btn" onclick="findEmail(' + idx + ', \\'' + escapeHtml(kol.name).replace(/'/g, "\\\\'") + '\\', \\'' + escapeHtml(kol.institution || '').replace(/'/g, "\\\\'") + '\\')">Find</button>';

        html += \`<tr>
          <td><span class="kol-name" onclick="toggleDetails(\${idx})">\${escapeHtml(kol.name)}</span></td>
          <td><span class="institution">\${escapeHtml(kol.institution || '—')}</span></td>
          <td id="email-cell-\${idx}">\${emailCell}</td>
          <td><span class="count-badge \${pubClass}">\${kol.publicationCount}</span></td>
          <td><span class="count-badge \${trialClass}">\${kol.trialCount}</span></td>
          <td><span class="role-badge \${roleClass}">\${roleText}</span></td>
        </tr>\`;

        // Details row
        html += \`<tr class="kol-details-row"><td colspan="6">
          <div class="kol-details" id="details-\${idx}">
            <div class="details-grid">
              <div class="details-section">
                <h4>Publications (\${kol.publicationCount})</h4>
                <ul class="details-list">\`;

        if (kol.publications && kol.publications.length > 0) {
          kol.publications.slice(0, 5).forEach(pub => {
            html += \`<li><a href="https://pubmed.ncbi.nlm.nih.gov/\${pub.pmid}/" target="_blank">\${escapeHtml(truncate(pub.title, 80))}</a><br><small>\${escapeHtml(pub.journal)} (\${pub.year})</small></li>\`;
          });
        } else {
          html += '<li>No publications found</li>';
        }

        html += \`</ul></div>
              <div class="details-section">
                <h4>Clinical Trials (\${kol.trialCount})</h4>
                <ul class="details-list">\`;

        if (kol.trials && kol.trials.length > 0) {
          kol.trials.slice(0, 5).forEach(trial => {
            html += \`<li><a href="https://clinicaltrials.gov/study/\${trial.nctId}" target="_blank">\${trial.nctId}</a>: \${escapeHtml(truncate(trial.title, 60))}<br><small>\${trial.phase} - \${trial.status}</small></li>\`;
          });
        } else {
          html += '<li>No clinical trials found</li>';
        }

        html += '</ul></div></div></div></td></tr>';
      });

      html += '</tbody></table></div></div>';
      container.innerHTML = html;
    }

    function toggleDetails(idx) {
      const details = document.getElementById('details-' + idx);
      if (details) {
        details.classList.toggle('show');
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function truncate(str, len) {
      if (!str) return '';
      return str.length > len ? str.substring(0, len) + '...' : str;
    }

    async function findEmail(idx, name, institution) {
      const cell = document.getElementById('email-cell-' + idx);
      if (!cell) return;

      cell.innerHTML = '<span class="email-searching">...</span>';

      try {
        const params = new URLSearchParams({ name, institution });
        const response = await fetch('/api/kols/email?' + params);
        const data = await response.json();

        if (data.email) {
          cell.innerHTML = '<a href="mailto:' + escapeHtml(data.email) + '" class="email-link">' + escapeHtml(data.email) + '</a>';
          // Update the stored KOL data
          if (allKOLs[idx]) {
            allKOLs[idx].email = data.email;
          }
        } else {
          cell.innerHTML = '<span class="email-none">Not found</span>';
        }
      } catch (error) {
        cell.innerHTML = '<span class="email-none">Error</span>';
      }
    }
  </script>
</body>
</html>`);
  });

  // KOL Finder API
  app.get('/api/kols', async (req: Request, res: Response) => {
    try {
      const query = (req.query.q as string) || '';
      const country = (req.query.country as string) || '';
      const minPubs = parseInt((req.query.minPubs as string) || '0', 10);
      const role = (req.query.role as string) || 'all';

      if (!query) {
        return res.json({ query: '', kols: [], totalKOLs: 0, searchTime: 0 });
      }

      const result = await findKOLsCached(query, {
        country: country || undefined,
        minPublications: minPubs,
        roleFilter: role as 'all' | 'pi' | 'author',
        maxResults: 50,
      });

      res.json(result);
    } catch (error) {
      console.error('KOL search error:', error);
      res.status(500).json({ error: 'Failed to search KOLs' });
    }
  });

  // KOL Email Finder API - search for a single KOL's email
  app.get('/api/kols/email', async (req: Request, res: Response) => {
    try {
      const name = (req.query.name as string) || '';
      const institution = (req.query.institution as string) || '';

      if (!name) {
        return res.status(400).json({ error: 'Name is required' });
      }

      const email = await findEmailBySearch(name, institution);
      res.json({ name, institution, email });
    } catch (error) {
      console.error('Email search error:', error);
      res.status(500).json({ error: 'Failed to search for email' });
    }
  });

  // About Page
  app.get('/about', (_req: Request, res: Response) => {
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>About | Satya Bio</title>
  <meta name="description" content="We're building the intelligence layer for biotech investing.">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --navy: #1a2b3c;
      --navy-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --accent-light: #fef5f3;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --border-light: #eeeeea;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

    /* Header */
    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 68px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.4rem; font-weight: 800; color: var(--navy); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: var(--navy); }
    .nav-cta a { padding: 10px 20px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; font-size: 0.9rem; }

    /* Hero */
    .hero { background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%); padding: 100px 32px; text-align: center; position: relative; overflow: hidden; }
    .hero-bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }
    .circle { position: absolute; border-radius: 50%; opacity: 0.12; }
    .circle-1 { width: 300px; height: 300px; background: linear-gradient(135deg, #fef08a 0%, #fde68a 100%); top: -100px; right: 10%; }
    .circle-2 { width: 200px; height: 200px; background: linear-gradient(135deg, #fef5f3 0%, #fecaca 100%); bottom: -50px; left: 5%; }
    .hero-content { position: relative; z-index: 1; max-width: 700px; margin: 0 auto; }
    .hero h1 { font-family: 'Fraunces', serif; font-size: 3rem; font-weight: 700; color: white; margin-bottom: 20px; }
    .hero p { color: rgba(255,255,255,0.85); font-size: 1.25rem; line-height: 1.6; }

    /* Main Content */
    .main { max-width: 800px; margin: 0 auto; padding: 80px 32px; }

    /* Section */
    .section { margin-bottom: 64px; }
    .section h2 { font-family: 'Fraunces', serif; font-size: 1.75rem; color: var(--navy); margin-bottom: 20px; }
    .section > p { color: var(--text-secondary); font-size: 1.1rem; line-height: 1.8; }

    /* Track List */
    .track-list { margin-top: 24px; display: flex; flex-direction: column; gap: 12px; }
    .track-item { display: flex; align-items: flex-start; gap: 14px; padding: 16px 20px; background: var(--surface); border: 1px solid var(--border-light); border-radius: 12px; }
    .track-icon { width: 8px; height: 8px; background: var(--accent); border-radius: 50%; margin-top: 8px; flex-shrink: 0; }
    .track-text { color: var(--text); font-size: 1rem; font-weight: 500; }

    /* Different List */
    .different-list { margin-top: 24px; display: flex; flex-direction: column; gap: 16px; }
    .different-item { display: flex; align-items: flex-start; gap: 16px; }
    .different-dot { width: 10px; height: 10px; background: var(--accent); border-radius: 50%; flex-shrink: 0; margin-top: 7px; }
    .different-content h4 { font-size: 1rem; font-weight: 600; color: var(--navy); margin-bottom: 4px; }
    .different-content p { font-size: 0.9rem; color: var(--text-secondary); margin: 0; }

    /* CTA Section */
    .cta-section { background: var(--navy); border-radius: 20px; padding: 56px 40px; text-align: center; color: white; }
    .cta-section h2 { font-family: 'Fraunces', serif; font-size: 2rem; margin-bottom: 12px; }
    .cta-section > p { opacity: 0.8; margin-bottom: 32px; }
    .cta-form { display: flex; gap: 12px; max-width: 420px; margin: 0 auto 16px; }
    .cta-form input { flex: 1; padding: 14px 18px; border: none; border-radius: 10px; font-size: 1rem; font-family: inherit; outline: none; }
    .cta-form button { padding: 14px 24px; background: var(--accent); color: white; border: none; border-radius: 10px; font-size: 1rem; font-weight: 700; cursor: pointer; white-space: nowrap; }
    .cta-form button:hover { background: var(--accent-hover); }
    .cta-note { font-size: 0.85rem; opacity: 0.6; }

    /* Footer */
    .footer { background: var(--navy); color: rgba(255,255,255,0.6); padding: 40px 32px; text-align: center; margin-top: 80px; }
    .footer p { font-size: 0.9rem; }

    @media (max-width: 768px) {
      .nav-links { display: none; }
      .hero { padding: 64px 20px; }
      .hero h1 { font-size: 2rem; }
      .hero p { font-size: 1.05rem; }
      .main { padding: 48px 20px; }
      .cta-form { flex-direction: column; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research">Research</a>
        <a href="/about" class="active">About</a>
      </nav>
      <div class="nav-cta">
        <a href="#cta">Request Access</a>
      </div>
    </div>
  </header>

  <section class="hero">
    <div class="hero-bg">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>
    <div class="hero-content">
      <h1>About Satya Bio</h1>
      <p>We're building the intelligence layer for biotech investing</p>
    </div>
  </section>

  <main class="main">
    <section class="section">
      <h2>Our Mission</h2>
      <p>Biotech investing requires synthesizing data from dozens of sources — SEC filings, clinical trials, company presentations, deal announcements. We built Satya Bio to do that synthesis automatically, so investors can focus on what matters: making better decisions.</p>
    </section>

    <section class="section">
      <h2>What We Track</h2>
      <div class="track-list">
        <div class="track-item">
          <div class="track-icon"></div>
          <div class="track-text">60+ public biotech companies with full pipeline coverage</div>
        </div>
        <div class="track-item">
          <div class="track-icon"></div>
          <div class="track-text">200+ drug assets across all clinical stages</div>
        </div>
        <div class="track-item">
          <div class="track-icon"></div>
          <div class="track-text">10+ therapeutic target landscapes</div>
        </div>
        <div class="track-item">
          <div class="track-icon"></div>
          <div class="track-text">$30B+ in licensing and M&A deal value</div>
        </div>
        <div class="track-item">
          <div class="track-icon"></div>
          <div class="track-text">Catalyst tracking with automated date updates</div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>How We're Different</h2>
      <div class="different-list">
        <div class="different-item">
          <div class="different-dot"></div>
          <div class="different-content">
            <h4>Built by biotech investors, for biotech investors</h4>
            <p>We understand the questions you're actually trying to answer</p>
          </div>
        </div>
        <div class="different-item">
          <div class="different-dot"></div>
          <div class="different-content">
            <h4>Updated daily, not quarterly</h4>
            <p>Real-time catalyst tracking and pipeline updates</p>
          </div>
        </div>
        <div class="different-item">
          <div class="different-dot"></div>
          <div class="different-content">
            <h4>Primary source data, not aggregated news</h4>
            <p>SEC filings, ClinicalTrials.gov, FDA databases, company IR pages</p>
          </div>
        </div>
      </div>
    </section>

    <section class="cta-section" id="cta">
      <h2>Request Access</h2>
      <p>Currently in private beta with select funds</p>
      <form class="cta-form" onsubmit="event.preventDefault(); const email = this.querySelector('input').value; if(email) { window.location.href = 'mailto:hello@satyabio.com?subject=Beta%20Access%20Request&body=Email:%20' + encodeURIComponent(email); }">
        <input type="email" placeholder="work@fund.com" required>
        <button type="submit">Request Access</button>
      </form>
      <p class="cta-note">We'll be in touch within 24 hours</p>
    </section>
  </main>

  <footer class="footer">
    <p>© 2026 Satya Bio. Biotech intelligence for the buy side.</p>
  </footer>
</body>
</html>`);
  });

  // Research Hub Page
  app.get('/research', (_req: Request, res: Response) => {
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Research | Satya Bio</title>
  <meta name="description" content="In-depth biotech research reports and analysis.">
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a2b3c;
      --primary-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --accent-light: #fef5f3;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }

    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 72px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 800; color: var(--primary); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.95rem; font-weight: 500; transition: color 0.2s; }
    .nav-links a:hover, .nav-links a.active { color: var(--primary); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-ghost { padding: 10px 18px; color: var(--text-secondary); font-weight: 600; text-decoration: none; }
    .btn-primary { padding: 10px 22px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; transition: all 0.2s; }
    .btn-primary:hover { background: var(--accent-hover); }

    .hero { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); padding: 80px 32px; text-align: center; position: relative; overflow: hidden; }
    .hero-bg { position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }
    .circle { position: absolute; border-radius: 50%; opacity: 0.15; animation: float 20s ease-in-out infinite; }
    .circle-1 { width: 300px; height: 300px; background: linear-gradient(135deg, #fef08a 0%, #fde68a 100%); top: -100px; right: 10%; }
    .circle-2 { width: 200px; height: 200px; background: linear-gradient(135deg, #fef5f3 0%, #fecaca 100%); bottom: -50px; left: 5%; animation-delay: -5s; }
    @keyframes float {
      0%, 100% { transform: translate(0, 0) rotate(0deg); }
      50% { transform: translate(-10px, 20px) rotate(-5deg); }
    }
    .hero-content { position: relative; z-index: 1; }
    .hero h1 { font-family: 'Fraunces', serif; font-size: 3rem; font-weight: 700; color: white; margin-bottom: 16px; }
    .hero p { color: rgba(255,255,255,0.85); font-size: 1.2rem; max-width: 700px; margin: 0 auto; }

    .main { max-width: 1200px; margin: 0 auto; padding: 64px 32px; }

    .section-title { font-family: 'Fraunces', serif; font-size: 1.5rem; color: var(--primary); margin-bottom: 24px; }

    .reports-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; }
    .report-card { background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 28px; transition: all 0.25s; text-decoration: none; color: inherit; display: block; }
    .report-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.08); border-color: var(--accent); }
    .report-badge { display: inline-block; padding: 4px 12px; background: var(--accent-light); color: var(--accent); font-size: 0.75rem; font-weight: 700; border-radius: 20px; text-transform: uppercase; margin-bottom: 16px; }
    .report-badge.new { background: #dcfce7; color: #16a34a; }
    .report-title { font-family: 'Fraunces', serif; font-size: 1.3rem; font-weight: 700; color: var(--primary); margin-bottom: 12px; }
    .report-desc { color: var(--text-secondary); font-size: 0.95rem; margin-bottom: 16px; line-height: 1.6; }
    .report-meta { display: flex; justify-content: space-between; align-items: center; padding-top: 16px; border-top: 1px solid var(--border); }
    .report-date { font-size: 0.85rem; color: var(--text-muted); }
    .report-link { color: var(--accent); font-weight: 600; font-size: 0.9rem; }

    .coming-soon { opacity: 0.6; pointer-events: none; }
    .coming-soon .report-badge { background: var(--bg); color: var(--text-muted); }

    .footer { background: var(--primary); color: rgba(255,255,255,0.7); padding: 48px 32px; text-align: center; margin-top: 64px; }

    @media (max-width: 768px) {
      .nav-links { display: none; }
      .hero { padding: 60px 20px; }
      .hero h1 { font-size: 2rem; }
      .main { padding: 40px 20px; }
      .reports-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research" class="active">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
                <a href="mailto:hello@satyabio.com?subject=Early%20Access%20Request&body=I'd%20like%20to%20request%20early%20access%20to%20Satya%20Bio." class="btn-primary">Get Started</a>
      </div>
    </div>
  </header>

  <section class="hero">
    <div class="hero-bg">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>
    <div class="hero-content">
      <h1>Research Reports</h1>
      <p>In-depth analysis of biotech trends, therapeutic landscapes, and market dynamics</p>
    </div>
  </section>

  <main class="main">
    <h2 class="section-title">Featured Reports</h2>
    <div class="reports-grid">
      <a href="/research/2025-licensing-deals" class="report-card">
        <span class="report-badge new">New</span>
        <h3 class="report-title">2024-2025 Biopharma Licensing Deals</h3>
        <p class="report-desc">Comprehensive analysis of major licensing and partnership deals, including deal terms, valuations, and strategic implications.</p>
        <div class="report-meta">
          <span class="report-date">Updated Jan 2026</span>
          <span class="report-link">Read Report →</span>
        </div>
      </a>

      <a href="/api/report/target/GLP-1/html" class="report-card">
        <span class="report-badge">Target Landscape</span>
        <h3 class="report-title">GLP-1 Competitive Landscape</h3>
        <p class="report-desc">Deep dive into the GLP-1 agonist market including Ozempic, Mounjaro competitors, and emerging oral formulations.</p>
        <div class="report-meta">
          <span class="report-date">Auto-updated</span>
          <span class="report-link">View Landscape →</span>
        </div>
      </a>

      <a href="/api/report/target/TL1A/html" class="report-card">
        <span class="report-badge">Target Landscape</span>
        <h3 class="report-title">TL1A: The Next Big IBD Target</h3>
        <p class="report-desc">Analysis of the emerging TL1A space including Prometheus, Roche/Roivant, and Merck programs for IBD and fibrosis.</p>
        <div class="report-meta">
          <span class="report-date">Auto-updated</span>
          <span class="report-link">View Landscape →</span>
        </div>
      </a>

      <a href="/api/report/target/KRAS/html" class="report-card">
        <span class="report-badge">Target Landscape</span>
        <h3 class="report-title">KRAS Inhibitor Landscape</h3>
        <p class="report-desc">From "undruggable" to approved: tracking G12C inhibitors, emerging G12D programs, and resistance mechanisms.</p>
        <div class="report-meta">
          <span class="report-date">Auto-updated</span>
          <span class="report-link">View Landscape →</span>
        </div>
      </a>

      <div class="report-card coming-soon">
        <span class="report-badge">Coming Soon</span>
        <h3 class="report-title">Q1 2026 Biotech Catalysts Guide</h3>
        <p class="report-desc">Comprehensive guide to major clinical data readouts, PDUFA dates, and conferences in Q1 2026.</p>
        <div class="report-meta">
          <span class="report-date">Coming Feb 2026</span>
          <span class="report-link">Subscribe for Updates</span>
        </div>
      </div>

      <div class="report-card coming-soon">
        <span class="report-badge">Coming Soon</span>
        <h3 class="report-title">ADC Landscape Report</h3>
        <p class="report-desc">Analysis of the antibody-drug conjugate space including approved drugs, pipeline assets, and emerging payloads.</p>
        <div class="report-meta">
          <span class="report-date">Coming Q1 2026</span>
          <span class="report-link">Subscribe for Updates</span>
        </div>
      </div>
    </div>
  </main>

  <footer class="footer">
    <p>© 2026 Satya Bio. Institutional-grade biotech intelligence.</p>
  </footer>
</body>
</html>`);
  });

  // Research Report: 2025 Licensing Deals
  app.get('/research/2025-licensing-deals', (_req: Request, res: Response) => {
    res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>2024–2025 Biopharma Licensing Deals | Satya Bio Research</title>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a2b3c;
      --primary-light: #2d4a5e;
      --accent: #e07a5f;
      --accent-hover: #d06a4f;
      --accent-light: #fef5f3;
      --highlight: #fef08a;
      --bg: #fafaf8;
      --surface: #ffffff;
      --border: #e5e5e0;
      --text: #1a1d21;
      --text-secondary: #5f6368;
      --text-muted: #9aa0a6;
      --success: #22c55e;
      --success-light: #dcfce7;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'DM Sans', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; }

    /* Header */
    .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 32px; height: 72px; position: sticky; top: 0; z-index: 100; }
    .header-inner { max-width: 1200px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; height: 100%; }
    .logo { font-family: 'DM Sans', sans-serif; font-size: 1.5rem; font-weight: 800; color: var(--primary); text-decoration: none; }
    .logo span { color: var(--accent); }
    .nav-links { display: flex; gap: 32px; }
    .nav-links a { color: var(--text-secondary); text-decoration: none; font-size: 0.95rem; font-weight: 500; }
    .nav-links a:hover, .nav-links a.active { color: var(--primary); }
    .nav-cta { display: flex; gap: 12px; }
    .btn-ghost { padding: 10px 18px; color: var(--text-secondary); font-weight: 600; text-decoration: none; }
    .btn-primary { padding: 10px 22px; background: var(--accent); color: white; font-weight: 600; text-decoration: none; border-radius: 8px; }

    /* Report Hero */
    .report-hero { background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%); padding: 64px 32px 80px; }
    .report-hero-inner { max-width: 900px; margin: 0 auto; }
    .report-badge { display: inline-block; padding: 6px 14px; background: rgba(255,255,255,0.15); color: white; font-size: 0.8rem; font-weight: 700; border-radius: 4px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 0.5px; }
    .report-hero h1 { font-family: 'Fraunces', serif; font-size: 2.75rem; font-weight: 700; color: white; margin-bottom: 16px; line-height: 1.2; }
    .report-hero .subtitle { color: rgba(255,255,255,0.85); font-size: 1.2rem; margin-bottom: 32px; max-width: 700px; }
    .report-meta { display: flex; gap: 32px; flex-wrap: wrap; }
    .report-meta-item { color: rgba(255,255,255,0.7); font-size: 0.9rem; }
    .report-meta-item strong { color: white; font-weight: 600; }

    /* Metrics Bar */
    .metrics-bar { background: var(--surface); border-bottom: 1px solid var(--border); padding: 32px; margin-top: -40px; margin-left: 32px; margin-right: 32px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); position: relative; z-index: 10; }
    .metrics-inner { max-width: 900px; margin: 0 auto; display: grid; grid-template-columns: repeat(4, 1fr); gap: 32px; text-align: center; }
    .metric-value { font-family: 'Fraunces', serif; font-size: 2.5rem; font-weight: 700; color: var(--primary); }
    .metric-label { font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }

    /* Main Content */
    .content-wrapper { max-width: 1200px; margin: 0 auto; padding: 48px 32px; display: grid; grid-template-columns: 1fr 300px; gap: 48px; }
    .main-content { min-width: 0; }

    /* Sidebar */
    .sidebar { position: sticky; top: 100px; height: fit-content; }
    .sidebar-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 24px; }
    .sidebar-card h4 { font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }
    .btn-download { display: block; width: 100%; padding: 14px 20px; text-align: center; font-weight: 600; border-radius: 8px; text-decoration: none; margin-bottom: 12px; transition: all 0.2s; }
    .btn-download.primary { background: var(--accent); color: white; }
    .btn-download.primary:hover { background: var(--accent-hover); }
    .btn-download.secondary { background: var(--surface); color: var(--text); border: 2px solid var(--border); }
    .btn-download.secondary:hover { border-color: var(--accent); color: var(--accent); }
    .toc-list { list-style: none; }
    .toc-list li { margin-bottom: 10px; }
    .toc-list a { color: var(--text-secondary); text-decoration: none; font-size: 0.9rem; }
    .toc-list a:hover { color: var(--accent); }
    .related-link { display: block; padding: 12px 0; border-bottom: 1px solid var(--border); color: var(--text); text-decoration: none; font-size: 0.9rem; }
    .related-link:last-child { border-bottom: none; }
    .related-link:hover { color: var(--accent); }

    /* Section Styles */
    .section { margin-bottom: 48px; }
    .section-title { font-family: 'Fraunces', serif; font-size: 1.5rem; font-weight: 700; color: var(--primary); margin-bottom: 20px; }
    .section-title .hl { background: var(--highlight); padding: 0 6px; margin: 0 -3px; }

    /* Insight Cards */
    .insight-card { background: var(--surface); border-left: 4px solid var(--accent); border-radius: 0 12px 12px 0; padding: 24px 28px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .insight-card h4 { font-size: 1rem; font-weight: 700; color: var(--primary); margin-bottom: 8px; }
    .insight-card p { color: var(--text-secondary); font-size: 0.95rem; margin: 0; }

    /* Bar Chart */
    .chart-container { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 28px; margin: 24px 0; }
    .chart-title { font-weight: 700; color: var(--primary); margin-bottom: 20px; }
    .bar-row { display: flex; align-items: center; margin-bottom: 12px; }
    .bar-label { width: 140px; font-size: 0.85rem; color: var(--text-secondary); flex-shrink: 0; }
    .bar-track { flex: 1; height: 32px; background: var(--bg); border-radius: 6px; overflow: hidden; margin-right: 12px; }
    .bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent) 0%, #f4a261 100%); border-radius: 6px; transition: width 0.5s ease; }
    .bar-value { width: 70px; font-size: 0.9rem; font-weight: 700; color: var(--primary); text-align: right; }

    /* Data Table */
    .data-table { width: 100%; border-collapse: collapse; margin: 24px 0; background: var(--surface); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); }
    .data-table th { background: var(--bg); padding: 14px 16px; text-align: left; font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
    .data-table td { padding: 14px 16px; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
    .data-table tr:hover { background: var(--bg); }
    .data-table tr.summary-row { background: var(--primary); color: white; font-weight: 600; }
    .data-table tr.summary-row td { border-bottom: none; }
    .phase-badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .phase-badge.preclinical { background: var(--highlight); color: #854d0e; }
    .phase-badge.phase1 { background: #dbeafe; color: #1e40af; }
    .phase-badge.phase2 { background: #fef3c7; color: #92400e; }
    .phase-badge.phase3 { background: #dcfce7; color: #166534; }
    .phase-badge.approved { background: var(--success-light); color: #166534; }

    /* Footer CTA */
    .footer-cta { background: var(--primary); padding: 64px 32px; text-align: center; }
    .footer-cta h3 { font-family: 'Fraunces', serif; font-size: 1.75rem; color: white; margin-bottom: 12px; }
    .footer-cta p { color: rgba(255,255,255,0.7); margin-bottom: 24px; }
    .footer-cta .btn { padding: 14px 32px; background: var(--accent); color: white; font-weight: 700; text-decoration: none; border-radius: 8px; display: inline-block; }
    .footer-cta .btn:hover { background: var(--accent-hover); }

    /* Footer */
    .footer { background: var(--primary); color: rgba(255,255,255,0.5); padding: 24px 32px; text-align: center; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.1); }

    @media (max-width: 900px) {
      .content-wrapper { grid-template-columns: 1fr; }
      .sidebar { position: static; order: -1; }
      .metrics-inner { grid-template-columns: repeat(2, 1fr); }
      .report-hero h1 { font-size: 2rem; }
    }
    @media (max-width: 600px) {
      .nav-links { display: none; }
      .metrics-inner { grid-template-columns: 1fr 1fr; gap: 20px; }
      .metric-value { font-size: 1.75rem; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">Satya<span>Bio</span></a>
      <nav class="nav-links">
        <a href="/targets">Targets</a>
        <a href="/companies">Companies</a>
        <a href="/kols">KOL Finder</a>
        <a href="/research" class="active">Research</a>
        <a href="/about">About</a>
      </nav>
      <div class="nav-cta">
                <a href="mailto:hello@satyabio.com?subject=Early%20Access%20Request&body=I'd%20like%20to%20request%20early%20access%20to%20Satya%20Bio." class="btn-primary">Get Started</a>
      </div>
    </div>
  </header>

  <section class="report-hero">
    <div class="report-hero-inner">
      <span class="report-badge">Deal Intelligence Report</span>
      <h1>2024–2025 Biopharma Licensing Deals: A Comprehensive Analysis</h1>
      <p class="subtitle">An in-depth analysis of licensing deal structures, valuations, and trends across therapeutic areas, modalities, and development stages.</p>
      <div class="report-meta">
        <div class="report-meta-item"><strong>Published:</strong> January 2026</div>
        <div class="report-meta-item"><strong>Deals Analyzed:</strong> 389</div>
        <div class="report-meta-item"><strong>Total Value:</strong> $383B+</div>
      </div>
    </div>
  </section>

  <div class="metrics-bar">
    <div class="metrics-inner">
      <div class="metric">
        <div class="metric-value">389</div>
        <div class="metric-label">Total Deals</div>
      </div>
      <div class="metric">
        <div class="metric-value">$95M</div>
        <div class="metric-label">Avg Upfront</div>
      </div>
      <div class="metric">
        <div class="metric-value">$985M</div>
        <div class="metric-label">Avg Total Value</div>
      </div>
      <div class="metric">
        <div class="metric-value">34%</div>
        <div class="metric-label">Preclinical Stage</div>
      </div>
    </div>
  </div>

  <div class="content-wrapper">
    <main class="main-content">
      <section class="section" id="summary">
        <h2 class="section-title">Executive <span class="hl">Summary</span></h2>
        <p style="margin-bottom: 20px;">The 2024–2025 biopharma licensing landscape reveals significant shifts in deal-making priorities, with oncology maintaining dominance while cardiometabolic assets command the highest premiums. Our analysis of 389 licensing deals uncovers key patterns in valuation, stage preferences, and therapeutic focus.</p>

        <div class="insight-card">
          <h4>Key Finding #1: Cardiometabolic Commands Premium</h4>
          <p>Cardiometabolic deals average $151M upfront — 37% higher than oncology ($110M) despite oncology's deal volume dominance.</p>
        </div>

        <div class="insight-card">
          <h4>Key Finding #2: Early-Stage Dominance</h4>
          <p>34% of all deals are for preclinical assets, signaling pharma's increasing appetite for early-stage risk in exchange for lower upfronts and greater upside.</p>
        </div>

        <div class="insight-card">
          <h4>Key Finding #3: Platform Deals Rising</h4>
          <p>Multi-target platform deals now represent 18% of total value, up from 11% in 2023, as pharma seeks broader optionality.</p>
        </div>
      </section>

      <section class="section" id="therapeutic">
        <h2 class="section-title">Deals by <span class="hl">Therapeutic Area</span></h2>
        <p style="margin-bottom: 24px;">Average upfront payments vary significantly by therapeutic area, reflecting risk profiles, market sizes, and competitive dynamics.</p>

        <div class="chart-container">
          <div class="chart-title">Average Upfront Payment by Therapeutic Area ($M)</div>
          <div class="bar-row">
            <span class="bar-label">Cardiometabolic</span>
            <div class="bar-track"><div class="bar-fill" style="width: 100%;"></div></div>
            <span class="bar-value">$151M</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">Oncology</span>
            <div class="bar-track"><div class="bar-fill" style="width: 73%;"></div></div>
            <span class="bar-value">$110M</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">Immunology</span>
            <div class="bar-track"><div class="bar-fill" style="width: 66%;"></div></div>
            <span class="bar-value">$99M</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">Neurology</span>
            <div class="bar-track"><div class="bar-fill" style="width: 58%;"></div></div>
            <span class="bar-value">$87M</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">Infectious Disease</span>
            <div class="bar-track"><div class="bar-fill" style="width: 47%;"></div></div>
            <span class="bar-value">$71M</span>
          </div>
          <div class="bar-row">
            <span class="bar-label">Rare Disease</span>
            <div class="bar-track"><div class="bar-fill" style="width: 44%;"></div></div>
            <span class="bar-value">$66M</span>
          </div>
        </div>
      </section>

      <section class="section" id="stage">
        <h2 class="section-title">Deals by <span class="hl">Development Stage</span></h2>

        <table class="data-table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Deal Count</th>
              <th>Avg Upfront</th>
              <th>Avg Total Value</th>
              <th>% of Deals</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><span class="phase-badge preclinical">Preclinical</span></td>
              <td>132</td>
              <td>$45M</td>
              <td>$620M</td>
              <td>34%</td>
            </tr>
            <tr>
              <td><span class="phase-badge phase1">Phase 1</span></td>
              <td>89</td>
              <td>$78M</td>
              <td>$890M</td>
              <td>23%</td>
            </tr>
            <tr>
              <td><span class="phase-badge phase2">Phase 2</span></td>
              <td>97</td>
              <td>$125M</td>
              <td>$1.2B</td>
              <td>25%</td>
            </tr>
            <tr>
              <td><span class="phase-badge phase3">Phase 3</span></td>
              <td>54</td>
              <td>$210M</td>
              <td>$1.8B</td>
              <td>14%</td>
            </tr>
            <tr>
              <td><span class="phase-badge approved">Approved</span></td>
              <td>17</td>
              <td>$340M</td>
              <td>$2.1B</td>
              <td>4%</td>
            </tr>
            <tr class="summary-row">
              <td><strong>Total / Average</strong></td>
              <td><strong>389</strong></td>
              <td><strong>$95M</strong></td>
              <td><strong>$985M</strong></td>
              <td><strong>100%</strong></td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="section" id="methodology">
        <h2 class="section-title">Methodology</h2>
        <p>This analysis includes 389 licensing deals announced between January 2024 and December 2025, sourced from SEC filings, press releases, and proprietary databases. Deals were categorized by therapeutic area, development stage at signing, and deal structure. Platform deals were allocated proportionally across therapeutic areas when applicable.</p>
      </section>
    </main>

    <aside class="sidebar">
      <div class="sidebar-card">
        <h4>Download Report</h4>
        <a href="#" class="btn-download primary">Download PDF</a>
        <a href="#" class="btn-download secondary">Download Excel Data</a>
      </div>

      <div class="sidebar-card">
        <h4>Table of Contents</h4>
        <ul class="toc-list">
          <li><a href="#summary">Executive Summary</a></li>
          <li><a href="#therapeutic">By Therapeutic Area</a></li>
          <li><a href="#stage">By Development Stage</a></li>
          <li><a href="#methodology">Methodology</a></li>
        </ul>
      </div>

      <div class="sidebar-card">
        <h4>Related Reports</h4>
        <a href="/api/report/target/TL1A/html" class="related-link">TL1A Target Landscape →</a>
        <a href="/api/report/target/B7-H3/html" class="related-link">B7-H3 ADC Landscape →</a>
        <a href="/research" class="related-link">All Research →</a>
      </div>
    </aside>
  </div>

  <section class="footer-cta">
    <h3>Want custom analysis?</h3>
    <p>Get bespoke research on specific targets, therapeutic areas, or competitive landscapes.</p>
    <a href="#" class="btn">Contact Us</a>
  </section>

  <footer class="footer">
    <p>© 2026 Satya Bio. All rights reserved.</p>
  </footer>
</body>
</html>`);
  });

  // Health check endpoint
  app.get('/api/health', (_req: Request, res: Response) => {
    const rateLimit = getRateLimitStatus();
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      rateLimit: {
        remaining: rateLimit.remaining,
        limit: RATE_LIMIT_MAX_CALLS,
        resetInMinutes: rateLimit.resetInMinutes
      }
    });
  });

  // Get all XBI companies
  app.get('/api/companies', async (_req: Request, res: Response) => {
    try {
      const companies = await getAllCompanies();
      res.json({
        count: companies.length,
        companies: companies.map(c => ({
          ticker: c.ticker,
          name: c.name,
          marketCap: c.weight ? `$${(c.weight * 100).toFixed(1)}B` : null,
          sector: c.sector,
          stage: c.stage
        }))
      });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Batch analyze multiple tickers
  app.post('/api/analyze/batch', async (req: Request, res: Response) => {
    try {
      const { tickers } = req.body as { tickers: string[] };
      if (!tickers || !Array.isArray(tickers)) {
        res.status(400).json({ error: 'Request body must include "tickers" array' });
        return;
      }

      const results: { ticker: string; status: string; cached?: boolean }[] = [];

      for (let i = 0; i < tickers.length; i++) {
        const ticker = tickers[i].toUpperCase();

        try {
          // Check cache first
          const cached = getCachedAnalysis(ticker);
          if (cached) {
            results.push({ ticker, status: 'cached', cached: true });
            continue;
          }

          // Check rate limit before calling Claude
          if (isRateLimitExceeded()) {
            // Try to get expired cache as fallback
            const expiredCache = getCachedAnalysisIgnoreExpiry(ticker);
            if (expiredCache) {
              console.log(chalk.yellow(`  [Batch] Rate limit reached, using expired cache for ${ticker}`));
              results.push({ ticker, status: 'rate-limited-cached', cached: true });
            } else {
              const { resetInMinutes } = getRateLimitStatus();
              console.log(chalk.red(`  [Batch] Rate limit reached for ${ticker}, no cache available`));
              results.push({ ticker, status: `rate-limited (reset in ${resetInMinutes}m)` });
            }
            continue;
          }

          // Rate limit: wait 10 seconds between API calls (except first)
          if (i > 0) {
            console.log(chalk.gray(`  [Batch] Waiting 10s before analyzing ${ticker}...`));
            await sleep(10000);
          }

          console.log(chalk.cyan(`  [Batch] Analyzing ${ticker} (${i + 1}/${tickers.length})...`));

          // Get filing
          const filings = await getFilings(ticker, 5);
          const filing = filings.find(f => f.form === '10-K' || f.form === '10-K/A');

          if (!filing) {
            results.push({ ticker, status: 'no-10k-filing' });
            continue;
          }

          // Analyze
          const content = await getFilingForAnalysis(filing);
          const llm = getLLMProvider();
          let analysis = await llm.analyze(content, ticker);
          recordApiCall(); // Record the API call for rate limiting
          analysis = postProcessAnalysis(analysis, filing);

          // Save to cache
          saveCachedAnalysis(ticker, filing.filingDate, analysis);

          results.push({ ticker, status: 'analyzed', cached: false });
        } catch (err) {
          results.push({ ticker, status: `error: ${err instanceof Error ? err.message : 'unknown'}` });
        }
      }

      res.json({
        completed: results.length,
        results
      });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Dashboard - HTML view of all analyzed companies
  app.get('/api/dashboard', async (_req: Request, res: Response) => {
    try {
      // Get all cached analyses
      const cachedAnalyses = getAllCachedAnalyses();

      // Get company info for each
      const dashboardData = await Promise.all(
        cachedAnalyses.map(async (cached) => {
          const company = await getCompanyByTicker(cached.ticker);
          const mostAdvancedPhase = getMostAdvancedPhase(cached.analysis.pipeline);
          const keyCatalyst = getKeyCatalyst(cached.analysis.pipeline);

          return {
            ticker: cached.ticker,
            name: company?.name || cached.ticker,
            filingDate: cached.filingDate,
            marketCap: cached.analysis.company.marketCap,
            phase: mostAdvancedPhase,
            runway: cached.analysis.financials.runwayMonths,
            cash: cached.analysis.financials.cash,
            catalyst: keyCatalyst,
            pipelineCount: cached.analysis.pipeline.length
          };
        })
      );

      // Sort by phase (most advanced first)
      dashboardData.sort((a, b) => getPhaseRank(b.phase) - getPhaseRank(a.phase));

      const html = generateDashboardHtml(dashboardData);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // List filings for a ticker
  app.get('/api/filings/:ticker', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();
      const company = await getCompanyByTicker(ticker);
      const filings = await getFilings(ticker, 10);

      res.json({
        ticker,
        company: company?.name || ticker,
        filings: filings.map(f => ({
          form: f.form,
          filingDate: f.filingDate,
          reportDate: f.reportDate,
          url: f.fileUrl
        }))
      });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Analyze a ticker
  app.get('/api/analyze/:ticker', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();
      const useMock = req.query.mock === 'true';
      const form = (req.query.form as string)?.toUpperCase() || '10-K';

      // Get company info
      const company = await getCompanyByTicker(ticker);

      // Fetch filings
      const filings = await getFilings(ticker, 10);
      if (filings.length === 0) {
        res.status(404).json({ error: `No filings found for ${ticker}` });
        return;
      }

      // Find requested filing type
      const filing = filings.find(f => f.form === form || f.form === `${form}/A`);
      if (!filing) {
        res.status(404).json({
          error: `No ${form} filing found for ${ticker}`,
          availableFilings: filings.slice(0, 5).map(f => ({ form: f.form, date: f.filingDate }))
        });
        return;
      }

      let analysis: AnalysisResult;
      let fromCache = false;

      if (useMock) {
        // Return mock data
        analysis = getMockAnalysis(ticker);
      } else {
        // Check cache first
        const cached = getCachedAnalysis(ticker);
        if (cached) {
          console.log(chalk.green(`  [Cache] Using cached analysis for ${ticker}`));
          analysis = cached.analysis;
          fromCache = true;
        } else {
          // Check rate limit before calling Claude
          if (isRateLimitExceeded()) {
            // Try to get expired cache as fallback
            const expiredCache = getCachedAnalysisIgnoreExpiry(ticker);
            if (expiredCache) {
              console.log(chalk.yellow(`  [Rate Limit] Using expired cache for ${ticker}`));
              analysis = expiredCache.analysis;
              fromCache = true;
            } else {
              const { resetInMinutes } = getRateLimitStatus();
              res.status(429).json({
                error: 'Rate limit reached, try again later',
                resetInMinutes
              });
              return;
            }
          } else {
            // Fetch filing content and analyze
            console.log(chalk.yellow(`  [API] Running Claude analysis for ${ticker}...`));
            const content = await getFilingForAnalysis(filing);
            const llm = getLLMProvider();
            analysis = await llm.analyze(content, ticker);
            recordApiCall(); // Record the API call for rate limiting

            // Post-process to fix common LLM issues
            analysis = postProcessAnalysis(analysis, filing);

            // Save to cache
            saveCachedAnalysis(ticker, filing.filingDate, analysis);
          }
        }
      }

      // Remove rawResponse to reduce response size
      const { rawResponse, ...cleanAnalysis } = analysis;

      res.json({
        ticker,
        company: company?.name || ticker,
        filing: {
          form: filing.form,
          filingDate: filing.filingDate,
          reportDate: filing.reportDate,
          url: filing.fileUrl
        },
        analysis: cleanAnalysis,
        provider: useMock ? 'mock' : getConfig().llmProvider,
        cached: fromCache,
        mock: useMock
      });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // HTML Report endpoint
  app.get('/api/report/:ticker', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();
      const useMock = req.query.mock === 'true';

      // Get company info
      const company = await getCompanyByTicker(ticker);

      // Check cache first for instant loading
      const cached = getCachedAnalysis(ticker);
      if (cached && !useMock) {
        console.log(chalk.green(`  [Cache] Using cached analysis for ${ticker}`));
        const html = generateHtmlReport(
          ticker,
          company?.name || ticker,
          { form: '10-K', filingDate: cached.filingDate, reportDate: cached.filingDate, fileUrl: '' },
          cached.analysis
        );
        res.setHeader('Content-Type', 'text/html');
        res.send(html);
        return;
      }

      // Fetch filings
      const filings = await getFilings(ticker, 10);
      if (filings.length === 0) {
        res.status(404).send(`<h1>No filings found for ${ticker}</h1>`);
        return;
      }

      const filing = filings.find(f => f.form === '10-K' || f.form === '10-K/A') || filings[0];

      let analysis: AnalysisResult;
      if (useMock) {
        analysis = getMockAnalysis(ticker);
      } else {
        // Check rate limit before calling Claude
        if (isRateLimitExceeded()) {
          // Try to get expired cache as fallback
          const expiredCache = getCachedAnalysisIgnoreExpiry(ticker);
          if (expiredCache) {
            console.log(chalk.yellow(`  [Rate Limit] Using expired cache for ${ticker}`));
            analysis = expiredCache.analysis;
          } else {
            const { resetInMinutes } = getRateLimitStatus();
            res.status(429).send(`<h1>Rate limit reached</h1><p>Try again in ${resetInMinutes} minutes.</p>`);
            return;
          }
        } else {
          console.log(chalk.yellow(`  [API] Running Claude analysis for ${ticker}...`));
          const content = await getFilingForAnalysis(filing);
          const llm = getLLMProvider();
          analysis = await llm.analyze(content, ticker);
          recordApiCall(); // Record the API call for rate limiting
          analysis = postProcessAnalysis(analysis, filing);

          // Save to cache for next time
          saveCachedAnalysis(ticker, filing.filingDate, analysis);
        }
      }

      const html = generateHtmlReport(ticker, company?.name || ticker, filing, analysis);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // Search companies
  app.get('/api/search', async (req: Request, res: Response) => {
    try {
      const query = req.query.q as string;
      if (!query) {
        res.status(400).json({ error: 'Missing query parameter: q' });
        return;
      }

      const results = await searchCompanies(query);
      res.json({ query, results });
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Therapeutic Landscape Dashboard
  app.get('/api/landscape/:condition/full', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      console.log(chalk.cyan(`  [Landscape] Building dashboard for "${condition}"...`));

      const data = await getLandscapeData(condition);
      const html = generateLandscapeHtml(data);

      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // Landscape CSV Export
  app.get('/api/landscape/:condition/csv', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      const data = await getLandscapeData(condition);
      const csv = generateLandscapeCSV(data);

      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="landscape-${condition.replace(/\s+/g, '-')}.csv"`);
      res.send(csv);
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Landscape JSON API
  app.get('/api/landscape/:condition/json', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      const data = await getLandscapeData(condition);
      res.json(data);
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Molecules Landscape API
  app.get('/api/landscape/:condition/molecules', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      const maxTrials = parseInt(req.query.maxTrials as string) || 500;

      console.log(chalk.cyan(`  [Molecules] Fetching molecules for "${condition}"...`));

      // Fetch trials from ClinicalTrials.gov
      const trials = await searchTrialsByCondition(condition, { maxResults: maxTrials });
      console.log(chalk.gray(`  [Molecules] Found ${trials.length} trials, extracting molecules...`));

      // Extract molecules from trials
      const molecules = extractMoleculesFromTrials(trials);
      console.log(chalk.green(`  [Molecules] Extracted ${molecules.length} unique molecules`));

      // Sort by highest phase (descending) then by trial count (descending)
      molecules.sort((a, b) => {
        const phaseDiff = getMoleculePhaseRank(b.highestPhase) - getMoleculePhaseRank(a.highestPhase);
        if (phaseDiff !== 0) return phaseDiff;
        return b.trialCount - a.trialCount;
      });

      // Format response
      const response = {
        condition,
        totalTrials: trials.length,
        totalMolecules: molecules.length,
        fetchedAt: new Date().toISOString(),
        molecules: molecules.map(mol => ({
          name: mol.name,
          aliases: mol.aliases.slice(0, 3), // Limit aliases for readability
          mechanism: mol.mechanism,
          target: mol.target,
          type: mol.type,
          sponsor: mol.sponsors[0] || 'Unknown',
          allSponsors: mol.sponsors,
          highestPhase: mol.highestPhase,
          trialCount: mol.trialCount,
          activeTrialCount: mol.activeTrialCount,
          leadTrialNctId: mol.leadTrialId,
          conditions: mol.conditions.slice(0, 5), // Limit conditions
        }))
      };

      res.json(response);
    } catch (error) {
      console.error(chalk.red(`  [Molecules] Error: ${error instanceof Error ? error.message : 'Unknown'}`));
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Molecules HTML View
  app.get('/api/landscape/:condition/molecules/html', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      const maxTrials = parseInt(req.query.maxTrials as string) || 500;

      console.log(chalk.cyan(`  [Molecules] Building HTML view for "${condition}"...`));

      // Fetch trials from ClinicalTrials.gov
      const trials = await searchTrialsByCondition(condition, { maxResults: maxTrials });

      // Extract molecules from trials
      const molecules = extractMoleculesFromTrials(trials);

      // Sort by highest phase then trial count
      molecules.sort((a, b) => {
        const phaseDiff = getMoleculePhaseRank(b.highestPhase) - getMoleculePhaseRank(a.highestPhase);
        if (phaseDiff !== 0) return phaseDiff;
        return b.trialCount - a.trialCount;
      });

      const html = generateMoleculesHtml(condition, trials.length, molecules);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // ============================================
  // Trial Results Endpoints
  // ============================================

  // Trial Results JSON API
  app.get('/api/trial/:nctId/results', async (req: Request, res: Response) => {
    try {
      const nctId = (req.params.nctId as string).toUpperCase();

      if (!nctId.startsWith('NCT')) {
        res.status(400).json({ error: 'Invalid NCT ID format. Expected format: NCT########' });
        return;
      }

      console.log(chalk.cyan(`  [Trial] Fetching results for ${nctId}...`));

      const data = await getFullTrialData(nctId);

      if (!data) {
        res.status(404).json({ error: `Trial ${nctId} not found or has no data` });
        return;
      }

      if (!data.hasResults) {
        res.status(200).json({
          ...data,
          message: 'Trial found but no results have been posted yet',
        });
        return;
      }

      res.json(data);
    } catch (error) {
      console.error(chalk.red(`  [Trial] Error: ${error instanceof Error ? error.message : 'Unknown'}`));
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Trial Results HTML View
  app.get('/api/trial/:nctId/results/html', async (req: Request, res: Response) => {
    try {
      const nctId = (req.params.nctId as string).toUpperCase();

      if (!nctId.startsWith('NCT')) {
        res.status(400).send('<h1>Error</h1><p>Invalid NCT ID format. Expected: NCT########</p>');
        return;
      }

      console.log(chalk.cyan(`  [Trial] Building HTML report for ${nctId}...`));

      const data = await getFullTrialData(nctId);

      if (!data) {
        res.status(404).send(`<h1>Not Found</h1><p>Trial ${nctId} not found</p>`);
        return;
      }

      const html = generateTrialResultsHtml(data);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // Trial Comparison Endpoint
  app.get('/api/compare-trials', async (req: Request, res: Response) => {
    try {
      const nctsParam = req.query.ncts as string;

      if (!nctsParam) {
        res.status(400).json({
          error: 'Missing required parameter: ncts',
          example: '/api/compare-trials?ncts=NCT02819635,NCT03518086'
        });
        return;
      }

      const nctIds = nctsParam.split(',').map(id => id.trim().toUpperCase());

      if (nctIds.length < 2) {
        res.status(400).json({ error: 'At least 2 NCT IDs required for comparison' });
        return;
      }

      if (nctIds.length > 5) {
        res.status(400).json({ error: 'Maximum 5 trials can be compared at once' });
        return;
      }

      console.log(chalk.cyan(`  [Compare] Comparing ${nctIds.length} trials: ${nctIds.join(', ')}...`));

      const comparison = await compareTrials(nctIds);

      if (comparison.trials.length === 0) {
        res.status(404).json({ error: 'No trial data found for the provided NCT IDs' });
        return;
      }

      res.json(comparison);
    } catch (error) {
      console.error(chalk.red(`  [Compare] Error: ${error instanceof Error ? error.message : 'Unknown'}`));
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Trial Comparison HTML View
  app.get('/api/compare-trials/html', async (req: Request, res: Response) => {
    try {
      const nctsParam = req.query.ncts as string;

      if (!nctsParam) {
        res.status(400).send('<h1>Error</h1><p>Missing required parameter: ncts</p><p>Example: /api/compare-trials/html?ncts=NCT02819635,NCT03518086</p>');
        return;
      }

      const nctIds = nctsParam.split(',').map(id => id.trim().toUpperCase());

      if (nctIds.length < 2 || nctIds.length > 5) {
        res.status(400).send('<h1>Error</h1><p>Provide 2-5 NCT IDs for comparison</p>');
        return;
      }

      console.log(chalk.cyan(`  [Compare] Building comparison HTML for ${nctIds.join(', ')}...`));

      const comparison = await compareTrials(nctIds);

      if (comparison.trials.length === 0) {
        res.status(404).send('<h1>Not Found</h1><p>No trial data found</p>');
        return;
      }

      const html = generateTrialComparisonHtml(comparison);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // ============================================
  // Patent/Exclusivity Endpoints
  // NOTE: Condition routes MUST come before :drugName routes
  // to avoid Express matching "condition" as a drug name
  // ============================================

  // Patents by Condition JSON
  app.get('/api/patents/condition/:condition', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      console.log(chalk.cyan(`  [Patents] Finding patents for "${condition}" drugs...`));

      const profiles = await getPatentsByCondition(condition);
      res.json({
        condition,
        drugCount: profiles.length,
        profiles,
        fetchedAt: new Date().toISOString(),
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Patents by Condition HTML (Timeline)
  app.get('/api/patents/condition/:condition/html', async (req: Request, res: Response) => {
    try {
      const condition = decodeURIComponent(req.params.condition as string);
      console.log(chalk.cyan(`  [Patents] Building patent timeline for "${condition}"...`));

      const profiles = await getPatentsByCondition(condition);
      const html = generatePatentTimelineHtml(condition, profiles);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // Patent Profile JSON (must be after /condition/ routes)
  app.get('/api/patents/:drugName', async (req: Request, res: Response) => {
    try {
      const drugName = decodeURIComponent(req.params.drugName as string);
      console.log(chalk.cyan(`  [Patents] Looking up "${drugName}"...`));

      const profile = await getDrugPatentProfile(drugName);
      if (!profile) {
        res.status(404).json({ error: `No FDA approval found for "${drugName}"` });
        return;
      }

      res.json(profile);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Patent Profile HTML (must be after /condition/ routes)
  app.get('/api/patents/:drugName/html', async (req: Request, res: Response) => {
    try {
      const drugName = decodeURIComponent(req.params.drugName as string);
      console.log(chalk.cyan(`  [Patents] Building HTML for "${drugName}"...`));

      const profile = await getDrugPatentProfile(drugName);
      if (!profile) {
        res.status(404).send(`<h1>Not Found</h1><p>No FDA approval found for "${drugName}"</p>`);
        return;
      }

      const html = generatePatentProfileHtml(profile);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // ============================================
  // Target Report Routes
  // ============================================

  // Target Report - JSON
  app.get('/api/report/target/:target', async (req: Request, res: Response) => {
    try {
      const target = decodeURIComponent(req.params.target as string);
      console.log(chalk.cyan(`  [Report] Generating JSON report for "${target}"...`));

      const report = await generateTargetReport(target);
      res.json(report);
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Target Report - Excel Download
  app.get('/api/report/target/:target/excel', async (req: Request, res: Response) => {
    try {
      const target = decodeURIComponent(req.params.target as string);
      console.log(chalk.cyan(`  [Report] Generating Excel for "${target}"...`));

      const report = await generateTargetReport(target);
      const buffer = await generateExcel(report);

      const filename = `${target.replace(/[^a-zA-Z0-9]/g, '_')}_Report.xlsx`;
      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      res.send(buffer);
    } catch (error) {
      res.status(500).json({
        error: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  });

  // Target Report - HTML
  app.get('/api/report/target/:target/html', async (req: Request, res: Response) => {
    try {
      const target = decodeURIComponent(req.params.target as string);
      const forceRefresh = req.query.refresh === 'true';

      if (forceRefresh) {
        console.log(chalk.yellow(`  [Report] Force refresh requested for "${target}"`));
      }
      console.log(chalk.cyan(`  [Report] Generating HTML report for "${target}"...`));

      const report = await generateTargetReport(target, { forceRefresh });
      const trialAnalytics = getTrialAnalytics(report.trials);
      const targetAnalysis = getTargetAnalysis(target);

      const html = generateTargetReportHtml(report, trialAnalytics, targetAnalysis);
      res.setHeader('Content-Type', 'text/html');
      res.send(html);
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // ============================================
  // Company Research Module
  // ============================================

  // Company Profile - JSON
  app.get('/api/company/:ticker', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();

      if (ticker === 'ARWR') {
        res.json(getARWRProfile());
      } else {
        res.status(404).json({ error: `Company profile not found for ${ticker}` });
      }
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Company Pipeline - JSON
  app.get('/api/company/:ticker/pipeline', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();

      if (ticker === 'ARWR') {
        res.json(getARWRPipeline());
      } else {
        res.status(404).json({ error: `Pipeline not found for ${ticker}` });
      }
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Company Catalysts - JSON
  app.get('/api/company/:ticker/catalysts', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();

      if (ticker === 'ARWR') {
        res.json(getARWRCatalysts());
      } else {
        res.status(404).json({ error: `Catalysts not found for ${ticker}` });
      }
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Company Presentations - JSON
  app.get('/api/company/:ticker/presentations', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();

      if (ticker === 'ARWR') {
        res.json(getARWRPresentations());
      } else {
        res.status(404).json({ error: `Presentations not found for ${ticker}` });
      }
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Company Profile - HTML Report
  app.get('/api/company/:ticker/html', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();

      if (ticker === 'ARWR') {
        const profile = getARWRProfile();
        const html = generateCompanyReportHtml(profile);
        res.setHeader('Content-Type', 'text/html');
        res.send(html);
      } else {
        res.status(404).send(`<h1>Company Not Found</h1><p>No profile available for ${ticker}</p>`);
      }
    } catch (error) {
      res.status(500).send(`<h1>Error</h1><p>${error instanceof Error ? error.message : 'Unknown error'}</p>`);
    }
  });

  // Scrape IR Documents (refresh)
  app.get('/api/company/:ticker/refresh', async (req: Request, res: Response) => {
    try {
      const ticker = (req.params.ticker as string).toUpperCase();

      if (!isTickerSupported(ticker)) {
        res.status(404).json({ error: `IR scraping not configured for ${ticker}` });
        return;
      }

      console.log(chalk.cyan(`  [Company] Scraping IR documents for ${ticker}...`));
      const result = await scrapeIRDocuments(ticker);

      res.json({
        ticker,
        documentsFound: result.totalDocuments,
        documentsByYear: result.documentsByYear,
        scrapedAt: result.scrapedAt,
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
    }
  });

  // Start server
  app.listen(port, () => {
    console.log('');
    console.log(chalk.green.bold('Server running!'));
    console.log('');
    console.log(chalk.white('API Endpoints:'));
    console.log(chalk.gray(`  GET  /api/health`));
    console.log(chalk.gray(`  GET  /api/companies`));
    console.log(chalk.gray(`  GET  /api/filings/:ticker`));
    console.log(chalk.gray(`  GET  /api/analyze/:ticker`));
    console.log(chalk.gray(`  POST /api/analyze/batch`));
    console.log('');
    console.log(chalk.cyan('HTML Views:'));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/dashboard`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/report/MRNA`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/landscape/ulcerative%20colitis/full`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/landscape/ulcerative%20colitis/molecules/html`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/trial/NCT02819635/results/html`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/compare-trials/html?ncts=NCT02819635,NCT03518086`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/patents/rinvoq/html`));
    console.log(chalk.cyan(`  GET  http://localhost:${port}/api/patents/condition/ulcerative%20colitis/html`));
    console.log('');
    console.log(chalk.gray('API Endpoints (JSON):'));
    console.log(chalk.gray(`  GET  /api/landscape/:condition/molecules`));
    console.log(chalk.gray(`  GET  /api/trial/:nctId/results`));
    console.log(chalk.gray(`  GET  /api/compare-trials?ncts=NCT1,NCT2`));
    console.log(chalk.gray(`  GET  /api/patents/:drugName`));
    console.log(chalk.gray(`  GET  /api/patents/condition/:condition`));
    console.log('');
    console.log(chalk.magenta('Pharma Intelligence:'));
    console.log(chalk.magenta(`  GET  http://localhost:${port}/api/pharma`));
    console.log(chalk.magenta(`  GET  http://localhost:${port}/api/pharma/MRK/html`));
    console.log(chalk.magenta(`  GET  http://localhost:${port}/api/pharma/MRK`));
    console.log(chalk.magenta(`  GET  http://localhost:${port}/api/pharma/catalysts`));
    console.log(chalk.magenta(`  GET  http://localhost:${port}/api/pharma/compare?a=MRK&b=PFE`));
    console.log(chalk.magenta(`  GET  http://localhost:${port}/api/pharma/bd-fit?target=MRK&area=oncology&modality=ADC`));
    console.log('');
    console.log(chalk.blue('Company Research:'));
    console.log(chalk.blue(`  GET  http://localhost:${port}/api/company/ARWR/html`));
    console.log(chalk.blue(`  GET  http://localhost:${port}/api/company/ARWR`));
    console.log(chalk.blue(`  GET  http://localhost:${port}/api/company/ARWR/pipeline`));
    console.log(chalk.blue(`  GET  http://localhost:${port}/api/company/ARWR/catalysts`));
    console.log(chalk.blue(`  GET  http://localhost:${port}/api/company/ARWR/presentations`));
    console.log(chalk.blue(`  GET  http://localhost:${port}/api/company/ARWR/refresh`));
    console.log('');
    console.log(chalk.gray(`Cache: ${CACHE_DIR}`));
    console.log('');
    console.log(chalk.yellow('Press Ctrl+C to stop'));
  });
}

// ============================================
// Post-processing (duplicated from analyze.ts for server use)
// ============================================

function postProcessAnalysis(analysis: AnalysisResult, filing: { filingDate: string }): AnalysisResult {
  const cleaned = JSON.parse(JSON.stringify(analysis)) as AnalysisResult;
  cleaned.pipeline = deduplicatePipeline(cleaned.pipeline);
  cleaned.financials = validateFinancials(cleaned.financials, filing);
  return cleaned;
}

function deduplicatePipeline(pipeline: PipelineItem[]): PipelineItem[] {
  const drugMap = new Map<string, PipelineItem>();

  for (const item of pipeline) {
    const drugKey = item.drug.toLowerCase().trim();
    const existing = drugMap.get(drugKey);

    if (!existing) {
      drugMap.set(drugKey, item);
    } else {
      const existingScore = scoreEntry(existing);
      const newScore = scoreEntry(item);

      if (newScore > existingScore ||
          (newScore === existingScore && getPhaseRank(item.phase) > getPhaseRank(existing.phase))) {
        drugMap.set(drugKey, item);
      }
    }
  }

  return Array.from(drugMap.values());
}

function scoreEntry(item: PipelineItem): number {
  let score = 0;
  if (item.drug) score += 1;
  if (item.phase) score += 1;
  if (item.indication) score += 1;
  if (item.status) score += 2;
  if (item.catalyst) score += 2;
  return score;
}

function getPhaseRank(phase: string): number {
  const p = phase.toLowerCase();
  if (p.includes('approved') || p.includes('marketed')) return 100;
  if (p.includes('bla') || p.includes('nda')) return 90;
  if (p.includes('3')) return 70;
  if (p.includes('2/3')) return 60;
  if (p.includes('2')) return 50;
  if (p.includes('1/2')) return 40;
  if (p.includes('1')) return 30;
  if (p.includes('preclinical') || p.includes('pre-clinical')) return 10;
  return 0;
}

interface ValidatedFinancials {
  cash: string | null;
  cashDate: string | null;
  quarterlyBurnRate: string | null;
  runwayMonths: number | null;
  revenue: string | null;
  revenueSource: string | null;
  dataWarning?: string;
}

function validateFinancials(financials: any, filing: { filingDate: string }): ValidatedFinancials {
  const validated = { ...financials } as ValidatedFinancials;
  const warnings: string[] = [];
  const filingYear = new Date(filing.filingDate).getFullYear();

  if (validated.cashDate) {
    const yearMatch = validated.cashDate.match(/20\d{2}/);
    if (yearMatch) {
      const cashYear = parseInt(yearMatch[0]);
      if (filingYear - cashYear > 1) {
        warnings.push(`Cash date (${cashYear}) may be outdated for ${filingYear} filing`);
      }
    }
  }

  if (validated.runwayMonths !== null) {
    if (validated.runwayMonths > 120) {
      warnings.push('Runway >10 years seems unrealistic');
    } else if (validated.runwayMonths < 0) {
      warnings.push('Negative runway detected');
      validated.runwayMonths = null;
    }
  }

  if (warnings.length > 0) {
    validated.dataWarning = warnings.join('; ');
  }

  return validated;
}

// ============================================
// Mock data
// ============================================

function getMockAnalysis(ticker: string): AnalysisResult {
  return {
    company: {
      name: `${ticker} Inc.`,
      ticker: ticker,
      marketCap: '$18.5B',
      employees: 5200
    },
    analystSummary: `${ticker} is a clinical-stage biotechnology company focused on developing novel mRNA therapeutics for infectious diseases and oncology. The company has a diversified pipeline with lead assets in Phase 3 trials. Strong cash position provides runway through 2026, though burn rate has increased due to expanded clinical programs. Key catalyst: Phase 3 data readout expected Q2 2025.`,
    financials: {
      cash: '$4.2B',
      cashDate: 'Dec 31, 2024',
      quarterlyBurnRate: '$380M',
      runwayMonths: 28,
      revenue: '$1.8B',
      revenueSource: 'Product sales (COVID-19 vaccine)'
    },
    pipeline: [
      { drug: 'mRNA-1283', indication: 'COVID-19 (next-gen)', phase: 'Phase 3', status: 'Enrollment complete', catalyst: 'Data Q2 2025' },
      { drug: 'mRNA-1345', indication: 'RSV Vaccine', phase: 'Approved', status: 'FDA approved May 2024', catalyst: 'EU approval pending' },
      { drug: 'mRNA-4157', indication: 'Melanoma (adjuvant)', phase: 'Phase 3', status: 'Partnered with Merck', catalyst: 'Pivotal data H2 2025' },
      { drug: 'mRNA-1893', indication: 'Zika Vaccine', phase: 'Phase 2', status: 'Dose optimization', catalyst: 'Phase 3 initiation 2025' },
      { drug: 'mRNA-3927', indication: 'Propionic Acidemia', phase: 'Phase 1/2', status: 'Rare disease orphan drug', catalyst: 'Interim data Q3 2025' }
    ],
    fdaInteractions: [
      'Breakthrough Therapy designation granted for mRNA-4157 in melanoma',
      'Fast Track designation for mRNA-3927 in propionic acidemia',
      'Pre-BLA meeting completed for next-gen COVID vaccine'
    ],
    partnerships: [
      { partner: 'Merck', type: 'Development', value: 'Up to $950M + royalties', details: 'Collaboration on personalized cancer vaccines using mRNA-4157' },
      { partner: 'Vertex', type: 'Research', value: '$75M upfront', details: 'Cystic fibrosis mRNA therapeutics development' },
      { partner: 'BARDA', type: 'Government', value: '$1.3B contract', details: 'Pandemic preparedness and vaccine stockpile' }
    ],
    risks: [
      'Revenue concentration: 85% from COVID-19 vaccine which faces declining demand',
      'Competition: Multiple mRNA competitors advancing similar programs',
      'Manufacturing capacity constraints may delay commercial scale-up',
      'Patent litigation ongoing with CureVac and Arbutus',
      'Regulatory uncertainty around annual vaccine reformulation requirements'
    ],
    recentEvents: [
      'Q4 2024 revenue beat estimates by 12%, driven by updated COVID booster',
      'Announced $3B share repurchase program in January 2025',
      'Expanded manufacturing facility in Melbourne, Australia',
      'Phase 2 flu/COVID combo vaccine showed positive immunogenicity data',
      'CEO highlighted plans for 10+ Phase 3 programs by 2026'
    ]
  };
}

// ============================================
// HTML Report Generator
// ============================================

interface Filing {
  form: string;
  filingDate: string;
  reportDate: string;
  fileUrl: string;
}

function generateHtmlReport(
  ticker: string,
  companyName: string,
  filing: Filing,
  analysis: AnalysisResult
): string {
  const timestamp = new Date().toISOString();
  const filingYear = filing.reportDate ? new Date(filing.reportDate).getFullYear() : '';

  // Get runway indicator
  const runway = analysis.financials.runwayMonths;
  let runwayIndicator = '';
  let runwayClass = '';
  if (runway !== null) {
    if (runway >= 24) {
      runwayIndicator = '🟢';
      runwayClass = 'runway-good';
    } else if (runway >= 12) {
      runwayIndicator = '🟡';
      runwayClass = 'runway-moderate';
    } else {
      runwayIndicator = '🔴';
      runwayClass = 'runway-low';
    }
  }

  // Sort pipeline by phase
  const sortedPipeline = [...analysis.pipeline].sort((a, b) => {
    return getPhaseRank(b.phase) - getPhaseRank(a.phase);
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${ticker} Analysis | Satya Bio</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-300: #d1d5db;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .container {
      max-width: 1100px;
      margin: 0 auto;
      padding: 2rem;
    }

    /* Header */
    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
      border-radius: 12px;
      margin-bottom: 2rem;
    }

    .header-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .company-name {
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 0.25rem;
    }

    .ticker-badge {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      font-size: 1.25rem;
      font-weight: 600;
      margin-left: 1rem;
    }

    .filing-info {
      font-size: 0.95rem;
      opacity: 0.9;
      margin-top: 0.5rem;
    }

    .sec-link {
      color: white;
      text-decoration: underline;
      opacity: 0.9;
    }

    .sec-link:hover {
      opacity: 1;
    }

    .satya-logo {
      font-size: 1.5rem;
      font-weight: 700;
      opacity: 0.9;
    }

    /* Executive Summary */
    .summary-box {
      background: white;
      border: 1px solid var(--gray-200);
      border-left: 4px solid var(--primary);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }

    .summary-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--primary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;
    }

    .summary-text {
      font-size: 1.1rem;
      color: var(--gray-700);
      line-height: 1.7;
    }

    .key-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--gray-200);
    }

    .stat-item {
      text-align: center;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--gray-900);
    }

    .stat-label {
      font-size: 0.75rem;
      color: var(--gray-500);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* Cards */
    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .card-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card-icon {
      font-size: 1.25rem;
    }

    /* Pipeline Table */
    .pipeline-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }

    .pipeline-table th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      border-bottom: 2px solid var(--gray-200);
      font-weight: 600;
      color: var(--gray-700);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .pipeline-table td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    .pipeline-table tr:hover {
      background: var(--gray-50);
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-preclinical { background: var(--gray-100); color: var(--gray-500); }

    .drug-name {
      font-weight: 600;
      color: var(--gray-900);
    }

    .catalyst-tag {
      display: inline-block;
      background: #fef3c7;
      color: #92400e;
      padding: 0.125rem 0.375rem;
      border-radius: 4px;
      font-size: 0.75rem;
      margin-top: 0.25rem;
    }

    /* Financials */
    .financials-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
    }

    .financial-item {
      padding: 1rem;
      background: var(--gray-50);
      border-radius: 8px;
    }

    .financial-label {
      font-size: 0.75rem;
      color: var(--gray-500);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.25rem;
    }

    .financial-value {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--gray-900);
    }

    .financial-detail {
      font-size: 0.875rem;
      color: var(--gray-500);
      margin-top: 0.25rem;
    }

    .runway-good .financial-value { color: var(--success); }
    .runway-moderate .financial-value { color: var(--warning); }
    .runway-low .financial-value { color: var(--danger); }

    /* FDA & Partnerships */
    .fda-list, .risk-list {
      list-style: none;
    }

    .fda-list li, .risk-list li {
      padding: 0.75rem 0;
      border-bottom: 1px solid var(--gray-100);
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
    }

    .fda-list li:last-child, .risk-list li:last-child {
      border-bottom: none;
    }

    .fda-icon {
      color: var(--primary);
      font-size: 1.25rem;
    }

    .risk-icon {
      color: var(--warning);
    }

    .partnership-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }

    .partnership-card {
      background: var(--gray-50);
      border-radius: 8px;
      padding: 1rem;
    }

    .partner-name {
      font-weight: 600;
      color: var(--gray-900);
      font-size: 1.1rem;
    }

    .partner-type {
      display: inline-block;
      background: var(--gray-200);
      color: var(--gray-700);
      padding: 0.125rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      margin-left: 0.5rem;
    }

    .partner-value {
      color: var(--success);
      font-weight: 600;
      font-size: 1.1rem;
      margin: 0.5rem 0;
    }

    .partner-details {
      font-size: 0.875rem;
      color: var(--gray-500);
    }

    /* Events */
    .events-list {
      list-style: none;
    }

    .events-list li {
      padding: 0.5rem 0;
      padding-left: 1.5rem;
      position: relative;
      border-left: 2px solid var(--gray-200);
      margin-left: 0.5rem;
    }

    .events-list li::before {
      content: '';
      position: absolute;
      left: -5px;
      top: 0.75rem;
      width: 8px;
      height: 8px;
      background: var(--secondary);
      border-radius: 50%;
    }

    /* Collapsible */
    .collapsible-header {
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .collapsible-header::after {
      content: '▼';
      font-size: 0.75rem;
      transition: transform 0.2s;
    }

    .collapsible.collapsed .collapsible-header::after {
      transform: rotate(-90deg);
    }

    .collapsible.collapsed .collapsible-content {
      display: none;
    }

    /* Footer */
    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    .footer-brand {
      font-weight: 600;
      color: var(--primary);
    }

    .disclaimer {
      margin-top: 1rem;
      font-size: 0.75rem;
      color: var(--gray-400);
    }

    /* Responsive */
    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }

      .company-name {
        font-size: 1.75rem;
      }

      .ticker-badge {
        display: block;
        margin-left: 0;
        margin-top: 0.5rem;
      }

      .header-top {
        flex-direction: column;
      }

      .pipeline-table {
        font-size: 0.8rem;
      }

      .pipeline-table th:nth-child(4),
      .pipeline-table td:nth-child(4) {
        display: none;
      }
    }

    /* Print */
    @media print {
      body {
        background: white;
      }

      .container {
        max-width: none;
        padding: 0;
      }

      .header {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }

      .collapsible.collapsed .collapsible-content {
        display: block;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="header-top">
        <div>
          <h1 class="company-name">
            ${escapeHtml(companyName)}
            <span class="ticker-badge">${ticker}</span>
          </h1>
          <div class="filing-info">
            ${filing.form} | Filed ${formatDate(filing.filingDate)} | FY ${filingYear}
            <br>
            <a href="${filing.fileUrl}" target="_blank" class="sec-link">View SEC Filing →</a>
          </div>
        </div>
        <div class="satya-logo">सत्य Satya Bio</div>
      </div>
    </header>

    <!-- Executive Summary -->
    <div class="summary-box">
      <div class="summary-title">Executive Summary</div>
      <p class="summary-text">${escapeHtml(analysis.analystSummary)}</p>

      <div class="key-stats">
        <div class="stat-item">
          <div class="stat-value">${analysis.company.marketCap || '—'}</div>
          <div class="stat-label">Market Cap</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${analysis.financials.revenue || '—'}</div>
          <div class="stat-label">Revenue</div>
        </div>
        <div class="stat-item ${runwayClass}">
          <div class="stat-value">${runwayIndicator} ${runway ? runway + ' mo' : '—'}</div>
          <div class="stat-label">Cash Runway</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">${analysis.pipeline.length}</div>
          <div class="stat-label">Pipeline Assets</div>
        </div>
      </div>
    </div>

    <!-- Two Column Layout -->
    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 1.5rem;">
      <div>
        <!-- Pipeline Table -->
        <div class="card">
          <h2 class="card-title">Pipeline</h2>
          <table class="pipeline-table">
            <thead>
              <tr>
                <th>Drug</th>
                <th>Phase</th>
                <th>Indication</th>
                <th>Status</th>
                <th>Catalyst</th>
              </tr>
            </thead>
            <tbody>
              ${sortedPipeline.map(drug => `
                <tr>
                  <td class="drug-name">${escapeHtml(drug.drug)}</td>
                  <td><span class="phase-badge ${getPhaseClass(drug.phase)}">${escapeHtml(drug.phase)}</span></td>
                  <td>${escapeHtml(drug.indication)}</td>
                  <td>${drug.status ? escapeHtml(drug.status) : '—'}</td>
                  <td>${drug.catalyst ? `<span class="catalyst-tag">${escapeHtml(drug.catalyst)}</span>` : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>

        <!-- Partnerships -->
        ${analysis.partnerships.length > 0 ? `
        <div class="card">
          <h2 class="card-title">Partnerships</h2>
          <div class="partnership-cards">
            ${analysis.partnerships.map(p => `
              <div class="partnership-card">
                <div>
                  <span class="partner-name">${escapeHtml(p.partner)}</span>
                  <span class="partner-type">${escapeHtml(p.type)}</span>
                </div>
                ${p.value ? `<div class="partner-value">${escapeHtml(p.value)}</div>` : ''}
                <div class="partner-details">${escapeHtml(p.details)}</div>
              </div>
            `).join('')}
          </div>
        </div>
        ` : ''}

        <!-- Recent Events -->
        ${analysis.recentEvents.length > 0 ? `
        <div class="card">
          <h2 class="card-title">Recent Events</h2>
          <ul class="events-list">
            ${analysis.recentEvents.map(event => `
              <li>${escapeHtml(event)}</li>
            `).join('')}
          </ul>
        </div>
        ` : ''}
      </div>

      <div>
        <!-- Financials -->
        <div class="card">
          <h2 class="card-title">Financials</h2>
          <div class="financials-grid" style="grid-template-columns: 1fr;">
            <div class="financial-item ${runwayClass}">
              <div class="financial-label">Cash Position</div>
              <div class="financial-value">${analysis.financials.cash || '—'}</div>
              ${analysis.financials.cashDate ? `<div class="financial-detail">as of ${escapeHtml(analysis.financials.cashDate)}</div>` : ''}
            </div>

            <div class="financial-item ${runwayClass}">
              <div class="financial-label">Cash Runway</div>
              <div class="financial-value">${runwayIndicator} ${runway ? runway + ' months' : '—'}</div>
            </div>

            ${analysis.financials.quarterlyBurnRate ? `
            <div class="financial-item">
              <div class="financial-label">Quarterly Burn</div>
              <div class="financial-value">${escapeHtml(analysis.financials.quarterlyBurnRate)}</div>
            </div>
            ` : ''}

            ${analysis.financials.revenue ? `
            <div class="financial-item">
              <div class="financial-label">Revenue</div>
              <div class="financial-value">${escapeHtml(analysis.financials.revenue)}</div>
              ${analysis.financials.revenueSource ? `<div class="financial-detail">${escapeHtml(analysis.financials.revenueSource)}</div>` : ''}
            </div>
            ` : ''}
          </div>
        </div>

        <!-- FDA Interactions -->
        ${analysis.fdaInteractions.length > 0 ? `
        <div class="card">
          <h2 class="card-title">FDA Interactions</h2>
          <ul class="fda-list">
            ${analysis.fdaInteractions.map(item => `
              <li>
                <span class="fda-icon">✓</span>
                <span>${escapeHtml(item)}</span>
              </li>
            `).join('')}
          </ul>
        </div>
        ` : ''}

        <!-- Risks -->
        ${analysis.risks.length > 0 ? `
        <div class="card collapsible">
          <h2 class="card-title collapsible-header">
            <span>Key Risks</span>
          </h2>
          <div class="collapsible-content">
            <ul class="risk-list">
              ${analysis.risks.map(risk => `
                <li>
                  <span class="risk-icon">⚠</span>
                  <span>${escapeHtml(risk)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        </div>
        ` : ''}
      </div>
    </div>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-brand">Powered by Satya Bio</div>
      <div>Generated ${new Date().toLocaleString()}</div>
      <div class="disclaimer">
        Data extracted from SEC filings using AI. Verify all information before making investment decisions.
        This is not financial advice.
      </div>
    </footer>
  </div>

  <script>
    // Toggle collapsible sections
    document.querySelectorAll('.collapsible-header').forEach(header => {
      header.addEventListener('click', () => {
        header.closest('.collapsible').classList.toggle('collapsed');
      });
    });
  </script>
</body>
</html>`;
}

function escapeHtml(text: string): string {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

function getPhaseClass(phase: string): string {
  const p = phase.toLowerCase();
  if (p.includes('approved') || p.includes('marketed')) return 'phase-approved';
  if (p.includes('3') || p.includes('nda') || p.includes('bla')) return 'phase-3';
  if (p.includes('2')) return 'phase-2';
  if (p.includes('1')) return 'phase-1';
  return 'phase-preclinical';
}

// ============================================
// Cache Functions
// ============================================

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

interface CachedAnalysis {
  ticker: string;
  filingDate: string;
  analyzedAt: string;
  analysis: AnalysisResult;
}

function getCacheFilePath(ticker: string): string {
  return path.join(CACHE_DIR, `${ticker.toUpperCase()}.json`);
}

// Cache validity period: 7 days
const CACHE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000;

// ============================================
// Rate Limiting Functions
// ============================================

function isRateLimitExceeded(): boolean {
  const now = Date.now();
  // Remove timestamps older than the rate limit window
  while (apiCallTimestamps.length > 0 && apiCallTimestamps[0] < now - RATE_LIMIT_WINDOW_MS) {
    apiCallTimestamps.shift();
  }
  return apiCallTimestamps.length >= RATE_LIMIT_MAX_CALLS;
}

function recordApiCall(): void {
  apiCallTimestamps.push(Date.now());
}

function getRateLimitStatus(): { remaining: number; resetInMinutes: number } {
  const now = Date.now();
  // Clean up old timestamps
  while (apiCallTimestamps.length > 0 && apiCallTimestamps[0] < now - RATE_LIMIT_WINDOW_MS) {
    apiCallTimestamps.shift();
  }
  const remaining = Math.max(0, RATE_LIMIT_MAX_CALLS - apiCallTimestamps.length);
  const oldestCall = apiCallTimestamps[0];
  const resetInMinutes = oldestCall
    ? Math.ceil((oldestCall + RATE_LIMIT_WINDOW_MS - now) / (60 * 1000))
    : 0;
  return { remaining, resetInMinutes };
}

// Get cached analysis ignoring expiry (for rate limit scenarios)
function getCachedAnalysisIgnoreExpiry(ticker: string): CachedAnalysis | null {
  const filePath = getCacheFilePath(ticker);
  if (!fs.existsSync(filePath)) return null;

  try {
    const data = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(data) as CachedAnalysis;
  } catch {
    return null;
  }
}

function getCachedAnalysis(ticker: string): CachedAnalysis | null {
  const filePath = getCacheFilePath(ticker);
  if (!fs.existsSync(filePath)) return null;

  try {
    const data = fs.readFileSync(filePath, 'utf-8');
    const cached = JSON.parse(data) as CachedAnalysis;

    // Check if cache is still valid (less than 7 days old)
    if (cached.analyzedAt) {
      const cacheAge = Date.now() - new Date(cached.analyzedAt).getTime();
      if (cacheAge > CACHE_MAX_AGE_MS) {
        console.log(chalk.yellow(`  [Cache] ${ticker} cache expired (${Math.floor(cacheAge / (24 * 60 * 60 * 1000))} days old)`));
        return null;
      }
    }

    return cached;
  } catch {
    return null;
  }
}

function saveCachedAnalysis(ticker: string, filingDate: string, analysis: AnalysisResult): void {
  const filePath = getCacheFilePath(ticker);
  const cached: CachedAnalysis = {
    ticker: ticker.toUpperCase(),
    filingDate,
    analyzedAt: new Date().toISOString(),
    analysis
  };

  fs.writeFileSync(filePath, JSON.stringify(cached, null, 2));
}

function getAllCachedAnalyses(): CachedAnalysis[] {
  if (!fs.existsSync(CACHE_DIR)) return [];

  const files = fs.readdirSync(CACHE_DIR).filter(f => f.endsWith('.json'));
  const analyses: CachedAnalysis[] = [];

  for (const file of files) {
    try {
      const data = fs.readFileSync(path.join(CACHE_DIR, file), 'utf-8');
      analyses.push(JSON.parse(data) as CachedAnalysis);
    } catch {
      // Skip invalid files
    }
  }

  return analyses;
}

function getMostAdvancedPhase(pipeline: PipelineItem[]): string {
  if (pipeline.length === 0) return 'N/A';

  let maxRank = 0;
  let maxPhase = 'Preclinical';

  for (const item of pipeline) {
    const rank = getPhaseRank(item.phase);
    if (rank > maxRank) {
      maxRank = rank;
      maxPhase = item.phase;
    }
  }

  return maxPhase;
}

function getKeyCatalyst(pipeline: PipelineItem[]): string | null {
  // Find the first catalyst from the most advanced drugs
  const sorted = [...pipeline].sort((a, b) => getPhaseRank(b.phase) - getPhaseRank(a.phase));
  for (const item of sorted) {
    if (item.catalyst) return item.catalyst;
  }
  return null;
}

// ============================================
// Company Report HTML Generator
// ============================================

function generateCompanyReportHtml(profile: ReturnType<typeof getARWRProfile>): string {
  const { company, pipeline, clinicalData, catalysts, presentations, stats } = profile;
  const timestamp = new Date().toLocaleString();

  const phaseOrder: Record<string, number> = {
    'Approved': 0,
    'Filed': 1,
    'Phase 3': 2,
    'Phase 2b': 3,
    'Phase 2': 4,
    'Phase 1/2': 5,
    'Phase 1': 6,
    'Preclinical': 7,
  };

  const sortedPipeline = [...pipeline].sort((a, b) =>
    (phaseOrder[a.phase] ?? 99) - (phaseOrder[b.phase] ?? 99)
  );

  const getPhaseBadgeClass = (phase: string): string => {
    if (phase === 'Approved') return 'phase-approved';
    if (phase === 'Phase 3' || phase === 'Filed') return 'phase-phase3';
    if (phase.includes('Phase 2')) return 'phase-phase2';
    if (phase.includes('Phase 1')) return 'phase-phase1';
    return '';
  };

  const highCatalysts = catalysts.filter(c => c.importance === 'high');
  const mediumCatalysts = catalysts.filter(c => c.importance === 'medium');

  // Build pipeline rows
  const pipelineRows = sortedPipeline.map(asset => {
    const codes = asset.codeNames.filter(c => c !== asset.name).join(', ');
    const partnerBadge = asset.partner ? '<span class="partner-badge">' + escapeHtml(asset.partner) + '</span>' : '-';
    const catalystSpan = asset.nextCatalyst ? '<span class="catalyst-text">' + escapeHtml(asset.nextCatalyst) + '</span>' : '-';
    return '<tr>' +
      '<td><div class="drug-name">' + escapeHtml(asset.name) + '</div><div class="drug-codes">' + escapeHtml(codes) + '</div></td>' +
      '<td>' + escapeHtml(asset.target) + '</td>' +
      '<td><span class="phase-badge ' + getPhaseBadgeClass(asset.phase) + '">' + escapeHtml(asset.phase) + '</span></td>' +
      '<td>' + escapeHtml(asset.leadIndication) + '</td>' +
      '<td>' + partnerBadge + '</td>' +
      '<td>' + escapeHtml(asset.keyData || '-') + '</td>' +
      '<td>' + catalystSpan + '</td>' +
      '</tr>';
  }).join('');

  // Build catalyst cards
  const catalystCards = [...highCatalysts, ...mediumCatalysts].slice(0, 8).map(c => {
    const notesDiv = c.notes ? '<div style="margin-top: 8px; font-size: 0.85rem; color: var(--text-secondary);">' + escapeHtml(c.notes) + '</div>' : '';
    return '<div class="catalyst-card ' + c.importance + '">' +
      '<div class="catalyst-drug">' + escapeHtml(c.drug) + '</div>' +
      '<div class="catalyst-event">' + escapeHtml(c.event) + '</div>' +
      '<span class="catalyst-date">' + escapeHtml(c.expectedDate) + '</span>' +
      notesDiv +
      '</div>';
  }).join('');

  // Build clinical data cards
  const clinicalCards = clinicalData.slice(0, 6).map(d => {
    const comparatorDiv = d.comparator ? '<div style="font-size: 0.85rem; color: var(--text-secondary);">vs ' + escapeHtml(d.comparator) + ': ' + escapeHtml(d.comparatorResult || '') + '</div>' : '';
    return '<div class="data-card">' +
      '<div class="data-header"><div>' +
      '<div class="data-drug">' + escapeHtml(d.drug) + '</div>' +
      '<div class="data-trial">' + escapeHtml(d.trial) + ' (' + escapeHtml(d.indication) + ')</div>' +
      '</div><div class="data-result">' + escapeHtml(d.result) + '</div></div>' +
      '<div class="data-endpoint">' + escapeHtml(d.endpoint) + '</div>' +
      comparatorDiv +
      '<div class="data-source">' + escapeHtml(d.source) + ' (' + escapeHtml(d.sourceDate) + ')</div>' +
      '</div>';
  }).join('');

  // Build presentation items
  const presentationItems = presentations.slice(0, 10).map(p => {
    const eventPart = p.event ? ' &bull; ' + escapeHtml(p.event) : '';
    const sizePart = p.fileSize ? ' &bull; ' + escapeHtml(p.fileSize) : '';
    return '<div class="presentation-item">' +
      '<div class="presentation-info">' +
      '<div class="presentation-title">' + escapeHtml(p.title) + '</div>' +
      '<div class="presentation-meta">' + escapeHtml(p.date) + eventPart + sizePart + '</div>' +
      '</div>' +
      '<a href="' + escapeHtml(p.url) + '" target="_blank" class="presentation-download">Download PDF</a>' +
      '</div>';
  }).join('');

  return '<!DOCTYPE html>' +
    '<html lang="en">' +
    '<head>' +
    '<meta charset="UTF-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
    '<title>' + escapeHtml(company.ticker) + ' - ' + escapeHtml(company.name) + ' | Satya Bio</title>' +
    '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">' +
    '<style>' +
    ':root { --navy: #1E3A5F; --coral: #E07A5F; --cream: #FAFAF8; --text: #1a1a1a; --text-secondary: #666; --border: #e0e0e0; --success: #10B981; --warning: #F59E0B; --info: #3B82F6; }' +
    '* { box-sizing: border-box; margin: 0; padding: 0; }' +
    'body { font-family: "Plus Jakarta Sans", -apple-system, sans-serif; background: var(--cream); color: var(--text); line-height: 1.6; }' +
    '.container { max-width: 1400px; margin: 0 auto; padding: 24px; }' +
    'a { color: var(--coral); text-decoration: none; } a:hover { text-decoration: underline; }' +
    '.header { background: linear-gradient(135deg, var(--navy) 0%, #2d4a6f 100%); color: white; padding: 48px 0; margin-bottom: 32px; }' +
    '.header-content { max-width: 1400px; margin: 0 auto; padding: 0 24px; }' +
    '.back-link { color: rgba(255,255,255,0.7); margin-bottom: 16px; display: inline-block; } .back-link:hover { color: white; }' +
    '.company-title { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }' +
    '.ticker-badge { background: var(--coral); color: white; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 1.5rem; }' +
    'h1 { font-size: 2.5rem; font-weight: 700; }' +
    '.company-desc { font-size: 1.1rem; opacity: 0.9; max-width: 800px; margin-bottom: 24px; }' +
    '.platform-badge { display: inline-block; background: rgba(255,255,255,0.2); padding: 6px 16px; border-radius: 20px; font-size: 0.9rem; }' +
    '.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-top: 24px; }' +
    '.stat-card { background: rgba(255,255,255,0.15); padding: 20px; border-radius: 12px; text-align: center; }' +
    '.stat-num { font-size: 2rem; font-weight: 700; color: white; }' +
    '.stat-label { font-size: 0.85rem; opacity: 0.8; }' +
    '.section { background: white; border-radius: 16px; padding: 28px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); border: 1px solid var(--border); }' +
    '.section-title { font-size: 1.4rem; font-weight: 700; color: var(--navy); margin-bottom: 20px; }' +
    'table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }' +
    'th { background: var(--cream); color: var(--text-secondary); padding: 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; border-bottom: 2px solid var(--border); }' +
    'td { padding: 14px 12px; border-bottom: 1px solid var(--border); }' +
    'tr:hover { background: var(--cream); }' +
    '.drug-name { font-weight: 600; color: var(--navy); }' +
    '.drug-codes { font-size: 0.8rem; color: var(--text-secondary); }' +
    '.phase-badge { padding: 4px 12px; border-radius: 16px; font-size: 0.75rem; font-weight: 600; display: inline-block; }' +
    '.phase-approved { background: #F3E8FF; color: #7C3AED; }' +
    '.phase-phase3 { background: #DCFCE7; color: #166534; }' +
    '.phase-phase2 { background: #DBEAFE; color: #1E40AF; }' +
    '.phase-phase1 { background: #F3F4F6; color: #4B5563; }' +
    '.partner-badge { background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }' +
    '.catalyst-text { font-size: 0.85rem; color: var(--success); font-weight: 500; }' +
    '.catalyst-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 16px; }' +
    '.catalyst-card { background: var(--cream); border-radius: 12px; padding: 20px; border-left: 4px solid var(--coral); }' +
    '.catalyst-card.high { border-left-color: var(--success); }' +
    '.catalyst-drug { font-weight: 700; color: var(--navy); margin-bottom: 4px; }' +
    '.catalyst-event { font-size: 0.95rem; margin-bottom: 8px; }' +
    '.catalyst-date { display: inline-block; background: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; color: var(--coral); }' +
    '.data-card { background: var(--cream); border-radius: 12px; padding: 20px; }' +
    '.data-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }' +
    '.data-drug { font-weight: 700; color: var(--navy); }' +
    '.data-trial { font-size: 0.85rem; color: var(--text-secondary); }' +
    '.data-result { font-size: 1.5rem; font-weight: 700; color: var(--success); }' +
    '.data-endpoint { font-size: 0.9rem; color: var(--text-secondary); }' +
    '.data-source { font-size: 0.8rem; color: var(--text-secondary); margin-top: 8px; }' +
    '.presentation-list { display: grid; gap: 12px; }' +
    '.presentation-item { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: var(--cream); border-radius: 10px; }' +
    '.presentation-info { flex: 1; }' +
    '.presentation-title { font-weight: 600; color: var(--navy); margin-bottom: 4px; }' +
    '.presentation-meta { font-size: 0.85rem; color: var(--text-secondary); }' +
    '.presentation-download { background: var(--coral); color: white; padding: 8px 16px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; text-decoration: none; }' +
    '.presentation-download:hover { background: #c66a52; }' +
    '.footer { text-align: center; color: var(--text-secondary); padding: 32px; font-size: 0.85rem; }' +
    '</style></head><body>' +
    '<div class="header"><div class="header-content">' +
    '<a href="/" class="back-link">&larr; Back to Satya Bio</a>' +
    '<div class="company-title">' +
    '<span class="ticker-badge">' + escapeHtml(company.ticker) + '</span>' +
    '<h1>' + escapeHtml(company.name) + '</h1></div>' +
    '<p class="company-desc">' + escapeHtml(company.description) + '</p>' +
    '<span class="platform-badge">' + escapeHtml(company.platform) + '</span>' +
    '<div class="stats-grid">' +
    '<div class="stat-card"><div class="stat-num">' + stats.totalPipelineAssets + '</div><div class="stat-label">Pipeline Assets</div></div>' +
    '<div class="stat-card"><div class="stat-num">' + stats.approvedProducts + '</div><div class="stat-label">Approved</div></div>' +
    '<div class="stat-card"><div class="stat-num">' + stats.phase3Programs + '</div><div class="stat-label">Phase 3</div></div>' +
    '<div class="stat-card"><div class="stat-num">' + stats.partneredPrograms + '</div><div class="stat-label">Partnered</div></div>' +
    '<div class="stat-card"><div class="stat-num">' + stats.upcomingCatalysts + '</div><div class="stat-label">Key Catalysts</div></div>' +
    '<div class="stat-card"><div class="stat-num">' + stats.totalPresentations + '</div><div class="stat-label">Presentations</div></div>' +
    '</div></div></div>' +
    '<div class="container">' +
    '<div class="section"><h2 class="section-title">Pipeline</h2>' +
    '<table><thead><tr><th>Drug</th><th>Target</th><th>Phase</th><th>Lead Indication</th><th>Partner</th><th>Key Data</th><th>Next Catalyst</th></tr></thead>' +
    '<tbody>' + pipelineRows + '</tbody></table></div>' +
    '<div class="section"><h2 class="section-title">Upcoming Catalysts</h2>' +
    '<div class="catalyst-grid">' + catalystCards + '</div></div>' +
    '<div class="section"><h2 class="section-title">Key Clinical Data</h2>' +
    '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">' + clinicalCards + '</div></div>' +
    '<div class="section"><h2 class="section-title">Investor Presentations</h2>' +
    '<div class="presentation-list">' + presentationItems + '</div></div>' +
    '</div>' +
    '<div class="footer"><p>Generated by Satya Bio | ' + timestamp + '</p>' +
    '<p style="margin-top: 8px;">Data from ' + stats.totalPresentations + ' investor presentations analyzed</p></div>' +
    '</body></html>';
}

// ============================================
// Dashboard HTML Generator
// ============================================

interface DashboardRow {
  ticker: string;
  name: string;
  filingDate: string;
  marketCap: string | null;
  phase: string;
  runway: number | null;
  cash: string | null;
  catalyst: string | null;
  pipelineCount: number;
}

function generateDashboardHtml(data: DashboardRow[]): string {
  const timestamp = new Date().toLocaleString();

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Satya Bio Dashboard | Biotech Portfolio Analysis</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.5;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 1.5rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 700;
    }

    .header-stats {
      display: flex;
      gap: 2rem;
    }

    .header-stat {
      text-align: center;
    }

    .header-stat-value {
      font-size: 1.5rem;
      font-weight: 700;
    }

    .header-stat-label {
      font-size: 0.75rem;
      opacity: 0.8;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .controls {
      display: flex;
      gap: 1rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }

    .search-box {
      flex: 1;
      min-width: 200px;
      padding: 0.75rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 1rem;
    }

    .filter-btn {
      padding: 0.75rem 1rem;
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.875rem;
    }

    .filter-btn:hover {
      background: var(--gray-50);
    }

    .filter-btn.active {
      background: var(--primary);
      color: white;
      border-color: var(--primary);
    }

    .table-container {
      background: white;
      border-radius: 12px;
      border: 1px solid var(--gray-200);
      overflow: hidden;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    th {
      text-align: left;
      padding: 1rem;
      background: var(--gray-50);
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--gray-500);
      border-bottom: 1px solid var(--gray-200);
      cursor: pointer;
      user-select: none;
    }

    th:hover {
      background: var(--gray-100);
    }

    th .sort-arrow {
      margin-left: 0.5rem;
      opacity: 0.5;
    }

    td {
      padding: 1rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: middle;
    }

    tr:hover {
      background: var(--gray-50);
    }

    tr.clickable {
      cursor: pointer;
    }

    .ticker-cell {
      font-weight: 700;
      color: var(--primary);
    }

    .company-name {
      color: var(--gray-700);
      font-size: 0.875rem;
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
    }

    .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }

    .runway-good { color: var(--success); font-weight: 600; }
    .runway-moderate { color: var(--warning); font-weight: 600; }
    .runway-low { color: var(--danger); font-weight: 600; }

    .catalyst-tag {
      background: #fef3c7;
      color: #92400e;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
    }

    .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: var(--gray-500);
    }

    .empty-state h2 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
      color: var(--gray-700);
    }

    .batch-btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
    }

    .batch-btn:hover {
      background: var(--primary-dark);
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .header { flex-direction: column; gap: 1rem; }
      .header-stats { justify-content: center; }
      th, td { padding: 0.75rem 0.5rem; font-size: 0.8rem; }
      .controls { flex-direction: column; }
    }
  </style>
</head>
<body>
  <header class="header">
    <h1>⬡ Satya Bio Dashboard</h1>
    <div class="header-stats">
      <div class="header-stat">
        <div class="header-stat-value">${data.length}</div>
        <div class="header-stat-label">Companies Analyzed</div>
      </div>
      <div class="header-stat">
        <div class="header-stat-value">${data.filter(d => d.phase.toLowerCase().includes('approved')).length}</div>
        <div class="header-stat-label">With Approved Drugs</div>
      </div>
      <div class="header-stat">
        <div class="header-stat-value">${data.filter(d => d.phase.toLowerCase().includes('3')).length}</div>
        <div class="header-stat-label">Phase 3</div>
      </div>
    </div>
  </header>

  <div class="container">
    ${data.length === 0 ? `
      <div class="empty-state">
        <h2>No analyses yet</h2>
        <p>Run a batch analysis to populate the dashboard</p>
        <br>
        <code>POST /api/analyze/batch</code> with <code>{"tickers": ["MRNA", "REGN", "VRTX"]}</code>
      </div>
    ` : `
      <div class="controls">
        <input type="text" class="search-box" placeholder="Search by ticker or company..." id="searchInput">
        <button class="filter-btn active" data-filter="all">All</button>
        <button class="filter-btn" data-filter="approved">Approved</button>
        <button class="filter-btn" data-filter="phase-3">Phase 3</button>
        <button class="filter-btn" data-filter="phase-2">Phase 2</button>
        <button class="filter-btn" data-filter="low-runway">Low Runway (&lt;12mo)</button>
      </div>

      <div class="table-container">
        <table id="dashboardTable">
          <thead>
            <tr>
              <th data-sort="ticker">Ticker <span class="sort-arrow">↕</span></th>
              <th data-sort="name">Company <span class="sort-arrow">↕</span></th>
              <th data-sort="phase">Phase <span class="sort-arrow">↕</span></th>
              <th data-sort="runway">Runway <span class="sort-arrow">↕</span></th>
              <th data-sort="cash">Cash <span class="sort-arrow">↕</span></th>
              <th>Key Catalyst</th>
              <th>Pipeline</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(row => {
              const runwayClass = row.runway === null ? '' :
                row.runway >= 24 ? 'runway-good' :
                row.runway >= 12 ? 'runway-moderate' : 'runway-low';
              const runwayIcon = row.runway === null ? '' :
                row.runway >= 24 ? '🟢' :
                row.runway >= 12 ? '🟡' : '🔴';

              return `
                <tr class="clickable" onclick="window.location='/api/report/${row.ticker}'" data-phase="${row.phase.toLowerCase()}" data-runway="${row.runway || 0}">
                  <td class="ticker-cell">${row.ticker}</td>
                  <td>
                    <div>${escapeHtml(row.name)}</div>
                    ${row.marketCap ? `<div class="company-name">${row.marketCap}</div>` : ''}
                  </td>
                  <td><span class="phase-badge ${getPhaseClass(row.phase)}">${escapeHtml(row.phase)}</span></td>
                  <td class="${runwayClass}">${runwayIcon} ${row.runway ? row.runway + ' mo' : '—'}</td>
                  <td>${row.cash || '—'}</td>
                  <td>${row.catalyst ? `<span class="catalyst-tag">${escapeHtml(row.catalyst)}</span>` : '—'}</td>
                  <td>${row.pipelineCount} assets</td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `}

    <footer class="footer">
      <div>Powered by Satya Bio</div>
      <div>Last updated: ${timestamp}</div>
    </footer>
  </div>

  <script>
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        document.querySelectorAll('#dashboardTable tbody tr').forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      });
    }

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        const filter = this.dataset.filter;
        document.querySelectorAll('#dashboardTable tbody tr').forEach(row => {
          const phase = row.dataset.phase || '';
          const runway = parseInt(row.dataset.runway) || 0;

          let show = true;
          if (filter === 'approved') show = phase.includes('approved');
          else if (filter === 'phase-3') show = phase.includes('3');
          else if (filter === 'phase-2') show = phase.includes('2');
          else if (filter === 'low-runway') show = runway > 0 && runway < 12;

          row.style.display = show ? '' : 'none';
        });
      });
    });

    // Sort functionality
    document.querySelectorAll('th[data-sort]').forEach(th => {
      th.addEventListener('click', function() {
        const table = document.getElementById('dashboardTable');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const col = this.dataset.sort;
        const colIndex = Array.from(this.parentNode.children).indexOf(this);

        const direction = this.classList.contains('sort-asc') ? -1 : 1;
        this.parentNode.querySelectorAll('th').forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
        this.classList.add(direction === 1 ? 'sort-asc' : 'sort-desc');

        rows.sort((a, b) => {
          let aVal = a.children[colIndex].textContent.trim();
          let bVal = b.children[colIndex].textContent.trim();

          // Handle numeric columns
          if (col === 'runway') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
            return (aVal - bVal) * direction;
          }

          return aVal.localeCompare(bVal) * direction;
        });

        rows.forEach(row => tbody.appendChild(row));
      });
    });
  </script>
</body>
</html>`;
}

// ============================================
// Landscape Dashboard HTML Generator
// ============================================

function generateLandscapeHtml(data: LandscapeData): string {
  const timestamp = new Date(data.fetchedAt).toLocaleString();

  // Prepare chart data
  const phaseLabels = Object.keys(data.clinicalTrials.phaseBreakdown);
  const phaseValues = Object.values(data.clinicalTrials.phaseBreakdown);
  const sponsorLabels = data.clinicalTrials.topSponsors.map(s => s.name.substring(0, 30));
  const sponsorValues = data.clinicalTrials.topSponsors.map(s => s.count);
  const yearLabels = data.research.byYear.map(y => y.year.toString());
  const yearValues = data.research.byYear.map(y => y.count);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(data.condition)} Landscape | Satya Bio</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-300: #d1d5db;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header-content {
      max-width: 1400px;
      margin: 0 auto;
    }

    .header h1 {
      font-size: 2.5rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .header-subtitle {
      opacity: 0.9;
      font-size: 1rem;
    }

    .summary-stats {
      display: flex;
      gap: 2rem;
      margin-top: 1.5rem;
      flex-wrap: wrap;
    }

    .stat-box {
      background: rgba(255,255,255,0.15);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      text-align: center;
      min-width: 140px;
    }

    .stat-value {
      font-size: 2rem;
      font-weight: 700;
    }

    .stat-label {
      font-size: 0.75rem;
      opacity: 0.9;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .section {
      margin-bottom: 2rem;
    }

    .section-title {
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1rem;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 1.5rem;
    }

    .chart-container {
      position: relative;
      height: 300px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--gray-200);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    tr:hover {
      background: var(--gray-50);
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-4 { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-na { background: var(--gray-100); color: var(--gray-500); }

    .status-recruiting { color: var(--success); font-weight: 500; }
    .status-completed { color: var(--gray-500); }
    .status-active { color: var(--secondary); font-weight: 500; }
    .status-terminated { color: var(--danger); }

    .deal-type {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      background: var(--gray-100);
      color: var(--gray-700);
    }

    .deal-value {
      color: var(--success);
      font-weight: 600;
    }

    .link {
      color: var(--primary);
      text-decoration: none;
    }

    .link:hover {
      text-decoration: underline;
    }

    .kol-rank {
      color: var(--primary);
      font-weight: 700;
    }

    .export-btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
    }

    .export-btn:hover {
      background: var(--primary-dark);
    }

    .search-box {
      width: 100%;
      max-width: 400px;
      padding: 0.75rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    .no-data {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
    }

    @media (max-width: 768px) {
      .grid-2 { grid-template-columns: 1fr; }
      .summary-stats { flex-direction: column; gap: 1rem; }
      .stat-box { min-width: auto; }
      .header h1 { font-size: 1.75rem; }
      th, td { padding: 0.5rem; font-size: 0.75rem; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <h1>⬡ ${escapeHtml(data.condition)}</h1>
      <div class="header-subtitle">Therapeutic Landscape Analysis | Updated ${timestamp}</div>

      <div class="summary-stats">
        <div class="stat-box">
          <div class="stat-value">${data.summary.totalTrials}</div>
          <div class="stat-label">Clinical Trials</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.uniqueMolecules || 0}</div>
          <div class="stat-label">Molecules</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.activeCompanies}</div>
          <div class="stat-label">Active Companies</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.recentDeals}</div>
          <div class="stat-label">Recent Deals</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${data.summary.totalPublications.toLocaleString()}</div>
          <div class="stat-label">Publications</div>
        </div>
      </div>
    </div>
  </header>

  <div class="container">
    <!-- Section 1: Clinical Landscape -->
    <section class="section">
      <h2 class="section-title">Clinical Landscape</h2>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">Phase Distribution</div>
          <div class="chart-container">
            <canvas id="phaseChart"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Top 10 Sponsors</div>
          <div class="chart-container">
            <canvas id="sponsorChart"></canvas>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Clinical Trials (${data.clinicalTrials.trials.length})</div>
        <input type="text" class="search-box" placeholder="Search trials..." id="trialSearch">
        <div style="max-height: 500px; overflow-y: auto;">
          <table id="trialsTable">
            <thead>
              <tr>
                <th>NCT ID</th>
                <th>Title</th>
                <th>Phase</th>
                <th>Status</th>
                <th>Sponsor</th>
                <th>Enrollment</th>
              </tr>
            </thead>
            <tbody>
              ${data.clinicalTrials.trials.length === 0 ? `
                <tr><td colspan="6" class="no-data">No trials found</td></tr>
              ` : data.clinicalTrials.trials.map(trial => `
                <tr>
                  <td><a href="https://clinicaltrials.gov/study/${trial.nctId}" target="_blank" class="link">${trial.nctId}</a></td>
                  <td>${escapeHtml(trial.title.substring(0, 100))}${trial.title.length > 100 ? '...' : ''}</td>
                  <td><span class="phase-badge ${getTrialPhaseClass(trial.phase)}">${escapeHtml(trial.phase)}</span></td>
                  <td class="${getTrialStatusClass(trial.status)}">${escapeHtml(trial.status)}</td>
                  <td>${escapeHtml(trial.sponsor.substring(0, 40))}${trial.sponsor.length > 40 ? '...' : ''}</td>
                  <td>${trial.enrollment ? trial.enrollment.toLocaleString() : '—'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Section 2: Molecule Landscape -->
    <section class="section">
      <h2 class="section-title">💊 Molecule Landscape</h2>

      <div class="card">
        <div class="card-title">Drugs & Molecules in Development (${data.molecules?.length || 0})</div>
        ${!data.molecules || data.molecules.length === 0 ? `
          <div class="no-data">No molecules extracted from trials</div>
        ` : `
          <input type="text" class="search-box" placeholder="Search molecules..." id="moleculeSearch">
          <div style="max-height: 400px; overflow-y: auto;">
            <table id="moleculesTable">
              <thead>
                <tr>
                  <th>Molecule</th>
                  <th>Mechanism</th>
                  <th>Sponsor</th>
                  <th>Highest Phase</th>
                  <th>Trials</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${data.molecules.map(mol => `
                  <tr>
                    <td><strong>${escapeHtml(mol.name)}</strong></td>
                    <td>${mol.mechanism ? `<span class="deal-type">${escapeHtml(mol.mechanism)}</span>` : '—'}</td>
                    <td>${escapeHtml(mol.sponsor.substring(0, 35))}${mol.sponsor.length > 35 ? '...' : ''}</td>
                    <td><span class="phase-badge ${getTrialPhaseClass(mol.highestPhase)}">${escapeHtml(mol.highestPhase)}</span></td>
                    <td>${mol.trialCount}</td>
                    <td class="${getTrialStatusClass(mol.status)}">${escapeHtml(mol.status)}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    </section>

    <!-- Section 3: Deal Tracker -->
    <section class="section">
      <h2 class="section-title">Deal Tracker</h2>

      <div class="card">
        <div class="card-title">Recent Deals & News (${data.dealsNews.length})</div>
        ${data.dealsNews.length === 0 ? `
          <div class="no-data">No deals or news found matching "${escapeHtml(data.condition)}"</div>
        ` : `
          <div style="max-height: 400px; overflow-y: auto;">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Title</th>
                  <th>Source</th>
                  <th>Type</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                ${data.dealsNews.map(deal => {
                  const date = new Date(deal.pubDate);
                  const dateStr = isNaN(date.getTime()) ? '—' : date.toLocaleDateString();
                  return `
                    <tr>
                      <td>${dateStr}</td>
                      <td><a href="${escapeHtml(deal.link)}" target="_blank" class="link">${escapeHtml(deal.title.substring(0, 80))}${deal.title.length > 80 ? '...' : ''}</a></td>
                      <td>${escapeHtml(deal.source)}</td>
                      <td>${deal.dealType ? `<span class="deal-type">${escapeHtml(deal.dealType)}</span>` : '—'}</td>
                      <td class="deal-value">${deal.dealValue || '—'}</td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        `}
      </div>
    </section>

    <!-- Section 4: Research Intelligence -->
    <section class="section">
      <h2 class="section-title">📚 Research Intelligence</h2>

      <div class="grid-2">
        <div class="card">
          <div class="card-title">Publications by Year</div>
          <div class="chart-container">
            <canvas id="pubChart"></canvas>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Top Key Opinion Leaders (Active Researchers)</div>
          ${data.research.topKOLs.length === 0 ? `
            <div class="no-data">No KOL data available</div>
          ` : `
            <div style="max-height: 350px; overflow-y: auto;">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Author</th>
                    <th>Institution</th>
                    <th>Pubs</th>
                    <th>Contact</th>
                  </tr>
                </thead>
                <tbody>
                  ${data.research.topKOLs.map((kol, i) => `
                    <tr>
                      <td class="kol-rank">${i + 1}</td>
                      <td><strong>${escapeHtml(kol.name)}</strong></td>
                      <td>${kol.institution ? escapeHtml(kol.institution.substring(0, 30)) + (kol.institution.length > 30 ? '...' : '') : '—'}</td>
                      <td>${kol.publicationCount}</td>
                      <td>${kol.email ? `<a href="mailto:${escapeHtml(kol.email)}" class="link">${escapeHtml(kol.email.substring(0, 25))}${kol.email.length > 25 ? '...' : ''}</a>` : '—'}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          `}
        </div>
      </div>
    </section>

    <!-- Section 5: Export -->
    <section class="section">
      <h2 class="section-title">📥 Export Data</h2>
      <div class="card">
        <p style="margin-bottom: 1rem; color: var(--gray-500);">Download the complete landscape data including all trials, deals, and KOL information.</p>
        <a href="/api/landscape/${encodeURIComponent(data.condition)}/csv" class="export-btn">Download CSV</a>
        <a href="/api/landscape/${encodeURIComponent(data.condition)}/json" class="export-btn" style="margin-left: 1rem; background: var(--gray-700);">Download JSON</a>
      </div>
    </section>

    <footer class="footer">
      <div>Powered by Satya Bio</div>
      <div>Data sources: ClinicalTrials.gov, PubMed, Fierce Biotech, Fierce Pharma, PR Newswire, Endpoints News, BioPharma Dive</div>
      <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--gray-400);">
        This is aggregated public data. Verify all information before making decisions.
      </div>
    </footer>
  </div>

  <script>
    // Phase Distribution Pie Chart
    new Chart(document.getElementById('phaseChart'), {
      type: 'doughnut',
      data: {
        labels: ${JSON.stringify(phaseLabels)},
        datasets: [{
          data: ${JSON.stringify(phaseValues)},
          backgroundColor: [
            '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#6b7280', '#06b6d4'
          ]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' }
        }
      }
    });

    // Top Sponsors Bar Chart
    new Chart(document.getElementById('sponsorChart'), {
      type: 'bar',
      data: {
        labels: ${JSON.stringify(sponsorLabels)},
        datasets: [{
          label: 'Trials',
          data: ${JSON.stringify(sponsorValues)},
          backgroundColor: '#6366f1'
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true }
        }
      }
    });

    // Publications by Year Line Chart
    new Chart(document.getElementById('pubChart'), {
      type: 'line',
      data: {
        labels: ${JSON.stringify(yearLabels)},
        datasets: [{
          label: 'Publications',
          data: ${JSON.stringify(yearValues)},
          borderColor: '#6366f1',
          backgroundColor: 'rgba(99, 102, 241, 0.1)',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true }
        }
      }
    });

    // Trial search functionality
    document.getElementById('trialSearch')?.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      document.querySelectorAll('#trialsTable tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });

    // Molecule search functionality
    document.getElementById('moleculeSearch')?.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      document.querySelectorAll('#moleculesTable tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  </script>
</body>
</html>`;
}

function getTrialPhaseClass(phase: string): string {
  const p = phase.toLowerCase();
  if (p.includes('4')) return 'phase-4';
  if (p.includes('3')) return 'phase-3';
  if (p.includes('2')) return 'phase-2';
  if (p.includes('1')) return 'phase-1';
  return 'phase-na';
}

function getTrialStatusClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('recruiting')) return 'status-recruiting';
  if (s.includes('completed')) return 'status-completed';
  if (s.includes('active')) return 'status-active';
  if (s.includes('terminated') || s.includes('withdrawn')) return 'status-terminated';
  return '';
}

// ============================================
// Molecules Endpoint Helpers
// ============================================

function getMoleculePhaseRank(phase: string): number {
  const p = phase.toLowerCase();
  if (p.includes('approved') || p.includes('marketed')) return 100;
  if (p.includes('4')) return 90;
  if (p.includes('3')) return 70;
  if (p.includes('2/3')) return 60;
  if (p.includes('2')) return 50;
  if (p.includes('1/2')) return 40;
  if (p.includes('1')) return 30;
  if (p.includes('early')) return 20;
  if (p.includes('preclinical') || p.includes('pre-clinical')) return 10;
  return 0;
}

function generateMoleculesHtml(condition: string, trialCount: number, molecules: MoleculeSummary[]): string {
  const timestamp = new Date().toLocaleString();

  // Count by phase
  const phaseBreakdown: Record<string, number> = {};
  for (const mol of molecules) {
    const phase = mol.highestPhase || 'Unknown';
    phaseBreakdown[phase] = (phaseBreakdown[phase] || 0) + 1;
  }

  // Count by mechanism
  const mechanismBreakdown: Record<string, number> = {};
  for (const mol of molecules) {
    const mech = mol.mechanism || 'Unknown';
    mechanismBreakdown[mech] = (mechanismBreakdown[mech] || 0) + 1;
  }
  const topMechanisms = Object.entries(mechanismBreakdown)
    .filter(([key]) => key !== 'Unknown')
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(condition)} Molecules | Satya Bio</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header-content {
      max-width: 1400px;
      margin: 0 auto;
    }

    .header h1 {
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .header-subtitle {
      opacity: 0.9;
      font-size: 1rem;
    }

    .summary-stats {
      display: flex;
      gap: 2rem;
      margin-top: 1.5rem;
      flex-wrap: wrap;
    }

    .stat-box {
      background: rgba(255,255,255,0.15);
      padding: 1rem 1.5rem;
      border-radius: 8px;
      text-align: center;
      min-width: 120px;
    }

    .stat-value {
      font-size: 1.75rem;
      font-weight: 700;
    }

    .stat-label {
      font-size: 0.75rem;
      opacity: 0.9;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .card-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    .search-box {
      width: 100%;
      max-width: 400px;
      padding: 0.75rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 2px solid var(--gray-200);
      position: sticky;
      top: 0;
      cursor: pointer;
    }

    th:hover {
      background: var(--gray-100);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: middle;
    }

    tr:hover {
      background: var(--gray-50);
    }

    .molecule-name {
      font-weight: 600;
      color: var(--gray-900);
    }

    .molecule-aliases {
      font-size: 0.75rem;
      color: var(--gray-500);
      margin-top: 0.25rem;
    }

    .phase-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-4, .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-na { background: var(--gray-100); color: var(--gray-500); }

    .mechanism-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 500;
      background: #ede9fe;
      color: #5b21b6;
    }

    .type-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 500;
      background: #e0f2fe;
      color: #0369a1;
    }

    .link {
      color: var(--primary);
      text-decoration: none;
    }

    .link:hover {
      text-decoration: underline;
    }

    .trial-count {
      font-weight: 600;
      color: var(--gray-700);
    }

    .sponsor-name {
      color: var(--gray-600);
      font-size: 0.8rem;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .mechanism-list {
      list-style: none;
    }

    .mechanism-list li {
      display: flex;
      justify-content: space-between;
      padding: 0.5rem 0;
      border-bottom: 1px solid var(--gray-100);
    }

    .mechanism-list li:last-child {
      border-bottom: none;
    }

    .mechanism-count {
      font-weight: 600;
      color: var(--primary);
    }

    .export-btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      display: inline-block;
      font-size: 0.875rem;
    }

    .export-btn:hover {
      background: var(--primary-dark);
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .summary-stats { flex-direction: column; gap: 1rem; }
      th, td { padding: 0.5rem; font-size: 0.75rem; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <h1>💊 ${escapeHtml(condition)} - Molecule Landscape</h1>
      <div class="header-subtitle">Drug candidates in clinical development | ${timestamp}</div>

      <div class="summary-stats">
        <div class="stat-box">
          <div class="stat-value">${molecules.length}</div>
          <div class="stat-label">Molecules</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${trialCount}</div>
          <div class="stat-label">Trials Analyzed</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${molecules.filter(m => m.highestPhase.includes('3')).length}</div>
          <div class="stat-label">Phase 3</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${molecules.filter(m => m.highestPhase.includes('2')).length}</div>
          <div class="stat-label">Phase 2</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${new Set(molecules.flatMap(m => m.sponsors)).size}</div>
          <div class="stat-label">Sponsors</div>
        </div>
      </div>
    </div>
  </header>

  <div class="container">
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Phase Distribution</div>
        <ul class="mechanism-list">
          ${Object.entries(phaseBreakdown)
            .sort((a, b) => getMoleculePhaseRank(b[0]) - getMoleculePhaseRank(a[0]))
            .map(([phase, count]) => `
              <li>
                <span><span class="phase-badge ${getTrialPhaseClass(phase)}">${escapeHtml(phase)}</span></span>
                <span class="mechanism-count">${count}</span>
              </li>
            `).join('')}
        </ul>
      </div>

      <div class="card">
        <div class="card-title">Top Mechanisms of Action</div>
        <ul class="mechanism-list">
          ${topMechanisms.map(([mech, count]) => `
            <li>
              <span class="mechanism-badge">${escapeHtml(mech)}</span>
              <span class="mechanism-count">${count}</span>
            </li>
          `).join('') || '<li>No mechanism data available</li>'}
        </ul>
      </div>
    </div>

    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem;">
        <div class="card-title" style="margin-bottom: 0;">Molecules in Development (${molecules.length})</div>
        <a href="/api/landscape/${encodeURIComponent(condition)}/molecules" class="export-btn">Download JSON</a>
      </div>
      <input type="text" class="search-box" placeholder="Search molecules, mechanisms, sponsors..." id="moleculeSearch">
      <div style="max-height: 600px; overflow-y: auto;">
        <table id="moleculesTable">
          <thead>
            <tr>
              <th>Molecule</th>
              <th>Type</th>
              <th>Mechanism</th>
              <th>Target</th>
              <th>Sponsor</th>
              <th>Phase</th>
              <th>Trials</th>
              <th>Lead Trial</th>
            </tr>
          </thead>
          <tbody>
            ${molecules.length === 0 ? `
              <tr><td colspan="8" style="text-align: center; color: var(--gray-500); padding: 2rem;">No molecules found</td></tr>
            ` : molecules.map(mol => `
              <tr>
                <td>
                  <div class="molecule-name">${escapeHtml(mol.name)}</div>
                  ${mol.aliases.length > 0 ? `<div class="molecule-aliases">${mol.aliases.slice(0, 2).map(a => escapeHtml(a)).join(', ')}${mol.aliases.length > 2 ? '...' : ''}</div>` : ''}
                </td>
                <td>${mol.type ? `<span class="type-badge">${escapeHtml(mol.type)}</span>` : '—'}</td>
                <td>${mol.mechanism ? `<span class="mechanism-badge">${escapeHtml(mol.mechanism)}</span>` : '—'}</td>
                <td>${mol.target ? escapeHtml(mol.target) : '—'}</td>
                <td><span class="sponsor-name">${escapeHtml((mol.sponsors[0] || 'Unknown').substring(0, 35))}${(mol.sponsors[0] || '').length > 35 ? '...' : ''}</span></td>
                <td><span class="phase-badge ${getTrialPhaseClass(mol.highestPhase)}">${escapeHtml(mol.highestPhase)}</span></td>
                <td class="trial-count">${mol.trialCount}</td>
                <td>${mol.leadTrialId ? `<a href="https://clinicaltrials.gov/study/${mol.leadTrialId}" target="_blank" class="link">${mol.leadTrialId}</a>` : '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <footer class="footer">
      <div>Powered by Satya Bio</div>
      <div>Data source: ClinicalTrials.gov</div>
    </footer>
  </div>

  <script>
    // Search functionality
    document.getElementById('moleculeSearch')?.addEventListener('input', function() {
      const query = this.value.toLowerCase();
      document.querySelectorAll('#moleculesTable tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  </script>
</body>
</html>`;
}

// ============================================
// Trial Results HTML Generator
// ============================================

function generateTrialResultsHtml(data: FullTrialData): string {
  const timestamp = new Date().toLocaleString();

  // Build arms table data
  const armsHtml = data.arms.map(arm => `
    <tr>
      <td><strong>${escapeHtml(arm.title)}</strong></td>
      <td>${arm.type || '—'}</td>
      <td>${arm.intervention ? escapeHtml(arm.intervention) : '—'}</td>
      <td class="text-center">${arm.n !== undefined ? arm.n.toLocaleString() : '—'}</td>
    </tr>
  `).join('');

  // Build primary outcomes table
  const primaryOutcomesHtml = data.primaryOutcomes.length > 0
    ? data.primaryOutcomes.map(outcome => generateOutcomeSection(outcome, 'primary')).join('')
    : '<p class="no-data">No primary outcome results posted</p>';

  // Build secondary outcomes table
  const secondaryOutcomesHtml = data.secondaryOutcomes.length > 0
    ? data.secondaryOutcomes.map(outcome => generateOutcomeSection(outcome, 'secondary')).join('')
    : '<p class="no-data">No secondary outcome results posted</p>';

  // Build safety tables
  const safetyHtml = data.safety ? generateSafetySection(data.safety) : '<p class="no-data">No adverse events data posted</p>';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(data.nctId)} Results | Satya Bio</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --secondary: #0ea5e9;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header-content {
      max-width: 1200px;
      margin: 0 auto;
    }

    .nct-badge {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      padding: 0.25rem 0.75rem;
      border-radius: 6px;
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 600;
      margin-bottom: 0.5rem;
      line-height: 1.3;
    }

    .header-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 1.5rem;
      margin-top: 1rem;
      font-size: 0.9rem;
      opacity: 0.9;
    }

    .header-meta-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .status-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .status-completed { background: #dcfce7; color: #166534; }
    .status-recruiting { background: #dbeafe; color: #1e40af; }
    .status-terminated { background: #fee2e2; color: #991b1b; }
    .status-other { background: var(--gray-200); color: var(--gray-700); }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
    }

    .section {
      margin-bottom: 2rem;
    }

    .section-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1rem;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 2px solid var(--gray-200);
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    tr:hover {
      background: var(--gray-50);
    }

    .text-center {
      text-align: center;
    }

    .text-right {
      text-align: right;
    }

    .outcome-header {
      background: var(--gray-50);
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
    }

    .outcome-title {
      font-weight: 600;
      color: var(--gray-900);
      margin-bottom: 0.5rem;
    }

    .outcome-meta {
      font-size: 0.875rem;
      color: var(--gray-500);
    }

    .outcome-description {
      font-size: 0.875rem;
      color: var(--gray-600);
      margin-top: 0.5rem;
    }

    .result-value {
      font-weight: 600;
      color: var(--gray-900);
    }

    .result-ci {
      font-size: 0.8rem;
      color: var(--gray-500);
    }

    .p-value {
      font-weight: 600;
    }

    .p-significant {
      color: var(--success);
    }

    .p-not-significant {
      color: var(--gray-500);
    }

    .analysis-box {
      background: #f0fdf4;
      border: 1px solid #86efac;
      border-radius: 8px;
      padding: 1rem;
      margin-top: 1rem;
    }

    .analysis-box.not-significant {
      background: var(--gray-50);
      border-color: var(--gray-200);
    }

    .analysis-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--gray-500);
      text-transform: uppercase;
      margin-bottom: 0.5rem;
    }

    .analysis-value {
      font-size: 1.25rem;
      font-weight: 700;
    }

    .ae-rate {
      font-weight: 600;
    }

    .ae-rate-high {
      color: var(--danger);
    }

    .ae-rate-medium {
      color: var(--warning);
    }

    .ae-rate-low {
      color: var(--gray-700);
    }

    .search-box {
      width: 100%;
      max-width: 300px;
      padding: 0.5rem 1rem;
      border: 1px solid var(--gray-200);
      border-radius: 6px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }

    .link {
      color: var(--primary);
      text-decoration: none;
    }

    .link:hover {
      text-decoration: underline;
    }

    .no-data {
      color: var(--gray-500);
      font-style: italic;
      padding: 1rem;
      text-align: center;
    }

    .no-results-banner {
      background: #fef3c7;
      border: 1px solid #f59e0b;
      border-radius: 8px;
      padding: 1rem;
      text-align: center;
      color: #92400e;
      margin-bottom: 2rem;
    }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }

    @media (max-width: 768px) {
      .header h1 { font-size: 1.25rem; }
      .header-meta { flex-direction: column; gap: 0.5rem; }
      th, td { padding: 0.5rem; font-size: 0.8rem; }
    }

    @media print {
      .header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .search-box { display: none; }
    }
  </style>
</head>
<body>
  <header class="header">
    <div class="header-content">
      <div class="nct-badge">
        <a href="https://clinicaltrials.gov/study/${data.nctId}" target="_blank" style="color: white; text-decoration: none;">
          ${data.nctId} ↗
        </a>
      </div>
      <h1>${escapeHtml(data.title)}</h1>
      <div class="header-meta">
        <div class="header-meta-item">
          <span class="status-badge ${getStatusBadgeClass(data.status)}">${escapeHtml(data.status)}</span>
        </div>
        <div class="header-meta-item">
          <strong>Phase:</strong> ${escapeHtml(data.phase)}
        </div>
        <div class="header-meta-item">
          <strong>Sponsor:</strong> ${escapeHtml(data.sponsor)}
        </div>
        <div class="header-meta-item">
          <strong>Enrollment:</strong> ${data.enrollment.toLocaleString()}
        </div>
        ${data.completionDate ? `<div class="header-meta-item"><strong>Completed:</strong> ${data.completionDate}</div>` : ''}
      </div>
    </div>
  </header>

  <div class="container">
    ${!data.hasResults ? `
      <div class="no-results-banner">
        <strong>No Results Posted Yet</strong><br>
        This trial has not posted results to ClinicalTrials.gov.
        ${data.status === 'COMPLETED' ? 'Results may be posted within 12 months of completion.' : ''}
      </div>
    ` : ''}

    <!-- Study Arms -->
    <section class="section">
      <h2 class="section-title">Study Population & Arms</h2>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Arm</th>
              <th>Type</th>
              <th>Intervention</th>
              <th class="text-center">N</th>
            </tr>
          </thead>
          <tbody>
            ${armsHtml || '<tr><td colspan="4" class="no-data">No arm information available</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

    ${data.hasResults ? `
    <!-- Primary Outcomes -->
    <section class="section">
      <h2 class="section-title">Primary Outcomes</h2>
      ${primaryOutcomesHtml}
    </section>

    <!-- Secondary Outcomes -->
    <section class="section">
      <h2 class="section-title">Secondary Outcomes</h2>
      ${secondaryOutcomesHtml}
    </section>

    <!-- Safety -->
    <section class="section">
      <h2 class="section-title">Adverse Events</h2>
      ${safetyHtml}
    </section>
    ` : ''}

    <footer class="footer">
      <div>Powered by Satya Bio</div>
      <div>Data source: <a href="https://clinicaltrials.gov/study/${data.nctId}" class="link">ClinicalTrials.gov</a></div>
      <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--gray-400);">
        Fetched ${timestamp}. Verify all data before making clinical or investment decisions.
      </div>
    </footer>
  </div>

  <script>
    // Search functionality for AE tables
    document.querySelectorAll('.ae-search').forEach(input => {
      input.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        const tableId = this.dataset.table;
        document.querySelectorAll('#' + tableId + ' tbody tr').forEach(row => {
          const text = row.textContent.toLowerCase();
          row.style.display = text.includes(query) ? '' : 'none';
        });
      });
    });
  </script>
</body>
</html>`;
}

function generateOutcomeSection(outcome: FormattedOutcome, type: string): string {
  const resultsRows = outcome.results.map(r => `
    <tr>
      <td>${escapeHtml(r.armTitle)}</td>
      <td class="result-value">${escapeHtml(r.value)}${outcome.units ? ' ' + escapeHtml(outcome.units) : ''}</td>
      <td class="result-ci">${r.ci ? `[${r.ci.lower}, ${r.ci.upper}]` : r.spread ? `(${r.spread})` : '—'}</td>
      <td class="text-center">${r.n !== undefined ? r.n.toLocaleString() : '—'}</td>
    </tr>
  `).join('');

  const analysisHtml = outcome.analysis ? `
    <div class="analysis-box ${outcome.analysis.pValueSignificant ? '' : 'not-significant'}">
      <div class="analysis-label">Statistical Analysis</div>
      <div style="display: flex; gap: 2rem; flex-wrap: wrap;">
        ${outcome.analysis.pValue ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">P-value</div>
            <div class="p-value ${outcome.analysis.pValueSignificant ? 'p-significant' : 'p-not-significant'}">
              ${escapeHtml(outcome.analysis.pValue)}
              ${outcome.analysis.pValueSignificant ? ' ✓' : ''}
            </div>
          </div>
        ` : ''}
        ${outcome.analysis.estimateValue ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">${outcome.analysis.estimateType || 'Estimate'}</div>
            <div style="font-weight: 600;">${escapeHtml(outcome.analysis.estimateValue)}</div>
          </div>
        ` : ''}
        ${outcome.analysis.ci ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">${outcome.analysis.ci.pct}% CI</div>
            <div>[${outcome.analysis.ci.lower}, ${outcome.analysis.ci.upper}]</div>
          </div>
        ` : ''}
        ${outcome.analysis.method ? `
          <div>
            <div style="font-size: 0.75rem; color: var(--gray-500);">Method</div>
            <div style="font-size: 0.875rem;">${escapeHtml(outcome.analysis.method)}</div>
          </div>
        ` : ''}
      </div>
    </div>
  ` : '';

  return `
    <div class="card">
      <div class="outcome-header">
        <div class="outcome-title">${escapeHtml(outcome.title)}</div>
        <div class="outcome-meta">
          ${outcome.timeFrame ? `<strong>Time Frame:</strong> ${escapeHtml(outcome.timeFrame)}` : ''}
          ${outcome.paramType ? ` | <strong>Measure:</strong> ${escapeHtml(outcome.paramType)}` : ''}
        </div>
        ${outcome.description ? `<div class="outcome-description">${escapeHtml(outcome.description)}</div>` : ''}
      </div>

      ${outcome.results.length > 0 ? `
        <table>
          <thead>
            <tr>
              <th>Arm</th>
              <th>Value</th>
              <th>CI/Spread</th>
              <th class="text-center">N</th>
            </tr>
          </thead>
          <tbody>
            ${resultsRows}
          </tbody>
        </table>
        ${analysisHtml}
      ` : '<p class="no-data">No measurements posted</p>'}
    </div>
  `;
}

function generateSafetySection(safety: FormattedSafety): string {
  // Summary cards
  const summaryHtml = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
      ${safety.arms.map(arm => `
        <div class="card" style="margin-bottom: 0;">
          <div style="font-weight: 600; margin-bottom: 0.5rem;">${escapeHtml(arm.title)}</div>
          <div style="font-size: 0.875rem; color: var(--gray-600);">
            <div>Serious AEs: <strong>${arm.seriousNumAffected}</strong>/${arm.seriousNumAtRisk} (${arm.seriousNumAtRisk > 0 ? ((arm.seriousNumAffected / arm.seriousNumAtRisk) * 100).toFixed(1) : 0}%)</div>
            <div>Other AEs: <strong>${arm.otherNumAffected}</strong>/${arm.otherNumAtRisk} (${arm.otherNumAtRisk > 0 ? ((arm.otherNumAffected / arm.otherNumAtRisk) * 100).toFixed(1) : 0}%)</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;

  // Serious events table
  const seriousEventsHtml = safety.seriousEvents.length > 0 ? `
    <div class="card">
      <div class="card-title">Serious Adverse Events (${safety.seriousEvents.length})</div>
      <input type="text" class="search-box ae-search" data-table="sae-table" placeholder="Search serious events...">
      <div style="max-height: 400px; overflow-y: auto;">
        <table id="sae-table">
          <thead>
            <tr>
              <th>Event Term</th>
              <th>Organ System</th>
              ${safety.arms.map(arm => `<th class="text-center">${escapeHtml(arm.title.substring(0, 20))}</th>`).join('')}
              <th class="text-center">Overall</th>
            </tr>
          </thead>
          <tbody>
            ${safety.seriousEvents.slice(0, 50).map(event => `
              <tr>
                <td><strong>${escapeHtml(event.term)}</strong></td>
                <td style="font-size: 0.8rem; color: var(--gray-500);">${event.organSystem ? escapeHtml(event.organSystem) : '—'}</td>
                ${event.byArm.map(a => `
                  <td class="text-center">
                    <span class="ae-rate ${getRateClass(a.rate)}">${a.rate.toFixed(1)}%</span>
                    <div style="font-size: 0.7rem; color: var(--gray-400);">${a.numAffected}/${a.numAtRisk}</div>
                  </td>
                `).join('')}
                <td class="text-center">
                  <span class="ae-rate ${getRateClass(event.overallRate)}">${event.overallRate.toFixed(1)}%</span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  ` : '<div class="card"><p class="no-data">No serious adverse events reported</p></div>';

  // Other events table (top 30)
  const otherEventsHtml = safety.otherEvents.length > 0 ? `
    <div class="card">
      <div class="card-title">Other Adverse Events (showing top 30 of ${safety.otherEvents.length})</div>
      <input type="text" class="search-box ae-search" data-table="oae-table" placeholder="Search other events...">
      <div style="max-height: 400px; overflow-y: auto;">
        <table id="oae-table">
          <thead>
            <tr>
              <th>Event Term</th>
              <th>Organ System</th>
              ${safety.arms.map(arm => `<th class="text-center">${escapeHtml(arm.title.substring(0, 20))}</th>`).join('')}
              <th class="text-center">Overall</th>
            </tr>
          </thead>
          <tbody>
            ${safety.otherEvents.slice(0, 30).map(event => `
              <tr>
                <td><strong>${escapeHtml(event.term)}</strong></td>
                <td style="font-size: 0.8rem; color: var(--gray-500);">${event.organSystem ? escapeHtml(event.organSystem) : '—'}</td>
                ${event.byArm.map(a => `
                  <td class="text-center">
                    <span class="ae-rate ${getRateClass(a.rate)}">${a.rate.toFixed(1)}%</span>
                    <div style="font-size: 0.7rem; color: var(--gray-400);">${a.numAffected}/${a.numAtRisk}</div>
                  </td>
                `).join('')}
                <td class="text-center">
                  <span class="ae-rate ${getRateClass(event.overallRate)}">${event.overallRate.toFixed(1)}%</span>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  ` : '<div class="card"><p class="no-data">No other adverse events reported</p></div>';

  return `
    ${safety.timeFrame ? `<p style="margin-bottom: 1rem; color: var(--gray-600);"><strong>Time Frame:</strong> ${escapeHtml(safety.timeFrame)}</p>` : ''}
    ${summaryHtml}
    ${seriousEventsHtml}
    ${otherEventsHtml}
  `;
}

function getStatusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('completed')) return 'status-completed';
  if (s.includes('recruiting')) return 'status-recruiting';
  if (s.includes('terminated') || s.includes('withdrawn')) return 'status-terminated';
  return 'status-other';
}

function getRateClass(rate: number): string {
  if (rate >= 10) return 'ae-rate-high';
  if (rate >= 5) return 'ae-rate-medium';
  return 'ae-rate-low';
}

// ============================================
// Trial Comparison HTML Generator
// ============================================

function generateTrialComparisonHtml(comparison: {
  trials: FullTrialData[];
  comparison: {
    populations: { nctId: string; enrollment: number; arms: string[] }[];
    primaryEndpoints: { endpoint: string; byTrial: { nctId: string; value: string; pValue?: string; significant?: boolean }[] }[];
    safetyHighlights: { event: string; byTrial: { nctId: string; rate: number }[] }[];
    endpointDifferences: string[];
  };
}): string {
  const { trials } = comparison;
  const timestamp = new Date().toLocaleString();

  // Build comparison tables
  const populationHtml = `
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          ${trials.map(t => `<th class="text-center">${t.nctId}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Title</strong></td>
          ${trials.map(t => `<td style="font-size: 0.8rem;">${escapeHtml(t.title.substring(0, 60))}...</td>`).join('')}
        </tr>
        <tr>
          <td><strong>Phase</strong></td>
          ${trials.map(t => `<td class="text-center"><span class="phase-badge ${getTrialPhaseClass(t.phase)}">${escapeHtml(t.phase)}</span></td>`).join('')}
        </tr>
        <tr>
          <td><strong>Status</strong></td>
          ${trials.map(t => `<td class="text-center"><span class="status-badge ${getStatusBadgeClass(t.status)}">${escapeHtml(t.status)}</span></td>`).join('')}
        </tr>
        <tr>
          <td><strong>Sponsor</strong></td>
          ${trials.map(t => `<td style="font-size: 0.85rem;">${escapeHtml(t.sponsor)}</td>`).join('')}
        </tr>
        <tr>
          <td><strong>Enrollment</strong></td>
          ${trials.map(t => `<td class="text-center">${t.enrollment.toLocaleString()}</td>`).join('')}
        </tr>
        <tr>
          <td><strong>Arms</strong></td>
          ${trials.map(t => `<td style="font-size: 0.8rem;">${t.arms.map(a => `${escapeHtml(a.title)} (N=${a.n || '?'})`).join('<br>')}</td>`).join('')}
        </tr>
      </tbody>
    </table>
  `;

  const endpointsHtml = comparison.comparison.primaryEndpoints.length > 0 ? `
    <table>
      <thead>
        <tr>
          <th>Primary Endpoint</th>
          ${trials.map(t => `<th class="text-center">${t.nctId}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${comparison.comparison.primaryEndpoints.map(ep => `
          <tr>
            <td><strong>${escapeHtml(ep.endpoint.substring(0, 50))}${ep.endpoint.length > 50 ? '...' : ''}</strong></td>
            ${trials.map(t => {
              const result = ep.byTrial.find(r => r.nctId === t.nctId);
              if (!result) return '<td class="text-center" style="color: var(--gray-400);">N/A</td>';
              return `
                <td class="text-center">
                  <div class="result-value">${escapeHtml(result.value)}</div>
                  ${result.pValue ? `<div class="p-value ${result.significant ? 'p-significant' : 'p-not-significant'}">${escapeHtml(result.pValue)}</div>` : ''}
                </td>
              `;
            }).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  ` : '<p class="no-data">No primary endpoint data available for comparison</p>';

  const safetyHtml = comparison.comparison.safetyHighlights.length > 0 ? `
    <table>
      <thead>
        <tr>
          <th>Adverse Event</th>
          ${trials.map(t => `<th class="text-center">${t.nctId}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
        ${comparison.comparison.safetyHighlights.map(event => `
          <tr>
            <td><strong>${escapeHtml(event.event)}</strong></td>
            ${trials.map(t => {
              const result = event.byTrial.find(r => r.nctId === t.nctId);
              if (!result) return '<td class="text-center" style="color: var(--gray-400);">—</td>';
              return `<td class="text-center"><span class="ae-rate ${getRateClass(result.rate)}">${result.rate.toFixed(1)}%</span></td>`;
            }).join('')}
          </tr>
        `).join('')}
      </tbody>
    </table>
  ` : '<p class="no-data">No common adverse events to compare</p>';

  const differencesHtml = comparison.comparison.endpointDifferences.length > 0 ? `
    <div class="card" style="background: #fef3c7; border-color: #f59e0b;">
      <div class="card-title" style="color: #92400e;">Endpoint Differences</div>
      <ul style="margin-left: 1.5rem; color: #92400e;">
        ${comparison.comparison.endpointDifferences.map(d => `<li>${escapeHtml(d)}</li>`).join('')}
      </ul>
    </div>
  ` : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trial Comparison | Satya Bio</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --gray-50: #f9fafb;
      --gray-100: #f3f4f6;
      --gray-200: #e5e7eb;
      --gray-400: #9ca3af;
      --gray-500: #6b7280;
      --gray-700: #374151;
      --gray-900: #111827;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--gray-50);
      color: var(--gray-900);
      line-height: 1.6;
    }

    .header {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
      color: white;
      padding: 2rem;
    }

    .header h1 {
      font-size: 1.75rem;
      font-weight: 600;
      max-width: 1200px;
      margin: 0 auto;
    }

    .header-subtitle {
      max-width: 1200px;
      margin: 0.5rem auto 0;
      opacity: 0.9;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
    }

    .section {
      margin-bottom: 2rem;
    }

    .section-title {
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1rem;
    }

    .card {
      background: white;
      border: 1px solid var(--gray-200);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1rem;
      overflow-x: auto;
    }

    .card-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--gray-700);
      margin-bottom: 1rem;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }

    th {
      text-align: left;
      padding: 0.75rem;
      background: var(--gray-50);
      font-weight: 600;
      color: var(--gray-500);
      font-size: 0.75rem;
      text-transform: uppercase;
      border-bottom: 2px solid var(--gray-200);
      white-space: nowrap;
    }

    td {
      padding: 0.75rem;
      border-bottom: 1px solid var(--gray-100);
      vertical-align: top;
    }

    tr:hover { background: var(--gray-50); }

    .text-center { text-align: center; }

    .phase-badge, .status-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .phase-4, .phase-approved { background: #dcfce7; color: #166534; }
    .phase-3 { background: #dbeafe; color: #1e40af; }
    .phase-2 { background: #fef3c7; color: #92400e; }
    .phase-1 { background: var(--gray-100); color: var(--gray-700); }
    .phase-na { background: var(--gray-100); color: var(--gray-500); }

    .status-completed { background: #dcfce7; color: #166534; }
    .status-recruiting { background: #dbeafe; color: #1e40af; }
    .status-terminated { background: #fee2e2; color: #991b1b; }
    .status-other { background: var(--gray-200); color: var(--gray-700); }

    .result-value { font-weight: 600; }

    .p-value { font-size: 0.8rem; margin-top: 0.25rem; }
    .p-significant { color: var(--success); }
    .p-not-significant { color: var(--gray-500); }

    .ae-rate { font-weight: 600; }
    .ae-rate-high { color: var(--danger); }
    .ae-rate-medium { color: var(--warning); }
    .ae-rate-low { color: var(--gray-700); }

    .no-data { color: var(--gray-500); font-style: italic; padding: 1rem; text-align: center; }

    .link { color: var(--primary); text-decoration: none; }
    .link:hover { text-decoration: underline; }

    .footer {
      text-align: center;
      padding: 2rem;
      color: var(--gray-500);
      font-size: 0.875rem;
    }
  </style>
</head>
<body>
  <header class="header">
    <h1>Trial Comparison</h1>
    <div class="header-subtitle">
      Comparing ${trials.length} trials: ${trials.map(t => `<a href="/api/trial/${t.nctId}/results/html" style="color: white;">${t.nctId}</a>`).join(', ')}
    </div>
  </header>

  <div class="container">
    ${differencesHtml}

    <section class="section">
      <h2 class="section-title">Study Overview</h2>
      <div class="card">
        ${populationHtml}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Primary Efficacy Endpoints</h2>
      <div class="card">
        ${endpointsHtml}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Safety Comparison</h2>
      <div class="card">
        ${safetyHtml}
      </div>
    </section>

    <footer class="footer">
      <div>Powered by Satya Bio</div>
      <div>Data source: ClinicalTrials.gov | ${timestamp}</div>
    </footer>
  </div>
</body>
</html>`;
}

// ============================================
// Patent Profile HTML
// ============================================

function generatePatentProfileHtml(profile: DrugPatentProfile): string {
  const timestamp = new Date().toLocaleString();

  // LOE status badge
  const daysUntil = profile.daysUntilLOE;
  let loeStatus = '';
  let loeClass = '';
  if (daysUntil === null) {
    loeStatus = 'Unknown';
    loeClass = 'badge-gray';
  } else if (daysUntil <= 0) {
    loeStatus = 'Expired';
    loeClass = 'badge-red';
  } else if (daysUntil <= 365) {
    loeStatus = `${Math.round(daysUntil / 30)} months`;
    loeClass = 'badge-red';
  } else if (daysUntil <= 365 * 3) {
    loeStatus = `${(daysUntil / 365).toFixed(1)} years`;
    loeClass = 'badge-orange';
  } else {
    loeStatus = `${(daysUntil / 365).toFixed(1)} years`;
    loeClass = 'badge-green';
  }

  // Patent table rows
  const patentRows = profile.patents.map(p => {
    const typeFlags: string[] = [];
    if (p.drugSubstance) typeFlags.push('Substance');
    if (p.drugProduct) typeFlags.push('Product');
    if (p.patentUseCode) typeFlags.push(`Use: ${p.patentUseCode}`);
    return `<tr>
      <td><a href="https://patents.google.com/patent/US${p.patentNumber}" target="_blank">${p.patentNumber}</a></td>
      <td>${typeFlags.join(', ') || '—'}</td>
      <td>${p.expiryDate || '—'}</td>
      <td>${p.expiryDateParsed || '—'}</td>
      <td>${p.delistFlag ? 'Yes' : 'No'}</td>
    </tr>`;
  }).join('\n');

  // Exclusivity table rows
  const exclRows = profile.exclusivities.map(e => `<tr>
    <td><strong>${e.exclusivityCode}</strong></td>
    <td>${e.exclusivityType}</td>
    <td>${e.exclusivityDate}</td>
    <td>${e.exclusivityDateParsed || '—'}</td>
  </tr>`).join('\n');

  // Patent expiry timeline visualization
  const today = new Date();
  const timelineStart = today.getFullYear();
  const timelineEnd = timelineStart + 15;
  const timelineYears: number[] = [];
  for (let y = timelineStart; y <= timelineEnd; y++) timelineYears.push(y);

  // Group patents by expiry year
  const patentsByYear = new Map<number, OrangeBookPatent[]>();
  for (const p of profile.patents) {
    if (p.expiryDateParsed) {
      const year = new Date(p.expiryDateParsed).getFullYear();
      if (!patentsByYear.has(year)) patentsByYear.set(year, []);
      patentsByYear.get(year)!.push(p);
    }
  }

  const timelineBars = timelineYears.map(year => {
    const patents = patentsByYear.get(year) || [];
    const count = patents.length;
    const height = count > 0 ? Math.max(20, Math.min(count * 15, 150)) : 0;
    const isPast = year < today.getFullYear();
    const isLOEYear = profile.effectiveLOE && new Date(profile.effectiveLOE).getFullYear() === year;
    const barClass = isLOEYear ? 'timeline-bar-loe' : isPast ? 'timeline-bar-past' : count > 0 ? 'timeline-bar-active' : '';
    return `<div class="timeline-col">
      <div class="timeline-bar ${barClass}" style="height: ${height}px" title="${count} patents expire in ${year}">
        ${count > 0 ? `<span class="timeline-count">${count}</span>` : ''}
      </div>
      <div class="timeline-label${isLOEYear ? ' timeline-loe-label' : ''}">${year}</div>
    </div>`;
  }).join('\n');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Patent Profile: ${profile.brandName} - Satya Bio</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a1a; color: #e0e0e0; line-height: 1.6; }
    .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #1a1a3e, #2d1b4e); border-radius: 12px; padding: 30px; margin-bottom: 20px; }
    .header h1 { font-size: 2em; color: #fff; margin-bottom: 5px; }
    .header .subtitle { color: #aaa; font-size: 1.1em; }
    .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
    .meta-card { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; }
    .meta-label { color: #888; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; }
    .meta-value { font-size: 1.3em; font-weight: 600; color: #fff; margin-top: 4px; }
    .section { margin-bottom: 25px; }
    .section-title { font-size: 1.3em; color: #fff; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 1px solid #333; }
    .card { background: #12122a; border-radius: 10px; padding: 20px; border: 1px solid #222; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }
    .badge-green { background: rgba(0,200,100,0.15); color: #00c864; }
    .badge-orange { background: rgba(255,165,0,0.15); color: #ffa500; }
    .badge-red { background: rgba(255,60,60,0.15); color: #ff3c3c; }
    .badge-gray { background: rgba(150,150,150,0.15); color: #999; }
    .badge-blue { background: rgba(100,149,237,0.15); color: #6495ed; }
    table { width: 100%; border-collapse: collapse; }
    th { text-align: left; padding: 10px 12px; background: rgba(255,255,255,0.05); color: #aaa; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }
    td { padding: 10px 12px; border-top: 1px solid #1a1a35; }
    td a { color: #6495ed; text-decoration: none; }
    td a:hover { text-decoration: underline; }
    tr:hover td { background: rgba(255,255,255,0.03); }
    .loe-banner { background: linear-gradient(135deg, #1a2a1a, #1a3a1a); border: 1px solid #2a4a2a; border-radius: 10px; padding: 25px; text-align: center; margin-bottom: 25px; }
    .loe-date { font-size: 2em; font-weight: 700; color: #fff; }
    .loe-detail { color: #aaa; margin-top: 5px; }
    .timeline { display: flex; align-items: flex-end; gap: 4px; height: 180px; padding: 10px 0; }
    .timeline-col { display: flex; flex-direction: column; align-items: center; flex: 1; }
    .timeline-bar { width: 100%; max-width: 50px; border-radius: 4px 4px 0 0; display: flex; align-items: flex-end; justify-content: center; transition: all 0.3s; }
    .timeline-bar-active { background: linear-gradient(to top, #4a6cf7, #6a8cff); }
    .timeline-bar-past { background: #333; }
    .timeline-bar-loe { background: linear-gradient(to top, #ff3c3c, #ff6b6b); }
    .timeline-count { color: #fff; font-size: 0.8em; font-weight: 600; padding: 4px; }
    .timeline-label { font-size: 0.75em; color: #888; margin-top: 5px; writing-mode: vertical-rl; text-orientation: mixed; }
    .timeline-loe-label { color: #ff3c3c; font-weight: 700; }
    .footer { text-align: center; color: #555; font-size: 0.85em; margin-top: 30px; padding: 15px; border-top: 1px solid #222; }
    .empty-msg { color: #666; font-style: italic; padding: 20px; text-align: center; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>${profile.brandName}</h1>
      <div class="subtitle">${profile.drugName} | ${profile.sponsor} | ${profile.approval.applicationNumber}</div>
      <div class="meta-grid">
        <div class="meta-card">
          <div class="meta-label">Application Type</div>
          <div class="meta-value">
            <span class="badge ${profile.approval.isBiologic ? 'badge-blue' : 'badge-green'}">${profile.approval.applicationType}</span>
          </div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Approval Date</div>
          <div class="meta-value">${profile.approval.approvalDate || 'Unknown'}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Unique Patents</div>
          <div class="meta-value">${profile.uniquePatentNumbers.length}</div>
        </div>
        <div class="meta-card">
          <div class="meta-label">Exclusivities</div>
          <div class="meta-value">${profile.exclusivities.length}</div>
        </div>
      </div>
    </div>

    <div class="loe-banner">
      <div style="color: #888; font-size: 0.9em; text-transform: uppercase; letter-spacing: 2px;">Effective Loss of Exclusivity</div>
      <div class="loe-date">${profile.effectiveLOE || 'Unknown'}</div>
      <div class="loe-detail">
        <span class="badge ${loeClass}">${loeStatus} remaining</span>
        ${profile.biologicExclusivityExpiry ? `<span style="color:#888; margin-left:10px;">BPCIA 12-year: ${profile.biologicExclusivityExpiry}</span>` : ''}
      </div>
      <div class="loe-detail" style="margin-top:8px;">
        ${profile.latestPatentExpiry ? `Latest Patent: ${profile.latestPatentExpiry}` : ''}
        ${profile.latestPatentExpiry && profile.latestExclusivityExpiry ? ' | ' : ''}
        ${profile.latestExclusivityExpiry ? `Latest Exclusivity: ${profile.latestExclusivityExpiry}` : ''}
      </div>
    </div>

    <section class="section">
      <h2 class="section-title">Patent Expiry Timeline</h2>
      <div class="card">
        ${profile.patents.length > 0 ? `<div class="timeline">${timelineBars}</div>
        <div style="text-align:center; margin-top:10px; font-size:0.85em; color:#888;">
          <span style="display:inline-block; width:12px; height:12px; background:#4a6cf7; border-radius:2px; margin-right:4px;"></span> Active patents
          <span style="display:inline-block; width:12px; height:12px; background:#ff3c3c; border-radius:2px; margin-left:15px; margin-right:4px;"></span> LOE year
          <span style="display:inline-block; width:12px; height:12px; background:#333; border-radius:2px; margin-left:15px; margin-right:4px;"></span> Past
        </div>` : '<div class="empty-msg">No Orange Book patent data (biologic products use BPCIA exclusivity)</div>'}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Orange Book Patents (${profile.patents.length})</h2>
      <div class="card">
        ${profile.patents.length > 0 ? `<table>
          <thead><tr><th>Patent #</th><th>Type</th><th>Expiry</th><th>ISO Date</th><th>Delisted</th></tr></thead>
          <tbody>${patentRows}</tbody>
        </table>` : '<div class="empty-msg">No patents listed in Orange Book</div>'}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">Exclusivities (${profile.exclusivities.length})</h2>
      <div class="card">
        ${profile.exclusivities.length > 0 ? `<table>
          <thead><tr><th>Code</th><th>Type</th><th>Expiry</th><th>ISO Date</th></tr></thead>
          <tbody>${exclRows}</tbody>
        </table>` : `<div class="empty-msg">No exclusivities listed${profile.approval.isBiologic ? ' (biologic &mdash; 12-year BPCIA exclusivity applies)' : ''}</div>`}
      </div>
    </section>

    <footer class="footer">
      <div>Satya Bio | Patent & Exclusivity Tracker</div>
      <div>Data: FDA Orange Book + OpenFDA | ${timestamp}</div>
    </footer>
  </div>
</body>
</html>`;
}

// ============================================
// Patent Timeline HTML (by Condition)
// ============================================

function generatePatentTimelineHtml(condition: string, profiles: DrugPatentProfile[]): string {
  const timestamp = new Date().toLocaleString();
  const condTitle = condition.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

  // Build timeline data: group by year
  const today = new Date();
  const currentYear = today.getFullYear();
  const timelineStart = currentYear;
  const timelineEnd = currentYear + 15;

  // Create LOE timeline rows
  const drugRows = profiles.map(profile => {
    const loeYear = profile.effectiveLOE ? new Date(profile.effectiveLOE).getFullYear() : null;
    const daysUntil = profile.daysUntilLOE;
    let urgency = '';
    if (daysUntil === null) urgency = 'unknown';
    else if (daysUntil <= 0) urgency = 'expired';
    else if (daysUntil <= 365 * 2) urgency = 'imminent';
    else if (daysUntil <= 365 * 5) urgency = 'approaching';
    else urgency = 'protected';

    // Timeline bar
    const barCells = [];
    for (let y = timelineStart; y <= timelineEnd; y++) {
      const isLOE = loeYear === y;
      const isProtected = loeYear !== null && y < loeYear;
      const isExpired = loeYear !== null && y > loeYear;
      let cellClass = 'tl-empty';
      if (isLOE) cellClass = 'tl-loe';
      else if (isProtected) cellClass = 'tl-protected';
      else if (isExpired) cellClass = 'tl-expired';
      barCells.push(`<td class="tl-cell ${cellClass}" title="${profile.brandName}: ${isLOE ? 'LOE' : isProtected ? 'Protected' : isExpired ? 'Exposed' : 'Unknown'} in ${y}"></td>`);
    }

    return `<tr>
      <td class="drug-name">
        <a href="/api/patents/${encodeURIComponent(profile.brandName.toLowerCase())}/html">${profile.brandName}</a>
        <div class="drug-sub">${profile.drugName} | ${profile.sponsor}</div>
      </td>
      <td><span class="badge badge-${profile.approval.applicationType === 'BLA' ? 'blue' : 'green'}">${profile.approval.applicationType}</span></td>
      <td>${profile.uniquePatentNumbers.length}</td>
      <td class="loe-cell loe-${urgency}">${profile.effectiveLOE || '—'}</td>
      ${barCells.join('\n')}
    </tr>`;
  }).join('\n');

  // Year headers
  const yearHeaders = [];
  for (let y = timelineStart; y <= timelineEnd; y++) {
    yearHeaders.push(`<th class="tl-header">${y.toString().slice(2)}</th>`);
  }

  // Summary stats
  const loeThisYear = profiles.filter(p => p.effectiveLOE && new Date(p.effectiveLOE).getFullYear() === currentYear).length;
  const loeNext3Years = profiles.filter(p => {
    if (!p.effectiveLOE) return false;
    const y = new Date(p.effectiveLOE).getFullYear();
    return y >= currentYear && y <= currentYear + 3;
  }).length;
  const biologics = profiles.filter(p => p.approval.isBiologic).length;
  const totalPatents = profiles.reduce((sum, p) => sum + p.uniquePatentNumbers.length, 0);

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Patent Timeline: ${condTitle} - Satya Bio</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a1a; color: #e0e0e0; line-height: 1.6; }
    .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #1a1a3e, #2d1b4e); border-radius: 12px; padding: 30px; margin-bottom: 20px; }
    .header h1 { font-size: 2em; color: #fff; }
    .header .subtitle { color: #aaa; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-top: 20px; }
    .stat-card { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 15px; text-align: center; }
    .stat-num { font-size: 2em; font-weight: 700; color: #fff; }
    .stat-label { color: #888; font-size: 0.85em; }
    .section { margin-bottom: 25px; }
    .section-title { font-size: 1.3em; color: #fff; margin-bottom: 15px; }
    .card { background: #12122a; border-radius: 10px; padding: 20px; border: 1px solid #222; overflow-x: auto; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 0.8em; font-weight: 600; }
    .badge-green { background: rgba(0,200,100,0.15); color: #00c864; }
    .badge-blue { background: rgba(100,149,237,0.15); color: #6495ed; }
    table { width: 100%; border-collapse: collapse; white-space: nowrap; }
    th { text-align: left; padding: 8px 10px; background: rgba(255,255,255,0.05); color: #aaa; font-size: 0.8em; text-transform: uppercase; letter-spacing: 0.5px; position: sticky; top: 0; }
    td { padding: 8px 10px; border-top: 1px solid #1a1a35; font-size: 0.9em; }
    .drug-name a { color: #6495ed; text-decoration: none; font-weight: 600; }
    .drug-name a:hover { text-decoration: underline; }
    .drug-sub { color: #666; font-size: 0.8em; }
    .loe-cell { font-weight: 600; }
    .loe-expired { color: #ff3c3c; }
    .loe-imminent { color: #ff8c00; }
    .loe-approaching { color: #ffd700; }
    .loe-protected { color: #00c864; }
    .loe-unknown { color: #666; }
    .tl-cell { width: 30px; min-width: 30px; height: 20px; border: 1px solid #1a1a35; }
    .tl-protected { background: rgba(0,200,100,0.25); }
    .tl-loe { background: #ff3c3c; }
    .tl-expired { background: rgba(255,60,60,0.1); }
    .tl-empty { background: transparent; }
    .tl-header { text-align: center; font-size: 0.75em; width: 30px; min-width: 30px; }
    .footer { text-align: center; color: #555; font-size: 0.85em; margin-top: 30px; padding: 15px; border-top: 1px solid #222; }
    .legend { display: flex; gap: 20px; margin-top: 15px; font-size: 0.85em; color: #888; }
    .legend-item { display: flex; align-items: center; gap: 5px; }
    .legend-color { width: 16px; height: 12px; border-radius: 2px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Patent & Exclusivity Timeline</h1>
      <div class="subtitle">${condTitle} — ${profiles.length} drugs analyzed</div>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-num">${profiles.length}</div>
          <div class="stat-label">Drugs Tracked</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${totalPatents}</div>
          <div class="stat-label">Total Patents</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${biologics}</div>
          <div class="stat-label">Biologics (BLA)</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: ${loeThisYear > 0 ? '#ff3c3c' : '#00c864'}">${loeThisYear}</div>
          <div class="stat-label">LOE This Year</div>
        </div>
        <div class="stat-card">
          <div class="stat-num" style="color: ${loeNext3Years > 0 ? '#ffa500' : '#00c864'}">${loeNext3Years}</div>
          <div class="stat-label">LOE Next 3 Years</div>
        </div>
      </div>
    </div>

    <section class="section">
      <h2 class="section-title">LOE Timeline</h2>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Drug</th>
              <th>Type</th>
              <th>Patents</th>
              <th>Eff. LOE</th>
              ${yearHeaders.join('\n')}
            </tr>
          </thead>
          <tbody>
            ${drugRows}
          </tbody>
        </table>
        <div class="legend">
          <div class="legend-item"><div class="legend-color" style="background: rgba(0,200,100,0.25);"></div> Protected</div>
          <div class="legend-item"><div class="legend-color" style="background: #ff3c3c;"></div> LOE Year</div>
          <div class="legend-item"><div class="legend-color" style="background: rgba(255,60,60,0.1);"></div> Exposed</div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div>Satya Bio | Patent & Exclusivity Tracker</div>
      <div>Data: FDA Orange Book + OpenFDA + BPCIA | ${timestamp}</div>
    </footer>
  </div>
</body>
</html>`;
}

// ============================================
// Data Source Indicator Helper
// ============================================

function buildDataSourceIndicator(dataSource: any): string {
  if (!dataSource) {
    return '';
  }

  const { type, lastUpdated, fromCache, cacheAge, assetsDiscovered, totalSourcesChecked, error } = dataSource;

  if (type === 'curated') {
    return `
      <div class="data-source-indicator curated">
        <span class="source-icon">&#9989;</span>
        <span class="source-text">
          <strong>Curated Database</strong> - Investment-grade data, manually verified
          <span class="source-date">(Last updated: ${lastUpdated || 'Recent'})</span>
        </span>
      </div>`;
  }

  if (type === 'ai-research') {
    // Check if there was an error
    if (error) {
      return `
        <div class="data-source-indicator ai-error">
          <span class="source-icon">&#9888;</span>
          <span class="source-text">
            <strong>AI Research Failed</strong> - ${escapeHtml(error)}
            <br><small>Clinical trials and publications are still shown below. To enable AI research, configure a valid ANTHROPIC_API_KEY.</small>
          </span>
          <a href="?refresh=true" class="refresh-btn" title="Retry research">&#128260; Retry</a>
        </div>`;
    }

    const cacheInfo = fromCache
      ? `<span class="cache-badge">Cached ${cacheAge} ago</span>`
      : '<span class="fresh-badge">Fresh research</span>';

    return `
      <div class="data-source-indicator ai-research">
        <span class="source-icon">&#129302;</span>
        <span class="source-text">
          <strong>AI Research Agent</strong> - Discovered ${assetsDiscovered || 0} assets from ${totalSourcesChecked || 'multiple'} sources
          ${cacheInfo}
        </span>
        <a href="?refresh=true" class="refresh-btn" title="Refresh research">&#128260; Refresh</a>
      </div>`;
  }

  return '';
}

// ============================================
// Target Report HTML Generator
// ============================================

function generateTargetReportHtml(report: any, trialAnalytics: any, targetAnalysis?: TargetAnalysis | null): string {
  // Format date cleanly (no time)
  const now = new Date();
  const timestamp = now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  const { target, summary, trials, publications, deals, kols, curatedAssets, investmentMetrics, dataSource } = report;
  const assetCount = curatedAssets?.length || 0;

  // Build data source indicator
  const dataSourceHtml = buildDataSourceIndicator(dataSource);

  // Helper: Format deal values - show $M for <1B, $B for >=1B
  const formatDealValue = (valueInMillions: number): string => {
    if (!valueInMillions || valueInMillions === 0) return '$0';
    if (valueInMillions >= 1000) {
      return `$${(valueInMillions / 1000).toFixed(1)}B`;
    } else {
      return `$${Math.round(valueInMillions)}M`;
    }
  };

  // Trial rows
  const trialRows = trials.slice(0, 50).map((t: any) => `
    <tr>
      <td><a href="https://clinicaltrials.gov/study/${t.nctId}" target="_blank">${t.nctId}</a></td>
      <td class="title-cell">${t.briefTitle}</td>
      <td><span class="phase-badge phase-${(t.phase || '').toLowerCase().replace(/[^a-z0-9]/g, '')}">${t.phase}</span></td>
      <td><span class="status-badge status-${(t.status || '').toLowerCase().replace(/[^a-z]/g, '-')}">${t.status}</span></td>
      <td>${t.leadSponsor?.name || '-'}</td>
      <td>${t.enrollment?.count || '-'}</td>
      <td>${t.startDate || '-'}</td>
    </tr>
  `).join('');

  // Asset cards (curated investment-quality data)
  const assetCards = (curatedAssets || []).map((a: any) => {
    const regBadges = [];
    if (a.regulatory?.btd) regBadges.push('<span class="reg-pill">BTD</span>');
    if (a.regulatory?.odd) regBadges.push('<span class="reg-pill">ODD</span>');
    if (a.regulatory?.prime) regBadges.push('<span class="reg-pill">PRIME</span>');
    if (a.regulatory?.fastTrack) regBadges.push('<span class="reg-pill">FT</span>');

    const linkedTrials = (a.trialIds || []).slice(0, 4).map((nct: string) =>
      `<a href="https://clinicaltrials.gov/study/${nct}" target="_blank" class="trial-nct">${nct}</a>`
    ).join(' ');

    const phaseClass = (a.phase || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    const statusClass = (a.status || '').toLowerCase() === 'active' ? 'active' : 'inactive';

    // Build other indications list
    const otherIndications = (a.indications || []).filter((i: string) => i !== a.leadIndication).slice(0, 3);

    return `
    <div class="asset-card">
      <div class="asset-header">
        <div class="asset-name-section">
          <div class="asset-name">${a.primaryName}</div>
          ${a.codeNames?.length ? `<div class="asset-codes">${a.codeNames.join(', ')}</div>` : ''}
        </div>
        <div class="asset-badges">
          <span class="phase-pill phase-${phaseClass}">${a.phase}</span>
          <span class="status-pill status-${statusClass}">${a.status}</span>
        </div>
      </div>

      <div class="asset-meta">
        <span class="modality-pill">${a.modality}</span>
        <span class="meta-separator">•</span>
        <span class="asset-moa">${a.modalityDetail || a.payload || a.mechanism || ''}</span>
      </div>
      <div class="asset-owner">
        ${a.owner || '-'}${a.ownerType ? ` <span class="owner-type-tag">(${a.ownerType})</span>` : ''}${a.partner ? ` + ${a.partner}` : ''}
      </div>

      <div class="asset-indications">
        <div class="lead-indication"><strong>Lead:</strong> ${a.leadIndication || '-'}</div>
        ${otherIndications.length ? `<div class="other-indications"><strong>Also:</strong> ${otherIndications.join(', ')}</div>` : ''}
      </div>

      ${a.deal || a.keyData ? `
      <div class="asset-highlights">
        ${a.deal ? `
          <div class="deal-info">
            ${formatDealValue(a.deal.committed || 0)} committed${a.deal.partner ? ` to ${a.deal.partner}` : ''}
            ${a.deal.hasBreakdown ? `
              <div class="deal-breakdown">
                ${a.deal.upfront ? `• ${formatDealValue(a.deal.upfront)} upfront` : ''}
                ${a.deal.equity ? ` + ${formatDealValue(a.deal.equity)} equity` : ''}
                ${a.deal.milestones ? `<br>• Up to ${formatDealValue(a.deal.milestones)} in milestones` : ''}
                ${a.deal.totalPotential ? `<br>• Total potential: ${formatDealValue(a.deal.totalPotential)}` : ''}
              </div>
            ` : `<span class="unverified-deal"> ★ unverified</span>`}
          </div>
        ` : ''}
        ${a.keyData ? `<div class="key-data-info">${a.keyData}</div>` : ''}
      </div>
      ` : ''}

      <div class="asset-footer">
        ${linkedTrials ? `<div class="trials-row"><strong>Trials:</strong> ${linkedTrials}</div>` : ''}
        ${regBadges.length ? `<div class="reg-row">${regBadges.join('')}</div>` : ''}
      </div>
    </div>`;
  }).join('');

  // Publication rows
  const pubRows = publications.slice(0, 20).map((p: any) => `
    <tr>
      <td>${p.pmid ? `<a href="https://pubmed.ncbi.nlm.nih.gov/${p.pmid}" target="_blank">${p.pmid}</a>` : '-'}</td>
      <td class="title-cell">${p.title}</td>
      <td>${(p.authors || []).slice(0, 3).map((a: any) => `${a.lastName}`).join(', ')}${p.authors?.length > 3 ? ' et al.' : ''}</td>
      <td>${p.journal || '-'}</td>
      <td>${p.publicationDate?.split('-')[0] || '-'}</td>
    </tr>
  `).join('');

  // Deal rows
  const dealRows = deals.map((d: any) => `
    <tr>
      <td>${d.date || d.announcedDate || '-'}</td>
      <td><span class="deal-badge">${d.dealType || d.type || '-'}</span></td>
      <td>${(d.parties || []).join(' + ')}</td>
      <td>${d.assetName || d.asset?.name || '-'}</td>
      <td>${d.terms?.totalValue ? `$${d.terms.totalValue}M` : d.terms?.upfrontPayment ? `$${d.terms.upfrontPayment}M upfront` : '-'}</td>
    </tr>
  `).join('');

  // Author rows (derived from publications, no fake h-index)
  const authorRows = kols.map((k: any) => `
    <tr>
      <td><strong>${k.name || `${k.lastName || ''} ${k.foreName || ''}`.trim()}</strong></td>
      <td>${k.institution || '-'}</td>
      <td>${k.publicationCount || 0}</td>
      <td>${k.firstAuthorCount || 0}</td>
      <td>${k.lastAuthorCount || 0}</td>
      <td>${k.isActive ? '<span class="active-badge">Active</span>' : '<span class="inactive-badge">Inactive</span>'}</td>
    </tr>
  `).join('');

  // Phase breakdown
  const phaseLabels = Object.keys(trialAnalytics.phaseBreakdown);
  const phaseCounts = Object.values(trialAnalytics.phaseBreakdown) as number[];
  const maxPhaseCount = Math.max(...phaseCounts, 1);
  const phaseChart = phaseLabels.map((label, i) => {
    const pct = (phaseCounts[i] / maxPhaseCount) * 100;
    return `<div class="bar-row"><span class="bar-label">${label}</span><div class="bar-container"><div class="bar" style="width: ${pct}%"></div><span class="bar-value">${phaseCounts[i]}</span></div></div>`;
  }).join('');

  // Top sponsors
  const sponsorRows = (trialAnalytics.topSponsors || []).slice(0, 10).map((s: any) => `
    <tr>
      <td>${s.sponsor}</td>
      <td>${s.count}</td>
      <td><span class="type-badge ${s.type?.toLowerCase()}">${s.type}</span></td>
    </tr>
  `).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${target} - Satya Bio Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --background: #FAF9F7;
      --surface: #FFFFFF;
      --surface-hover: #F5F4F2;
      --border: #E5E4E2;
      --text-primary: #1A1915;
      --text-secondary: #706F6C;
      --text-muted: #9B9A97;
      --accent: #D97756;
      --accent-hover: #C4684A;
      --success: #5B8C6F;
      --warning: #D4A84B;
      --error: #C75D5D;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--background); color: var(--text-primary); line-height: 1.6; }
    .container { max-width: 1400px; margin: 0 auto; padding: 24px; }
    .header { background: var(--surface); padding: 32px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    h1 { color: var(--text-primary); font-size: 2rem; font-weight: 600; margin-bottom: 8px; }
    .subtitle { color: var(--text-secondary); margin-bottom: 24px; }
    .nav { display: flex; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }
    .nav a { background: var(--background); color: var(--text-secondary); padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 0.9rem; font-weight: 500; border: 1px solid var(--border); transition: all 0.2s; }
    .nav a:hover { background: var(--surface-hover); color: var(--text-primary); }
    .nav a.download { background: var(--accent); color: white; border-color: var(--accent); }
    .nav a.download:hover { background: var(--accent-hover); }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-top: 24px; }
    .stat-card { background: var(--background); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border); }
    .stat-num { font-size: 1.8rem; font-weight: 600; color: var(--accent); }
    .stat-label { font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; }
    .section { margin-bottom: 32px; }
    .section-title { color: var(--text-primary); font-size: 1.2rem; font-weight: 600; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }
    .card { background: var(--surface); border-radius: 10px; padding: 20px; overflow-x: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    th { background: var(--background); color: var(--text-secondary); padding: 12px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; position: sticky; top: 0; border-bottom: 1px solid var(--border); }
    td { padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
    tr:nth-child(even) { background: var(--background); }
    tr:hover { background: var(--surface-hover); }
    .title-cell { max-width: 400px; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; color: var(--accent-hover); }
    .phase-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; background: var(--background); border: 1px solid var(--border); }
    .phase-badge.phase-phase3, .phase-badge.phase-filed { background: #E8F5E9; color: #2E7D32; border-color: #C8E6C9; }
    .phase-badge.phase-phase2 { background: #FFF8E1; color: #F57F17; border-color: #FFECB3; }
    .phase-badge.phase-phase1 { background: #E3F2FD; color: #1565C0; border-color: #BBDEFB; }
    .status-badge { padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
    .status-badge.status-recruiting, .status-badge.status-active { background: #E8F5E9; color: #2E7D32; }
    .status-badge.status-completed { background: var(--background); color: var(--text-secondary); }
    .active-badge { background: #E8F5E9; color: #2E7D32; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; }
    .inactive-badge { background: var(--background); color: var(--text-muted); padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; }
    .type-badge { padding: 3px 8px; border-radius: 4px; font-size: 0.7rem; text-transform: uppercase; font-weight: 500; }
    .type-badge.industry { background: #F3E5F5; color: #7B1FA2; }
    .type-badge.academic { background: #E0F7FA; color: #00838F; }
    /* Asset Card Grid */
    .asset-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 20px; }
    .asset-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); transition: box-shadow 0.2s, transform 0.2s; }
    .asset-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }
    .asset-header { display: flex; justify-content: space-between; align-items: flex-start; padding: 18px 20px 12px; border-bottom: 1px solid var(--border); background: var(--surface); }
    .asset-name-section { flex: 1; }
    .asset-name { font-size: 1.1rem; font-weight: 600; color: var(--text-primary); line-height: 1.3; }
    .asset-codes { font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; }
    .asset-badges { display: flex; gap: 8px; flex-shrink: 0; margin-left: 12px; }
    .phase-pill { padding: 5px 12px; border-radius: 16px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
    .phase-pill.phase-phase3, .phase-pill.phase-filed { background: #DCFCE7; color: #166534; }
    .phase-pill.phase-phase23, .phase-pill.phase-phase2 { background: #DBEAFE; color: #1E40AF; }
    .phase-pill.phase-phase12, .phase-pill.phase-phase1 { background: #F3F4F6; color: #4B5563; }
    .phase-pill.phase-preclinical { background: #F3F4F6; color: #6B7280; }
    .phase-pill.phase-approved { background: #F3E8FF; color: #7C3AED; }
    .status-pill { padding: 5px 12px; border-radius: 16px; font-size: 0.75rem; font-weight: 500; }
    .status-pill.status-active { background: #DCFCE7; color: #166534; }
    .status-pill.status-inactive, .status-pill.status-terminated { background: #FEE2E2; color: #991B1B; }
    .asset-meta { display: flex; align-items: center; gap: 8px; padding: 12px 20px; font-size: 0.9rem; border-bottom: 1px solid var(--border); background: var(--background); }
    .modality-pill { background: var(--accent); color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
    .meta-separator { color: var(--text-muted); }
    .asset-moa { color: var(--text-secondary); font-size: 0.85rem; }
    .asset-owner { padding: 10px 20px; font-size: 0.9rem; color: var(--text-primary); border-bottom: 1px solid var(--border); }
    .owner-type-tag { color: var(--text-muted); font-weight: 400; }
    .asset-indications { padding: 12px 20px; font-size: 0.9rem; border-bottom: 1px solid var(--border); }
    .lead-indication { color: var(--text-primary); margin-bottom: 4px; }
    .lead-indication strong { color: var(--text-secondary); font-weight: 500; }
    .other-indications { color: var(--text-muted); font-size: 0.85rem; }
    .other-indications strong { color: var(--text-secondary); font-weight: 500; }
    .asset-highlights { padding: 12px 20px; background: #FFFBEB; border-bottom: 1px solid #FDE68A; }
    .deal-info { color: #166534; font-size: 0.95rem; font-weight: 600; margin-bottom: 6px; }
    .deal-info:last-child { margin-bottom: 0; }
    .deal-breakdown { font-size: 0.85rem; font-weight: 400; color: #92400E; margin-top: 6px; line-height: 1.5; }
    .unverified-deal { font-size: 0.75rem; font-weight: 400; color: var(--text-muted); margin-left: 8px; }
    .key-data-info { color: #166534; font-size: 0.9rem; font-weight: 500; }
    .asset-footer { padding: 12px 20px; background: var(--background); }
    .trials-row { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 8px; }
    .trials-row strong { color: var(--text-secondary); font-weight: 500; }
    .trial-nct { color: var(--accent); text-decoration: none; margin-right: 8px; font-weight: 500; }
    .trial-nct:hover { text-decoration: underline; }
    .reg-row { display: flex; gap: 6px; flex-wrap: wrap; }
    .reg-pill { padding: 3px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 600; background: var(--surface); border: 1px solid var(--border); color: var(--text-secondary); }
    .investment-dashboard { background: var(--surface); padding: 28px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid var(--border); }
    .investment-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 20px; }
    .investment-metric { text-align: center; padding: 20px; background: var(--background); border-radius: 10px; }
    .investment-metric .big-value { font-size: 2rem; font-weight: 600; color: var(--success); }
    .investment-metric .metric-label { font-size: 0.85rem; color: var(--text-secondary); margin-top: 6px; }
    .deal-highlight { background: #FFF8E1; border-left: 3px solid var(--warning); padding: 14px 18px; margin: 16px 0 0 0; border-radius: 0 8px 8px 0; }
    .deal-highlight strong { color: var(--text-primary); }
    .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }
    .summary-card { background: var(--background); padding: 18px; border-radius: 8px; border: 1px solid var(--border); }
    .summary-card h4 { color: var(--text-secondary); font-size: 0.8rem; font-weight: 600; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }
    .summary-item { display: flex; justify-content: space-between; padding: 5px 0; font-size: 0.9rem; }
    .summary-item .label { color: var(--text-secondary); }
    .summary-item .value { color: var(--text-primary); font-weight: 600; }
    .analytics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 28px; }
    .bar-row { display: flex; align-items: center; margin-bottom: 10px; }
    .bar-label { width: 100px; font-size: 0.85rem; color: var(--text-secondary); }
    .bar-container { flex: 1; display: flex; align-items: center; gap: 10px; }
    .bar { height: 24px; background: linear-gradient(90deg, var(--accent), #E89B7D); border-radius: 4px; min-width: 4px; }
    .bar-value { font-size: 0.85rem; color: var(--text-primary); font-weight: 500; min-width: 30px; }
    .footer { text-align: center; color: var(--text-muted); font-size: 0.85rem; padding: 24px; margin-top: 32px; border-top: 1px solid var(--border); }
    .back-link { margin-bottom: 20px; }
    .back-link a { color: var(--accent); font-weight: 500; }
    /* Data Source Indicator */
    .data-source-indicator { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 8px; margin: 16px 0; font-size: 0.9rem; }
    .data-source-indicator.curated { background: #DCFCE7; border: 1px solid #BBF7D0; color: #166534; }
    .data-source-indicator.ai-research { background: #DBEAFE; border: 1px solid #BFDBFE; color: #1E40AF; }
    .data-source-indicator.ai-error { background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; }
    .source-icon { font-size: 1.2rem; }
    .source-text { flex: 1; }
    .source-text strong { font-weight: 600; }
    .source-date { color: inherit; opacity: 0.7; margin-left: 8px; font-size: 0.85rem; }
    .cache-badge, .fresh-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-left: 8px; }
    .cache-badge { background: rgba(0,0,0,0.1); }
    .fresh-badge { background: #22C55E; color: white; }
    .refresh-btn { background: #3B82F6; color: white; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; text-decoration: none; font-weight: 500; transition: background 0.2s; }
    .refresh-btn:hover { background: #2563EB; text-decoration: none; color: white; }
  </style>
</head>
<body>
  <div class="container">
    <div class="back-link"><a href="/">&larr; Back to Home</a></div>

    <div class="header">
      <h1>${target}</h1>
      <p class="subtitle">Satya Bio Report | Updated ${timestamp}</p>
      ${dataSourceHtml}

      <div class="nav">
        ${targetAnalysis ? '<a href="#thesis">Investment Thesis</a>' : ''}
        ${targetAnalysis?.efficacyComparison?.length ? '<a href="#efficacy">Efficacy</a>' : ''}
        ${targetAnalysis?.differentiators?.length ? '<a href="#differentiation">Differentiation</a>' : ''}
        <a href="#assets">Assets (${assetCount})</a>
        <a href="#trials">Trials (${summary.totalTrials})</a>
        <a href="#publications">Publications (${summary.totalPublications})</a>
        <a href="#authors">Authors (${summary.totalKOLs})</a>
        <a href="/api/report/target/${encodeURIComponent(target)}/excel" class="download">Download Excel</a>
      </div>

      <div class="stats-grid">
        <div class="stat-card" style="background: linear-gradient(135deg, var(--success) 0%, #4A7A5E 100%); border: none;">
          <div class="stat-num" style="color: white;">${formatDealValue(investmentMetrics?.totalCommitted || 0)}</div>
          <div class="stat-label" style="color: rgba(255,255,255,0.9);">Committed Capital</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${investmentMetrics?.phase3Assets || 0}</div>
          <div class="stat-label">Phase 3 Assets</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${investmentMetrics?.assetsWithBTD || 0}</div>
          <div class="stat-label">BTD Designations</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${summary.activeTrials}</div>
          <div class="stat-label">Active Trials</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">${assetCount}</div>
          <div class="stat-label">Curated Assets</div>
        </div>
      </div>
    </div>

    ${investmentMetrics ? `
    <div class="investment-dashboard">
      <h2 style="color:var(--text-primary);margin-bottom:20px;font-weight:600;">Investment Metrics</h2>
      <div class="investment-grid">
        <div class="investment-metric" style="background: linear-gradient(135deg, var(--success) 0%, #4A7A5E 100%);">
          <div class="big-value" style="color: white;">${formatDealValue(investmentMetrics.totalCommitted || 0)}</div>
          <div class="metric-label" style="color: rgba(255,255,255,0.9);">Committed</div>
          <div style="color: rgba(255,255,255,0.7); font-size: 0.75rem; margin-top: 4px;">(upfront + equity)</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${formatDealValue(investmentMetrics.totalPotential || 0)}</div>
          <div class="metric-label">Total Potential</div>
          <div style="color: var(--text-muted); font-size: 0.75rem; margin-top: 4px;">(w/ milestones)</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${investmentMetrics.phase3Assets || 0}</div>
          <div class="metric-label">Phase 3 Assets</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${investmentMetrics.assetsWithBTD || 0}</div>
          <div class="metric-label">BTD Designations</div>
        </div>
        <div class="investment-metric">
          <div class="big-value">${investmentMetrics.assetsWithDeals || 0}</div>
          <div class="metric-label">Deals Tracked</div>
        </div>
      </div>
      ${investmentMetrics.largestDeal?.name ? `
      <div class="deal-highlight">
        <strong>Largest Deal:</strong> ${investmentMetrics.largestDeal.name} —
        ${formatDealValue(investmentMetrics.largestDeal.committed || 0)} committed${investmentMetrics.largestDeal.partner ? ` to ${investmentMetrics.largestDeal.partner}` : ''}
        <span style="color: var(--text-secondary); font-size: 0.9rem;"> (${formatDealValue(investmentMetrics.largestDeal.potential || 0)} potential with milestones)</span>
      </div>
      ` : ''}
    </div>
    ` : ''}

    ${targetAnalysis ? `
    <section class="section" id="thesis">
      <h2 class="section-title">Investment Thesis</h2>
      <div class="card" style="background: linear-gradient(135deg, #FEF3C7 0%, #FDF4E8 100%); border: 2px solid #D97706;">
        <div style="font-size: 1.15rem; font-weight: 600; color: #92400E; margin-bottom: 16px; line-height: 1.5;">
          ${targetAnalysis.investmentThesis.headline}
        </div>
        <div style="margin-bottom: 16px;">
          <strong style="color: var(--text-primary);">Key Investment Points:</strong>
          <ul style="margin: 10px 0 0 20px; color: var(--text-secondary); line-height: 1.8;">
            ${targetAnalysis.investmentThesis.keyPoints.map(p => `<li>${p}</li>`).join('')}
          </ul>
        </div>
        <div style="border-top: 1px solid #D4A574; padding-top: 16px; margin-top: 16px;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
              <strong style="color: var(--text-primary);">Market Opportunity:</strong>
              <div style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 6px;">
                Total: ${targetAnalysis.marketOpportunity.totalMarket}<br>
                Target: <span style="color: #166534; font-weight: 600;">${targetAnalysis.marketOpportunity.targetShare}</span><br>
                Population: ${targetAnalysis.marketOpportunity.patientPopulation}
              </div>
            </div>
            <div>
              <strong style="color: var(--text-primary);">Key Catalysts:</strong>
              <div style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 6px;">
                ${targetAnalysis.catalystsToWatch.slice(0, 3).map(c =>
                  `• ${c.drug}: ${c.event} (${c.timing})`
                ).join('<br>')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    ${targetAnalysis.efficacyComparison && targetAnalysis.efficacyComparison.length > 0 ? `
    <section class="section" id="efficacy">
      <h2 class="section-title">Efficacy Comparison</h2>
      <p style="color:var(--text-secondary);margin-bottom:15px;font-size:0.9rem;">
        Head-to-head comparison of clinical efficacy data across development programs (sorted by placebo-adjusted response)
      </p>
      <div class="card" style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Drug</th>
              <th>Trial</th>
              <th>Dose</th>
              <th>Endpoint</th>
              <th>Result</th>
              <th>Placebo</th>
              <th style="background: #166534; color: white;">Δ vs Placebo</th>
              <th>Population</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            ${[...targetAnalysis.efficacyComparison]
              .sort((a, b) => b.placeboAdjusted - a.placeboAdjusted)
              .map((e, i) => `
              <tr style="${i === 0 ? 'background: #DCFCE7;' : ''}">
                <td style="font-weight: 600;">${e.drug}</td>
                <td>${e.trial}</td>
                <td style="font-size: 0.85rem;">${e.dose}</td>
                <td>${e.endpoint}</td>
                <td>${e.result}%</td>
                <td>${e.placebo}%</td>
                <td style="font-weight: 700; color: ${e.placeboAdjusted >= 25 ? '#166534' : e.placeboAdjusted >= 20 ? '#16A34A' : 'inherit'};">
                  ${e.placeboAdjusted}%${i === 0 ? ' ★' : ''}
                </td>
                <td style="font-size: 0.85rem; color: ${e.population ? '#7C3AED' : 'inherit'}; font-style: ${e.population ? 'italic' : 'normal'};">
                  ${e.population || 'All patients'}
                </td>
                <td style="font-size: 0.85rem;">${e.source}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <p style="margin-top:15px;font-size:0.8rem;color:var(--text-muted);">
          ★ = Best-in-class result | <span style="color: #7C3AED;">Purple</span> = biomarker-selected population
        </p>
      </div>
    </section>
    ` : ''}

    ${targetAnalysis.differentiators && targetAnalysis.differentiators.length > 0 ? `
    <section class="section" id="differentiation">
      <h2 class="section-title">Competitive Differentiation</h2>
      <p style="color:var(--text-secondary);margin-bottom:15px;font-size:0.9rem;">
        Strategic positioning and key differentiators for each development program
      </p>
      <div class="card" style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Drug</th>
              <th>Strategy</th>
              <th>Dosing</th>
              <th>Biomarker</th>
              <th>Half-Life</th>
              <th>Beyond Lead Indication</th>
            </tr>
          </thead>
          <tbody>
            ${targetAnalysis.differentiators.map((d, i) => `
              <tr style="${i % 2 === 0 ? 'background: #F3E8FF;' : ''}">
                <td style="font-weight: 600;">${d.drug}</td>
                <td style="color: #7C3AED; font-weight: 500;">${d.strategy}</td>
                <td style="font-size: 0.9rem;">${d.dosing}</td>
                <td style="${d.biomarker && d.biomarker !== 'No' && d.biomarker !== 'TBD' ? 'font-weight: 600; color: #7C3AED;' : ''}">${d.biomarker}</td>
                <td>${d.halfLife}</td>
                <td style="font-size: 0.9rem;">${d.beyondIndication}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </section>
    ` : ''}

    ${targetAnalysis.keyRisks && targetAnalysis.keyRisks.length > 0 ? `
    <section class="section" id="risks">
      <h2 class="section-title">Key Risks</h2>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>Risk</th>
              <th>Severity</th>
              <th>Mitigation</th>
            </tr>
          </thead>
          <tbody>
            ${targetAnalysis.keyRisks.map(r => `
              <tr>
                <td>${r.risk}</td>
                <td style="font-weight: 600; color: ${r.severity === 'High' ? '#DC2626' : r.severity === 'Medium' ? '#EA580C' : '#166534'};">
                  ${r.severity}
                </td>
                <td style="font-size: 0.9rem; color: var(--text-secondary);">${r.mitigation || '-'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </section>
    ` : ''}
    ` : ''}

    <div class="analytics-grid">
      <section class="section">
        <h2 class="section-title">Trials by Phase</h2>
        <div class="card">
          ${phaseChart || '<p style="color:#94a3b8;">No trial phase data available</p>'}
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">Top Sponsors</h2>
        <div class="card">
          <table>
            <thead><tr><th>Sponsor</th><th>Trials</th><th>Type</th></tr></thead>
            <tbody>${sponsorRows || '<tr><td colspan="3" style="color:#94a3b8;">No sponsor data</td></tr>'}</tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="section" id="assets">
      <h2 class="section-title">Competitive Landscape: ${target} Assets (${assetCount})</h2>
      <p style="color:#94a3b8;margin-bottom:15px;font-size:0.9rem;">
        ${assetCount} assets tracked • ${investmentMetrics?.assetsWithDeals || 0} deals worth ${formatDealValue(investmentMetrics?.totalCommitted || 0)} • ${investmentMetrics?.phase3Assets || 0} in Phase 3
      </p>

      ${investmentMetrics ? `
      <div class="summary-cards">
        <div class="summary-card">
          <h4>By Modality</h4>
          ${Object.entries(investmentMetrics.modalityBreakdown || {}).map(([k, v]: [string, any]) =>
            `<div class="summary-item"><span class="label">${k}</span><span class="value">${v.count}${v.committed > 0 ? ` <span style="color:var(--success);font-size:0.75rem;">(${formatDealValue(v.committed)})</span>` : ''}</span></div>`
          ).join('')}
        </div>
        <div class="summary-card">
          <h4>By Phase</h4>
          ${Object.entries(investmentMetrics.phaseDistribution || {}).sort((a, b) => {
            const order = ['Approved', 'Filed', 'Phase 3', 'Phase 2/3', 'Phase 2', 'Phase 1/2', 'Phase 1', 'Preclinical'];
            return order.indexOf(a[0]) - order.indexOf(b[0]);
          }).map(([k, v]) => `<div class="summary-item"><span class="label">${k}</span><span class="value">${v}</span></div>`).join('')}
        </div>
        <div class="summary-card">
          <h4>By Owner Type</h4>
          ${Object.entries(investmentMetrics.ownershipBreakdown || {}).map(([k, v]) => `<div class="summary-item"><span class="label">${k}</span><span class="value">${v}</span></div>`).join('')}
        </div>
        <div class="summary-card">
          <h4>Regulatory Designations</h4>
          <div class="summary-item"><span class="label">BTD</span><span class="value">${investmentMetrics.assetsWithBTD || 0}</span></div>
          <div class="summary-item"><span class="label">ODD</span><span class="value">${investmentMetrics.assetsWithODD || 0}</span></div>
          <div class="summary-item"><span class="label">PRIME</span><span class="value">${investmentMetrics.assetsWithPRIME || 0}</span></div>
          <div class="summary-item"><span class="label">Fast Track</span><span class="value">${investmentMetrics.assetsWithFastTrack || 0}</span></div>
        </div>
      </div>
      ` : ''}

      <div class="asset-grid">
        ${assetCards || '<p style="color:var(--text-muted);padding:20px;">No assets found</p>'}
      </div>
      <p style="margin-top:20px;font-size:0.8rem;color:var(--text-muted);text-align:center;">
        <span class="reg-pill">BTD</span> Breakthrough Therapy &nbsp;
        <span class="reg-pill">ODD</span> Orphan Drug &nbsp;
        <span class="reg-pill">PRIME</span> EU Priority &nbsp;
        <span class="reg-pill">FT</span> Fast Track
      </p>
    </section>

    <section class="section" id="trials">
      <h2 class="section-title">Clinical Trials (${trials.length})</h2>
      <div class="card">
        <table>
          <thead>
            <tr><th>NCT ID</th><th>Title</th><th>Phase</th><th>Status</th><th>Sponsor</th><th>Enrollment</th><th>Start</th></tr>
          </thead>
          <tbody>
            ${trialRows || '<tr><td colspan="7" style="color:#94a3b8;">No trials found</td></tr>'}
          </tbody>
        </table>
        ${trials.length > 50 ? `<p style="margin-top:15px;color:#94a3b8;">Showing 50 of ${trials.length} trials. Download Excel for complete data.</p>` : ''}
      </div>
    </section>

    <section class="section" id="publications">
      <h2 class="section-title">Publications (${publications.length})</h2>
      <div class="card">
        <table>
          <thead>
            <tr><th>PMID</th><th>Title</th><th>Authors</th><th>Journal</th><th>Year</th></tr>
          </thead>
          <tbody>
            ${pubRows || '<tr><td colspan="5" style="color:#94a3b8;">No publications found</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section" id="authors">
      <h2 class="section-title">Top Authors (${kols.length})</h2>
      <p style="color:#94a3b8;margin-bottom:15px;font-size:0.9rem;">Authors ranked by publication count from PubMed search results</p>
      <div class="card">
        <table>
          <thead>
            <tr><th>Name</th><th>Institution</th><th>Publications</th><th>First Author</th><th>Last Author</th><th>Status</th></tr>
          </thead>
          <tbody>
            ${authorRows || '<tr><td colspan="6" style="color:#94a3b8;">No authors found in publications</td></tr>'}
          </tbody>
        </table>
      </div>
    </section>

    <footer class="footer">
      <div>Satya Bio | Truth in Biotech Research</div>
      <div>Data: ClinicalTrials.gov, PubMed, SEC EDGAR, FDA Orange Book</div>
    </footer>
  </div>
</body>
</html>`;
}
