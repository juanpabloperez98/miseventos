import { type ComponentFixture, TestBed } from '@angular/core/testing';

import {
  buildEvent,
  buildImage,
  provideTestDependencies,
  textOf,
} from '../../../../../testing/test-helpers';
import { type EventImage, type EventModel } from '../../models/event.model';
import { DEFAULT_EVENT_COVER, EventCard } from './event-card';

describe('EventCard', () => {
  let fixture: ComponentFixture<EventCard>;
  let element: HTMLElement;

  const image = () => element.querySelector('img.card__image') as HTMLImageElement;

  async function render(event: EventModel): Promise<void> {
    fixture.componentRef.setInput('event', event);
    await fixture.whenStable();
  }

  async function failToLoad(): Promise<void> {
    image().dispatchEvent(new Event('error'));
    await fixture.whenStable();
  }

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    fixture = TestBed.createComponent(EventCard);
    element = fixture.nativeElement;
  });

  it('should show the Cloudinary cover with its optimized, responsive variants', async () => {
    await render(buildEvent({ image: buildImage() }));

    expect(image().getAttribute('src')).toBe(
      'https://res.cloudinary.com/demo/image/upload/f_auto,q_auto,c_fill,g_auto,w_400,h_250/v1/mis-eventos/events/10/0123456789abcdef0123456789abcdef.jpg',
    );
    expect(image().getAttribute('srcset')).toContain('w_800,h_500/');
    expect(image().getAttribute('srcset')).toContain('800w');
    expect(image().getAttribute('sizes')).toContain('33vw');
    expect(image().getAttribute('loading')).toBe('lazy');
    expect([image().getAttribute('width'), image().getAttribute('height')]).toEqual(['400', '250']);
  });

  it('should put the cover first, then the date band and the content', async () => {
    await render(buildEvent({ image: buildImage() }));

    const sections = [...element.querySelectorAll('.card > *')].map((child) => child.className);
    expect(sections).toEqual(['card__media', 'card__band', 'card__body']);
    expect(element.querySelector('.card__media img')).toBe(image());
  });

  const withoutImage: [string, Partial<EventModel>][] = [
    ['null', { image: null }],
    ['missing', {}],
    ['with an empty URL', { image: buildImage({ secure_url: '' }) }],
    ['with a blank URL', { image: buildImage({ secure_url: '   ' }) }],
  ];
  for (const [description, overrides] of withoutImage) {
    it(`should show the default cover when the image is ${description}`, async () => {
      const event = buildEvent(overrides);
      if (!('image' in overrides)) {
        delete event.image;
      }
      await render(event);

      expect(image().getAttribute('src')).toBe(DEFAULT_EVENT_COVER);
      expect(image().hasAttribute('srcset')).toBeFalse();
      expect(image().hasAttribute('sizes')).toBeFalse();
      expect([image().getAttribute('width'), image().getAttribute('height')]).toEqual([
        '400',
        '250',
      ]);
    });
  }

  it('should replace a Cloudinary cover that fails to load by the default one', async () => {
    const event = buildEvent({ image: buildImage() });
    await render(event);

    await failToLoad();

    expect(image().getAttribute('src')).toBe(DEFAULT_EVENT_COVER);
    expect(image().hasAttribute('srcset')).toBeFalse();
    expect(event.image).toEqual(buildImage());
  });

  it('should not loop when the default cover also fails', async () => {
    await render(buildEvent({ image: buildImage() }));
    await failToLoad();

    await failToLoad();
    await failToLoad();

    expect(image().getAttribute('src')).toBe(DEFAULT_EVENT_COVER);
  });

  it('should try the image of another event even after a failure', async () => {
    await render(buildEvent({ image: buildImage() }));
    await failToLoad();

    const other: EventImage = buildImage({
      secure_url: 'https://res.cloudinary.com/demo/image/upload/v2/mis-eventos/events/11/other.jpg',
    });
    await render(buildEvent({ id: 11, image: other }));

    expect(image().getAttribute('src')).toContain(
      '/upload/f_auto,q_auto,c_fill,g_auto,w_400,h_250/v2/',
    );
  });

  it('should keep the event data and status', async () => {
    await render(
      buildEvent({
        image: null,
        name: 'PyCon',
        description: 'Charlas de Python',
        location: 'Medellín',
        capacity: 120,
        status: 'DRAFT',
      }),
    );

    expect(textOf(element.querySelector('.card__title'))).toBe('PyCon');
    expect(element.querySelector('a.card__link')?.getAttribute('href')).toBe('/events/10');
    expect(textOf(element.querySelector('.card__description'))).toBe('Charlas de Python');
    expect(textOf(element.querySelector('app-event-status-badge'))).toBe('Borrador');
    expect(textOf(element.querySelector('.card__day'))).toBe('10');
    const meta = textOf(element.querySelector('.card__meta'));
    expect(meta).toContain('Medellín');
    expect(meta).toContain('120 personas');
    expect(meta).toContain('10/05/2030 · 9:00 AM – 5:00 PM');
  });
});
