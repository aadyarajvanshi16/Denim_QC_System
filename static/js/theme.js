// =====================================
// LOAD SAVED THEME
// =====================================

window.addEventListener("load", function () {

    const savedTheme =
        localStorage.getItem("theme");

    if (savedTheme === "light") {

        document.body.classList.add(
            "light-mode"
        );

    }

});

// =====================================
// TOGGLE THEME
// =====================================

function toggleTheme() {

    document.body.classList.toggle(
        "light-mode"
    );

    // SAVE THEME

    if (
        document.body.classList.contains(
            "light-mode"
        )
    ) {

        localStorage.setItem(
            "theme",
            "light"
        );

    } else {

        localStorage.setItem(
            "theme",
            "dark"
        );

    }

}