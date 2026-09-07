document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("line-form");
    if (!form) {
        return;
    }
    const family = form.querySelector("#id_family");
    const subFamily = form.querySelector("#id_sub_family");
    const manufacturer = form.querySelector("#id_manufacturer");
    const item = form.querySelector("#id_item");
    if (!manufacturer || !item) {
        return;
    }

    function optionValue(select) {
        return select ? select.value : "";
    }

    function filterSelect(select, keep) {
        if (!select) {
            return;
        }
        const current = select.value;
        Array.prototype.forEach.call(select.options, function (opt) {
            if (!opt.value) {
                opt.hidden = false;
                opt.disabled = false;
                return;
            }
            const visible = keep(opt);
            opt.hidden = !visible;
            opt.disabled = !visible;
        });
        const selected = select.options[select.selectedIndex];
        if (selected && selected.hidden) {
            select.value = "";
        } else if (current) {
            select.value = current;
        }
    }

    function defaultOption(select) {
        if (!select) {
            return null;
        }
        return Array.prototype.find.call(select.options, function (opt) {
            return opt.value && !opt.hidden && opt.getAttribute("data-default") === "1";
        });
    }

    function firstVisible(select) {
        if (!select) {
            return null;
        }
        return Array.prototype.find.call(select.options, function (opt) {
            return opt.value && !opt.hidden;
        });
    }

    function lockManufacturer() {
        if (!subFamily) {
            manufacturer.disabled = false;
            return;
        }
        const selected = subFamily.options[subFamily.selectedIndex];
        const brandId =
            selected && selected.value ? selected.getAttribute("data-brand") || "" : "";
        if (brandId) {
            manufacturer.value = brandId;
            manufacturer.disabled = true;
        } else {
            manufacturer.disabled = false;
        }
    }

    function sync(applyDefaults) {
        const familyId = optionValue(family);
        if (subFamily) {
            filterSelect(subFamily, function (opt) {
                return !familyId || opt.getAttribute("data-family") === familyId;
            });
            if (applyDefaults && !subFamily.value) {
                const fallback = defaultOption(subFamily) || firstVisible(subFamily);
                if (fallback) {
                    subFamily.value = fallback.value;
                }
            }
        }
        lockManufacturer();
        const subId = optionValue(subFamily);
        const brandId = optionValue(manufacturer);
        filterSelect(item, function (opt) {
            const matchSub =
                !subFamily || !subId || opt.getAttribute("data-sub-family") === subId;
            const matchBrand = !brandId || opt.getAttribute("data-brand") === brandId;
            return matchSub && matchBrand;
        });
        if (applyDefaults && !item.value) {
            const fallback = defaultOption(item);
            if (fallback) {
                item.value = fallback.value;
            }
        }
    }

    function applyNewLineDefaults() {
        if (item.value) {
            sync(false);
            return;
        }
        if (family && !family.value) {
            const fam = defaultOption(family);
            if (fam) {
                family.value = fam.value;
            }
        }
        if (!manufacturer.value) {
            const brand = defaultOption(manufacturer);
            if (brand) {
                manufacturer.value = brand.value;
            }
        }
        sync(true);
    }

    if (family) {
        family.addEventListener("change", function () {
            if (subFamily) {
                subFamily.value = "";
            }
            item.value = "";
            sync(true);
        });
    }
    if (subFamily) {
        subFamily.addEventListener("change", function () {
            item.value = "";
            sync(true);
        });
    }
    manufacturer.addEventListener("change", function () {
        item.value = "";
        sync(true);
    });

    applyNewLineDefaults();
});
