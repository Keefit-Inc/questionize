// Opens the side panel from the toolbar button and from a right-click on selected text.

chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((err) => console.error("sidePanel behavior", err));

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "questionize-selection",
    title: "Questionize this passage",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "questionize-selection" || !tab) return;
  // open() must run synchronously inside the user gesture, before any await.
  const opening = chrome.sidePanel.open({ tabId: tab.id });
  await chrome.storage.session.set({
    pendingSelection: { tabId: tab.id, text: info.selectionText || "", at: Date.now() },
  });
  await opening;
});
