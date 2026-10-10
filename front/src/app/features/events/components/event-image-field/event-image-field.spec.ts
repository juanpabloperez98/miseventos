import { type ComponentFixture, TestBed } from '@angular/core/testing';

import {
  buildImage,
  imageFile,
  provideTestDependencies,
  selectFile,
  textOf,
} from '../../../../../testing/test-helpers';
import { type EventImageSelection } from '../../services/event-images.service';
import { EventImageField } from './event-image-field';

describe('EventImageField', () => {
  let fixture: ComponentFixture<EventImageField>;
  let element: HTMLElement;
  let emitted: EventImageSelection[];

  const fileInput = () => element.querySelector('input[type="file"]') as HTMLInputElement;
  const image = () => element.querySelector('img');
  const button = () => element.querySelector('button');

  async function choose(file: File): Promise<void> {
    selectFile(fileInput(), file);
    await fixture.whenStable();
  }

  beforeEach(async () => {
    TestBed.configureTestingModule({ providers: provideTestDependencies() });
    fixture = TestBed.createComponent(EventImageField);
    element = fixture.nativeElement;
    emitted = [];
    fixture.componentInstance.selectionChange.subscribe((value) => emitted.push(value));
    spyOn(URL, 'createObjectURL').and.returnValue('blob:preview');
    spyOn(URL, 'revokeObjectURL');
    await fixture.whenStable();
  });

  it('should be labelled and accept only the allowed image types', () => {
    expect(textOf(element.querySelector('label'))).toBe('Imagen de portada');
    expect(fileInput().accept).toBe('image/jpeg,image/png,image/webp');
    expect(textOf(element.querySelector('.preview'))).toBe('Sin imagen');
  });

  it('should show the current image through an optimized Cloudinary URL', async () => {
    fixture.componentRef.setInput('image', buildImage());
    await fixture.whenStable();

    expect(image()?.getAttribute('src')).toContain(
      '/upload/f_auto,q_auto,c_fill,g_auto,w_400,h_225/',
    );
    expect(image()?.getAttribute('srcset')).toContain('1920w');
    expect(textOf(button())).toBe('Quitar imagen');
  });

  it('should preview a valid file locally and emit it', async () => {
    const file = imageFile();
    await choose(file);

    expect(image()?.getAttribute('src')).toBe('blob:preview');
    expect(emitted).toEqual([{ file, remove: false }]);
  });

  it('should reject invalid files before any upload', async () => {
    await choose(imageFile('big.jpg', 'image/jpeg', 6 * 1024 * 1024));

    expect(textOf(element.querySelector('.error'))).toBe('La imagen no puede superar 5 MB.');
    expect(fileInput().getAttribute('aria-invalid')).toBe('true');
    expect(emitted).toEqual([]);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('should discard a new file and release its preview', async () => {
    await choose(imageFile());
    button()?.click();
    await fixture.whenStable();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview');
    expect(image()).toBeNull();
    expect(emitted.at(-1)).toEqual({ file: null, remove: false });
  });

  it('should mark the current image for removal and allow undoing it', async () => {
    fixture.componentRef.setInput('image', buildImage());
    await fixture.whenStable();

    button()?.click();
    await fixture.whenStable();
    expect(textOf(element.querySelector('.preview'))).toBe('La imagen se quitará al guardar.');
    expect(emitted.at(-1)).toEqual({ file: null, remove: true });

    button()?.click();
    await fixture.whenStable();
    expect(image()).not.toBeNull();
    expect(emitted.at(-1)).toEqual({ file: null, remove: false });
  });

  it('should show the upload status and disable the controls while saving', async () => {
    fixture.componentRef.setInput('status', 'Subiendo la imagen… 40 %');
    fixture.componentRef.setInput('disabled', true);
    await fixture.whenStable();

    expect(textOf(element.querySelector('[role="status"]'))).toBe('Subiendo la imagen… 40 %');
    expect(fileInput().disabled).toBeTrue();
  });
});
