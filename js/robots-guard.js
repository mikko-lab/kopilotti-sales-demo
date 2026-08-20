// Belt-and-suspenders alongside the X-Robots-Tag response header
// (vercel.json) -- a crawler that somehow reads the HTML before honoring
// the HTTP header still sees this. A plain classic script (no defer/async/
// type=module) executes synchronously at its position during HTML
// parsing, same as an inline script would -- placed early in <head> so
// this runs before the rest of the page. document.write is deliberately
// used here for the one case where it's actually safe: synchronously
// during the initial parse, before the document has finished loading.
// The old demo page (no /n/ prefix) is unaffected and stays indexable.
if (/^\/n\//.test(location.pathname)) {
  document.write('<meta name="robots" content="noindex, nofollow">');
}
