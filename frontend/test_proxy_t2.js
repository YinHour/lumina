const i18nTranslateCopy = (path, options) => {
  if (path === "searchPage.search") return "Search";
  return path; // default fallback returns the key
};

const BLOCKED_PROPS = new Set([
  '__proto__', '__esModule', '$$typeof', 'toJSON', 'constructor',
  'valueOf', 'toString', 'inspect', 'nodeType', 'tagName',
  'then', 'catch', 'finally', 
  'prototype', 'caller', 'callee', 'arguments', 
  'Symbol(Symbol.toStringTag)', 'Symbol(Symbol.iterator)',
]);

const createProxy = (path, depth = 0) => {
  if (depth > 3) return path;
  
  const proxyTarget = (keyOrOptions, options) => {
    if (typeof keyOrOptions === 'string') {
      const fullPath = path ? `${path}.${keyOrOptions}` : keyOrOptions;
      return i18nTranslateCopy(fullPath, options);
    }
    return i18nTranslateCopy(path, keyOrOptions);
  };

  return new Proxy(proxyTarget, {
    get(target, prop) {
      if (typeof prop === 'symbol') return target[prop];
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
};

const t = createProxy('', 0);
console.log("Direct call output:", t('searchPage.search'));
console.log("Direct call type:", typeof t('searchPage.search'));
