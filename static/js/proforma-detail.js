document.addEventListener("DOMContentLoaded", function () {
    const dialog = document.getElementById("outcome-confirm");
    const message = document.getElementById("outcome-confirm-message");
    const yesBtn = document.getElementById("outcome-confirm-yes");
    const noBtn = document.getElementById("outcome-confirm-no");
    if (!dialog || !message || !yesBtn || !noBtn) {
        return;
    }

    let pendingButton = null;

    function translate(key) {
        if (typeof t === "function") {
            return t(key);
        }
        return key;
    }

    function closeDialog() {
        pendingButton = null;
        if (dialog.open) {
            dialog.close();
        }
    }

    function submitPending(btn) {
        const form = btn.form || document.getElementById(btn.getAttribute("form"));
        if (!form) {
            return;
        }
        const action = btn.getAttribute("value") || btn.value;
        if (action) {
            let hidden = form.querySelector('input[name="action"]');
            if (!hidden) {
                hidden = document.createElement("input");
                hidden.type = "hidden";
                hidden.name = "action";
                form.appendChild(hidden);
            }
            hidden.value = action;
        }
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit(btn);
        } else {
            form.submit();
        }
    }

    document.querySelectorAll("[data-confirm-i18n]").forEach(function (btn) {
        btn.addEventListener("click", function (event) {
            event.preventDefault();
            pendingButton = btn;
            try {
                message.textContent = translate(btn.getAttribute("data-confirm-i18n"));
                if (dialog.open) {
                    dialog.close();
                }
                dialog.showModal();
                yesBtn.focus();
            } catch (error) {
                pendingButton = null;
                submitPending(btn);
            }
        });
    });

    yesBtn.addEventListener("click", function () {
        const btn = pendingButton;
        closeDialog();
        if (!btn) {
            return;
        }
        try {
            submitPending(btn);
        } catch (error) {
            submitPending(btn);
        }
    });

    noBtn.addEventListener("click", closeDialog);
    dialog.addEventListener("cancel", function () {
        pendingButton = null;
    });
});
