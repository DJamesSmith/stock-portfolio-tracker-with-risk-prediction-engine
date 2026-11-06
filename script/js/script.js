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

document.addEventListener("DOMContentLoaded", function () {
    const fileInputs = document.querySelectorAll(".file-count-input")

    fileInputs.forEach(function (input) {
        const countText = document.getElementById(input.dataset.countTarget)

        input.addEventListener("change", function () {
            let usable = 0

            Array.from(input.files).forEach(function (file) {
                const name = file.name.toLowerCase()
                if (!name.startsWith(".") && (name.endsWith(".csv") || name.endsWith(".zip"))) {
                    usable += 1
                }
            })

            countText.textContent = usable + " usable file(s) selected out of " + input.files.length + "."
        })
    })

    const busyForms = document.querySelectorAll(".busy-form")

    busyForms.forEach(function (form) {
        form.addEventListener("submit", function () {
            const button = form.querySelector(".busy-button")
            button.disabled = true
            form.querySelector(".busy-spinner").classList.remove("d-none")

            const text = form.querySelector(".busy-text")
            if (text) {
                text.classList.remove("d-none")
            }
        })
    })
})