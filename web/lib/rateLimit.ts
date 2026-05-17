/** Simple in-process sliding-window rate limiter (per IP). */

interface Bucket {
  count: number;
  resetAt: number;
}

const store = new Map<string, Bucket>();

/**
 * Returns true if the request is allowed, false if rate-limited.
 * Cleans up expired buckets every 5 minutes to avoid memory leak.
 */
export function checkRateLimit(
  ip: string,
  maxRequests: number,
  windowMs: number,
): boolean {
  const now = Date.now();
  const bucket = store.get(ip);

  if (!bucket || now > bucket.resetAt) {
    store.set(ip, { count: 1, resetAt: now + windowMs });
    return true;
  }

  if (bucket.count >= maxRequests) return false;
  bucket.count += 1;
  return true;
}

// Purge stale entries every 5 minutes
if (typeof setInterval !== "undefined") {
  setInterval(() => {
    const now = Date.now();
    store.forEach((bucket, key) => {
      if (now > bucket.resetAt) store.delete(key);
    });
  }, 5 * 60 * 1000);
}
