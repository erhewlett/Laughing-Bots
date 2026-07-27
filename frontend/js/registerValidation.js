/**
 * Checks whether a username follows the registration requirements.
 *
 * Requirements:
 * - Must not be empty.
 * - Must be between 4 and 16 characters.
 * - Must contain only letters and numbers.
 * - Must not be an email address.
 */

function validateUsername(username) {
    const theUsername = username.trim();

    if (theUsername === "") {
        return {
            valid: false,
            message: "Username cannot be empty."
        };
    }

    if (theUsername.length < 4) {
        return {
            valid: false,
            message: "Username must be at least 4 characters."
        };
    }

    if (theUsername.length > 16) {
        return {
            valid: false,
            message: "Username cannot be longer than 16 characters."
        };
    }

    if (theUsername.includes("@")) {
        return {
            valid: false,
            message: "Username cannot be an email address."
        };
    }

    if (!/^[A-Za-z0-9]+$/.test(theUsername)) {
        return {
            valid: false,
            message: "Username can only contain letters and numbers."
        };
    }

    return {
        valid: true,
        message: ""
    };
}

/**
 * Checks whether a password follows the registration requirements.
 *
 * Requirements:
 * - Must be between 8 and 20 characters.
 * - Must contain at least one number.
 * - Must contain at least one supported special character.
 * - Must not contain spaces.
 */
function validatePassword(password) {
    const securePassword =
        /^(?=.*[0-9])(?=.*[!@#$%^&*])[A-Za-z0-9!@#$%^&*]{8,20}$/;

    if (!securePassword.test(password)) {
        return {
            valid: false,
            message:
                "Password must be 8 to 20 characters and contain a number and special character."
        };
    }

    return {
        valid: true,
        message: ""
    };
}

/**
 * Checks whether the password and confirmation password match.
 */
function validatePasswordMatch(password, confirmPassword) {
    if (password !== confirmPassword) {
        return {
            valid: false,
            message: "Passwords do not match."
        };
    }

    return {
        valid: true,
        message: ""
    };
}

/**
 * Checks the user's desired salary range.
 *
 * Requirements:
 * - Minimum value is $30,000.
 * - Maximum value is $500,000.
 * - Values must increase in increments of $10,000.
 * - Minimum salary cannot be greater than maximum salary.
 */
function validateSalaryRange(minimumSalary, maximumSalary) {
    const minimum = Number(minimumSalary);
    const maximum = Number(maximumSalary);

    if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) {
        return {
            valid: false,
            message: "Both salary values must be numbers."
        };
    }

    if (minimum < 30000 || maximum < 30000) {
        return {
            valid: false,
            message: "Salary cannot be less than $30,000."
        };
    }

    if (minimum > 500000 || maximum > 500000) {
        return {
            valid: false,
            message: "Salary cannot be greater than $500,000."
        };
    }

    if (minimum % 10000 !== 0 || maximum % 10000 !== 0) {
        return {
            valid: false,
            message: "Salary must use increments of $10,000."
        };
    }

    if (minimum > maximum) {
        return {
            valid: false,
            message: "Minimum salary cannot be greater than maximum salary."
        };
    }

    return {
        valid: true,
        message: ""
    };
}

/**
 * Validates the major registration fields together.
 */
function validateRegistration(userData) {
    const usernameResult = validateUsername(userData.username);
    const passwordResult = validatePassword(userData.password);
    const passwordMatchResult = validatePasswordMatch(
        userData.password,
        userData.confirmPassword
    );
    const salaryResult = validateSalaryRange(
        userData.minimumSalary,
        userData.maximumSalary
    );

    const errors = [];

    if (!usernameResult.valid) {
        errors.push(usernameResult.message);
    }

    if (!passwordResult.valid) {
        errors.push(passwordResult.message);
    }

    if (!passwordMatchResult.valid) {
        errors.push(passwordMatchResult.message);
    }

    if (!salaryResult.valid) {
        errors.push(salaryResult.message);
    }

    return {
        valid: errors.length === 0,
        errors
    };
}

module.exports = {
    validateUsername,
    validatePassword,
    validatePasswordMatch,
    validateSalaryRange,
    validateRegistration
};