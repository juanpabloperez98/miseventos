import indexHtml from './index.html' with { loader: 'text' };

/** Checks the static `index.html` shipped with the application. */
describe('index.html', () => {
  const document = new DOMParser().parseFromString(indexHtml, 'text/html');

  it('should declare a single favicon pointing to the MisEventos .ico', () => {
    const icons = document.querySelectorAll('link[rel~="icon"]');

    expect(icons.length).toBe(1);
    expect(icons[0].getAttribute('href')).toBe('logo_mis_eventos.ico');
    expect(icons[0].getAttribute('type')).toBe('image/x-icon');
  });

  it('should resolve the favicon from the root of the site, where public/ files are served', () => {
    const base = document.querySelector('base')?.getAttribute('href');
    const href = document.querySelector('link[rel~="icon"]')?.getAttribute('href') ?? '';

    expect(base).toBe('/');
    expect(new URL(href, new URL(base ?? '', 'https://mis-eventos.test')).pathname).toBe(
      '/logo_mis_eventos.ico',
    );
  });
});
