document.addEventListener("DOMContentLoaded", function () {
    const forms = document.querySelectorAll(".role-update-form")

    forms.forEach(function (form) {
        const roleSelect = form.querySelector(".role-select")
        const analystSelect = form.querySelector(".analyst-select")
        const updateButton = form.querySelector(".update-button")

        const originalRole = form.dataset.originalRole
        const originalAnalyst = form.dataset.originalAnalyst

        function checkForChanges() {
            const currentRole = roleSelect.value;
            const currentAnalyst = analystSelect.disabled
                ? ""
                : analystSelect.value

            const roleChanged = currentRole !== originalRole;
            const analystChanged = currentAnalyst !== originalAnalyst

            updateButton.disabled = !(roleChanged || analystChanged)
        }

        function updateAnalystState() {
            if (roleSelect.value === "investor") {
                analystSelect.disabled = false
            } else {
                analystSelect.disabled = true
                analystSelect.value = ""
            }

            checkForChanges()
        }

        roleSelect.addEventListener("change", updateAnalystState)
        analystSelect.addEventListener("change", checkForChanges)

        checkForChanges()
    })
})