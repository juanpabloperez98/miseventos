import { defer, type Observable, Subject } from 'rxjs';

import { RequestCache } from './request-cache';

const TTL = 60_000;

describe('RequestCache', () => {
  let now: number;
  let cache: RequestCache<string>;
  let calls: Subject<string>[];

  /** Each call starts a new "request", answered through `calls[index]`. */
  const load = (): Observable<string> =>
    defer(() => {
      const response = new Subject<string>();
      calls.push(response);
      return response;
    });

  function answer(index: number, value: string): void {
    calls[index].next(value);
    calls[index].complete();
  }

  beforeEach(() => {
    now = 1_000_000;
    cache = new RequestCache<string>(TTL, () => now);
    calls = [];
  });

  it('should share a request in flight between identical calls', () => {
    const received: string[] = [];
    cache.get('a', load).subscribe((value) => received.push(value));
    cache.get('a', load).subscribe((value) => received.push(value));

    expect(calls.length).toBe(1);
    answer(0, 'page');
    expect(received).toEqual(['page', 'page']);
  });

  it('should reuse a response until it expires', () => {
    cache.get('a', load).subscribe();
    answer(0, 'first');

    now += TTL - 1;
    let reused = '';
    cache.get('a', load).subscribe((value) => (reused = value));
    expect(reused).toBe('first');
    expect(calls.length).toBe(1);

    now += 1;
    cache.get('a', load).subscribe();
    expect(calls.length).toBe(2);
  });

  it('should count the expiration from the arrival of the response', () => {
    cache.get('a', load).subscribe();
    now += TTL * 2;
    answer(0, 'slow');

    cache.get('a', load).subscribe();
    expect(calls.length).toBe(1);
  });

  it('should keep different keys apart', () => {
    cache.get('a', load).subscribe();
    cache.get('b', load).subscribe();

    expect(calls.length).toBe(2);
  });

  it('should not keep failed responses', () => {
    let failure: unknown;
    cache.get('a', load).subscribe({ error: (error: unknown) => (failure = error) });
    calls[0].error(new Error('500'));
    expect(failure).toEqual(new Error('500'));

    let value = '';
    cache.get('a', load).subscribe((received) => (value = received));
    expect(calls.length).toBe(2);
    answer(1, 'recovered');
    expect(value).toBe('recovered');
  });

  it('should request again when every subscriber left before the response', () => {
    cache.get('a', load).subscribe().unsubscribe();
    expect(calls[0].observed).toBeFalse();

    cache.get('a', load).subscribe();
    expect(calls.length).toBe(2);
  });

  it('should forget every response when cleared', () => {
    cache.get('a', load).subscribe();
    answer(0, 'old');

    cache.clear();
    cache.get('a', load).subscribe();
    expect(calls.length).toBe(2);
  });
});
