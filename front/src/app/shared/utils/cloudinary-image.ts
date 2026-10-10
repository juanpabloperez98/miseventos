/**
 * Single place where Cloudinary delivery URLs are built. Cloudinary generates each variant on
 * demand from the original upload and caches it in its CDN, so no copies are stored per size.
 *
 * Every variant uses:
 * - `f_auto`: best format the browser supports (AVIF/WebP when possible, JPEG/PNG otherwise).
 * - `q_auto`: automatic quality/compression.
 * - `c_fill,g_auto`: fills the exact box, cropping around the most relevant area, so the layout
 *   never jumps (the ratio is fixed per use).
 */

export interface ImageSize {
  width: number;
  height: number;
}

export interface ResponsiveImage {
  /** Fallback for browsers without `srcset` (the smallest variant). */
  src: string;
  srcset: string;
  sizes: string;
  /** Intrinsic size of `src`, so the browser reserves the space before loading. */
  width: number;
  height: number;
}

/**
 * Variants per use. Widths match the reference devices (mobile 400, tablet 800, desktop 1200,
 * high resolution 1920); the height follows the ratio of each place in the interface.
 */
export const IMAGE_VARIANTS = {
  /** Event cards (16:10). The card is at most ~400 px wide; 800 covers 2x screens. */
  card: {
    sizes: '(min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw',
    variants: [
      { width: 400, height: 250 },
      { width: 800, height: 500 },
    ],
  },
  /** Cover of the event detail and form previews (16:9). */
  cover: {
    sizes: '(min-width: 1200px) 1200px, 100vw',
    variants: [
      { width: 400, height: 225 },
      { width: 800, height: 450 },
      { width: 1200, height: 675 },
      { width: 1920, height: 1080 },
    ],
  },
} as const satisfies Record<string, { sizes: string; variants: readonly ImageSize[] }>;

export type ImageUse = keyof typeof IMAGE_VARIANTS;

const UPLOAD_SEGMENT = '/image/upload/';
const CLOUDINARY_HOST = 'res.cloudinary.com';

/** Delivery URL of the image transformed to `size`. Non-Cloudinary URLs are returned unchanged. */
export function optimizedImageUrl(secureUrl: string, size: ImageSize): string {
  const index = secureUrl.indexOf(UPLOAD_SEGMENT);
  if (!isCloudinaryUrl(secureUrl) || index === -1) {
    return secureUrl;
  }
  const transformation = `f_auto,q_auto,c_fill,g_auto,w_${size.width},h_${size.height}`;
  const position = index + UPLOAD_SEGMENT.length;
  return `${secureUrl.slice(0, position)}${transformation}/${secureUrl.slice(position)}`;
}

/** `src`, `srcset` and `sizes` for an `<img>` in the given place of the interface. */
export function responsiveImage(secureUrl: string, use: ImageUse): ResponsiveImage {
  const { sizes, variants } = IMAGE_VARIANTS[use];
  const [smallest] = variants;
  return {
    src: optimizedImageUrl(secureUrl, smallest),
    srcset: variants
      .map((variant) => `${optimizedImageUrl(secureUrl, variant)} ${variant.width}w`)
      .join(', '),
    sizes,
    width: smallest.width,
    height: smallest.height,
  };
}

function isCloudinaryUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname === CLOUDINARY_HOST;
  } catch {
    return false;
  }
}
