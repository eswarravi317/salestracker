// Select modal
var orderpopup = document.getElementById('orderpopupBox');

// Select trigger link
var orderpLink = document.getElementById("orderpopupLink");

// Select close action element
var close_order = document.getElementsByClassName("close_order")[0];

// Open modal once the link is clicked
orderpLink.onclick = function() {
    orderpopup.style.display = "block";
};

// Close modal once close element is clicked
close_order.onclick = function() {
    orderpopup.style.display = "none";
};

// Close modal when user clicks outside of the modal box
window.onclick = function(event) {
    if (event.target == orderpopup) {
        orderpopup.style.display = "none";
    }
};