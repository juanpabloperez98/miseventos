import { Pipe, type PipeTransform } from '@angular/core';

import { type ImageUse, type ResponsiveImage, responsiveImage } from '../utils/cloudinary-image';

@Pipe({ name: 'responsiveImage' })
export class ResponsiveImagePipe implements PipeTransform {
  transform(secureUrl: string, use: ImageUse): ResponsiveImage {
    return responsiveImage(secureUrl, use);
  }
}
