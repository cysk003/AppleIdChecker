// Function to verify Apple ID credentials
function verifyCredentials() {
    var appleId = document.getElementById('apple_id').value;
    var password = document.getElementById('password').value;

    // Perform AJAX request to the Flask backend
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/verify", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var response = JSON.parse(this.responseText);
            document.getElementById('verification-result').innerText = response.verified ? appleId+':'+password+'->'+response.verified.status : "Not Verified";
        }
    };
    xhr.send(JSON.stringify({ apple_id: appleId, password: password }));
}

// Function to upload a file
function uploadFile() {
    var fileInput = document.getElementById('file');
    var file = fileInput.files[0];

    // Create FormData object and append the file
    var formData = new FormData();
    formData.append('file', file);

    // Perform AJAX request to the Flask backend
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);
    xhr.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var response = JSON.parse(this.responseText);
            // Handle response for file upload here
            // Assuming response contains an array of verification results
            updateResultsTable(response);
        }
    };
    xhr.send(formData);
}

// Function to update the results table with verification data
function updateResultsTable(data) {
    var tableBody = document.getElementById('results-body');
    tableBody.innerHTML = ''; // Clear existing table data
    data.forEach(function(row, index) {
        var tr = document.createElement('tr');
        tr.classList.add('bg-white', 'border-b', 'dark:bg-gray-800', 'dark:border-gray-700');
        tr.innerHTML = '<td scope="row" class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap dark:text-white">' + (index + 1) + '</td>' +
                       '<td class="px-6 py-4">' + row.apple_id + '</td>' +
                       '<td class="px-6 py-4">' + row.password + '</td>' +
                       '<td class="px-6 py-4">' + (row.verified ? row.verified.status : 'Not Verified') + '</td>';
        tableBody.appendChild(tr);
    });
}



// Function to start batch verification
// function batchVerify() {
//     // Get the data from the table
//     var tableBody = document.getElementById('results-body');
//     var rows = tableBody.getElementsByTagName('tr');
//     var credentialsList = [];

//     for (var i = 0; i < rows.length; i++) {
//         var cells = rows[i].getElementsByTagName('td');
//         credentialsList.push({
//             apple_id: cells[1].textContent, // Assuming second cell contains Apple ID
//             password: cells[2].textContent  // Assuming third cell contains password
//         });
//     }

//     // Perform AJAX request to the Flask backend for batch verification
//     var xhr = new XMLHttpRequest();
//     xhr.open("POST", "/batch-verify", true);
//     xhr.setRequestHeader("Content-Type", "application/json");
//     xhr.onreadystatechange = function() {
//         if (this.readyState == 4 && this.status == 200) {
//             var response = JSON.parse(this.responseText);
//             // Update the table with the verification results
//             updateVerificationResults(response);
//         }
//     };
//     xhr.send(JSON.stringify(credentialsList));
// }



// Function to start batch verification222222
// function batchVerify() {
//     var tableBody = document.getElementById('results-body');
//     var rows = tableBody.getElementsByTagName('tr');

//     // This function processes a single row at a time.
//     function processRow(index) {
//         if (index >= rows.length) return; // Stop when all rows are processed

//         var cells = rows[index].getElementsByTagName('td');
//         var apple_id = cells[1].textContent; // Assuming second cell contains Apple ID
//         var password = cells[2].textContent; // Assuming third cell contains password
//         var verificationCell = cells[3]; // Assuming fourth cell is for verification results

//         // AJAX request to verify single credentials
//         var xhr = new XMLHttpRequest();
//         xhr.open("POST", "/verify", true);
//         xhr.setRequestHeader("Content-Type", "application/json");
//         xhr.onreadystatechange = function() {
//             if (this.readyState == 4 && this.status == 200) {
//                 var response = JSON.parse(this.responseText);
//                 verificationCell.textContent = response.verified ? 'Verified' : 'Not Verified';
//                 processRow(index + 1); // Process the next row
//             }
//         };
//         xhr.send(JSON.stringify({ apple_id: apple_id, password: password }));
//     }

//     processRow(0); // Start processing with the first row
// }

// Function to start batch verification
function batchVerify() {
    var tableBody = document.getElementById('results-body');
    var progressBarContainer = document.getElementById('progress-container');
    var progressBar = document.getElementById('progress-bar');
    var rows = tableBody.getElementsByTagName('tr');

    // Show the progress bar container
    progressBarContainer.style.display = 'block';
    progressBar.style.width = '0%'; // Reset progress bar

    // This function processes a single row at a time.
    function processRow(index) {
        if (index >= rows.length) {
            progressBarContainer.style.display = 'none'; // Hide progress bar when done
            return; // Stop when all rows are processed
        }

        var cells = rows[index].getElementsByTagName('td');
        var apple_id = cells[1].textContent; // Assuming second cell contains Apple ID
        var password = cells[2].textContent; // Assuming third cell contains password
        var verificationCell = cells[3]; // Assuming fourth cell is for verification results

        // AJAX request to verify single credentials
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/verify", true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
                var response = JSON.parse(this.responseText);
                verificationCell.textContent = response.status;

                // Update progress bar
                var progressPercentage = ((index + 1) / rows.length) * 100;
                progressBar.style.width = progressPercentage + '%';

                processRow(index + 1); // Process the next row
            }
        };
        xhr.send(JSON.stringify({ apple_id: apple_id, password: password }));
    }

    processRow(0); // Start processing with the first row
}


// Function to update the verification results in the table
function updateVerificationResults(verificationResults) {
    var tableBody = document.getElementById('results-body');
    for (var i = 0; i < verificationResults.length; i++) {
        var result = verificationResults[i];
        var row = tableBody.rows[i];
        var verificationCell = row.cells[3]; // Assuming fourth cell is for verification results
        verificationCell.textContent = result.verified.status ? result.verified.status : 'Not Verified';
    }
}
