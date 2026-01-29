/**
 * Research Cache Service
 *
 * File-based caching for AI research results to minimize API costs
 * and provide faster responses for recently researched targets.
 */

import fs from 'fs';
import path from 'path';
import { ResearchResult, researchTarget } from './ai-research-agent';

// ============================================
// Configuration
// ============================================

const CACHE_DIR = path.resolve(__dirname, '../../cache/research');
const DEFAULT_TTL_HOURS = 24;

// ============================================
// Types
// ============================================

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

// ============================================
// Cache Operations
// ============================================

/**
 * Initialize cache directory if it doesn't exist
 */
function ensureCacheDir(): void {
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }
}

/**
 * Get cache file path for a target
 */
function getCachePath(target: string): string {
  const normalized = target.toLowerCase().replace(/[^a-z0-9]/g, '-');
  return path.join(CACHE_DIR, `${normalized}.json`);
}

/**
 * Check if a cache entry is expired
 */
function isExpired(entry: CacheEntry): boolean {
  return new Date(entry.expiresAt) < new Date();
}

/**
 * Read cache for a target
 */
export function getCache(target: string): CacheEntry | null {
  ensureCacheDir();
  const cachePath = getCachePath(target);

  if (!fs.existsSync(cachePath)) {
    return null;
  }

  try {
    const data = fs.readFileSync(cachePath, 'utf-8');
    return JSON.parse(data) as CacheEntry;
  } catch (error) {
    console.warn(`[Cache] Failed to read cache for ${target}:`, error);
    return null;
  }
}

/**
 * Write cache for a target
 */
export function setCache(target: string, result: ResearchResult, ttlHours: number = DEFAULT_TTL_HOURS): void {
  ensureCacheDir();
  const cachePath = getCachePath(target);

  const now = new Date();
  const expiresAt = new Date(now.getTime() + ttlHours * 60 * 60 * 1000);

  const entry: CacheEntry = {
    result,
    cachedAt: now.toISOString(),
    expiresAt: expiresAt.toISOString(),
    ttlHours,
  };

  try {
    fs.writeFileSync(cachePath, JSON.stringify(entry, null, 2));
    console.log(`[Cache] Cached research for ${target} (expires: ${expiresAt.toISOString()})`);
  } catch (error) {
    console.warn(`[Cache] Failed to write cache for ${target}:`, error);
  }
}

/**
 * Clear cache for a target
 */
export function clearCache(target: string): boolean {
  const cachePath = getCachePath(target);

  if (fs.existsSync(cachePath)) {
    try {
      fs.unlinkSync(cachePath);
      console.log(`[Cache] Cleared cache for ${target}`);
      return true;
    } catch (error) {
      console.warn(`[Cache] Failed to clear cache for ${target}:`, error);
      return false;
    }
  }
  return false;
}

/**
 * Clear all research cache
 */
export function clearAllCache(): number {
  ensureCacheDir();
  let cleared = 0;

  try {
    const files = fs.readdirSync(CACHE_DIR);
    for (const file of files) {
      if (file.endsWith('.json')) {
        fs.unlinkSync(path.join(CACHE_DIR, file));
        cleared++;
      }
    }
    console.log(`[Cache] Cleared ${cleared} cached entries`);
  } catch (error) {
    console.warn(`[Cache] Failed to clear cache:`, error);
  }

  return cleared;
}

/**
 * Get cache statistics
 */
export function getCacheStats(): {
  totalEntries: number;
  validEntries: number;
  expiredEntries: number;
  oldestEntry: string | null;
  newestEntry: string | null;
  totalSizeKB: number;
} {
  ensureCacheDir();

  let totalEntries = 0;
  let validEntries = 0;
  let expiredEntries = 0;
  let oldestEntry: string | null = null;
  let newestEntry: string | null = null;
  let oldestDate: Date | null = null;
  let newestDate: Date | null = null;
  let totalSize = 0;

  try {
    const files = fs.readdirSync(CACHE_DIR);
    for (const file of files) {
      if (file.endsWith('.json')) {
        totalEntries++;
        const filePath = path.join(CACHE_DIR, file);
        const stats = fs.statSync(filePath);
        totalSize += stats.size;

        try {
          const data = fs.readFileSync(filePath, 'utf-8');
          const entry = JSON.parse(data) as CacheEntry;

          if (isExpired(entry)) {
            expiredEntries++;
          } else {
            validEntries++;
          }

          const cachedAt = new Date(entry.cachedAt);
          if (!oldestDate || cachedAt < oldestDate) {
            oldestDate = cachedAt;
            oldestEntry = entry.result.target;
          }
          if (!newestDate || cachedAt > newestDate) {
            newestDate = cachedAt;
            newestEntry = entry.result.target;
          }
        } catch {
          // Malformed entry
          expiredEntries++;
        }
      }
    }
  } catch (error) {
    console.warn(`[Cache] Failed to get stats:`, error);
  }

  return {
    totalEntries,
    validEntries,
    expiredEntries,
    oldestEntry,
    newestEntry,
    totalSizeKB: Math.round(totalSize / 1024),
  };
}

// ============================================
// Main Interface
// ============================================

/**
 * Get research results, using cache when available
 *
 * @param target - Target to research
 * @param options - Cache options
 * @returns Research result (from cache or fresh)
 */
export async function getCachedOrResearch(
  target: string,
  options: CacheOptions = {}
): Promise<ResearchResult & { fromCache: boolean; cacheAge?: string }> {
  const { ttlHours = DEFAULT_TTL_HOURS, forceRefresh = false } = options;

  // Check cache first (unless force refresh)
  if (!forceRefresh) {
    const cached = getCache(target);

    if (cached && !isExpired(cached)) {
      console.log(`[Cache] Using cached research for ${target} (cached ${getAge(cached.cachedAt)} ago)`);
      return {
        ...cached.result,
        fromCache: true,
        cacheAge: getAge(cached.cachedAt),
      };
    }

    if (cached) {
      console.log(`[Cache] Cache expired for ${target}, refreshing...`);
    }
  } else {
    console.log(`[Cache] Force refresh requested for ${target}`);
  }

  // Perform fresh research
  const result = await researchTarget(target);

  // Cache the result
  setCache(target, result, ttlHours);

  return {
    ...result,
    fromCache: false,
  };
}

/**
 * Get human-readable age string
 */
function getAge(isoDate: string): string {
  const cached = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - cached.getTime();

  const minutes = Math.floor(diffMs / (1000 * 60));
  const hours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
  if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
  return `${minutes} minute${minutes > 1 ? 's' : ''}`;
}

// ============================================
// Exports for API
// ============================================

export { DEFAULT_TTL_HOURS };
