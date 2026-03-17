(function () {
  "use strict";

  const udHeader = document.querySelector(".ud-header");
  const navbarToggler = document.querySelector(".navbar-toggler");
  const navbarCollapse = document.querySelector(".navbar-collapse");
  const mobileHeaderMedia = window.matchMedia("(max-width: 991px)");
  let isHeaderSticky = false;

  const syncHeaderStickyState = () => {
    if (!udHeader) {
      return;
    }

    if (mobileHeaderMedia.matches) {
      if (isHeaderSticky) {
        udHeader.classList.remove("sticky");
        isHeaderSticky = false;
      }
      return;
    }

    const stickyThreshold = udHeader.offsetTop;
    const shouldStick = window.pageYOffset > stickyThreshold;

    if (shouldStick === isHeaderSticky) {
      return;
    }

    udHeader.classList.toggle("sticky", shouldStick);
    isHeaderSticky = shouldStick;
  };

  // ======= Sticky
  const handleScroll = function () {
    syncHeaderStickyState();

    // show or hide the back-top-top button
    const backToTop = document.querySelector(".back-to-top");
    if (backToTop) {
      if (
        document.body.scrollTop > 50 ||
        document.documentElement.scrollTop > 50
      ) {
        backToTop.style.display = "flex";
      } else {
        backToTop.style.display = "none";
      }
    }
  };
  window.addEventListener("scroll", handleScroll, { passive: true });
  window.addEventListener("resize", syncHeaderStickyState);
  syncHeaderStickyState();

  //===== close navbar-collapse when a  clicked
  if (navbarToggler && navbarCollapse) {
    document.querySelectorAll(".ud-menu-scroll").forEach((e) =>
      e.addEventListener("click", () => {
        navbarToggler.classList.remove("active");
        navbarCollapse.classList.remove("show");
        navbarToggler.setAttribute("aria-expanded", "false");
      })
    );
    navbarToggler.addEventListener("click", function () {
      navbarToggler.classList.toggle("active");
      navbarCollapse.classList.toggle("show");
      navbarToggler.setAttribute(
        "aria-expanded",
        navbarCollapse.classList.contains("show") ? "true" : "false"
      );
    });
  }

  // ===== submenu
  const submenuButton = document.querySelectorAll(".nav-item-has-children");
  submenuButton.forEach((elem) => {
    elem.querySelector("a").addEventListener("click", () => {
      elem.querySelector(".ud-submenu").classList.toggle("show");
    });
  });

  // ===== wow js
  new WOW().init();

  // ====== scroll top js
  function scrollTo(element, to = 0, duration = 500) {
    const start = element.scrollTop;
    const change = to - start;
    const increment = 20;
    let currentTime = 0;

    const animateScroll = () => {
      currentTime += increment;

      const val = Math.easeInOutQuad(currentTime, start, change, duration);

      element.scrollTop = val;

      if (currentTime < duration) {
        setTimeout(animateScroll, increment);
      }
    };

    animateScroll();
  }

  Math.easeInOutQuad = function (t, b, c, d) {
    t /= d / 2;
    if (t < 1) return (c / 2) * t * t + b;
    t--;
    return (-c / 2) * (t * (t - 2) - 1) + b;
  };

  const backToTop = document.querySelector(".back-to-top");
  if (backToTop) {
    backToTop.onclick = () => {
      scrollTo(document.documentElement);
    };
  }
})();
