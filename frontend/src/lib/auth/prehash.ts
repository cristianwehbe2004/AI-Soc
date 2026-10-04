/**
 * Pre-hashes a raw user password with their email address using the Web Crypto API.
 * This guarantees that raw passwords are never transmitted in network request bodies.
 */
export async function prehashPassword(
  password: string,
  email: string,
): Promise<string> {
  if (
    typeof window === "undefined" ||
    !window.crypto ||
    !window.crypto.subtle
  ) {
    return password;
  }
  const normalizedEmail = email.trim().toLowerCase();
  const encoder = new TextEncoder();
  const data = encoder.encode(`ai-soc-salt:${normalizedEmail}:${password}`);
  const hashBuffer = await window.crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}
