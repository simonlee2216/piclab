function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem("access_token");
  console.log("Fetching with token:", token);

  if (!token) {
    console.warn("No token found. Redirecting to login...");
    window.location.href = "/login";
    return;
  }

  // Initialize headers with defaults and append necessary headers
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  console.log("Headers:", headers);

  // Make the fetch request with added Authorization header
  try {
    return fetch(url, {
      ...options,
      headers: headers,
    });
  } catch (error) {
    console.error("Fetch failed:", error);
    throw error;
  }
}
