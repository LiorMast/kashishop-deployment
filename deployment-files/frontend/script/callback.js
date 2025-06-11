document.addEventListener("DOMContentLoaded", async () => {

  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get("code");

  if (!code) {
    console.error("Authorization code not found.");
    return;
  }


  const clientId = "2k3i5ubbp0ed3omjjhef3u5jkj";
  const clientSecret = "avhrr3604g80h9t5mtmq0ol0a4u7n6ndq1pda65q8m1uk0djoe1";
  const redirectUri =
    "https://kashishop2.s3.us-east-1.amazonaws.com/main/callback.html";
  const tokenEndpoint =
    "https://us-east-1l8fw4esc3.auth.us-east-1.amazoncognito.com/oauth2/token";


  const basicAuth = btoa(`${clientId}:${clientSecret}`);

  try {
    console.log("Exchanging authorization code for tokens...");

    const response = await fetch(tokenEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Authorization: clientSecret ? `Basic ${basicAuth}` : undefined,
      },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: clientId,
        redirect_uri: redirectUri,
        code: code,
      }),
    });

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.statusText}`);
    }

    const tokens = await response.json();
    console.log("Tokens:", tokens);


    const idToken = tokens.id_token;
    const payload = JSON.parse(atob(idToken.split(".")[1]));
    const uuid = payload.sub;


    localStorage.setItem("userID", uuid);
    console.log("userID stored in localStorage:", uuid);

    const isAdmin = await fetch(
      API + "/prod/Users/isadmin?userID=" +
      uuid,
      { method: "GET" }
    );
    const isAdminResponse = await isAdmin.json();
    if (isAdmin.ok) {
      localStorage.setItem(
        "isAdmin",
        Boolean(JSON.parse(isAdminResponse.body).isAdmin)
      );
    } else {
      localStorage.setItem("isAdmin", false);
    }


    window.location.href = "index.html";
  } catch (error) {
    console.error("Error exchanging authorization code for tokens:", error);
  }
});
