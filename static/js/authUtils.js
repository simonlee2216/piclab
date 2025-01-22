async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem("access_token");
  console.log("Fetching with token:", token);

  if (!token) {
    console.warn("No token found. Redirecting to login...");
    window.location.href = "/login";
    throw new Error("No token found. Redirecting to login.");
  }
  try {
    const decodedToken = JSON.parse(atob(token.split('.')[1]));
    const currentTime = Math.floor(Date.now() / 1000);
    if (decodedToken && decodedToken.exp && decodedToken.exp < currentTime) {
      console.warn("Token expired. Redirecting to login...");
      localStorage.removeItem("access_token"); // Clear expired token
      window.location.href = "/login";
      throw new Error("Token expired. Redirecting to login.");
    }
  } catch (e) {
    console.error("Error decoding or validating token:", e);
    localStorage.removeItem("access_token"); // Clear potentially invalid token
    window.location.href = "/login";
    throw new Error("Invalid token. Redirecting to login.");
  }


  const headers = new Headers(); // create new headers, instead of re-using old
  headers.set("Authorization", `Bearer ${token}`);
  // only set content type header if we don't already have one
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  console.log("Headers:", headers);



  try {
    const response = await fetch(url, {
      ...options,
      headers: headers,
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        console.warn(`Authentication error (status ${response.status}). Redirecting to login...`);
        localStorage.removeItem("access_token");
        window.location.href = "/login";
        throw new Error(`Authentication error. Redirecting to login.`);
      } else {
        const errorMessage = await response.text();
        console.error(`Fetch failed with status ${response.status}:`, errorMessage);
        throw new Error(`Fetch failed with status ${response.status}: ${errorMessage}`);
      }
    }

    return response;
  } catch (error) {
    console.error("Fetch failed:", error);
    throw error;
  }
}