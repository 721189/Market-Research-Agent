export function sanitizeInput(input: string): string {
  // Simple prompt injection sanitization (stripping dangerous control characters/tags)
  return input.replace(/<\/?[^>]+(>|$)/g, "")
              .replace(/system:/gi, "user:")
              .replace(/ignore previous instructions/gi, "");
}

export function validateUrlForSsrf(url: string): boolean {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname;
    
    // Block private/internal IP ranges
    if (
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname.startsWith("10.") ||
      hostname.startsWith("192.168.") ||
      hostname.match(/^172\.(1[6-9]|2[0-9]|3[0-1])\./)
    ) {
      return false;
    }
    
    // Only allow http/https
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return false;
    }
    
    return true;
  } catch {
    return false;
  }
}
