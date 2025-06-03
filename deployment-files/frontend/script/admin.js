const Users = [];

document.addEventListener("DOMContentLoaded", () => {
  localStorage.removeItem("searchQuery");
  const userID = localStorage.getItem("userID");

  fetch(API + "Users/isadmin?userID=" + currentUserID, {
    method: "GET",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.body) {
        localStorage.setItem("isAdmin", JSON.parse(data.body).isAdmin);
        isAdmin = localStorage.getItem("isAdmin");
        if (isAdmin == "false") {
          window.location.href = "index.html";
        }
      }
    })
    .catch((error) => {
      console.error("Error: Can't get admin status ", error);
    });


  const navbar = document.querySelector(".navbar");
  navbar.innerHTML = `
        <button class="nav-btn" onclick="window.location.href='index.html';">Home</button>
        <input type="text" class="search-input" placeholder="Search">
        <button class="nav-btn" onclick="signOff();">Sign Off</button>
    `;

  fetch(API + "Users/admin_statistics", {
    method: "GET",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.body) {
        const statistics = JSON.parse(data.body);


        document.querySelector(
          ".statistics p:nth-of-type(1) span"
        ).textContent = statistics.total_items;
        document.querySelector(
          ".statistics p:nth-of-type(2) span"
        ).textContent = statistics.total_users;
        document.querySelector(
          ".statistics p:nth-of-type(3) span"
        ).innerHTML = `
            ${statistics.user_with_most_items.username} 
            (${statistics.user_with_most_items.item_count} items) 
            <a href="profile.html?userID=${statistics.user_with_most_items.userID}" class="profile-link">
              View Profile
            </a>
          `;
        document.querySelector(
          ".statistics p:nth-of-type(4) span"
        ).innerHTML = `
            ${statistics.user_with_most_purchases.username} 
            (${statistics.user_with_most_purchases.purchase_count} purchases) 
            <a href="profile.html?userID=${statistics.user_with_most_purchases.userID}" class="profile-link">
              View Profile
            </a>
          `;
      }
    })
    .catch((error) => {
      console.error("Error: Can't get statistics", error);
    });


  fetch(API + "Items/all", {
    method: "GET",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.body) {
        Items = JSON.parse(data.body);
        populateItemsTable(Items);
      }
    })
    .catch((error) => {
      console.error("Error: Can't get items ", error);
    });

  fetch(API + "Users/all", {
    method: "GET",
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data) {
        console.log("Users data received:", data);
        populateUsersTable(JSON.parse(data.body));
      }
    })
    .catch((error) => {
      console.error("Error: Can't get users", error);
    });
});


function initializeDataTable(selector) {
  if ($.fn.DataTable.isDataTable(selector)) {
    $(selector).DataTable().destroy();
  }
  $(selector).DataTable({
    paging: true,
    pageLength: 10,
    lengthMenu: [10, 25, 50, 100],
    ordering: true,
    order: [[0, "asc"]],
    info: true,
    searching: true,
  });
}

function populateItemsTable(Items) {
  const itemsTableBody = document.querySelector("#items-table tbody");
  itemsTableBody.innerHTML = "";

  Items.forEach((item) => {
    const isActive = item.isActive.toString().toLowerCase() === "true";
    const isSold = String(item.isSold || "false").toLowerCase() === "true";

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.itemID || "Undefined"}</td>
      <td>${item.name || "Unnamed"}</td>
      <td>${item.description || "No description available"}</td>
      <td>$${item.price || 0}</td>
      <td>
        <a href="profile.html?userID=${item.poster_id}" class="username-link">
          ${item.poster_username || "Unknown"}
        </a>
      </td>
      <td>${item.poster_id || "Unknown"}</td>
      <td>
        <label class="switch">
          <input 
            type="checkbox" 
            ${isActive ? "checked" : ""} 
            data-id="${item.itemID}" 
            data-type="item" 
            ${isSold ? "disabled" : ""}
          >
          <span class="slider"></span>
        </label>
      </td>
      <td>${isSold ? "True" : "False"}</td>
    `;
    itemsTableBody.appendChild(row);
  });


  document
    .querySelectorAll("#items-table input[type='checkbox']")
    .forEach((checkbox) => {
      checkbox.addEventListener("change", handleActiveToggle);
    });

  initializeDataTable("#items-table");
}


function populateUsersTable(Users) {
  console.log;
  const usersTableBody = document.querySelector("#users-table tbody");
  usersTableBody.innerHTML = "";

  Users.forEach((user) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${user.ID}</td>
      <td>${user.full_name || "N/A"}</td>
      <td>
        <a href="profile.html?userID=${user.ID}" class="username-link">
          ${user.username || "N/A"}
        </a>
      </td>
      <td>${user.phone_number || "N/A"}</td>
      <td>${user.items_for_sale}</td>
      <td>${new Date(user.join_date).toLocaleDateString()}</td>
      <td>
        <label class="switch">
          <input type="checkbox" ${user.isActive.toString().toLowerCase() === "true" ? "checked" : ""
      } data-id="${user.ID}">
          <span class="slider"></span>
        </label>
      </td>
    `;
    usersTableBody.appendChild(row);
  });


  document
    .querySelectorAll("#users-table input[type='checkbox']")
    .forEach((checkbox) => {
      checkbox.addEventListener("change", handleActiveToggle);
    });

  initializeDataTable("#users-table");
}


function handleActiveToggle(event) {
  const checkbox = event.target;
  const id = checkbox.getAttribute("data-id");
  const type = checkbox.getAttribute("data-type");

  console.log(`Toggling ${type} ID: ${id}`);

  checkbox.disabled = true;


  const url = API + `${type === "item" ? "Items" : "Users"}/isActive_switch`;


  const body = type === "item" ? { itemID: id } : { userID: id };


  fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Failed to toggle ${type} with ID ${id}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log(
        `${type === "item" ? "Item" : "User"} ID ${id} toggled successfully`,
        data
      );
      createPopupSuccess(
        `${type === "item" ? "Item" : "User"} ID ${id} toggled successfully`
      );
    })
    .catch((error) => {
      console.error(error);
      checkbox.disabled = false;
      createPopupError(
        `Failed to toggle ${type === "item" ? "item" : "user"}: ${id}.`
      );

      checkbox.checked = !checkbox.checked;
      checkbox.disabled = false;
    });
}
