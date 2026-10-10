import { IMAGE_VARIANTS, optimizedImageUrl, responsiveImage } from './cloudinary-image';

const URL_V1 = 'https://res.cloudinary.com/demo/image/upload/v1712/mis-eventos/events/10/abc.jpg';

describe('cloudinary-image', () => {
  it('should add automatic format, quality and a filled crop after /upload/', () => {
    expect(optimizedImageUrl(URL_V1, { width: 400, height: 250 })).toBe(
      'https://res.cloudinary.com/demo/image/upload/f_auto,q_auto,c_fill,g_auto,w_400,h_250/v1712/mis-eventos/events/10/abc.jpg',
    );
  });

  it('should not force a specific format such as WebP', () => {
    const url = optimizedImageUrl(URL_V1, { width: 800, height: 450 });

    expect(url).toContain('f_auto');
    expect(url).not.toContain('f_webp');
  });

  it('should leave URLs that are not Cloudinary deliveries unchanged', () => {
    for (const url of [
      'https://example.com/image/upload/a.jpg',
      'http://res.cloudinary.com/demo/image/upload/a.jpg',
      'https://res.cloudinary.com/demo/video/upload/a.mp4',
      'not a url',
    ]) {
      expect(optimizedImageUrl(url, { width: 400, height: 250 })).toBe(url);
    }
  });

  it('should offer the reference widths for mobile, tablet, desktop and high resolution', () => {
    const cover = responsiveImage(URL_V1, 'cover');

    expect(cover.srcset.split(', ').map((entry) => entry.split(' ')[1])).toEqual([
      '400w',
      '800w',
      '1200w',
      '1920w',
    ]);
    expect(cover.srcset).toContain('w_1200,h_675/');
    expect(cover.srcset).toContain('w_1920,h_1080/');
    expect(cover.src).toContain('w_400,h_225/');
    expect([cover.width, cover.height]).toEqual([400, 225]);
    expect(cover.sizes).toBe(IMAGE_VARIANTS.cover.sizes);
  });

  it('should keep a fixed ratio per place so the layout does not jump', () => {
    for (const { width, height } of IMAGE_VARIANTS.card.variants) {
      expect(width / height).toBeCloseTo(16 / 10);
    }
    for (const { width, height } of IMAGE_VARIANTS.cover.variants) {
      expect(width / height).toBeCloseTo(16 / 9, 2);
    }
    expect(responsiveImage(URL_V1, 'card').src).toContain('w_400,h_250/');
  });
});
