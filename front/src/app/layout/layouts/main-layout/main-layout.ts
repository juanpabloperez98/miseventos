import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { SiteFooter } from '../../components/site-footer/site-footer';
import { SiteHeader } from '../../components/site-header/site-header';

@Component({
  selector: 'app-main-layout',
  imports: [RouterOutlet, SiteHeader, SiteFooter],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MainLayout {}
