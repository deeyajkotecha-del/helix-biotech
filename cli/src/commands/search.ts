/**
 * Search Command
 *
 * Search for XBI companies by name or ticker.
 * Example: helix search moderna
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { searchCompanies } from '../services/companies';
import { Company } from '../types';

export function registerSearchCommand(program: Command): void {
  program
    .command('search <query>')
    .description('Search for XBI companies by name or ticker')
    .option('-l, --limit <number>', 'Maximum results to show', '10')
    .action(async (query: string, options: { limit: string }) => {
      const spinner = ora('Searching companies...').start();

      try {
        const companies = await searchCompanies(query);
        spinner.stop();

        const limit = parseInt(options.limit, 10);
        const results = companies.slice(0, limit);

        if (results.length === 0) {
          console.log(chalk.yellow(`No companies found matching "${query}"`));
          return;
        }

        console.log(chalk.bold(`\nFound ${results.length} companies:\n`));

        // Display results in a nice table format
        for (const company of results) {
          printCompany(company);
        }

        if (companies.length > limit) {
          console.log(chalk.gray(`\n... and ${companies.length - limit} more. Use --limit to see more.`));
        }
      } catch (error) {
        spinner.fail('Search failed');
        console.error(chalk.red(error instanceof Error ? error.message : 'Unknown error'));
        process.exit(1);
      }
    });
}

function printCompany(company: Company): void {
  // Ticker in bold cyan, name in white
  console.log(`  ${chalk.cyan.bold(company.ticker.padEnd(6))} ${company.name}`);

  // Show additional info if available
  const details: string[] = [];
  if (company.stage) details.push(company.stage);
  if (company.indication) details.push(company.indication);
  if (company.lead_asset) details.push(`Lead: ${company.lead_asset}`);

  if (details.length > 0) {
    console.log(chalk.gray(`         ${details.join(' | ')}`));
  }

  console.log(''); // Empty line between companies
}
