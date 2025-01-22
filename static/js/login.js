document.addEventListener('DOMContentLoaded', () => {
     const loginForm = document.getElementById('login-form');
     const messageDiv = document.getElementById('login-message');
 
     loginForm.addEventListener('submit', async (event) => {
         event.preventDefault();
 
         const username = document.getElementById('username').value;
         const password = document.getElementById('password').value;
 
        try {
         const response = await fetch('/login', {
             method: 'POST',
             headers: {
                 'Content-Type': 'application/json',
             },
             body: JSON.stringify({ username, password }),
         });
 
         const data = await response.json();
 
         if (response.ok) {
             localStorage.setItem('access_token', data.access_token);
             window.location.href = '/gallery';
         } else {
           messageDiv.textContent = data.error || 'Login failed.';
           messageDiv.style.display = 'block';
         }
     } catch (error) {
          messageDiv.textContent = 'An error occurred during login.';
          messageDiv.style.display = 'block';
         console.error('Error during login:', error)
     }
   });
 });