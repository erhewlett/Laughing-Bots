// the Form
const registrationForm = document.querySelector('#registrationForm');

// Input fields cherry picked from the registration page

const firstNameField = document.querySelector('#firstNameInput');
const lastNameField = document.querySelector('#lastNameInput');
const userNameField = document.querySelector('#usernameInput');
const confirmUserField = document.querySelector('#confirmUsernameInput');
const passwordField = document.querySelector('#passwordInput');
const confirmPasswordField = document.querySelector('#confirmPasswordInput');
const jobTitleField = document.querySelector('#jobTitleInput');
const locationField = document.querySelector('#locationInput');
const minSalaryField = document.querySelector('#minimumSalaryInput');
const theWordCount = document.querySelector('#wordCountSelect');
const cloudShape = document.querySelector('#wordCloudShapeSelect');

// Error Messages for select input fields
const usernameError = document.querySelector('#usernameError');
const confirmUsernameError = document.querySelector('#confirmUsernameError');
const passwordError = document.querySelector('#passwordError');
const confirmPasswordError = document.querySelector('#confirmPasswordError');
const jobTitleError = document.querySelector("#jobTitleError");
const jobIndustryError = document.querySelector("#jobIndustryError");
const salaryError = document.querySelector("#salaryError");
const countError = document.querySelector('#countError');
const shapeError = document.querySelector('#shapeError');


// location
const locationSuggestions = document.querySelector("#locationSuggestions");

// States for the location
const usaLocations = [
    "Birmingham, AL",
    "Anchorage, AK",
    "Phoenix, AZ",
    "Little Rock, AR",
    "Los Angeles, CA",
    "Denver, CO",
    "Bridgeport, CT",
    "Wilmington, DE",
    "Jacksonville, FL",
    "Atlanta, GA",
    "Honolulu, HI",
    "Boise, ID",
    "Chicago, IL",
    "Indianapolis, IN",
    "Des Moines, IA",
    "Wichita, KS",
    "Louisville, KY",
    "New Orleans, LA",
    "Portland, ME",
    "Baltimore, MD",
    "Boston, MA",
    "Detroit, MI",
    "Minneapolis, MN",
    "Jackson, MS",
    "Kansas City, MO",
    "Billings, MT",
    "Omaha, NE",
    "Las Vegas, NV",
    "Manchester, NH",
    "Newark, NJ",
    "Albuquerque, NM",
    "New York City, NY",
    "Charlotte, NC",
    "Fargo, ND",
    "Columbus, OH",
    "Oklahoma City, OK",
    "Portland, OR",
    "Philadelphia, PA",
    "Providence, RI",
    "Charleston, SC",
    "Sioux Falls, SD",
    "Nashville, TN",
    "Houston, TX",
    "Salt Lake City, UT",
    "Burlington, VT",
    "Virginia Beach, VA",
    "Seattle, WA",
    "Charleston, WV",
    "Milwaukee, WI",
    "Cheyenne, WY"
];

// Cycles through the locations within usaLocations Array
usaLocations.forEach((location) => {
    const option = document.createElement("option");

    option.value = location;

    locationSuggestions.appendChild(option);
});

// The form runs an async await function upon submission
// Async await works like so: It tells the browser while a function is awaiting the
// results of another funciton promise to run  all other commands
// simultaneously 
registrationForm.addEventListener("submit", async (e)=> {
    // Prevent the browser from submitting the form and refreshing the page
    e.preventDefault();

    const submitButton = registrationForm.querySelector('#sign-up-btn');


    const job_title = jobTitleField.value.trim();
    const the_location = locationField.value.trim();
    const min_salary = minSalaryField.value.trim();
    const word_count = theWordCount.value.trim();
    const shape = cloudShape.value.trim();

    const wordCloudGeneration = {
        job_title: job_title,
        industry: '',
        location: the_location,
        min_salary: min_salary,
        word_count: word_count,
        shape: shape
    };

    // localStroage set up
    localStorage.setItem("word_cloud_parameters", JSON.stringify(wordCloudGeneration));

    // combine first and last name to store name variable if not empty
    if (!firstNameField.value === "" && !lastNameField.value === "") {
        const nameInput = `${firstNameField.value.trim()} ${lastNameField.value.trim()}`.trim();
    } else if (firstNameField.value === "" && !lastNameField.value === "") {
        nameInput = `${lastNameField.value.trim()}`.trim();
    } else if (!firstNameField.value === "" && lastNameField.value === "") {
        nameInput = `${firstNameField.value.trim()}`.trim();
    } else {
        nameInput = "";
    }

    const isValid = verifying_registration(firstNameField,
        lastNameField,
        userNameField, 
        confirmUserField, 
        passwordField, 
        confirmPasswordField, 
        jobTitleField, 
        locationField,
        minSalaryField,
        theWordCount,
        cloudShape
    );



    if (!isValid) {
        console.log('Form validation did not pass');
        return;
    }

    // Is the minium salary input not blank?
    const minSalary = minSalaryField.value !== ""
            // if minimum salary is an actual number print it otherwise leave it null because it is NaN
                ? Number(minSalaryField.value)
                : null;

    // Check to ensure a user is not entering anything but a valid number
    if (
        minSalary !== null &&
        !Number.isFinite(minSalary)
    ) {
        alert("Minimum salary must be a valid number.");
        return;
    }

    // setting up data to go into the backend database
    const userData = {
        username: userNameField.value.trim(),
        password: passwordField.value,
        email: emailInput.value.trim() || null, // not in use
        name: nameInput || null

    };

    // Try running this to ensure there are no errors when the button is pressed
    try {

        // Prevent the user from submitting the form repeatedly.
        if (submitButton) {
            submitButton.disabled = true;
        }

        const response = await fetch("http://localhost:8000/auth/register", {

            method: "POST",

            headers: { "Content-Type": "application/json" },

            body: JSON.stringify(userData)

        });

        // gets the header "content-type" which is an allowed 
        // header within the main.py file
        const contentType = response.headers.get("content-type");

        let result;

        if (contentType?.includes("application/json")) {

            result = await response.json();

        } else {

            result = {

                detail: await response.text()

            };

        }

        if (!response.ok) {

            console.error("Registration failed:", result);

            let errorMessage =

                "Registration failed. Please check your information.";

            if (typeof result.detail === "string") {

                errorMessage = result.detail;

            } else if (Array.isArray(result.detail)) {

                errorMessage = result.detail

                    .map((error) => error.msg)

                    .join("\n");
            }

            alert(errorMessage);
            return;

        }

        // valid
        console.log("User registered:", result);

        alert("Account created successfully.");

        // Form destination after a successful validation
        window.location.href = 'word_cloud_creation_page.html';
        console.log('Form validated');

    } catch (error) {

        console.error("Could not reach the backend:", error);

        alert("Unable to connect to the server.");

        return;

    } finally {

        // This will not matter after a successful redirect,
        // but it restores the button when registration fails.

        if (submitButton) {
            submitButton.disabled = false;
        }
    }

});

//the funciton for verifiying all inputs within the registration form are valid inputs
function verifying_registration(firstName, lastName, userName, confirmUserName, passWord, confirmPassword, jobTitle, location, minSalary, wordCount, shape) {
    // assigning variables to the arguments and clearing empty space
    const firstNameVal = firstName.value.trim();
    const lastNameVal = lastName.value.trim();
    const userNameVal = userName.value.trim();
    const confirmUsernameVal = confirmUserName.value.trim();
    const passwordVal = passWord.value;
    const confirmPasswordVal = confirmPassword.value;
    const jobTitleVal = jobTitle.value.trim();
    const theCount = wordCount.value.trim();
    const theShape = shape.value.trim();
    // Regex to detect email
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    // logic for checking whether the username is valid by standards set
    function firstNameFeedback(reason, input, feedback) {

        if (reason) {
            // invalid
            input.classList.add("is-invalid");
            input.classList.remove("is-valid");
            feedback.classList.add("invalid-feedback");
            feedback.classList.remove("valid-feedback");
        } else {
            // valid
            input.classList.add("is-valid");
            input.classList.remove("is-invalid");
            feedback.classList.add("valid-feedback");
            feedback.classList.remove("invalid-feedback");
        }
        // Each case is a reason in string form with an appropriate feedback comment
        switch (reason) {
            case "tooShort":
                feedback.textContent = "First name is too short";
                break;
            case "tooLong":
                feedback.textContent = "First name is too long";
                break;
            case "isEmail":
                feedback.textContent = "First name cannot be an email address";
                break;
            case "empty":
                feedback.textContent = "First name cannot be empty";
                break;
            default:
                feedback.textContent = "Looks good";
        }
    }

    function lastNameFeedback(reason, input, feedback) {

        if (reason) {
            // invalid
            input.classList.add("is-invalid");
            input.classList.remove("is-valid");
            feedback.classList.add("invalid-feedback");
            feedback.classList.remove("valid-feedback");
        } else {
            // valid
            input.classList.add("is-valid");
            input.classList.remove("is-invalid");
            feedback.classList.add("valid-feedback");
            feedback.classList.remove("invalid-feedback");
        }
        // Each case is a reason in string form with an appropriate feedback comment
        switch (reason) {
            case "tooShort":
                feedback.textContent = "Last name is too short";
                break;
            case "tooLong":
                feedback.textContent = "Last name is too long";
                break;
            case "isEmail":
                feedback.textContent = "Last name cannot be an email address";
                break;
            case "empty":
                feedback.textContent = "Last name cannot be empty";
                break;
            default:
                feedback.textContent = "Looks good";
        }
    }

    function usernameFeedback(reason, input, feedback) {

        if (reason) {
            // invalid
            input.classList.add("is-invalid");
            input.classList.remove("is-valid");
            feedback.classList.add("invalid-feedback");
            feedback.classList.remove("valid-feedback");
        } else {
            // valid
            input.classList.add("is-valid");
            input.classList.remove("is-invalid");
            feedback.classList.add("valid-feedback");
            feedback.classList.remove("invalid-feedback");
        }
        // Each case is a reason in string form with an appropriate feedback comment
        switch (reason) {
            case "tooShort":
                feedback.textContent = "Username is too short";
                break;
            case "tooLong":
                feedback.textContent = "Username is too long";
                break;
            case "isEmail":
                feedback.textContent = "Username cannot be an email address";
                break;
            case "empty":
                feedback.textContent = "Username cannot be empty";
                break;
            default:
                feedback.textContent = "Looks good";
        }
    }

    function confirmedUsernameFeedback(reason, input, feedback) {
        if (reason) {
            input.classList.add("is-invalid");
            input.classList.remove("is-valid");
            feedback.classList.add("invalid-feedback");
            feedback.classList.remove("valid-feedback");
        } else {
            input.classList.add("is-valid");
            input.classList.remove("is-invalid");
            feedback.classList.add("valid-feedback");
            feedback.classList.remove("invalid-feedback");
        }
        switch (reason) {
            case "tooShort":
                feedback.textContent = "Username is too short";
                break;
            case "tooLong":
                feedback.textContent = "Username is too long";
                break;
            case "noMatch":
                feedback.textContent = "Username entered does not match";
                break;
            case "isEmail":
                feedback.textContent = "Username cannot be an email address";
                break;
            case "empty":
                feedback.textContent = "Username cannot be empty";
                break;
            default:
                feedback.textContent = "Looks good";
        }
    }

    function passwordFeedback(reason, input, feedback) {
        if (reason) {
            input.classList.add("is-invalid");
            input.classList.remove("is-valid");
            feedback.classList.add("invalid-feedback");
            feedback.classList.remove("valid-feedback");
        }
        else {
            input.classList.add("is-valid");
            input.classList.remove("is-invalid");
            feedback.classList.add("valid-feedback");
            feedback.classList.remove("invalid-feedback");
        }
        switch (reason) {
            case "tooShort":
                feedback.textContent = "Password is too short";
                break;
            case "tooLong":
                feedback.textContent = "Password is too long";
                break;
            case "isEmail":
                feedback.textContent = "Password cannot be an email address";
                break;
            case "weak":
                feedback.textContent = "Password must contain an uppercase letter, lowercase letter, and number";
                break;
            case "noSpace":
                feedback.textContent = "Password cannot contain spaces.";
                break;
            case "empty":
                feedback.textContent = "Password cannot be empty";
                break;
            default:
                feedback.textContent = "Looks good";
        }
    }

    function confirmedPasswordFeedback(reason, input, feedback) {
        if (reason) {
            input.classList.add("is-invalid");
            input.classList.remove("is-valid");
            feedback.classList.add("invalid-feedback");
            feedback.classList.remove("valid-feedback");
        } else {
            input.classList.add("is-valid");
            input.classList.remove("is-invalid");
            feedback.classList.add("valid-feedback");
            feedback.classList.remove("invalid-feedback");
        }
        switch (reason) {
            case "tooShort":
                feedback.textContent = "Password is too short";
                break;
            case "tooLong":
                feedback.textContent = "Password is too long";
                break;
            case "isEmail":
                feedback.textContent = "Password cannot be an email address";
                break;
            case "noMatch":
                feedback.textContent = "Password entered does not match";
                break;
            case "empty":
                feedback.textContent = "Password cannot be empty";
                break;
            default:
                feedback.textContent = "Looks good";
        }
    }

    function jobFeedback(reason) {

        if (reason) {

            jobTitle.classList.add("is-invalid");

            jobTitle.classList.remove("is-valid");

            jobTitleError.classList.add("invalid-feedback");

            jobTitleError.textContent =

                "Please enter a job title.";

        } else {

            jobTitle.classList.remove("is-invalid");

            // Optional

            if (jobTitle.value.trim() !== "") {

                jobTitle.classList.add("is-valid");

            }

            jobTitleError.textContent = "";

        }

    }

    function locationFeedback(reason) {
        const locationError = document.querySelector("#locationError");

        if (reason) {
            location.classList.add("is-invalid");
            location.classList.remove("is-valid");

            locationError.classList.add("invalid-feedback");
            locationError.classList.remove("valid-feedback");

            locationError.textContent =
                "Please select a city and state from the suggestions.";
        } else {
            location.classList.remove("is-invalid");

            locationError.classList.remove("invalid-feedback");
            locationError.textContent = "";

            if (location.value.trim() !== "") {
                location.classList.add("is-valid");
            } else {
                location.classList.remove("is-valid");
            }
        }
    }

    function salaryFeedback(reason) {
        if (reason) {
            minSalary.classList.add("is-invalid");

            minSalary.classList.remove("is-valid");

            salaryError.classList.add("invalid-feedback");
            salaryError.classList.remove("valid-feedback");

            switch (reason) {
                case "incomplete":
                    salaryError.textContent =
                        "Please enter both a minimum and maximum salary.";
                    break;

                case "belowMinimum":
                    salaryError.textContent =
                        "Salary cannot be lower than $30,000.";
                    break;

                case "aboveMaximum":
                    salaryError.textContent =
                        "Salary cannot be higher than $500,000.";
                    break;

                case "wrongIncrement":
                    salaryError.textContent =
                        "Salary must increase in increments of $10,000.";
                    break;
            }

            return;
        }

        minSalary.classList.remove("is-invalid");

        salaryError.classList.remove("invalid-feedback");
        salaryError.textContent = "";

    }

    function validateCount() {
        if (theCount === "") {
            wordCount.classList.add("is-invalid");
            wordCount.classList.remove("is-valid");

            countError.classList.add("invalid-feedback");
            countError.classList.remove("valid-feedback");

            countError.textContent = "Please select a given number.";

            return false;

        } 

        wordCount.classList.remove("is-invalid");
        wordCount.classList.add("is-valid");

        countError.classList.remove("invalid-feedback");
        countError.textContent = "";

        return true;
    }

    function validateShape() {
        if (theShape === "") {
            shape.classList.add("is-invalid");
            shape.classList.remove("is-valid");

            shapeError.classList.add("invalid-feedback");
            shapeError.classList.remove("valid-feedback");

            shapeError.textContent = "Please select a given shape.";

            return false;

        } 

        shape.classList.remove("is-invalid");
        shape.classList.add("is-valid");

        shapeError.classList.remove("invalid-feedback");
        shapeError.textContent = "";

        return true;
    }

    function validateSalaryRange() {

        const minSalaryValue = minSalary.value;

        // Salary is optional, so being empty is allowed

        if (minSalaryValue === "") {

            return "";

        }

        const minimumSalary = Number(minSalaryValue);


        if (minimumSalary < 30000) {

            return "belowMinimum";

        }

        if (minimumSalary > 500000) {

            return "aboveMaximum";

        }

        if (

            minimumSalary % 10000 !== 0

        ) {

            return "wrongIncrement";

        }

        return "";

    }

    // Rules to check in order for the form to validate properly
    function notValidFirstName() {
        if (firstNameVal.length === 0)
            return "empty";
        if (firstNameVal.length < 4)
            return "tooShort";
        if (firstNameVal.length > 16)
            return "tooLong";
        if (emailPattern.test(firstNameVal))
            return "isEmail";
        return "";
    }

    function notValidLastName() {
        if (lastNameVal.length === 0)
            return "empty";
        if (lastNameVal.length < 4)
            return "tooShort";
        if (lastNameVal.length > 16)
            return "tooLong";
        if (emailPattern.test(lastNameVal))
            return "isEmail";
        return "";
    }

    function notValidUsername() {
        if (userNameVal.length === 0)
            return "empty";
        if (userNameVal.length < 4)
            return "tooShort";
        if (userNameVal.length > 16)
            return "tooLong";
        if (emailPattern.test(userNameVal))
            return "isEmail";
        return "";
    }

    function noConfirmedUsername() {
        if (confirmUsernameVal.length === 0)
            return "empty";
        if (confirmUsernameVal.length < 4)
            return "tooShort";
        if (confirmUsernameVal.length > 16)
            return "tooLong";
        if (emailPattern.test(confirmUsernameVal))
            return "isEmail";
        if (confirmUsernameVal !== userNameVal)
            return "noMatch";
        return "";
    }

    function notValidPassword() {

        //Password must have uppercase, lowercase, and at least one number
        const securePass = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])[A-Za-z0-9]{8,20}$/;

        if (passwordVal.length === 0)
            return "empty";
        if (passwordVal.length < 8)
            return "tooShort";
        if (passwordVal.length > 20)
            return "tooLong";
        if (emailPattern.test(passwordVal))
            return "isEmail";
        if (!securePass.test(passwordVal))
            return "weak";
        // Ensure there are no spaces within the password
        if (/\s/.test(passwordVal)) {
            return "noSpace";
        }
        return "";
    }

    function noConfirmedPassword() {
        if (confirmPasswordVal.length === 0)
            return "empty";

        if (confirmPasswordVal !== passwordVal)
            return "noMatch";

        return "";
    }

    function noValidJobSelection() {

        if (jobTitle.value.trim() === "") {

            return "missing";

        }

        return "";

    }

    function noValidLocation() {
        const locationValue = location.value.trim().toLowerCase();

        if (locationValue === "") {
            return "";
        }

        const locationExists = usaLocations.some((location) => {
            const storedLocation = location.toLowerCase();

            return storedLocation === locationValue;
        });

        if (!locationExists) {
            return "notFound";
        }

        return "";
    }

    // Assigning variabes to the error checking functions
    const anyFirstNameError = notValidFirstName();
    const anyLastNameError = notValidLastName();
    const anyUsernameError = notValidUsername();
    const anyConfirmedUsernameError = noConfirmedUsername();
    const anyPasswordError = notValidPassword();
    const anyConfirmedPasswordError = noConfirmedPassword();
    const anyJobError = noValidJobSelection();
    const anyLocationError = noValidLocation();
    const anySalaryError = validateSalaryRange();
    

    // Funcitons that check each input for errors
    firstNameFeedback(anyFirstNameError, firstName, firstNameError);
    lastNameFeedback(anyLastNameError, lastName, lastNameError);
    usernameFeedback(anyUsernameError, userName, usernameError);
    confirmedUsernameFeedback(anyConfirmedUsernameError, confirmUserName, confirmUsernameError);
    passwordFeedback(anyPasswordError, passWord, passwordError);
    confirmedPasswordFeedback(anyConfirmedPasswordError, confirmPassword, confirmPasswordError);
    jobFeedback(anyJobError);
    locationFeedback(anyLocationError);
    salaryFeedback(anySalaryError);
    validateCount();
    validateShape();


    return (
        // No errors found
        !anyFirstNameError &&

        !anyLastNameError &&

        !anyUsernameError &&

        !anyConfirmedUsernameError &&

        !anyPasswordError &&

        !anyConfirmedPasswordError &&

        !anyJobError &&

        !anyLocationError &&

        !anySalaryError

    );
}

// will clear the form upon page reload
registrationForm.reset();

registrationForm.querySelectorAll(".form-control").forEach(input => {

    input.classList.remove("is-valid", "is-invalid");

});

registrationForm.querySelectorAll(".valid-feedback, .invalid-feedback").forEach(feedback => {

    feedback.classList.remove("valid-feedback", "invalid-feedback");

    feedback.textContent = "";

});