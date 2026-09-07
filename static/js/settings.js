document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("settings-toggle");
    const popover = document.getElementById("settings-popover");
    if (!toggle || !popover) {
        return;
    }

    function close() {
        popover.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
    }

    function open() {
        popover.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
    }

    toggle.addEventListener("click", function (event) {
        event.stopPropagation();
        if (popover.hidden) {
            open();
        } else {
            close();
        }
    });

    document.addEventListener("click", function (event) {
        if (!popover.hidden && !popover.contains(event.target) && event.target !== toggle) {
            close();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            close();
        }
    });
});
