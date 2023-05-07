// Select modal
var ppopup = document.getElementById('ppopupBox');
var opopup = document.getElementById('opopupBox');
var ipopup = document.getElementById('ipopupBox');

// Select trigger link
var ppLink = document.getElementById("ppopupLink");
var opLink = document.getElementById("opopupLink");
var ipLink = document.getElementById("ipopupLink");

// Select close action element
var close_personal = document.getElementsByClassName("close_personal")[0];
var close_outlet = document.getElementsByClassName("close_outlet")[0];
var close_item = document.getElementsByClassName("close_item")[0];

// Open modal once the link is clicked
ppLink.onclick = function() {
    ppopup.style.display = "block";
};
opLink.onclick = function() {
    opopup.style.display = "block";
};
ipLink.onclick = function() {
    ipopup.style.display = "block";
};

// Close modal once close element is clicked
close_personal.onclick = function() {
    ppopup.style.display = "none";
};
close_outlet.onclick = function() {
    opopup.style.display = "none";
};
close_item.onclick = function() {
    ipopup.style.display = "none";
};

// Close modal when user clicks outside of the modal box
window.onclick = function(event) {
    if (event.target == ppopup) {
        ppopup.style.display = "none";
    }
    if (event.target == opopup) {
        opopup.style.display = "none";
    }
    if (event.target == ipopup) {
        ipopup.style.display = "none";
    }
};