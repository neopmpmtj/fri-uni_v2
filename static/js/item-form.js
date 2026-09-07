document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("item-form");
    if (!form) {
        return;
    }
    const family = form.querySelector("#id_family");
    const subFamily = form.querySelector("#id_sub_family");
    const brand = form.querySelector("#id_brand");
    const kind = form.querySelector("#id_kind");
    if (!subFamily) {
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
        const familyId = family ? family.value : "";
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

    function syncKindFields() {
        const isOutdoor = kind && kind.value === "outdoor";
        Array.prototype.forEach.call(
            form.querySelectorAll(".item-indoor-field"),
            function (el) {
                el.hidden = isOutdoor;
            }
        );
        Array.prototype.forEach.call(
            form.querySelectorAll(".item-outdoor-field"),
            function (el) {
                el.hidden = !isOutdoor;
            }
        );
        if (isOutdoor && brand) {
            brand.disabled = false;
        } else {
            lockBrand();
        }
    }

    if (family) {
        family.addEventListener("change", function () {
            subFamily.value = "";
            filterSubFamilies();
        });
    }
    subFamily.addEventListener("change", lockBrand);
    if (kind) {
        kind.addEventListener("change", syncKindFields);
    }
    filterSubFamilies();
    syncKindFields();
});
