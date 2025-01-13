// A function to retrieve the token from localStorage and add it to the request headers
function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('access_token');
    console.log('Fetching with token:', token); // Log token to verify

    if (!token) {
        window.location.href = '/login';
        return;
    }

    // Clone the options object to avoid mutating the original request
    const headers = new Headers(options.headers || {});
    headers.append('Authorization', `Bearer ${token}`);
    headers.append('Content-Type', 'application/json');
  
    console.log(headers);

    // Make the fetch request with the added Authorization header
    return fetch(url, {
        ...options,
        headers: headers,
    });
}