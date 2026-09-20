async function loadUsers() {
  const r = await fetch("/api/users");
  return await r.json();
}

async function loadBilling() {
  // This endpoint intentionally does not exist in the demo backend.
  const r = await fetch("/api/login");
  console.log("billing response", r.status);
}

const api_key = "DEMO_SECRET_REPLACE_ME_123456";
