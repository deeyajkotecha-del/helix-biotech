/**
 * Analyze Command
 *
 * Fetch the latest SEC filing and run AI analysis.
 *
 * Examples:
 *   helix analyze MRNA           # Analyze latest 10-K
 *   helix analyze MRNA -f 10-Q   # Analyze latest 10-Q
 *   helix analyze MRNA --debug   # Show prompt, raw response, then parsed output
 *   helix analyze MRNA --raw     # Just show raw filing text, no AI
 */
import { Command } from 'commander';
export declare function registerAnalyzeCommand(program: Command): void;
//# sourceMappingURL=analyze.d.ts.map