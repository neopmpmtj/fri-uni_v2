document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("new-draft-form");
    if (!form) {
        return;
    }
    const client = form.querySelector("#id_client");
    const site = form.querySelector("#id_site");
    if (!client || !site) {
        return;
    }

    function filterSelect(select, keep) {
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

    function firstVisible(select) {
        return Array.prototype.find.call(select.options, function (opt) {
            return opt.value && !opt.hidden;
        });
    }

    function syncSites() {
        const clientId = client.value;
        site.disabled = !clientId;
        filterSelect(site, function (opt) {
            return !clientId || opt.getAttribute("data-client") === clientId;
        });
        if (clientId && !site.value) {
            const fallback = firstVisible(site);
            if (fallback) {
                site.value = fallback.value;
            }
        }
    }

    client.addEventListener("change", syncSites);
    syncSites();
});
