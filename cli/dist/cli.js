#!/usr/bin/env node
"use strict";
/**
 * Helix CLI - Biotech Investment Research Tool
 *
 * Analyze SEC filings for XBI (Biotech ETF) companies.
 *
 * Commands:
 *   helix search <query>   - Search for companies
 *   helix filings <ticker> - View SEC filings
 *   helix analyze <ticker> - AI analysis of filings
 *
 * Quick start:
 *   1. Copy .env.example to .env
 *   2. Install Ollama: https://ollama.ai
 *   3. Pull a model: ollama pull llama3.2
 *   4. Run: npm run dev search moderna
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const commander_1 = require("commander");
const chalk_1 = __importDefault(require("chalk"));
const search_1 = require("./commands/search");
const filings_1 = require("./commands/filings");
const analyze_1 = require("./commands/analyze");
const serve_1 = require("./commands/serve");
// ASCII art banner
const banner = `
${chalk_1.default.cyan('╦ ╦╔═╗╦  ╦═╗ ╦')}
${chalk_1.default.cyan('╠═╣║╣ ║  ║╔╩╦╝')}
${chalk_1.default.cyan('╩ ╩╚═╝╩═╝╩╩ ╚═')}
${chalk_1.default.gray('Biotech SEC Filing Analyzer')}
`;
// Create the CLI program
const program = new commander_1.Command();
program
    .name('helix')
    .description('Biotech investment research CLI - analyze SEC filings for XBI companies')
    .version('1.0.0')
    .hook('preAction', () => {
    // Show banner before each command
    console.log(banner);
});
// Register all commands
(0, search_1.registerSearchCommand)(program);
(0, filings_1.registerFilingsCommand)(program);
(0, analyze_1.registerAnalyzeCommand)(program);
(0, serve_1.registerServeCommand)(program);
// Handle unknown commands
program.on('command:*', () => {
    console.error(chalk_1.default.red(`Unknown command: ${program.args.join(' ')}`));
    console.log('');
    program.outputHelp();
    process.exit(1);
});
// Parse command line arguments
program.parse(process.argv);
// Show help if no command provided
if (!process.argv.slice(2).length) {
    console.log(banner);
    program.outputHelp();
}
//# sourceMappingURL=cli.js.map