"use strict";
/**
 * Search Command
 *
 * Search for XBI companies by name or ticker.
 * Example: helix search moderna
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerSearchCommand = registerSearchCommand;
const chalk_1 = __importDefault(require("chalk"));
const ora_1 = __importDefault(require("ora"));
const companies_1 = require("../services/companies");
function registerSearchCommand(program) {
    program
        .command('search <query>')
        .description('Search for XBI companies by name or ticker')
        .option('-l, --limit <number>', 'Maximum results to show', '10')
        .action(async (query, options) => {
        const spinner = (0, ora_1.default)('Searching companies...').start();
        try {
            const companies = await (0, companies_1.searchCompanies)(query);
            spinner.stop();
            const limit = parseInt(options.limit, 10);
            const results = companies.slice(0, limit);
            if (results.length === 0) {
                console.log(chalk_1.default.yellow(`No companies found matching "${query}"`));
                return;
            }
            console.log(chalk_1.default.bold(`\nFound ${results.length} companies:\n`));
            // Display results in a nice table format
            for (const company of results) {
                printCompany(company);
            }
            if (companies.length > limit) {
                console.log(chalk_1.default.gray(`\n... and ${companies.length - limit} more. Use --limit to see more.`));
            }
        }
        catch (error) {
            spinner.fail('Search failed');
            console.error(chalk_1.default.red(error instanceof Error ? error.message : 'Unknown error'));
            process.exit(1);
        }
    });
}
function printCompany(company) {
    // Ticker in bold cyan, name in white
    console.log(`  ${chalk_1.default.cyan.bold(company.ticker.padEnd(6))} ${company.name}`);
    // Show additional info if available
    const details = [];
    if (company.stage)
        details.push(company.stage);
    if (company.indication)
        details.push(company.indication);
    if (company.lead_asset)
        details.push(`Lead: ${company.lead_asset}`);
    if (details.length > 0) {
        console.log(chalk_1.default.gray(`         ${details.join(' | ')}`));
    }
    console.log(''); // Empty line between companies
}
//# sourceMappingURL=search.js.map