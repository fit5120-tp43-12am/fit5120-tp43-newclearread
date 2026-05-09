import { CLEAREAD_WEBSITE_URL } from "../shared/config.js";

const openButton = document.querySelector("#open-clearead");
const statusMessage = document.querySelector("#popup-status");
const openWebsiteLink = document.querySelector("#open-clearead-website");

function setStatus(type, message) {
  statusMessage.className = `popup-status status-${type}`;
  statusMessage.textContent = message;
  statusMessage.setAttribute("role", type === "error" ? "alert" : "status");
}

function sendRuntimeMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      const runtimeError = chrome.runtime.lastError;

      if (runtimeError) {
        reject(new Error(runtimeError.message));
        return;
      }

      resolve(response);
    });
  });
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab?.id) {
    throw new Error("Clearead could not find the current tab.");
  }

  return tab;
}

async function openSidePanelForTab(tab) {
  try {
    await chrome.sidePanel.open({ tabId: tab.id });
    return;
  } catch (error) {
    const response = await sendRuntimeMessage({
      type: "clearead:open-side-panel",
      tabId: tab.id,
      windowId: tab.windowId,
    });

    if (!response?.ok) {
      throw new Error(
        response?.message || error.message || "Clearead could not open the side panel."
      );
    }
  }
}

async function openClearead() {
  openButton.disabled = true;
  setStatus("loading", "Opening Clearead...");

  try {
    const tab = await getActiveTab();
    await sendRuntimeMessage({
      type: "clearead:mark-page-activation",
      tabId: tab.id,
      windowId: tab.windowId,
    }).catch(() => null);
    await openSidePanelForTab(tab);
    window.close();
  } catch (error) {
    openButton.disabled = false;
    setStatus("error", error.message || "Clearead could not open the side panel.");
  }
}

openButton.addEventListener("click", openClearead);
openWebsiteLink.href = CLEAREAD_WEBSITE_URL;
