const i18nTranslateCopy = (path, options) => {
  if (path === 'searchPage') return 'searchPage'; // Simulating missing/loading
  if (path === 'searchPage.search') return 'searchPage.search';
  return path;
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
    return 'target';
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
        return result; // RETURNED PRIMITIVE STRING!
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
console.log("t.searchPage =", t.searchPage);
console.log("typeof t.searchPage =", typeof t.searchPage);
console.log("t.searchPage.search =", t.searchPage.search);
console.log("typeof t.searchPage.search =", typeof t.searchPage.search);
