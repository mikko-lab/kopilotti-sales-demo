const toggle = document.getElementById('navToggle');
const nav = document.getElementById('primaryNav');

function closeNav() {
  nav.classList.remove('is-open');
  toggle.setAttribute('aria-expanded', 'false');
}

function openNav() {
  nav.classList.add('is-open');
  toggle.setAttribute('aria-expanded', 'true');
}

toggle.addEventListener('click', () => {
  if (nav.classList.contains('is-open')) {
    closeNav();
  } else {
    openNav();
  }
});

nav.addEventListener('click', (event) => {
  if (event.target.tagName === 'A') closeNav();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && nav.classList.contains('is-open')) {
    closeNav();
    toggle.focus();
  }
});

document.addEventListener('click', (event) => {
  if (!nav.classList.contains('is-open')) return;
  if (nav.contains(event.target) || toggle.contains(event.target)) return;
  closeNav();
});
