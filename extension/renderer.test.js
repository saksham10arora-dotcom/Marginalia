import { describe, it, expect } from 'vitest';
import { renderMarkdown } from './renderer.js';

describe('renderMarkdown', () => {
  it('renders a section heading with a timestamp link as real HTML', () => {
    const html = renderMarkdown('## Vectors [00:00:20](https://youtube.com/watch?v=a&t=20s)\n\nContent.');
    expect(html).toContain('<h2>');
    expect(html).toContain('<a href="https://youtube.com/watch?v=a&amp;t=20s">00:00:20</a>');
  });

  it('renders bold-term bullets as real HTML lists', () => {
    const html = renderMarkdown('- **Vectors** are ordered lists.\n- **Matrices** are 2D.');
    expect(html).toContain('<li><strong>Vectors</strong> are ordered lists.</li>');
    expect(html).toContain('<li><strong>Matrices</strong> are 2D.</li>');
  });

  it('leaves inline math delimiters untouched for the DOM-side KaTeX pass', () => {
    // renderMarkdown only does markdown->HTML; $...$ math is rendered separately
    // by renderMathInElement once the HTML is in a real DOM (KaTeX needs one).
    const html = renderMarkdown('The rate is $r$ and value is $(1+r)^n$.');
    expect(html).toContain('$r$');
    expect(html).toContain('$(1+r)^n$');
  });

  it('escapes raw HTML in the source to prevent injection from model output', () => {
    const html = renderMarkdown('Some text <script>alert(1)</script> more text.');
    expect(html).not.toContain('<script>');
  });

  it('neutralizes a javascript: URI in a markdown link to prevent XSS', () => {
    const html = renderMarkdown('[click me](javascript:alert(1))');
    expect(html).not.toContain('javascript:');
    expect(html).toContain('<a href="#">click me</a>');
  });

  it('preserves a legitimate https link', () => {
    const html = renderMarkdown('[click me](https://example.com)');
    expect(html).toContain('href="https://example.com"');
  });

  it('neutralizes a javascript: URI regardless of casing', () => {
    const html = renderMarkdown('[x](JAVASCRIPT:alert(1))');
    expect(html).not.toContain('JAVASCRIPT:');
    expect(html.toLowerCase()).not.toContain('javascript:');
    expect(html).toContain('<a href="#">x</a>');
  });

  it('renders an inline screenshot marker as fully invisible, not literal text', () => {
    const html = renderMarkdown('Some content <!-- screenshot: 00:02:00 --> continues here.');
    expect(html).not.toContain('screenshot:');
    expect(html).not.toContain('&lt;!--');
    expect(html).toContain('Some content');
    expect(html).toContain('continues here.');
  });

  it('leaves no empty paragraph when a screenshot marker sits on its own line', () => {
    const html = renderMarkdown('## Heading\n\n<!-- screenshot: 00:00:05 -->\n\n* A bullet.');
    expect(html).not.toContain('screenshot:');
    expect(html).not.toContain('<p></p>');
    expect(html).toContain('<li>A bullet.</li>');
  });

  it('does not let a fake screenshot marker smuggle a script tag through', () => {
    // The marker pattern is deliberately narrow (digits/colons only) --
    // anything that doesn't match exactly still goes through the normal
    // escape path.
    const html = renderMarkdown('<!-- screenshot: <script>alert(1)</script> -->');
    expect(html).not.toContain('<script>');
  });
});
