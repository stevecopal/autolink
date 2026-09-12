(function () {
  'use strict';

  const btn = document.getElementById('mobile-menu-btn');
  const menu = document.getElementById('mobile-menu');
  const closeBtn = document.getElementById('mobile-menu-close');
  if (!btn || !menu) return;

  const hamburger = btn.querySelector('.hamburger-icon');
  const close = btn.querySelector('.close-icon');

  document.head.insertAdjacentHTML('beforeend', `<style>
    #mobile-menu{
      position:fixed;inset:0;z-index:45;
      background:#00002B;
      transform-origin:top right;
      transform:perspective(1200px) rotateY(90deg);
      opacity:0;
      pointer-events:none;
      transition:transform .5s cubic-bezier(.4,0,.2,1),opacity .5s cubic-bezier(.4,0,.2,1);
      overflow-y:auto;
    }
    #mobile-menu.open{
      transform:perspective(1200px) rotateY(0deg);
      opacity:1;
      pointer-events:auto;
    }
    #mobile-menu.closing{
      transform:perspective(1200px) rotateY(90deg);
      opacity:0;
      pointer-events:none;
    }
  `);

  let animating = false;

  function openMenu() {
    if (animating) return;
    animating = true;
    menu.classList.remove('closing','hidden');
    hamburger.classList.add('hidden');
    close.classList.remove('hidden');
    btn.setAttribute('aria-expanded','true');
    void menu.offsetWidth;
    menu.classList.add('open');
    setTimeout(function(){ animating = false; }, 520);
  }

  function closeMenu() {
    if (animating) return;
    animating = true;
    menu.classList.remove('open');
    menu.classList.add('closing');
    hamburger.classList.remove('hidden');
    close.classList.add('hidden');
    btn.setAttribute('aria-expanded','false');
    setTimeout(function(){
      menu.classList.add('hidden');
      menu.classList.remove('closing');
      animating = false;
    }, 520);
  }

  btn.addEventListener('click', function () {
    if (menu.classList.contains('open')) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', closeMenu);
  }
})();
