document.addEventListener("DOMContentLoaded", async () => {

  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get("code");

  if (!code) {
    console.error("Authorization code not found.");
    return;
  }


  const clientId = "7vvhrl18402pe4rdo5ehlighr8";
  const clientSecret = "1snpgboa6lbdm5vh4qpe54sbul2h38pqctuvglolsa8blt9ab95";
  const redirectUri = "https://kashish2-kashishop2.s3.us-east-1.amazonaws.com/main/callback.html";
  const tokenEndpoint = "https://kashish2-us-east-1l8fw4esc3.auth.us-east-1.amazoncognito.com/oauth2/token";

  const API = "https://tuj21wu7l1.execute-api.us-east-1.amazonaws.com/kashish2";


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

    const text = await response.text();
    console.log("Raw token response:", text);

    let tokens;
    try {
      tokens = JSON.parse(text);
    } catch (e) {
      console.error("Failed to parse token JSON:", e);
      return;
    }


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
    window.location.href = "index.html";
  }
});
