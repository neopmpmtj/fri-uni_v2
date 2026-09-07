document.addEventListener("DOMContentLoaded", function () {
    const drawer = document.getElementById("drawer");
    const backdrop = document.getElementById("drawer-backdrop");
    const closeBtn = document.getElementById("drawer-close");
    if (!drawer || !backdrop) {
        return;
    }

    function closeDrawer() {
        drawer.hidden = true;
        backdrop.hidden = true;
    }

    function openDrawer() {
        drawer.hidden = false;
        backdrop.hidden = false;
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", closeDrawer);
    }
    backdrop.addEventListener("click", closeDrawer);
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeDrawer();
        }
    });

    window.openDrawer = openDrawer;
});
