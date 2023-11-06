// Function to verify Apple ID credentials
function verifyCredentials() {
    var appleId = document.getElementById('apple_id').value;
    var password = document.getElementById('password').value;

    // Perform AJAX request to the Flask backend
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/verify", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onreadystatechange = function () {
        if (this.readyState == 4 && this.status == 200) {
            var response = JSON.parse(this.responseText);
            document.getElementById('verification-result').innerText = response.verified ? appleId + ':' + password + '->' + response.verified.status : "Not Verified";
            document.getElementById('verification-result').innerHTML = `
            <div class="max-w-lg mx-auto"> <!-- This should match the width control of your form -->
                <div id="alert-3" class="flex items-center p-4 mb-4 text-sm text-green-800 rounded-lg bg-green-50 dark:bg-gray-800 dark:text-green-400" role="alert">
                    <svg class="flex-shrink-0 w-4 h-4" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5ZM9.5 4a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM12 15H8a1 1 0 0 1 0-2h1v-3H8a1 1 0 0 1 0-2h2a1 1 0 0 1 1 1v4h1a1 1 0 0 1 0 2Z"/>
                    </svg>
                    <span class="sr-only">Info</span>
                    <div class="ml-3 text-sm font-medium">
                        Apple ID: ${appleId} <br>
                        Password: ${password} <br>
                        Result: ${response.verified ? response.verified.status : 'Not Verified'}
                    </div>
                    <button type="button" class="ml-auto -mx-1.5 -my-1.5 bg-green-50 text-green-500 rounded-lg focus:ring-2 focus:ring-green-400 p-1.5 hover:bg-green-200 inline-flex items-center justify-center h-8 w-8 dark:bg-gray-800 dark:text-green-400 dark:hover:bg-gray-700" data-dismiss-target="#alert-3" aria-label="Close">
                        <span class="sr-only">Close</span>
                        <svg class="w-3 h-3" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 14 14">
                            <path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m1 1 6 6m0 0 6 6M7 7l6-6M7 7l-6 6"/>
                        </svg>
                    </button>
                </div>
            </div>`;
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
    xhr.onreadystatechange = function () {
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
    data.forEach(function (row, index) {
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
        xhr.onreadystatechange = function () {
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

