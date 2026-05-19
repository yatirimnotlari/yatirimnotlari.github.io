import fs from 'node:fs';
import path from 'node:path';
import pLimit from 'p-limit';
import ogs from 'open-graph-scraper';

// --- Types ---

export interface BookmarkCategory {
  slug: string;
  category: string;
  order: number;
  urls: string[];
}

export interface OGData {
  url: string;
  title: string;
  description: string | null;
  image: string | null;
  favicon: string;
}

export interface Bookmark extends OGData {
  category: string;
  categorySlug: string;
}

type CacheStore = Record<string, OGData>;

// --- Paths ---

const BOOKMARKS_DIR = path.join(process.cwd(), 'src/content/bookmarks');
const CACHE_FILE = path.join(process.cwd(), '.bookmarks-cache.json');

// --- Cache ---

function loadCache(): CacheStore {
  try {
    if (fs.existsSync(CACHE_FILE)) {
      return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf-8')) as CacheStore;
    }
  } catch {
    console.warn('[bookmarks] Cache okunamadı, sıfırdan başlanıyor.');
  }
  return {};
}

function saveCache(cache: CacheStore): void {
  try {
    fs.writeFileSync(CACHE_FILE, JSON.stringify(cache, null, 2), 'utf-8');
  } catch (err) {
    console.warn('[bookmarks] Cache kaydedilemedi:', err);
  }
}

// --- Frontmatter parser ---

function parseFrontmatter(raw: string): { frontmatter: Record<string, string | number>; body: string } {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { frontmatter: {}, body: raw };

  const frontmatter: Record<string, string | number> = {};
  for (const line of match[1].split('\n')) {
    const [key, ...rest] = line.split(':');
    if (!key) continue;
    const raw = rest.join(':').trim();
    frontmatter[key.trim()] = isNaN(Number(raw)) ? raw : Number(raw);
  }
  return { frontmatter, body: match[2] };
}

// --- Category loader ---

export function loadBookmarkCategories(): BookmarkCategory[] {
  const files = fs.readdirSync(BOOKMARKS_DIR).filter(f => f.endsWith('.md'));
  const categories: BookmarkCategory[] = [];

  for (const file of files) {
    const raw = fs.readFileSync(path.join(BOOKMARKS_DIR, file), 'utf-8');
    const { frontmatter, body } = parseFrontmatter(raw);

    const urls = body
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.startsWith('- '))
      .map(line => line.slice(2).trim())
      .filter(Boolean);

    categories.push({
      slug: String(frontmatter.slug ?? file.replace('.md', '')),
      category: String(frontmatter.category ?? file.replace('.md', '')),
      order: Number(frontmatter.order ?? 99),
      urls,
    });
  }

  return categories.sort((a, b) => a.order - b.order);
}

// --- Helpers ---

function getDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

function getFavicon(url: string): string {
  return `https://www.google.com/s2/favicons?domain=${getDomain(url)}&sz=128`;
}

function fallback(url: string): OGData {
  return {
    url,
    title: getDomain(url),
    description: null,
    image: null,
    favicon: getFavicon(url),
  };
}

// --- FxTwitter fetch ---

async function fetchTweetData(url: string): Promise<OGData> {
  try {
    const parsed = new URL(url);
    // pathname: /<username>/status/<id>
    const parts = parsed.pathname.split('/').filter(Boolean);
    const username = parts[0];
    const id = parts[2];

    if (!username || !id) return fallback(url);

    const apiUrl = `https://api.fxtwitter.com/${username}/status/${id}`;
    console.log(`[bookmarks] FxTwitter isteği: ${apiUrl}`);

    const res = await fetch(apiUrl, { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) return fallback(url);

    const json = (await res.json()) as {
      tweet?: {
        author?: { name?: string; avatar_url?: string };
        text?: string;
      };
    };

    const tweet = json.tweet;
    if (!tweet) return fallback(url);

    return {
      url,
      title: tweet.author?.name ?? getDomain(url),
      description: tweet.text ?? null,
      image: tweet.author?.avatar_url ?? null,
      favicon: getFavicon(url),
    };
  } catch (err) {
    console.warn(`[bookmarks] Tweet verisi alınamadı (${url}):`, err);
    return fallback(url);
  }
}

// --- OG fetch ---

async function fetchRegularOGData(url: string): Promise<OGData> {
  try {
    console.log(`[bookmarks] OG çekiliyor: ${url}`);
    const { result } = await ogs({ url, timeout: 10_000 });

    const image = Array.isArray(result.ogImage) && result.ogImage.length > 0
      ? (result.ogImage[0].url ?? null)
      : null;

    return {
      url,
      title: result.ogTitle ?? getDomain(url),
      description: result.ogDescription ?? null,
      image,
      favicon: getFavicon(url),
    };
  } catch (err) {
    console.warn(`[bookmarks] OG verisi alınamadı (${url}):`, err);
    return fallback(url);
  }
}

// --- Main fetch (cache-aware) ---

export async function fetchOGData(url: string, cache: CacheStore): Promise<OGData> {
  if (cache[url]) {
    console.log(`[bookmarks] Cache'den: ${url}`);
    return cache[url];
  }

  const isTweet = url.includes('twitter.com') || url.includes('x.com');
  const data = isTweet ? await fetchTweetData(url) : await fetchRegularOGData(url);

  cache[url] = data;
  return data;
}

// --- getAllBookmarks ---

export async function getAllBookmarks(): Promise<Bookmark[]> {
  const cache = loadCache();
  const categories = loadBookmarkCategories();

  const allUrls = categories.flatMap(cat => cat.urls.map(url => ({ url, cat })));

  const uncachedUrls = allUrls.filter(({ url }) => !cache[url]);
  if (uncachedUrls.length > 0) {
    console.log(`[bookmarks] ${uncachedUrls.length} yeni URL çekilecek...`);
  }

  const limit = pLimit(5);

  await Promise.all(
    allUrls.map(({ url }) =>
      limit(async () => {
        if (!cache[url]) {
          await fetchOGData(url, cache);
        }
      })
    )
  );

  saveCache(cache);

  const bookmarks: Bookmark[] = [];
  for (const cat of categories) {
    for (const url of cat.urls) {
      const og = cache[url] ?? fallback(url);
      bookmarks.push({
        ...og,
        category: cat.category,
        categorySlug: cat.slug,
      });
    }
  }

  return bookmarks;
}
