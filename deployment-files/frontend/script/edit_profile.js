localStorage.removeItem("searchQuery");
document
  .querySelector(".edit-profile-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault();


    document.querySelectorAll(".error-message").forEach((msg) => msg.remove());

    const address = document.getElementById("address").value.trim();
    const name = document.getElementById("name").value.trim();
    const phone = document.getElementById("phone").value.trim();
    const photo = document.getElementById("photo").files[0];

    let photoLink = "";
    let isValid = true;


    if (!phone && !photo && !address && !name) {
      createPopupError(
        "Please fill in at least one field to update your profile."
      );
      return;
    }


    const showError = (input, message) => {
      const error = document.createElement("p");
      error.textContent = message;
      error.classList.add("error-message");
      input.parentElement.appendChild(error);
      isValid = false;
    };


    if (name && name.length < 2 && name.length > 50) {
      showError(
        document.getElementById("name"),
        "Name must be between 2 and 50 characters long."
      );
    }


    if (address && address.length < 5 && address.length > 200) {
      showError(
        document.getElementById("address"),
        "Address must be between 5 and 200 characters long."
      );
    }


    const phoneRegex = /^\+[1-9]\d{1,14}$/;
    if (phone && !phoneRegex.test(phone)) {
      showError(
        document.getElementById("phone"),
        "Phone number must follow the format: +<country_code><number>."
      );
    }


    if (!isValid) return;

    const acceptBtn = e.target.querySelector("button[type='submit']");
    addSpinnerToButton(acceptBtn);


    if (photo) {
      const imageSuffix = photo.name.split(".").pop();
      const imageName = `${generateUUID()}.${imageSuffix}`;

      const imageBase64 = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = (error) => reject(error);
        reader.readAsDataURL(photo);
      });

      const bodyPayload = {
        imageName: imageName,
        imageBase64: imageBase64,
        destinationFolder: "images/profile-photos",
      };



      try {
        const response = await fetch(API + `Images`, {
          method: "POST",
          body: JSON.stringify(bodyPayload),
        });

        if (!response.ok) {
          throw new Error("Failed to upload photo.");
          createPopupError("Failed to upload photo. Please try again.");
          restoreButton(acceptBtn);
        }

        const responseData = await response.json();
        photoLink = responseData.imageUrl;
      } catch (error) {
        console.error("Error uploading photo:", error);
        createPopupError("Failed to upload photo. Please try again.");
        restoreButton(acceptBtn);
        return;
      }
    }


    const updates = {};
    if (phone) updates.phone_number = phone;
    if (photoLink) updates.picture = photoLink;
    if (address) updates.address = address;
    if (name) updates.name = name;

    try {



      const body = { attributes: updates };


      const requestJson = {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }

      const response = await fetch(API + `Users/?userID=${currentUserID}`, requestJson);

      const data = await response.json();


      if (!response.ok) {
        throw new Error("Failed to update profile.");
        createPopupError("Failed to update profile. Please try again.");
        restoreButton(acceptBtn);
      }

      createPopupSuccess("Profile updated successfully!");

      setTimeout(() => window.location.href = `profile.html?userID=${currentUserID}`, 1600);
    } catch (error) {
      console.error("Error updating profile:", error);
      createPopupError("Error updating profile: " + error.message);
    }
  });
