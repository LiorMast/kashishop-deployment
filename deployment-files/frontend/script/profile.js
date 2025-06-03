let Items = [];

const urlParams = new URLSearchParams(window.location.search);
const userIDFromQuery = urlParams.get('userID');
if (localStorage.getItem('isAdmin') === 'true' && userIDFromQuery === localStorage.getItem('userID')) {
  window.location.href = 'index.html';
}
document.addEventListener("DOMContentLoaded", () => {
  localStorage.removeItem("searchQuery");
  const urlParams = new URLSearchParams(window.location.search);
  const referencedProfileID = urlParams.get("userID");
  let pendingItems;

  console.log(referencedProfileID, "profile ID:");

  const pendingTransactionsContainer = document.getElementById("pending-transactions-container");
  const profileActions = document.getElementById("profile-actions");
  const itemsContainer = document.getElementById("items-container");
  const transactionsContainer = document.getElementById("transactions-container");



  let Transactions = [];

  fetch(API + `Items/seller?sellerID=${referencedProfileID}`, { method: "GET" })
    .then((response) => response.json())
    .then((data) => {
      console.log("Raw Items Data:", data);
      const parsedData = JSON.parse(data.body);

      Items = parsedData.items.map((item) => ({
        ...item,
        isActive:
          item.isActive === "TRUE" ||
          item.isActive === "true" ||
          item.isActive === true,
        price: Number(item.price),
        seller: item.seller,
        creationDate: new Date(item.creationDate),
        itemID: item.itemID,
      }));
      if (currentUserID === referencedProfileID) {

        populateUserItems(referencedProfileID);
        itemsContainer.style.display = "block";
      } else {

        console.log(Items);
        showForeignUserItems(referencedProfileID);
      }
      console.log("Items:", Items);
    })
    .catch((error) => console.error("Error fetching items:", error));

  let dataTableInstance = null;

  if (referencedProfileID === currentUserID) {
    pendingTransactionsContainer.style.display = "block";
    loadPendingTransactions();

    fetch(
      API +
      `Users/byid_accepted_transactions?userID=${currentUserID.toString()}`,
      {
        method: "GET",
      }
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Raw Transactions Data:", data);


        const parsedBody = JSON.parse(data.body);


        Transactions = parsedBody.map((transaction) => ({
          transactionID: transaction.transactionID,
          itemID: transaction.itemID,
          state: transaction.state,
          itemName: transaction.itemName,
          itemPrice: transaction.itemPrice,
          transactionDate: transaction.transactionDate,
          otherUserTranID: transaction.buyerOrSellerID,
          otherUsername: transaction.buyerOrSellerName,
        }));

        console.log("Parsed Transactions for Display:", Transactions);


        showTransactions();
      })
      .catch((error) => {
        console.error("Error fetching transactions:", error);
      });
  }






















  function populateUserItems(referencedProfileID) {
    const activeItems = Items.filter(
      (item) => item.seller === referencedProfileID && item.isActive
    );

    itemsContainer.innerHTML = activeItems
      .map(
        (item) => `
          <div class="item-card">
            <img src="${item.image}" alt="${item.item_name}" class="item-image">
            <div class="item-details">
              <h3 class="item-name">${item.item_name}</h3>
              <p class="item-description">${item.item_description}</p>
              <p class="item-price">$${item.price}</p>
            </div>
          </div>`
      )
      .join("");
    document.getElementById("user-items-count").textContent =
      "Items in Stock: " + activeItems.length;
  }

  console.log(urlParams.toString(), "shit on the API");

  fetch(API + `Users/byid?${urlParams.toString()}`, { method: "GET" })
    .then((response) => response.json())
    .then((data) => {
      console.log("Raw Items Data:", data);
      const parsedData = JSON.parse(data.body);
      console.log(parsedData);

      const creationDate = new Date(parsedData.creationDate);


      const formattedDate = creationDate.toLocaleString("en-US", {
        year: "numeric",
        month: "long",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      });

      document.getElementById("userName").textContent =
        "User name: " + parsedData.username;
      document.getElementById("user-name").textContent =
        "Full Name: " + parsedData.name;
      document.getElementById("user-joined").textContent =
        "Date Joined: " + formattedDate;
      document.getElementById("address").textContent =
        "Address: " + parsedData.address;
      console.log(parsedData);
      document.getElementById("phone-number").textContent =
        "Phone Number: " + formatPhoneNumber(parsedData.phone_number);
      document.getElementsByClassName("profile-pic")[0].src =
        parsedData.picture;
    })
    .catch((error) => console.error("Error fetching items:", error));

  function showForeignUserItems(referencedProfileID) {
    const activeItems = Items.filter(
      (item) => item.seller === referencedProfileID && item.isActive
    );

    itemsContainer.innerHTML = `
      <div class="d-flex justify-content-center" id="spinni">
        <div class="spinner-border text-info my-5" style="width: 3rem; height: 3rem" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    `;

    fetch(API + `transactions/buyer_pending?buyerID=${currentUserID}`, {
      method: "GET",
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Raw Items Data:", data);
        const pendingItems = JSON.parse(data.body).itemIDs;

        activeItems.forEach((item) => {
          const itemCard = document.createElement("div");
          itemCard.classList.add("item-card", "visitor-card");

          itemCard.innerHTML = `
              <img src="${item.image}" alt="${item.item_name}" class="item-image">
              <div class="item-details">
                <h3 class="item-name">${item.item_name}</h3>
                <p class="item-description">${item.item_description}</p>
              </div>
              <div class="item-price-section">
                <p class="price-label">Price:</p>
                <p class="item-price">$${item.price}</p>
                <button class="buy-button" data-item-id="${item.itemID}" onClick="buyItem('${item.itemID}')">BUY</button>
              </div>
            `;

          itemsContainer.appendChild(itemCard);


          const button = itemCard.querySelector(".buy-button");


          console.log(pendingItems);
          if (pendingItems.includes(item.itemID)) {
            button.disabled = true;
            button.textContent = "Pending";
            button.classList.add("disabled-button");
          }
        });


        document.getElementById("user-items-count").textContent =
          "Items in Stock: " + activeItems.length;

        itemsContainer.removeChild(document.getElementById("spinni"));
      })
      .catch((error) => console.error("Error fetching pending items:", error));
  }

  let transactionsTableInitialized = false;

  function showTransactions() {
    const transactionsTableBody = document.querySelector(
      "#transactions-table tbody"
    );
    transactionsTableBody.innerHTML = "";

    Transactions.forEach((transaction) => {
      console.log(transaction, "transaction data");
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${transaction.state === "bought" ? "Bought" : "Sold"}</td>
        <td>${transaction.itemName}</td>
        <td>
          <a href="profile.html?userID=${transaction.otherUserTranID}">
            ${transaction.otherUsername}
          </a>
        </td>
        <td>${new Date(transaction.transactionDate).toLocaleDateString()}</td>
        <td>$${transaction.itemPrice}</td>`;

      transactionsTableBody.appendChild(row);
    });

    if (!transactionsTableInitialized) {
      new DataTable("#transactions-table", {
        paging: true,
        searching: true,
        ordering: true,
      });
      transactionsTableInitialized = true;
    }
  }

  if (referencedProfileID === currentUserID) {
    profileActions.innerHTML = `
      <h1>Profile options</h1>
      <div class="profile-actions-buttons-holder">
      <button id="show-items-btn" class="active">Show Items for Sale</button>
      <button id="show-transactions-btn">Show Transactions</button>
      <button id="upload-item-btn" onclick="window.location.href='new_item.html'">Upload New Item</button>
      <button id="edit-profile-btn" onclick="window.location.href='edit_profile.html'">Edit Profile</button>
      </div>`;

    transactionsContainer.style.display = "none";

    document.getElementById("show-items-btn").addEventListener("click", () => {

      document.getElementById("show-items-btn").classList.add("active");
      document
        .getElementById("show-transactions-btn")
        .classList.remove("active");


      itemsContainer.style.display = "block";
      transactionsContainer.style.display = "none";


      populateUserItems(referencedProfileID);
    });

    document
      .getElementById("show-transactions-btn")
      .addEventListener("click", () => {

        document
          .getElementById("show-transactions-btn")
          .classList.add("active");
        document.getElementById("show-items-btn").classList.remove("active");


        itemsContainer.style.display = "none";
        transactionsContainer.style.display = "block";


        showTransactions();
      });

    populateUserItems(referencedProfileID);
  } else {
    profileActions.innerHTML = "";
    showForeignUserItems(referencedProfileID);
  }



  document.addEventListener("click", (event) => {
    if (event.target.classList.contains("accept-btn")) {
      const transactionID = event.target.dataset.id;
      const email = event.target.dataset.email;
      const item_name = event.target.dataset.itemname;
      handleTransactionDecision(transactionID, email, item_name, "accepted");
    } else if (event.target.classList.contains("reject-btn")) {
      const transactionID = event.target.dataset.id;
      const email = event.target.dataset.email;
      const item_name = event.target.dataset.itemname;
      console.log(item_name, "item name from addevent listener");
      handleTransactionDecision(transactionID, email, item_name, "rejected");
    }
  });
});

async function loadPendingTransactions() {
  try {
    const response = await fetch(
      API + `Users/pending_transactions?userID=${currentUserID}`
    );
    if (!response.ok) throw new Error("Failed to fetch pending transactions.");

    const rawResponse = await response.json();
    console.log("Raw Pending Transactions Response:", rawResponse);


    const pendingTransactions = JSON.parse(rawResponse.body || "[]");
    console.log("Parsed Pending Transactions:", pendingTransactions);

    if (!Array.isArray(pendingTransactions)) {
      throw new Error("Pending transactions data is not an array.");
    }

    const tableBody = document.querySelector(
      "#pending-transactions-table tbody"
    );
    tableBody.innerHTML = "";

    pendingTransactions.forEach((transaction) => {
      const row = document.createElement("tr");
      row.innerHTML = `
          <td>${transaction.itemName}</td>
          <td><a href="profile.html?userID=${transaction.buyerOrSellerID}" >${transaction.buyerOrSellerName
        }</a></td>
          <td>${new Date(transaction.transactionDate).toLocaleDateString()}</td>
          <td>$${transaction.itemPrice}</td>
          <td>
            <button class="btn btn-success accept-btn" data-email="${transaction.buyerEmail
        }" data-itemname="${transaction.itemName}" data-id="${transaction.transactionID
        }">Accept <i class="bi bi-hand-thumbs-up-fill"></i></button>
            <button class="btn btn-danger reject-btn" data-email="${transaction.buyerEmail
        }" data-id="${transaction.transactionID}" data-itemname="${transaction.itemName
        }">Reject <i class="bi bi-hand-thumbs-down-fill"></i></button>
          </td>
        `;
      tableBody.appendChild(row);
    });


    if (!$.fn.DataTable.isDataTable("#pending-transactions-table")) {
      $("#pending-transactions-table").DataTable({
        paging: true,
        searching: true,
        ordering: true,
      });
    }
  } catch (error) {
    console.error("Error loading pending transactions:", error);
  }
}



async function handleTransactionDecision(
  transactionID,
  email,
  itemName,
  decision
) {
  try {
    console.log(itemName, "item name from handle");
    const endpoint = decision === "accepted" ? "accepted" : "rejected";
    const transactionBtn = document.querySelector(`.${endpoint === "accepted" ? "accept" : "reject"}-btn[data-id="${transactionID.toString()}"]`);
    const bothBtns = document.querySelectorAll(`[data-id="${transactionID.toString()}"]`);
    const origText = transactionBtn.innerHTML;
    bothBtns.forEach((btn) => {
      btn.disabled = true;
      btn.classList.add("btn-disabled");
    });
    const thumbs = transactionBtn.querySelector("i");
    thumbs.classList.remove(
      "bi",
      `bi-hand-thumbs-${endpoint === "accepted" ? "up" : "down"}-fill`
    );
    thumbs.classList.add("spinner-border", "spinner-border-sm");
    const response = await fetch(API + `transactions/byid_update_status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transactionID,
        status: decision,
      }),
    });

    if (decision == "accepted") {
      await sendEmail(
        email,
        `Offer accepted`,
        `Your offer for the item ${itemName} has been accepted.`
      );
    } else {
      await sendEmail(
        email,
        `Offer rejected`,
        `Your offer for the item ${itemName} has been rejected.`
      );
    }

    if (!response.ok) {
      throw new Error(`Failed to ${decision === "accepted" ? "accept" : "reject"} the transaction.`);
      createPopupError(`Failed to ${decision === "accepted" ? "accept" : "reject"} transaction.`);
      bothBtns.forEach((btn) => {
        btn.disabled = false;
        btn.classList.remove("btn-disabled");
      });
      transactionBtn.innerHTML = origText;
    }
    const result = await response.json();
    createPopupSuccess(`Transaction ${decision} successfully!`);
    loadPendingTransactions();
  } catch (error) {
    console.error(`Error handling transaction ${decision}:`, error);
    createPopupError(`Failed to ${decision} transaction.`);
    bothBtns.forEach((btn) => {
      btn.disabled = false;
      btn.classList.remove("btn-disabled");
    });
    transactionBtn.innerHTML = origText;
  }
}

function formatPhoneNumber(number) {
  if (number.length != 13) {
    return number;
  }
  const countryCode = number.slice(0, 4);
  const areaCode = number.slice(4, 6);
  const part1 = number.slice(6, 9);
  const part2 = number.slice(9);

  return `${countryCode} ${areaCode}-${part1}-${part2}`;
}


async function buyItem(itemID) {
  if (currentUserID === null) {
    createPopupWarning("You must be logged in to buy an item!");
    return;
  }

  console.log("itemID from button:", typeof itemID, itemID);

  const item = Items.find((i) => String(i.itemID) === String(itemID));
  if (!item) {
    createPopupError("Item not found!");
    console.error("Item not found! Debug info:");
    console.log("itemID provided:", itemID);
    console.log("Available Items:", Items);
    return;
  }

  console.log(" item seller id:", item.seller, typeof item.seller);
  console.log(" current user id: ", currentUserID, typeof currentUserID);

  if (item.seller === currentUserID) {
    createPopupWarning("You cannot buy your own item!");
    const button = document.querySelector(`[class="buy-button"][data-item-id="${itemID.toString()}"]`);
    button.disabled = true;
    button.classList.add("disabled-button");
    return;
  }

  const button = document.querySelector(`[class="buy-button"][data-item-id="${itemID.toString()}"]`);
  addSpinnerToButton(button);
  const transaction = {
    transactionID: generateUUID(),
    buyerID: currentUserID.toString(),
    sellerID: item.seller.toString(),
    ItemID: item.itemID.toString(),
    transactionDate: new Date().toISOString().split(".")[0],
    price: item.price.toString(),
    status: "pending".toString().toLowerCase(),
  };

  console.log(transaction);

  try {
    const transactionResponse = await fetch(API + `transactions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(transaction),
    });

    if (!transactionResponse.ok) {
      const errorData = await transactionResponse.json();
      console.error("Error response data:", errorData);
      throw new Error(
        `Error: ${errorData.message || "Unknown error while creating transaction."
        }`
      );
      createPopupError("Error while creating transaction.");
      restoreButton(button);
    }

    const transactionData = await transactionResponse.json();
    console.log("Transaction Response:", transactionData);

    // const button = document.querySelector(
    //   `[class="buy-button"][data-item-id="${itemID.toString()}"]`
    // );
    // button.disabled = true;
    // button.classList.add("disabled-button");

    if (transactionData.transactionExists) {
      if (
        transactionData.message ===
        "Transaction with this buyerID and ItemID already exists."
      ) {
        createPopupWarning("You can only offer to buy this item once!");
        button.innerHTML = "Pending";
      }
      if (
        transactionData.message ===
        "The seller has rejected your offer for this product."
      ) {
        createPopupWarning(
          "The seller has rejected your offer for this product."
        );
        button.innerHTML = "Rejected";
      }
    } else {
      createPopupSuccess("Offer sent successfully!");
      button.innerHTML = "Pending";
    }
  } catch (error) {
    console.error("Error occurred while creating transaction:", error);
    createPopupError("Error while creating transaction.");
    restoreButton(button);
    return;
  }

  try {
    const emailResponse = await fetch(
      API + `Users/get_email?userID=${item.seller}`,
      {
        method: "GET",
      }
    );

    if (!emailResponse.ok) {
      const errorData = await emailResponse.json();
      console.error("Error response data:", errorData);
      throw new Error(
        `Error: ${errorData.message || "Unknown error while fetching email."}`
      );
    }

    const emailData = await emailResponse.json();
    const email = emailData.body;
    console.log("Email:", email);

    await sendEmail(
      email,
      `You have a new offer for your item, ${item.item_name} on Kashishop!`,
      `You have a new offer for your item! Please check your offers in your profile.`
    );
  } catch (error) {
    console.error("Error occurred while sending email:", error);
  }

  console.log("Item purchase process completed.");
}
