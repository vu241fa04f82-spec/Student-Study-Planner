
// ==================================
// 1. Automatically hide alert messages
// ==================================

document.addEventListener("DOMContentLoaded", function () {

    const alerts = document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {

        setTimeout(function () {

            alert.style.transition = "opacity 0.5s";
            alert.style.opacity = "0";

            setTimeout(function () {
                alert.remove();
            }, 500);

        }, 4000);

    });


    // ==================================
    // 2. Prevent selecting past dates
    // ==================================

    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");

    const currentDate = `${year}-${month}-${day}`;

    const dateInputs = document.querySelectorAll(
        'input[type="date"]'
    );

    dateInputs.forEach(function (input) {

        input.min = currentDate;

    });


    // ==================================
    // 3. Validate study duration
    // ==================================

    const durationInput = document.querySelector(
        'input[name="duration"]'
    );

    if (durationInput) {

        durationInput.addEventListener("input", function () {

            if (Number(durationInput.value) <= 0) {
                durationInput.setCustomValidity(
                    "Study duration must be greater than zero."
                );
            } else {
                durationInput.setCustomValidity("");
            }

        });

    }

});
