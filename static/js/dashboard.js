document.addEventListener("DOMContentLoaded", function () {
    const select = document.getElementById("pref-language");
    if (!select) {
        return;
    }
    select.value = currentLang();
    select.addEventListener("change", function () {
        persistLang(select.value);
        applyStaticI18n();
    });
});
