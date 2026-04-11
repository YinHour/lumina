const i18nTranslateCopy = (path, options) => {
  if (path === "searchPage.search") return "Search";
  return path; // default fallback returns the key
};

// Now what happens in use-translation when we call t('searchPage.search')
const target = function(key) {
    return i18nTranslateCopy(key);
}

const proxy = new Proxy(target, {
    get(t, prop) {
        console.log("get", prop);
        return i18nTranslateCopy(prop);
    }
});

// User wrote {t('searchPage.search')}
// In JS, calling a proxy function triggers apply trap, OR if not present, the target function!
console.log("Call as function:", proxy("searchPage.search"));

// But what if it's called somewhere else?
