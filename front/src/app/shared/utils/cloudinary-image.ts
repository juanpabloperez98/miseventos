export interface ImageSize {
  width: number;
  height: number;
}

export interface ResponsiveImage {
  src: string;
  srcset: string;
  sizes: string;
  width: number;
  height: number;
}

export const IMAGE_VARIANTS = {
  card: {
    sizes: '(min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw',
    variants: [
      { width: 400, height: 250 },
      { width: 800, height: 500 },
    ],
  },
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

export function optimizedImageUrl(secureUrl: string, size: ImageSize): string {
  const index = secureUrl.indexOf(UPLOAD_SEGMENT);
  if (!isCloudinaryUrl(secureUrl) || index === -1) {
    return secureUrl;
  }
  const transformation = `f_auto,q_auto,c_fill,g_auto,w_${size.width},h_${size.height}`;
  const position = index + UPLOAD_SEGMENT.length;
  return `${secureUrl.slice(0, position)}${transformation}/${secureUrl.slice(position)}`;
}

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
