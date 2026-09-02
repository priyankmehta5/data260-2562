"use strict";

// Closure used to maintain the number of successful form submissions.
// The count variable cannot be accessed directly from outside the closure.
const createSubmissionCounter = () => {
    let count = 0;

    return () => {
        count += 1;
        return count;
    };
};

const trackSuccessfulSubmission = createSubmissionCounter();

// Arrow function used to validate the assignment-specific requirements.
const validateForm = () => {
    const incidentDescription = document
        .getElementById("incidentDescription")
        .value
        .trim();

    const termsAccepted = document
        .getElementById("termsAccepted")
        .checked;

    // "More than 25 characters" means that 25 or fewer is invalid.
    if (incidentDescription.length <= 25) {
        alert(
            "The incident description must contain more than 25 characters."
        );

        document.getElementById("incidentDescription").focus();
        return false;
    }

    if (!termsAccepted) {
        alert(
            "You must agree to the terms and conditions before submitting."
        );

        document.getElementById("termsAccepted").focus();
        return false;
    }

    return true;
};

const incidentForm = document.getElementById("incidentForm");

incidentForm.addEventListener("submit", (event) => {
    // Prevent the browser from reloading the page after submission.
    event.preventDefault();

    // Stop processing if the custom validation fails.
    if (!validateForm()) {
        return;
    }

    // Read the values entered in the form.
    const incidentTitle = document
        .getElementById("incidentTitle")
        .value
        .trim();

    const transitRoute = document
        .getElementById("transitRoute")
        .value
        .trim();

    const submitterEmail = document
        .getElementById("submitterEmail")
        .value
        .trim();

    const incidentDescription = document
        .getElementById("incidentDescription")
        .value
        .trim();

    const incidentCategory = document
        .getElementById("incidentCategory")
        .value;

    const termsAccepted = document
        .getElementById("termsAccepted")
        .checked;

    // Create a JavaScript object from the submitted form data.
    const incidentData = {
        incidentTitle,
        transitRoute,
        submitterEmail,
        incidentDescription,
        incidentCategory,
        termsAccepted
    };

    // Convert the form data object into a JSON string.
    const incidentJsonString = JSON.stringify(incidentData);

    console.log("Form data as a JSON string:");
    console.log(incidentJsonString);

    // Convert the JSON string back into a JavaScript object.
    const parsedIncidentData = JSON.parse(incidentJsonString);

    console.log("Parsed incident object:");
    console.log(parsedIncidentData);

    // Use object destructuring to extract the primary field and email field.
    const {
        incidentTitle: extractedIncidentTitle,
        submitterEmail: extractedSubmitterEmail
    } = parsedIncidentData;

    console.log("Destructured incident title:", extractedIncidentTitle);
    console.log("Destructured submitter email:", extractedSubmitterEmail);

    // Use the spread operator to copy the parsed object and add submissionDate.
    const updatedIncidentData = {
        ...parsedIncidentData,
        submissionDate: new Date().toISOString()
    };

    console.log("Updated incident object with submission date:");
    console.log(updatedIncidentData);

    // Increase the closure counter only after successful validation.
    const submissionCount = trackSuccessfulSubmission();

    console.log("Successful submission count:", submissionCount);

    // Display confirmation on the webpage.
    const successMessage = document.getElementById("successMessage");

    successMessage.textContent =
        `Transit incident submitted successfully. ` +
        `Successful submission count: ${submissionCount}`;

    successMessage.style.display = "block";

    // Clear the form after successful submission.
    incidentForm.reset();

    // Return focus to the primary field.
    document.getElementById("incidentTitle").focus();
});