document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("item-form");
    if (!form) {
        return;
    }
    const family = form.querySelector("#id_family");
    const subFamily = form.querySelector("#id_sub_family");
    const brand = form.querySelector("#id_brand");
    if (!family || !subFamily) {
        return;
    }

    function selectedSubFamilyBrandId() {
        const selected = subFamily.options[subFamily.selectedIndex];
        if (!selected || !selected.value) {
            return "";
        }
        return selected.getAttribute("data-brand") || "";
    }

    function lockBrand() {
        if (!brand) {
            return;
        }
        const brandId = selectedSubFamilyBrandId();
        if (brandId) {
            brand.value = brandId;
            brand.disabled = true;
        } else {
            brand.disabled = false;
        }
    }

    function filterSubFamilies() {
        const familyId = family.value;
        Array.prototype.forEach.call(subFamily.options, function (opt) {
            if (!opt.value) {
                opt.hidden = false;
                opt.disabled = false;
                return;
            }
            const visible = !familyId || opt.getAttribute("data-family") === familyId;
            opt.hidden = !visible;
            opt.disabled = !visible;
        });
        const selected = subFamily.options[subFamily.selectedIndex];
        if (selected && selected.hidden) {
            subFamily.value = "";
        }
        lockBrand();
    }

    family.addEventListener("change", function () {
        subFamily.value = "";
        filterSubFamilies();
    });
    subFamily.addEventListener("change", lockBrand);
    filterSubFamilies();
});
