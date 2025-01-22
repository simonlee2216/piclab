document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded");
  fetchWithAuth("/api/gallery", { method: "GET" })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        showError("Error fetching gallery data.");
      } else {
        renderGallery(data.images);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showError("An unexpected error occurred. Please try again later.");
    });

  async function fetchImagesByUserId(userId) {
    try {
      const response = await fetch(`/api/gallery?user_id=${userId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch images: ${response.statusText}`);
      }
      const data = await response.json();
      return data.images; // Assuming the response contains an `images` array
    } catch (error) {
      showError(error.message);
      return [];
    }
  }

  function renderGallery(images) {
    const galleryContainer = document.getElementById("image-gallery");
    galleryContainer.innerHTML = ""; // Clear previous gallery items

    if (images && images.length > 0) {
      images.forEach((image, index) => {
        const imgElement = document.createElement("img");
        imgElement.src = image.url;
        imgElement.alt = `Gallery image ${index + 1}`; // Add alt text for accessibility
        imgElement.classList.add("gallery-image"); // Add a class for styling
        galleryContainer.appendChild(imgElement);
      });
    } else {
      showError("No images found.");
    }
  }

  function showError(message) {
    const errorContainer = document.getElementById("error-message");
    errorContainer.textContent = message;
    errorContainer.style.display = "block";
  }

  // Main function to handle rendering based on user_id
  async function loadUserGallery(userId) {
    const images = await fetchImagesByUserId(userId);
    renderGallery(images);
  }
});
