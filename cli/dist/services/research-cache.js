"use strict";
/**
 * Research Cache Service
 *
 * File-based caching for AI research results to minimize API costs
 * and provide faster responses for recently researched targets.
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_TTL_HOURS = void 0;
exports.getCache = getCache;
exports.setCache = setCache;
exports.clearCache = clearCache;
exports.clearAllCache = clearAllCache;
exports.getCacheStats = getCacheStats;
exports.getCachedOrResearch = getCachedOrResearch;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const ai_research_agent_1 = require("./ai-research-agent");
// ============================================
// Configuration
// ============================================
const CACHE_DIR = path_1.default.resolve(__dirname, '../../cache/research');
const DEFAULT_TTL_HOURS = 24;
exports.DEFAULT_TTL_HOURS = DEFAULT_TTL_HOURS;
// ============================================
// Cache Operations
// ============================================
/**
 * Initialize cache directory if it doesn't exist
 */
function ensureCacheDir() {
    if (!fs_1.default.existsSync(CACHE_DIR)) {
        fs_1.default.mkdirSync(CACHE_DIR, { recursive: true });
    }
}
/**
 * Get cache file path for a target
 */
function getCachePath(target) {
    const normalized = target.toLowerCase().replace(/[^a-z0-9]/g, '-');
    return path_1.default.join(CACHE_DIR, `${normalized}.json`);
}
/**
 * Check if a cache entry is expired
 */
function isExpired(entry) {
    return new Date(entry.expiresAt) < new Date();
}
/**
 * Read cache for a target
 */
function getCache(target) {
    ensureCacheDir();
    const cachePath = getCachePath(target);
    if (!fs_1.default.existsSync(cachePath)) {
        return null;
    }
    try {
        const data = fs_1.default.readFileSync(cachePath, 'utf-8');
        return JSON.parse(data);
    }
    catch (error) {
        console.warn(`[Cache] Failed to read cache for ${target}:`, error);
        return null;
    }
}
/**
 * Write cache for a target
 */
function setCache(target, result, ttlHours = DEFAULT_TTL_HOURS) {
    ensureCacheDir();
    const cachePath = getCachePath(target);
    const now = new Date();
    const expiresAt = new Date(now.getTime() + ttlHours * 60 * 60 * 1000);
    const entry = {
        result,
        cachedAt: now.toISOString(),
        expiresAt: expiresAt.toISOString(),
        ttlHours,
    };
    try {
        fs_1.default.writeFileSync(cachePath, JSON.stringify(entry, null, 2));
        console.log(`[Cache] Cached research for ${target} (expires: ${expiresAt.toISOString()})`);
    }
    catch (error) {
        console.warn(`[Cache] Failed to write cache for ${target}:`, error);
    }
}
/**
 * Clear cache for a target
 */
function clearCache(target) {
    const cachePath = getCachePath(target);
    if (fs_1.default.existsSync(cachePath)) {
        try {
            fs_1.default.unlinkSync(cachePath);
            console.log(`[Cache] Cleared cache for ${target}`);
            return true;
        }
        catch (error) {
            console.warn(`[Cache] Failed to clear cache for ${target}:`, error);
            return false;
        }
    }
    return false;
}
/**
 * Clear all research cache
 */
function clearAllCache() {
    ensureCacheDir();
    let cleared = 0;
    try {
        const files = fs_1.default.readdirSync(CACHE_DIR);
        for (const file of files) {
            if (file.endsWith('.json')) {
                fs_1.default.unlinkSync(path_1.default.join(CACHE_DIR, file));
                cleared++;
            }
        }
        console.log(`[Cache] Cleared ${cleared} cached entries`);
    }
    catch (error) {
        console.warn(`[Cache] Failed to clear cache:`, error);
    }
    return cleared;
}
/**
 * Get cache statistics
 */
function getCacheStats() {
    ensureCacheDir();
    let totalEntries = 0;
    let validEntries = 0;
    let expiredEntries = 0;
    let oldestEntry = null;
    let newestEntry = null;
    let oldestDate = null;
    let newestDate = null;
    let totalSize = 0;
    try {
        const files = fs_1.default.readdirSync(CACHE_DIR);
        for (const file of files) {
            if (file.endsWith('.json')) {
                totalEntries++;
                const filePath = path_1.default.join(CACHE_DIR, file);
                const stats = fs_1.default.statSync(filePath);
                totalSize += stats.size;
                try {
                    const data = fs_1.default.readFileSync(filePath, 'utf-8');
                    const entry = JSON.parse(data);
                    if (isExpired(entry)) {
                        expiredEntries++;
                    }
                    else {
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
                }
                catch {
                    // Malformed entry
                    expiredEntries++;
                }
            }
        }
    }
    catch (error) {
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
async function getCachedOrResearch(target, options = {}) {
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
    }
    else {
        console.log(`[Cache] Force refresh requested for ${target}`);
    }
    // Perform fresh research
    const result = await (0, ai_research_agent_1.researchTarget)(target);
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
function getAge(isoDate) {
    const cached = new Date(isoDate);
    const now = new Date();
    const diffMs = now.getTime() - cached.getTime();
    const minutes = Math.floor(diffMs / (1000 * 60));
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (days > 0)
        return `${days} day${days > 1 ? 's' : ''}`;
    if (hours > 0)
        return `${hours} hour${hours > 1 ? 's' : ''}`;
    return `${minutes} minute${minutes > 1 ? 's' : ''}`;
}
//# sourceMappingURL=research-cache.js.map