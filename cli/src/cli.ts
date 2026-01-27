#!/usr/bin/env node

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

import { Command } from 'commander';
import chalk from 'chalk';
import { registerSearchCommand } from './commands/search';
import { registerFilingsCommand } from './commands/filings';
import { registerAnalyzeCommand } from './commands/analyze';
import { registerServeCommand } from './commands/serve';

// ASCII art banner
const banner = `
${chalk.cyan('╦ ╦╔═╗╦  ╦═╗ ╦')}
${chalk.cyan('╠═╣║╣ ║  ║╔╩╦╝')}
${chalk.cyan('╩ ╩╚═╝╩═╝╩╩ ╚═')}
${chalk.gray('Biotech SEC Filing Analyzer')}
`;

// Create the CLI program
const program = new Command();

program
  .name('helix')
  .description('Biotech investment research CLI - analyze SEC filings for XBI companies')
  .version('1.0.0')
  .hook('preAction', () => {
    // Show banner before each command
    console.log(banner);
  });

// Register all commands
registerSearchCommand(program);
registerFilingsCommand(program);
registerAnalyzeCommand(program);
registerServeCommand(program);

// Handle unknown commands
program.on('command:*', () => {
  console.error(chalk.red(`Unknown command: ${program.args.join(' ')}`));
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
