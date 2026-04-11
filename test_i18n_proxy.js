const i18nTranslateCopy = (key) => {
  if (key === 'searchPage.search') return 'Search';
  return key;
};

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
      if (typeof prop !== 'string') return undefined;
      const currentPath = path ? `${path}.${prop}` : prop;
      const result = i18nTranslateCopy(currentPath, { returnObjects: true });
      if (typeof result === 'string') return result;
      return createProxy(currentPath, depth + 1);
    }
  });
};

const t = createProxy('', 0);
console.log("t.searchPage.search:", t.searchPage.search);
console.log("t('searchPage.search'):", t('searchPage.search'));
