import { useState, useCallback } from "react";

const SAVED_DETAILS_KEY = "tripweaver_saved_booking_message";

function loadSavedMessage() {
  try {
    return localStorage.getItem(SAVED_DETAILS_KEY) || null;
  } catch {
    return null;
  }
}

export function useSavedBookingDetails() {
  const [savedMessage, setSavedMessage] = useState(loadSavedMessage);

  const saveBookingMessage = useCallback((message) => {
    try {
      localStorage.setItem(SAVED_DETAILS_KEY, message);
      setSavedMessage(message);
    } catch {
      // localStorage can fail (private browsing, storage full) - skip silently
    }
  }, []);

  const clearSavedMessage = useCallback(() => {
    try {
      localStorage.removeItem(SAVED_DETAILS_KEY);
    } catch {
      // ignore
    }
    setSavedMessage(null);
  }, []);

  return { savedMessage, saveBookingMessage, clearSavedMessage };
}

export function isAskingForBookingDetails(assistantText) {
  return (assistantText || "").toLowerCase().includes("could you share your");
}

export function isBookingConfirmation(assistantText) {
  return (assistantText || "").includes("🎉 You're booked!");
}