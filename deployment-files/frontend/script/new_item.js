
const itemNameInput = document.getElementById("item-name");
const descriptionInput = document.getElementById("description");
const priceInput = document.getElementById("price");
const photoInput = document.getElementById("photo");
const newItemForm = document.querySelector(".new-item-form");
localStorage.removeItem("searchQuery");

const escapeQuotes = (text) => {
  return text.replace(/'/g, "\\'").replace(/"/g, '\\"');
};



const validateTextInput = (text) => {

  const noSpecialChars = /^[a-zA-Z0-9\s.,'"\\]+$/;
  const noConsecutiveSpaces = !/\s{2,}/.test(text);
  const containsLetters = /[a-zA-Z]/.test(text);
  const isNotEmpty = text.trim().length > 0;

  return (
    noSpecialChars.test(text) &&
    noConsecutiveSpaces &&
    containsLetters &&
    isNotEmpty
  );
};

const validateImageFile = (file) => {
  const allowedExtensions = ["image/jpeg", "image/png", "image/webp"];
  return file && allowedExtensions.includes(file.type);
};


const showError = (input, message) => {
  const errorSpan = input.parentElement.querySelector(".error-message");
  errorSpan.textContent = message;
  errorSpan.classList.add("active");
};


const clearError = (input) => {
  const errorSpan = input.parentElement.querySelector(".error-message");
  errorSpan.textContent = "";
  errorSpan.classList.remove("active");
};


[itemNameInput, descriptionInput, priceInput, photoInput].forEach((input) => {
  input.addEventListener("input", () => clearError(input));
});


newItemForm.addEventListener("submit", async (event) => {
  event.preventDefault();



  const itemName = itemNameInput.value.trim();
  const description = descriptionInput.value.trim();
  const escapedDescription = escapeQuotes(description);
  const price = parseFloat(priceInput.value.trim());
  const photo = photoInput.files[0];


  if (!validateTextInput(itemName)) {
    showError(itemNameInput, "Invalid item name.");
    return;
  }

  if (!validateTextInput(escapedDescription)) {
    showError(descriptionInput, "Invalid description.");
    return;
  }

  if (isNaN(price) || price <= 0) {
    showError(priceInput, "Invalid price.");
    return;
  }

  if (!validateImageFile(photo)) {
    showError(photoInput, "Invalid photo file type.");
    return;
  }

  const submitBtn = event.target.querySelector("button[type='submit']");
  addSpinnerToButton(submitBtn);


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
    destinationFolder: "images/item-images",
  };


  let photoLink = "";

  try {
    const response = await fetch(API + `Images`, {
      method: "POST",
      body: JSON.stringify(bodyPayload),
    });

    if (!response.ok) {
      console.log(response);
      throw new Error("Network response was not ok");
      createPopupError("Failed to upload image. Please try again.");
      restoreButton(submitBtn);
      return;
    }

    const responseData = await response.json();
    photoLink = responseData.imageUrl;
  } catch (error) {
    console.error("Error uploading image:", error);
    createPopupError("Failed to upload image. Please try again.");
    restoreButton(submitBtn);
    return;
  }

  const newItem = {
    item_name: itemName.toString(),
    item_description: description.toString(),
    price: price.toString(),
    seller: currentUserID.toString(),
    image: photoLink,
    isActive: true,
    isSold: false,
  };



  fetch(API + `Items`, {
    method: "POST",
    body: JSON.stringify(newItem),
  }).then((response) => {
    if (!response.ok) {
      throw new Error("Network response was not ok");
      createPopupError("Failed to add item. Please try again.");
      restoreButton(submitBtn);
      return;
    }
    createPopupSuccess("Item added successfully!");
    setTimeout(() => window.location.href = `profile.html?userID=${currentUserID}`, 1600);
    //return response.json();
  });
});
