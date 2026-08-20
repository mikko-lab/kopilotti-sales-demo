// Vercel Web Analytics is never loaded on a Magic Link page (/n/{token}) --
// no analytics or marketing script of any kind belongs there. Checked
// directly against location.pathname before anything is injected, so the
// script is never even requested on that path, not just hidden after load.
if (!/^\/n\//.test(location.pathname)) {
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  const analyticsScript = document.createElement('script');
  analyticsScript.defer = true;
  analyticsScript.src = '/_vercel/insights/script.js';
  document.head.appendChild(analyticsScript);
}
