const { calculateScore } = require("../js/game_questions");

describe("calculateScore", () => {

    test("returns points for a correct answer", () => {

        const score = calculateScore(true, "easy", 120);

        expect(score).toBeGreaterThan(0);

    });

    test("returns zero base points for an incorrect answer", () => {

        const score = calculateScore(false, "easy", 120);

        expect(score).toBe(0);

    });

});