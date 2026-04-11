const i18next = require('i18next');
i18next.init({
    lng: 'en',
    resources: {
        en: {
            translation: {
                searchPage: {
                    search: "Search"
                }
            }
        }
    }
});

const t = i18next.t.bind(i18next);
const result = t("searchPage.search", { returnObjects: true });
console.log("result type:", typeof result, "result value:", result);

const missing = t("searchPage.missing", { returnObjects: true });
console.log("missing type:", typeof missing, "missing value:", missing);
