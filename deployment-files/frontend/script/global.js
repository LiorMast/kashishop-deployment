const API = "https://qulm22toj6.execute-api.us-east-1.amazonaws.com/kashlior24/";
const currentUserID = localStorage.getItem("userID");
let isAdmin = localStorage.getItem("isAdmin");


if (
  !currentUserID &&
  !window.location.pathname.includes("index.html") &&
  !(
    window.location.pathname.includes("profile.html") &&
    window.location.search.includes("userID=")
  )
) {
  window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", () => {
  generateNavBar(isAdmin === "true");

  fetch(API + `Users/byid?userID=${currentUserID}`)
    .then((response) => response.json())
    .then((data) => {
      console.log(data.body, "this is data.body");


      const userData =
        typeof data.body === "string" ? JSON.parse(data.body) : data.body;

      console.log(userData.isActive, "is this isActive?");
      if (userData.isActive.toString().toLowerCase() === "false") {
        Swal.fire({
          title: "User Deactivated",
          text: "Please contact administrator.",
          imageUrl:
            "https://kashishop2.s3.us-east-1.amazonaws.com/media/site+images/lock.png",
          imageWidth: 80,
          imageHeight: 80,
          showConfirmButton: false,
          allowOutsideClick: false,
          allowEscapeKey: false,
          allowEnterKey: false,
          backdrop: "rgba(0, 0, 0, 0.9)",
          customClass: {
            popup: "animate__animated animate__bounceInDown",
          },
        });
      }
    })
    .catch((error) => { });
});

function generateNavBar(isAdmin) {
  const navbar = document.querySelector(".navbar");


  navbar.innerHTML = `<input type="text" class="search-input" placeholder="Search">`;

  if (!currentUserID) {

    navbar.insertAdjacentHTML(
      "afterbegin",
      `
              <button class="nav-btn" onclick="window.location.href='index.html';">Home</button>
          `
    );
    navbar.insertAdjacentHTML(
      "beforeend",
      `
              <button class="nav-btn" onclick="window.location.href='https://us-east-1l8fw4esc3.auth.us-east-1.amazoncognito.com/login?client_id=2k3i5ubbp0ed3omjjhef3u5jkj&response_type=code&scope=email+openid+phone&redirect_uri=https%3A%2F%2Fkashishop2.s3.us-east-1.amazonaws.com%2Fmain%2Fcallback.html';">Login</button>
          `
    );
  } else if (isAdmin) {

    navbar.insertAdjacentHTML(
      "afterbegin",
      `
              <button class="nav-btn" onclick="window.location.href='index.html';">Home</button>
          `
    );
    navbar.insertAdjacentHTML(
      "beforeend",
      `
              <button class="nav-btn" onclick="window.location.href='admin.html';">Admin</button>
              <button class="nav-btn" onclick="signOff();">Sign Off</button>
          `
    );
  } else {

    navbar.insertAdjacentHTML(
      "afterbegin",
      `
              <button class="nav-btn" onclick="window.location.href='index.html';">Home</button>
              <button class="nav-btn" onclick="window.location.href='new_item.html';">New Item</button>
          `
    );
    navbar.insertAdjacentHTML(
      "beforeend",
      `
              <button class="nav-btn nav-btn-profile" onclick="window.location.href='https://kashishop2.s3.us-east-1.amazonaws.com/main/profile.html';">Profile</button>
              <button class="nav-btn" onclick="signOff();">Sign Off</button>
          `
    );


    document.querySelector(".nav-btn-profile").addEventListener("click", () => {
      if (currentUserID) {
        window.location.href = `https://kashishop2.s3.us-east-1.amazonaws.com/main/profile.html?userID=${currentUserID}`;
      } else {
        createPopupError("You need to be logged in to view your profile.");
      }
    });
  }


  const searchInput = document.querySelector(".search-input");
  searchInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const searchQuery = searchInput.value.trim().toLowerCase();

      if (!window.location.pathname.includes("index.html")) {

        localStorage.setItem("searchQuery", searchQuery);
        window.location.href = "index.html";
      }
    }
  });
}


function signOff() {
  localStorage.removeItem("userID");
  localStorage.removeItem("isAdmin");
  window.location.href =
    "https://kashishop2.s3.us-east-1.amazonaws.com/main/index.html";
}


function goToProfile() {
  if (currentUserID) {
    window.location.href = `https://kashishop2.s3.us-east-1.amazonaws.com/main/profile.html?userID=${currentUserID}`;
  } else {
    window.location.href =
      "https://us-east-1l8fw4esc3.auth.us-east-1.amazoncognito.com/login?client_id=2k3i5ubbp0ed3omjjhef3u5jkj&response_type=code&scope=email+openid+phone&redirect_uri=https%3A%2F%2Fkashishop2.s3.us-east-1.amazonaws.com%2Fmain%2Fcallback.html";
  }
}

function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function sendEmail(recipientEmail, subject, mailBody) {
  try {
    const response = await fetch(API + `Users/mail`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        recipient_email: recipientEmail,
        subject: subject,
        mail_body: mailBody,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("Error response data:", errorData);
      throw new Error(`Error: ${errorData.message || "Failed to send email."}`);
    }

    const data = await response.json();
  } catch (error) {
    console.error("Error occurred while sending email:", error);
  }
}

//////////////////////////////////////POPUPS//////////////////////////////////////

function createPopup(message) {
  Swal.fire({
    position: "top",
    title: `<div class="text-center h5">${message}</div>`,
    toast: true,
    showClass: {
      popup: `
            animate__animated
            animate__zoomIn
            animate__faster
            
            `,
    },
    hideClass: {
      popup: `
            animate__animated
            animate__zoomOut
            animate__faster
            
          `,
    },
    showConfirmButton: false,
    timer: 1500,
  });
}

function createPopupSuccess(message) {
  Swal.fire({
    position: "top",
    title: message,
    icon: "success",
    toast: true,
    showClass: {
      popup: `
          animate__animated
          animate__zoomIn
          animate__faster
          
          `,
    },
    hideClass: {
      popup: `
          animate__animated
          animate__zoomOut
          animate__faster
          
        `,
    },
    showConfirmButton: false,
    timer: 1500,
  });
}

function createPopupError(message) {
  Swal.fire({
    position: "top",
    title: message,
    icon: "error",
    toast: true,
    showClass: {
      popup: `
          animate__animated
          animate__zoomIn
          animate__faster
          
          `,
    },
    hideClass: {
      popup: `
          animate__animated
          animate__zoomOut
          animate__faster
          
        `,
    },
    showConfirmButton: false,
    timer: 2500,
  });
}

function createPopupWarning(message) {
  Swal.fire({
    position: "top",
    title: message,
    icon: "warning",
    toast: true,
    showClass: {
      popup: `
          animate__animated
          animate__zoomIn
          animate__faster
          
          `,
    },
    hideClass: {
      popup: `
          animate__animated
          animate__zoomOut
          animate__faster
          
        `,
    },
    showConfirmButton: false,
    timer: 2500,
  });
}

//////////////////////////////////////POPUPS//////////////////////////////////////

//////////////////////////////////////SPINNER//////////////////////////////////////


function addSpinnerToButton(button) {
  if (!button || !(button instanceof HTMLButtonElement)) {
    console.error("Invalid button element provided.");
    return;
  }


  button.setAttribute("data-original-content", button.innerHTML);


  button.innerHTML = `
        ${button.innerHTML}
        <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
    `;


  button.disabled = "disabled";
  button.classList.add("btn-disabled");
}


function restoreButton(button) {
  if (!button || !(button instanceof HTMLButtonElement)) {
    console.error("Invalid button element provided.");
    return;
  }


  const originalContent = button.getAttribute("data-original-content");
  if (originalContent) {
    button.innerHTML = originalContent;
    button.removeAttribute("data-original-content");
  }


  button.disabled = false;
  button.classList.remove("btn-disabled");
}

//////////////////////////////////////SPINNER//////////////////////////////////////
