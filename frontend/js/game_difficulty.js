const easyBtn = document.querySelector('.easyMode');
const mediumBtn = document.querySelector('.mediumMode');
const hardBtn = document.querySelector('.hardMode');
// Skill selected from the word cloud
const theSkill = localStorage.getItem("selected_skill");
const skillDisplay = document.querySelector("#skillDisplay");

const API_BASE_URL = "http://localhost:8000";

// Displays the skill on the dashboard

if (theSkill) {

    skillDisplay.textContent = theSkill;

    // Remove it so it won't be there after a refresh
    localStorage.removeItem("selected_skill");
    
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
        const response = await fetch(SEED_API);

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

/**

 * Requests a new quiz from the backend.

 *

 * @param {"easy" | "medium" | "hard"} difficulty

 */

async function startGame(difficulty) {

    // False result
    if (!theSkill) {

        displayDashboardError(

            "No skill was selected. Please return to the word cloud and select a skill."

        );

        return;

    }

    setButtonsDisabled(true);

    try {

        const skillPath = encodeURIComponent(theSkill);

        const requestURL =

            `${API_BASE_URL}/game/${skillPath}` +

            `?difficulty=${encodeURIComponent(difficulty)}`;

        const response = await fetch(requestURL, {

            method: "GET",

            headers: {

                Accept: "application/json"

            }

        });

        const responseData = await response.json();

        if (!response.ok) {

            throw new Error(

                responseData.detail ||

                `The quiz could not be loaded. Status: ${response.status}`

            );

        }

        /*

         * Expected backend response:

         *

         * {

         *   quiz_id: 25,

         *   skill: "JavaScript",

         *   difficulty: "easy",

         *   questions: [

         *     {

         *       question_id: 1,

         *       question_text: "...",

         *       options: [

         *         {

         *           option_id: 4,

         *           option_text: "..."

         *         }

         *       ]

         *     }

         *   ]

         * }

         */

        sessionStorage.setItem("current_quiz", JSON.stringify(responseData));

        sessionStorage.setItem("selected_difficulty", responseData.difficulty);

        sessionStorage.setItem("selected_skill", responseData.skill);

        window.location.href = "../html/game_question_page.html";

    } catch (error) {

        console.error("Unable to start the game:", error);

        displayDashboardError(

            error.message || "Unable to connect to the game server."

        );

        setButtonsDisabled(false);

    }

}

function setButtonsDisabled(disabled) {

    easyBtn.disabled = disabled;

    mediumBtn.disabled = disabled;

    hardBtn.disabled = disabled;

}

function displayDashboardError(message) {

    // Class game-error does not exist
    let errorElement = document.querySelector(".game-error");
    // since it does not this if statement will relay false
    if (!errorElement) {
        // we create a <p> tag 
        errorElement = document.createElement("p");
        // Class game-error is created
        errorElement.classList.add("game-error");

        errorElement.setAttribute("role", "alert");

        const gameSetup = document.querySelector(".game-set-up");
        // adds the newly created element below the current element on the page
        gameSetup?.insertAdjacentElement("afterend", errorElement);

    }

    errorElement.textContent = message;

}