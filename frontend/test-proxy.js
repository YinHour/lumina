const i18nTranslateCopy = (key, opts) => {
  if (key === 'searchPage') return { search: "Search" };
  if (key === 'searchPage.search') return "Search";
  return key;
};

const BLOCKED_PROPS = new Set([
  '__proto__', '__esModule', '$$typeof', 'toJSON', 'constructor',
  'apply', 'call', 'bind'
]);

function createProxy(path, depth) {
  if (depth > 10) return path;

  const proxyTarget = (keyOrOptions, options) => {
      // dummy
  };

  return new Proxy(proxyTarget, {
    get(target, prop) {
      if (typeof prop === 'string' && prop === '$$typeof') return undefined;
      
      if (typeof prop !== 'string') return undefined;

      if (prop.startsWith('__') || prop.startsWith('@@') || BLOCKED_PROPS.has(prop)) {
        return undefined;
      }

      const currentPath = path ? `${path}.${prop}` : prop;

      const result = i18nTranslateCopy(currentPath, { returnObjects: true });

      if (typeof result === 'string') {
        return result;
      }

      if (prop === 'replace' || prop === 'split' || prop === 'length' ||
          prop === 'trim' || prop === 'toLowerCase' || prop === 'toUpperCase') {
        const translated = i18nTranslateCopy(path);
        if (typeof translated === 'string') {
          const val = translated[prop];
          return typeof val === 'function' ? val.bind(translated) : val;
        }
      }

      if (result === currentPath || result === undefined || result === null) {
        return currentPath;
      }

      if (typeof result === 'object') {
        return createProxy(currentPath, depth + 1);
      }

      return result;
    }
  });
}

const t = createProxy('', 0);
console.log(typeof t.searchPage.search);
console.log(t.searchPage.search);
