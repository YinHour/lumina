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
}, () => {
    const t = i18next.t.bind(i18next);
    console.log(t('searchPage.search', { returnObjects: true }));
    console.log(typeof t('searchPage.search', { returnObjects: true }));
});
