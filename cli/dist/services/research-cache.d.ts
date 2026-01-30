/**
 * Research Cache Service
 *
 * File-based caching for AI research results to minimize API costs
 * and provide faster responses for recently researched targets.
 */
import { ResearchResult } from './ai-research-agent';
declare const DEFAULT_TTL_HOURS = 24;
interface CacheEntry {
    result: ResearchResult;
    cachedAt: string;
    expiresAt: string;
    ttlHours: number;
}
interface CacheOptions {
    ttlHours?: number;
    forceRefresh?: boolean;
}
/**
 * Read cache for a target
 */
export declare function getCache(target: string): CacheEntry | null;
/**
 * Write cache for a target
 */
export declare function setCache(target: string, result: ResearchResult, ttlHours?: number): void;
/**
 * Clear cache for a target
 */
export declare function clearCache(target: string): boolean;
/**
 * Clear all research cache
 */
export declare function clearAllCache(): number;
/**
 * Get cache statistics
 */
export declare function getCacheStats(): {
    totalEntries: number;
    validEntries: number;
    expiredEntries: number;
    oldestEntry: string | null;
    newestEntry: string | null;
    totalSizeKB: number;
};
/**
 * Get research results, using cache when available
 *
 * @param target - Target to research
 * @param options - Cache options
 * @returns Research result (from cache or fresh)
 */
export declare function getCachedOrResearch(target: string, options?: CacheOptions): Promise<ResearchResult & {
    fromCache: boolean;
    cacheAge?: string;
}>;
export { DEFAULT_TTL_HOURS };
//# sourceMappingURL=research-cache.d.ts.map