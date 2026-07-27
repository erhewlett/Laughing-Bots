//login button and signup button getting connected by their id name
const loginBTN = document.querySelector('#userLoginBtn');
const signUpBTN = document.querySelector('#registerBtn');

//event listener so that the buttons direct users to the right pages

loginBTN.addEventListener('click', () => {
    window.location.href = 'sign_in_page.html';
});

signUpBTN.addEventListener('click', () => {
    window.location.href = 'registration_page.html';
});
