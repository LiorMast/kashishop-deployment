const Items = [];


const searchQuery = localStorage.getItem("searchQuery");


document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.querySelector(".search-input");
  const itemsPerPageDropdown = document.getElementById("items-per-page");
  const paginationContainer = document.querySelector(".pagination");

  searchInput.value = searchQuery || "";

  let itemsPerPage = parseInt(itemsPerPageDropdown.value, 10);
  let currentPage = 1;
  let filteredItems = [];


  fetch(API + "Items", {
    method: "GET",
  })
    .then((response) => response.json())
    .then((data) => {
      const parsedData = JSON.parse(data.body);
      console.log("Parsed Data:", parsedData);

      parsedData.forEach((item) => {
        const transformedItem = {
          ...item,
          isActive: item.isActive.toString().toLowerCase() === "true",
          isSold: item.isSold.toString().toLowerCase() === "true",
          price: Number(item.price),
          seller: item.seller,
          creationDate: new Date(item.creationDate),
          itemID: item.itemID,
        };
        Items.push(transformedItem);
      });

      console.log("Transformed Items:", Items);
      filteredItems = Items.filter((item) => item.isActive);
      console.log("Filtered Items:", filteredItems);
      updateUI();


      if (searchQuery) {
        filterItemsBySearch(searchQuery);
      }
    })
    .catch((error) => {
      console.error("Error fetching data:", error);
      updateUI();
    });

  const renderItems = async () => {
    const itemsContainer = document.querySelector(".items-container");


    itemsContainer.innerHTML = `
        <div class="d-flex justify-content-center" id="spinni">
          <div class="spinner-border text-info my-5" style="width: 3rem; height: 3rem;" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>
      `;

    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredItems.length);
    const itemsToDisplay = filteredItems.slice(startIndex, endIndex);

    try {

      const response = await fetch(
        API + `transactions/buyer_pending?buyerID=${currentUserID}`,
        {
          method: "GET",
        }
      );
      const data = await response.json();
      const pendingItems = JSON.parse(data.body).itemIDs;
      console.log("Pending Items:", pendingItems);


      itemsContainer.innerHTML = "";


      itemsToDisplay.forEach((item) => {
        const itemCard = document.createElement("div");
        itemCard.classList.add("item-card");
        itemCard.innerHTML = `
            <img src="${item.image}" alt="${item.item_name}" class="item-image">
            <div class="item-details">
              <h3 class="item-name">${item.item_name}</h3>
              <p class="item-description">${item.item_description}</p>
              <p class="item-seller">
                Sold by: 
                <a href="profile.html?userID=${item.seller}" class="seller-link">${item.sellerUsername}</a>
              </p>
            </div>
            <div class="item-price-section">
              <p class="price-label">Price:</p>
              <p class="item-price">$${item.price}</p>
              <button class="buy-button" data-item-id="${item.itemID}" data-seller-id="${item.seller}" onClick="buyItem('${item.itemID}')">BUY</button>
            </div>`;
        itemsContainer.appendChild(itemCard);


        const button = itemCard.querySelector(".buy-button");
        if (pendingItems.includes(item.itemID)) {
          button.disabled = true;
          button.textContent = "Pending";
          button.classList.add("disabled-button");
        }
        if (item.seller == currentUserID) {
          button.disabled = true;
          button.textContent = "Your listing";
          button.classList.add("disabled-button");
        }
      });

      if (itemsToDisplay.length === 0) {
        itemsContainer.innerHTML = `<p class="no-items-message">No items match your search criteria.</p>`;
      }
    } catch (error) {
      console.error("Error fetching pending items:", error);
      itemsContainer.innerHTML = `<p class="error-message">No Items To Display.</p>`;
    }
  };

  const renderPagination = () => {
    paginationContainer.innerHTML = "";
    const totalPages = Math.ceil(filteredItems.length / itemsPerPage);

    const createButton = (text, page) => {
      const button = document.createElement("button");
      button.textContent = text;
      button.disabled = page === currentPage;
      button.addEventListener("click", () => {
        currentPage = page;
        updateUI();
      });
      return button;
    };

    paginationContainer.appendChild(createButton("First Page", 1));
    if (currentPage > 1) {
      paginationContainer.appendChild(
        createButton("Previous", currentPage - 1)
      );
    }

    for (let i = 1; i <= totalPages; i++) {
      paginationContainer.appendChild(createButton(i, i));
    }

    if (currentPage < totalPages) {
      paginationContainer.appendChild(createButton("Next", currentPage + 1));
    }
    paginationContainer.appendChild(createButton("Last Page", totalPages));
  };

  const updateUI = () => {
    renderItems();
    renderPagination();
  };


  const filterItemsBySearch = (query) => {
    const normalizedQuery = query.toLowerCase();
    filteredItems = Items.filter((item) => {
      return (
        item.isActive &&
        (item.item_name.toLowerCase().includes(normalizedQuery) ||
          item.item_description.toLowerCase().includes(normalizedQuery) ||
          item.sellerUsername.toLowerCase().includes(normalizedQuery))
      );
    });
    currentPage = 1;
    console.log(`Filtered items for query "${query}":`, filteredItems);
    updateUI();
  };


  searchInput.addEventListener("input", (event) => {
    const query = event.target.value;
    localStorage.setItem("searchQuery", query);
    filterItemsBySearch(query);
  });


  itemsPerPageDropdown.addEventListener("change", (event) => {
    itemsPerPage = parseInt(event.target.value, 10);
    currentPage = 1;
    updateUI();
  });
});

async function buyItem(itemID) {
  if (currentUserID == null) {
    createPopupWarning("You must be logged in to buy an item!");
    return;
  }
  console.log(currentUserID);
  console.log("itemID from button:", typeof itemID, itemID);

  const item = Items.find((i) => String(i.itemID) === String(itemID));
  if (!item) {
    showPopupError("Item not found!");



    return;
  }

  console.log(" item seller id:", item.seller, typeof item.seller);
  console.log(" current user id: ", currentUserID, typeof currentUserID);

  if (item.seller === currentUserID) {
    createPopupWarning("You cannot buy your own item!");
    const button = document.querySelector(`[class="buy-button"][data-item-id="${itemID.toString()}"]`);


    return;
  }

  const buyBtn = document.querySelector(`[class="buy-button"][data-item-id="${itemID.toString()}"]`);
  addSpinnerToButton(buyBtn);


  const transaction = {
    transactionID: generateUUID(),
    buyerID: currentUserID.toString(),
    sellerID: item.seller.toString(),
    ItemID: item.itemID.toString(),
    transactionDate: new Date().toISOString().split(".")[0],
    price: item.price.toString(),
    status: "pending".toString().toLowerCase(),
  };



  fetch(API + `transactions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(transaction),
  })
    .then((response) => {
      if (!response.ok) {

        return response.json().then((errorData) => {
          console.error("Error response data:", errorData);
          throw new Error(`Error: ${errorData.message || "Unknown error"}`);
          restoreButton(buyBtn);
        });
      }
      return response.json();
    })
    .then((data) => {





      if (data.transactionExists) {
        if (
          data.message ==
          "Transaction with this buyerID and ItemID already exists."
        ) {
          createPopupWarning("You can only offer to buy this item once!");
          buyBtn.innerHTML = "Pending";

          if (
            data.message ==
            "The seller has rejected your offer for this product."
          ) {
            createPopupWarning(
              "The seller has rejected your offer for this product"
            );
            button.innerHTML = "Rejected";
          }
        } else {
          createPopupSuccess("Offer sent successfully!");
        }
        restoreButton(buyBtn);
        button.innerHTML = "Pending";
      }
      console.log("Success:", data);
    })
    .catch((error) => {
      console.error("Error occurred:", error);
      restoreButton(buyBtn);
    });
  fetch(API + `Users/get_email?userID=` + item.seller, {

    method: "GET",
  })
    .then((response) => {
      if (!response.ok) {

        return response.json().then((errorData) => {
          console.error("Error response data:", errorData);
          restoreButton(buyBtn);
          throw new Error(`Error: ${errorData.message || "Unknown error"}`);
        });
      }
      return response.json();
    })
    .then(async (data) => {
      console.log("Success:", data);
      const email = data.body;
      console.log("email:", email);
      await sendEmail(
        email,
        `You have a new offer for ${item.item_name}!`,
        `You have a new offer for your item, ${item.item_name}! Please check your offers in your profile.`
      );
      createPopupSuccess("Offer sent successfully!");

      buyBtn.innerHTML = "Pending";
    })
    .catch((error) => {
      console.error("Error occurred:", error);
      createPopupError("Error occurred:", error);
      restoreButton(buyBtn)
    });
  console.log("supposed success but maybe not unless no CORS");

  //alert(`You bought "${item.item_name}" for $${item.price}!`);

}
