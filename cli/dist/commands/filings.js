"use strict";
/**
 * Filings Command
 *
 * Fetch and display SEC filings (10-K and 10-Q) for a company.
 *
 * Examples:
 *   helix filings MRNA           # List recent filings
 *   helix filings MRNA --save    # Download latest 10-K to ./samples/
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerFilingsCommand = registerFilingsCommand;
const chalk_1 = __importDefault(require("chalk"));
const ora_1 = __importDefault(require("ora"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const sec_edgar_1 = require("../services/sec-edgar");
const companies_1 = require("../services/companies");
function registerFilingsCommand(program) {
    program
        .command('filings <ticker>')
        .description('Fetch SEC filings (10-K, 10-Q) for a company')
        .option('-n, --count <number>', 'Number of filings to fetch', '5')
        .option('--save', 'Download the latest filing to ./samples/', false)
        .option('-f, --form <type>', 'Filing type for --save: 10-K or 10-Q', '10-K')
        .action(async (ticker, options) => {
        const tickerUpper = ticker.toUpperCase();
        const spinner = (0, ora_1.default)(`Looking up ${tickerUpper}...`).start();
        try {
            // First, verify the company exists in XBI
            const company = await (0, companies_1.getCompanyByTicker)(tickerUpper);
            if (company) {
                spinner.text = `Found: ${company.name}`;
            }
            // Look up the CIK
            spinner.text = `Looking up SEC CIK for ${tickerUpper}...`;
            const cik = await (0, sec_edgar_1.getCIKFromTicker)(tickerUpper);
            if (!cik) {
                spinner.fail(`Could not find SEC CIK for ${tickerUpper}`);
                console.log(chalk_1.default.yellow('\nThis company may not file with the SEC (foreign company, etc.)'));
                return;
            }
            spinner.text = `Fetching filings for ${tickerUpper} (CIK: ${cik})...`;
            // Fetch filings
            const count = parseInt(options.count, 10);
            const filings = await (0, sec_edgar_1.getFilings)(tickerUpper, count);
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
                console.log(chalk_1.default.bold(`${company.name} (${tickerUpper})`));
            }
            else {
                console.log(chalk_1.default.bold(tickerUpper));
            }
            console.log(chalk_1.default.gray(`CIK: ${cik}\n`));
            console.log(chalk_1.default.bold(`SEC Filings:\n`));
            // Display filings
            for (const filing of filings) {
                printFiling(filing);
            }
            // Usage hints
            console.log(chalk_1.default.gray('To analyze a filing:'));
            console.log(chalk_1.default.cyan(`  helix analyze ${tickerUpper}`));
            console.log('');
            console.log(chalk_1.default.gray('To save a filing locally:'));
            console.log(chalk_1.default.cyan(`  helix filings ${tickerUpper} --save\n`));
        }
        catch (error) {
            spinner.fail('Failed to fetch filings');
            console.error(chalk_1.default.red(error instanceof Error ? error.message : 'Unknown error'));
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
async function saveFiling(spinner, ticker, filings, formType) {
    const targetForm = formType.toUpperCase();
    // Find the requested filing type
    const filing = filings.find(f => f.form === targetForm || f.form === `${targetForm}/A`);
    if (!filing) {
        spinner.fail(`No ${targetForm} filing found for ${ticker}`);
        console.log(chalk_1.default.yellow('\nAvailable filings:'));
        for (const f of filings.slice(0, 5)) {
            console.log(`  ${f.form} - ${f.filingDate}`);
        }
        return;
    }
    // Download the filing content
    spinner.text = `Downloading ${filing.form} from ${filing.filingDate}...`;
    // Use a larger limit for saved files (full content)
    const content = await (0, sec_edgar_1.getFilingForAnalysis)(filing, 500000);
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
    console.log(chalk_1.default.gray(`  ${content.length.toLocaleString()} characters`));
    console.log(chalk_1.default.gray(`  Filing date: ${filing.filingDate}`));
    console.log(chalk_1.default.gray(`  Report period: ${filing.reportDate}`));
    console.log('');
    console.log(chalk_1.default.gray('To analyze this filing:'));
    console.log(chalk_1.default.cyan(`  helix analyze ${ticker}\n`));
}
function printFiling(filing) {
    // Form type with color coding
    const formColor = filing.form.includes('10-K') ? chalk_1.default.green : chalk_1.default.blue;
    const formType = filing.form.includes('10-K') ? 'Annual' : 'Quarterly';
    console.log(`  ${formColor.bold(filing.form.padEnd(8))} ${chalk_1.default.gray(formType)}`);
    console.log(`    Filed:  ${filing.filingDate}`);
    console.log(`    Period: ${filing.reportDate}`);
    console.log(chalk_1.default.gray(`    ${filing.fileUrl}`));
    console.log('');
}
//# sourceMappingURL=filings.js.map