html_head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Product Page</title>
<link rel="stylesheet" href="style.css">
<script>
document.addEventListener("DOMContentLoaded", function() {
    var copyButtons = document.querySelectorAll(".copyButton");

    copyButtons.forEach(button => {
        button.addEventListener("click", function() {
            var textToCopy = this.getAttribute("data-text-to-copy");

            navigator.clipboard.writeText(textToCopy).then(function() {
                console.log("Successfully copied to clipboard: " + textToCopy);
                // Provide user feedback here, like changing the icon or displaying a tooltip
            }).catch(function(err) {
                console.error("Error in copying text: ", err);
            });
        });
    });
});
</script>
</head>
"""