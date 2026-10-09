/** Files imported as text in tests: `import html from './index.html' with { loader: 'text' };`. */
declare module '*.html' {
  const content: string;
  export default content;
}
