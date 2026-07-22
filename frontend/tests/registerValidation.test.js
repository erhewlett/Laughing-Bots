const {
    validateUsername,
    validatePassword,
    validatePasswordMatch,
    validateSalaryRange,
    validateRegistration
} = require("../js/registerValidation");

/**
 * Scenario 1:
 * A user enters valid registration information.
 */
test("Scenario 1: accepts valid registration information", () => {
    const userData = {
        username: "terrell2026",
        password: "SecurePass1!",
        confirmPassword: "SecurePass1!",
        minimumSalary: 50000,
        maximumSalary: 100000
    };

    const result = validateRegistration(userData);

    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
});

/**
 * Scenario 2:
 * A user enters an invalid username.
 */
test("Scenario 2: rejects a username that is too short", () => {
    const result = validateUsername("abc");

    expect(result.valid).toBe(false);
    expect(result.message).toBe(
        "Username must be at least 4 characters."
    );
});

/**
 * Scenario 3:
 * A user enters an invalid or mismatched password.
 */
test("Scenario 3: rejects passwords that do not match", () => {
    const result = validatePasswordMatch(
        "SecurePass1!",
        "DifferentPass2!"
    );

    expect(result.valid).toBe(false);
    expect(result.message).toBe("Passwords do not match.");
});

/**
 * Scenario 4:
 * A user enters an invalid salary range.
 */
test("Scenario 4: rejects a minimum salary greater than maximum salary", () => {
    const result = validateSalaryRange(150000, 80000);

    expect(result.valid).toBe(false);
    expect(result.message).toBe(
        "Minimum salary cannot be greater than maximum salary."
    );
});

// addtional test

describe("Password validation", () => {

    test("rejects a password without a number", () => {

        expect(validatePassword("Password!").valid).toBe(false);

    });

    test("rejects a password without a special character", () => {

        expect(validatePassword("Password123").valid).toBe(false);

    });

    test("accepts a secure password", () => {

        expect(validatePassword("Password1!").valid).toBe(true);

    });

});