chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => {
    console.error("Clearead could not enable action-click side panel opening.", error);
  });
