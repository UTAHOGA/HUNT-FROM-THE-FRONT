(() => {
  function isEmbedded() {
    try {
      return window.self !== window.top;
    } catch {
      return true;
    }
  }

  function resolveEmbedMode() {
    const params = new URLSearchParams(window.location.search);
    const forced = params.get('embed');
    if (forced === '1' || forced === 'true') return true;
    if (forced === '0' || forced === 'false') return false;
    return isEmbedded();
  }

  if (resolveEmbedMode()) {
    document.documentElement.classList.add('embed');
    if (document.body) document.body.classList.add('embed');
  }
})();

