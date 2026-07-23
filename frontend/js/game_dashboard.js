const easyBtn = document.querySelector('.easyMode');
const mediumBtn = document.querySelector('.mediumMode');
const hardBtn = document.querySelector('.hardMode');
// Skill selected from the word cloud
const theSkill = sessionStorage.getItem("selectedSkill");
const skillDisplay = document.querySelector("#skillDisplay");


// Displays the skill on the dashboard

if (theSkill) {

    skillDisplay.textContent = theSkill;

    // Remove it so it won't be there after a refresh
    localStorage.removeItem("selectedSkill");
} else {

    skillDisplay.textContent = "No skill selected";

}

/* Loads the question file and filters questions

 * by the selected skill and difficulty.

*/

async function selectDifficulty(difficulty) {

    try {

        if (!theSkill) {

            throw new Error("No skill was selected.");

        }

        // Path to questions data
        const response = await fetch("../../backend/app/seed_data/questions_seed.json");

        // if the response is NOT okay
        if (!response.ok) {
            // then give an error stating:
            throw new Error(

                `Could not load questions. Status: ${response.status}`

            );

        }
        // represents the entire JSON object
        const questionData = await response.json();
        
        // we only want questions that match up with the skills in the database
        const matchingQuestions = questionData.questions.filter((question) => {

            const skillMatches = question.skill.toLowerCase() === theSkill.toLowerCase();

            const difficultyMatches = question.difficulty.toLowerCase() === difficulty.toLowerCase();

            return skillMatches && difficultyMatches;

        });

        if (matchingQuestions.length === 0) {

            throw new Error(

                `No ${difficulty} questions were found for ${theSkill}.`

            );

        }

        // Store the difficulty for the quiz page

        localStorage.setItem("selectedDifficulty", difficulty);

        // Store the matching questions temporarily

        localStorage.setItem("quizQuestions", JSON.stringify(matchingQuestions));

        // Send the user to the questions
        window.location.href = "../html/game_question_page.html";

    } catch (error) {

        console.error("Question loading error:", error);

        alert(error.message);

    }

}

easyBtn.addEventListener("click", () => {

    selectDifficulty("easy");
    console.log("easy difficulty selected");

});

mediumBtn.addEventListener("click", () => {

    selectDifficulty("medium");
    console.log("medium difficulty selected");

});

hardBtn.addEventListener("click", () => {

    selectDifficulty("hard");
    console.log("hard difficulty selected");

});