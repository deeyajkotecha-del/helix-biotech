/**
 * Configuration Module
 *
 * Loads settings from environment variables.
 * Copy .env.example to .env and customize as needed.
 */
import { Config } from './types';
/**
 * Get the application configuration
 * Reads from environment variables with sensible defaults
 */
export declare function getConfig(): Config;
/**
 * Reset config cache (useful for testing)
 */
export declare function resetConfig(): void;
//# sourceMappingURL=config.d.ts.map