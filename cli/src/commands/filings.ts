/**
 * Filings Command
 *
 * Fetch and display SEC filings (10-K and 10-Q) for a company.
 *
 * Examples:
 *   helix filings MRNA           # List recent filings
 *   helix filings MRNA --save    # Download latest 10-K to ./samples/
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs';
import * as path from 'path';
import { getFilings, getCIKFromTicker, getFilingForAnalysis } from '../services/sec-edgar';
import { getCompanyByTicker } from '../services/companies';
import { Filing } from '../types';

// Command options type
interface FilingsOptions {
  count: string;
  save: boolean;
  form: string;
}

export function registerFilingsCommand(program: Command): void {
  program
    .command('filings <ticker>')
    .description('Fetch SEC filings (10-K, 10-Q) for a company')
    .option('-n, --count <number>', 'Number of filings to fetch', '5')
    .option('--save', 'Download the latest filing to ./samples/', false)
    .option('-f, --form <type>', 'Filing type for --save: 10-K or 10-Q', '10-K')
    .action(async (ticker: string, options: FilingsOptions) => {
      const tickerUpper = ticker.toUpperCase();
      const spinner = ora(`Looking up ${tickerUpper}...`).start();

      try {
        // First, verify the company exists in XBI
        const company = await getCompanyByTicker(tickerUpper);

        if (company) {
          spinner.text = `Found: ${company.name}`;
        }

        // Look up the CIK
        spinner.text = `Looking up SEC CIK for ${tickerUpper}...`;
        const cik = await getCIKFromTicker(tickerUpper);

        if (!cik) {
          spinner.fail(`Could not find SEC CIK for ${tickerUpper}`);
          console.log(chalk.yellow('\nThis company may not file with the SEC (foreign company, etc.)'));
          return;
        }

        spinner.text = `Fetching filings for ${tickerUpper} (CIK: ${cik})...`;

        // Fetch filings
        const count = parseInt(options.count, 10);
        const filings = await getFilings(tickerUpper, count);

        if (filings.length === 0) {
          spinner.fail(`No 10-K or 10-Q filings found for ${tickerUpper}`);
          return;
        }

        // If --save flag is set, download the filing
        if (options.save) {
          await saveFiling(spinner, tickerUpper, filings, options.form);
          return;
        }

        spinner.stop();

        // Display header
        console.log('');
        if (company) {
          console.log(chalk.bold(`${company.name} (${tickerUpper})`));
        } else {
          console.log(chalk.bold(tickerUpper));
        }
        console.log(chalk.gray(`CIK: ${cik}\n`));
        console.log(chalk.bold(`SEC Filings:\n`));

        // Display filings
        for (const filing of filings) {
          printFiling(filing);
        }

        // Usage hints
        console.log(chalk.gray('To analyze a filing:'));
        console.log(chalk.cyan(`  helix analyze ${tickerUpper}`));
        console.log('');
        console.log(chalk.gray('To save a filing locally:'));
        console.log(chalk.cyan(`  helix filings ${tickerUpper} --save\n`));

      } catch (error) {
        spinner.fail('Failed to fetch filings');
        console.error(chalk.red(error instanceof Error ? error.message : 'Unknown error'));
        process.exit(1);
      }
    });
}

/**
 * Save a filing to the ./samples/ directory
 *
 * Creates the samples directory if it doesn't exist.
 * Filename format: TICKER-FORM-YEAR.txt (e.g., MRNA-10K-2024.txt)
 */
async function saveFiling(
  spinner: ora.Ora,
  ticker: string,
  filings: Filing[],
  formType: string
): Promise<void> {
  const targetForm = formType.toUpperCase();

  // Find the requested filing type
  const filing = filings.find(f =>
    f.form === targetForm || f.form === `${targetForm}/A`
  );

  if (!filing) {
    spinner.fail(`No ${targetForm} filing found for ${ticker}`);
    console.log(chalk.yellow('\nAvailable filings:'));
    for (const f of filings.slice(0, 5)) {
      console.log(`  ${f.form} - ${f.filingDate}`);
    }
    return;
  }

  // Download the filing content
  spinner.text = `Downloading ${filing.form} from ${filing.filingDate}...`;

  // Use a larger limit for saved files (full content)
  const content = await getFilingForAnalysis(filing, 500000);

  // Create samples directory if it doesn't exist
  const samplesDir = path.join(process.cwd(), 'samples');
  if (!fs.existsSync(samplesDir)) {
    fs.mkdirSync(samplesDir, { recursive: true });
  }

  // Extract year from report date (format: YYYY-MM-DD)
  const year = filing.reportDate.split('-')[0];

  // Create filename (remove / from form type for filename)
  const formForFilename = filing.form.replace('/', '');
  const filename = `${ticker}-${formForFilename}-${year}.txt`;
  const filepath = path.join(samplesDir, filename);

  // Save the file
  spinner.text = `Saving to ${filepath}...`;
  fs.writeFileSync(filepath, content, 'utf-8');

  spinner.succeed(`Saved to ./samples/${filename}`);
  console.log(chalk.gray(`  ${content.length.toLocaleString()} characters`));
  console.log(chalk.gray(`  Filing date: ${filing.filingDate}`));
  console.log(chalk.gray(`  Report period: ${filing.reportDate}`));
  console.log('');
  console.log(chalk.gray('To analyze this filing:'));
  console.log(chalk.cyan(`  helix analyze ${ticker}\n`));
}

function printFiling(filing: Filing): void {
  // Form type with color coding
  const formColor = filing.form.includes('10-K') ? chalk.green : chalk.blue;
  const formType = filing.form.includes('10-K') ? 'Annual' : 'Quarterly';

  console.log(`  ${formColor.bold(filing.form.padEnd(8))} ${chalk.gray(formType)}`);
  console.log(`    Filed:  ${filing.filingDate}`);
  console.log(`    Period: ${filing.reportDate}`);
  console.log(chalk.gray(`    ${filing.fileUrl}`));
  console.log('');
}
