const strings = {
  en: {
    connecting: "Connecting",
    idle: "Printer idle",
    busy: "Printer busy",
    disconnected: "Printer disconnected",
    pausePrinting: "Pause printing",
    resumePrinting: "Resume printing",
    printingPaused: "Printing paused. Queued jobs will wait.",
    printingResumed: "Printing resumed.",
    logout: "Log out",
    newDocument: "New document",
    fileTypes: "PDF, PNG, JPEG, TIFF, BMP, WebP or GIF",
    chooseFile: "Choose a file",
    upload: "Upload",
    uploading: "Uploading...",
    printTestPage: "Print test page",
    confirmTestPage: "Do you want to print a test page?",
    yes: "Yes",
    no: "No",
    testPageName: "Printer test page",
    builtInPage: "Built-in test page",
    documents: "Documents",
    ready: "Ready",
    queue: "Queue",
    history: "History",
    print: "Print",
    cancel: "Cancel",
    download: "Download",
    deleteFile: "Delete",
    deleteStoredFile: "Delete saved file",
    confirmDeleteFile: "Delete this history record? This only removes the file stored by the server; the print history entry will remain.",
    fileUnavailable: "The stored file has been deleted.",
    fileDeleted: "Stored file deleted. The history entry remains.",
    uploaded: "Ready to print",
    queued: "Waiting",
    printing: "Printing",
    completed: "Submitted",
    failed: "Failed",
    canceled: "Canceled",
    emptyReady: "Uploaded documents will appear here.",
    emptyQueue: "There are no documents waiting to print.",
    emptyHistory: "No print history yet.",
    oneDocument: "1 document",
    manyDocuments: "{count} documents",
    fileSelected: "Selected: {name}",
    uploadComplete: "File uploaded.",
    queuedMessage: "Document added to the print queue.",
    testPageQueued: "Test page added to the print queue.",
    canceledMessage: "Document canceled.",
    requestFailed: "The request could not be completed.",
    authentication_required: "Your session expired. Please sign in again.",
    invalid_csrf_token: "Your session expired. Please refresh the page.",
    missing_file: "Choose a file first.",
    unsupported_file_type: "This website only supports printing PDF and image files. Please convert the file to PDF before printing.",
    invalid_file: "The selected file is invalid or cannot be read.",
    empty_file: "The selected file is empty.",
    file_too_large: "The selected file is too large.",
    job_not_found: "This document no longer exists.",
    job_cannot_be_queued: "This document cannot be queued.",
    printing_job_cannot_be_canceled: "A document already printing cannot be canceled.",
    job_cannot_be_canceled: "This document cannot be canceled.",
    job_file_cannot_be_deleted: "This stored file cannot be deleted.",
    file_missing: "The stored file is missing.",
    invalid_pause_state: "The pause state is invalid.",
    printerWarning: "The printer was last active at {time}. It has been unused for {duration}. Please check the printer power status and ensure there is enough paper.",
    errorPrefix: "Error: {message}"
  },
  zh: {
    connecting: "正在连接",
    idle: "打印机空闲",
    busy: "打印机忙碌",
    disconnected: "打印机已断开",
    pausePrinting: "暂停打印",
    resumePrinting: "继续打印",
    printingPaused: "打印已暂停，排队任务将继续等待。",
    printingResumed: "打印已继续。",
    logout: "退出登录",
    newDocument: "新文档",
    fileTypes: "支持 PDF、PNG、JPEG、TIFF、BMP、WebP 或 GIF",
    chooseFile: "选择文件",
    upload: "上传",
    uploading: "上传中...",
    printTestPage: "打印测试页",
    confirmTestPage: "是否要打印测试页？",
    yes: "是",
    no: "否",
    testPageName: "打印机测试页",
    builtInPage: "内置测试页",
    documents: "文档",
    ready: "待确认",
    queue: "打印队列",
    history: "打印历史",
    print: "打印",
    cancel: "取消",
    download: "下载",
    deleteFile: "删除",
    deleteStoredFile: "删除后台文件",
    confirmDeleteFile: "是否删除该历史记录？删除历史记录仅会删除后台保存的文件，而不会删除这个打印历史表项。",
    fileUnavailable: "后台保存的文件已被删除。",
    fileDeleted: "后台文件已删除，打印历史表项仍会保留。",
    uploaded: "等待确认打印",
    queued: "排队中",
    printing: "正在打印",
    completed: "已提交",
    failed: "失败",
    canceled: "已取消",
    emptyReady: "上传后的文档会显示在这里。",
    emptyQueue: "目前没有等待打印的文档。",
    emptyHistory: "暂无打印历史。",
    oneDocument: "1 个文档",
    manyDocuments: "{count} 个文档",
    fileSelected: "已选择：{name}",
    uploadComplete: "文件上传成功。",
    queuedMessage: "文档已加入打印队列。",
    testPageQueued: "测试页已加入打印队列。",
    canceledMessage: "文档已取消。",
    requestFailed: "请求未能完成。",
    authentication_required: "登录已过期，请重新登录。",
    invalid_csrf_token: "会话已过期，请刷新页面。",
    missing_file: "请先选择文件。",
    unsupported_file_type: "本网站仅支持打印 pdf 与图片文件，请先将其转换为 pdf 格式再打印",
    invalid_file: "所选文件无效或无法读取。",
    empty_file: "所选文件为空。",
    file_too_large: "所选文件过大。",
    job_not_found: "该文档已不存在。",
    job_cannot_be_queued: "该文档无法加入队列。",
    printing_job_cannot_be_canceled: "正在打印的文档不能取消。",
    job_cannot_be_canceled: "该文档无法取消。",
    job_file_cannot_be_deleted: "该后台文件无法删除。",
    file_missing: "服务器中的文件已丢失。",
    invalid_pause_state: "暂停状态无效。",
    printerWarning: "打印机上次活跃时刻为 {time}，目前已经 {duration} 未使用，请关注线下打印机启动状态，并检查是否有足够的纸张。",
    errorPrefix: "错误：{message}"
  }
};

const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
const jobList = document.getElementById("job-list");
const fileInput = document.getElementById("file-input");
const fileLabel = document.getElementById("file-label");
const uploadButton = document.getElementById("upload-button");
const uploadForm = document.getElementById("upload-form");
const testPageButton = document.getElementById("test-page-button");
const testPageDialog = document.getElementById("test-page-dialog");
const confirmTestPageButton = document.getElementById("confirm-test-page");
const pausePrintingButton = document.getElementById("pause-printing");
const deleteFileDialog = document.getElementById("delete-file-dialog");
const confirmDeleteFileButton = document.getElementById("confirm-delete-file");
let language = preferredLanguage();
let activeTab = "ready";
let jobs = [];
let printerStatus = "disconnected";
let printingPaused = false;
let reconnectDelay = 1000;
let deleteFileJobId = null;
let deleteFileTrigger = null;

function preferredLanguage() {
  const saved = localStorage.getItem("printer-language");
  if (saved === "en" || saved === "zh") return saved;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
}

function t(key, values = {}) {
  let value = strings[language][key] || strings[language].requestFailed;
  Object.entries(values).forEach(([name, replacement]) => {
    value = value.replace(`{${name}}`, replacement);
  });
  return value;
}

function setLanguage(nextLanguage) {
  language = nextLanguage;
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === language);
    button.setAttribute("aria-pressed", String(button.dataset.lang === language));
  });
  localStorage.setItem("printer-language", language);
  updatePrinterStatus(printerStatus);
  updatePauseButton();
  renderJobs();
  updatePrinterWarning();
}

function updatePrinterStatus(status) {
  printerStatus = status;
  const light = document.getElementById("status-light");
  light.className = `status-light ${status}`;
  document.getElementById("status-label").textContent = t(status);
}

function updatePauseButton() {
  pausePrintingButton.textContent = t(
    printingPaused ? "resumePrinting" : "pausePrinting"
  );
  pausePrintingButton.classList.toggle("active", printingPaused);
  pausePrintingButton.setAttribute("aria-pressed", String(printingPaused));
}

function jobsForTab() {
  if (activeTab === "ready") return jobs.filter((job) => job.status === "uploaded");
  if (activeTab === "queue") return jobs.filter((job) => ["queued", "printing"].includes(job.status));
  return jobs.filter((job) => ["completed", "failed", "canceled"].includes(job.status));
}

function renderJobs() {
  const readyCount = jobs.filter((job) => job.status === "uploaded").length;
  const queueCount = jobs.filter((job) => ["queued", "printing"].includes(job.status)).length;
  const historyCount = jobs.filter((job) => ["completed", "failed", "canceled"].includes(job.status)).length;
  document.getElementById("ready-count").textContent = readyCount;
  document.getElementById("queue-count").textContent = queueCount;
  document.getElementById("history-count").textContent = historyCount;
  document.getElementById("job-summary").textContent = t(jobs.length === 1 ? "oneDocument" : "manyDocuments", {count: jobs.length});

  jobList.replaceChildren();
  const visibleJobs = jobsForTab();
  if (!visibleJobs.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = t(`empty${activeTab[0].toUpperCase()}${activeTab.slice(1)}`);
    jobList.append(empty);
    return;
  }
  visibleJobs.forEach((job) => jobList.append(createJobRow(job)));
}

function createJobRow(job) {
  const row = document.createElement("article");
  row.className = "job-row";

  const file = document.createElement("div");
  file.className = "job-file";
  const name = document.createElement("strong");
  const displayName = job.kind === "test_page" ? t("testPageName") : job.name;
  name.textContent = displayName;
  name.title = displayName;
  const meta = document.createElement("span");
  const fileDetail = job.kind === "test_page" ? t("builtInPage") : formatSize(job.size);
  meta.textContent = `${fileDetail} · ${formatDate(job.created_at)}`;
  file.append(name, meta);

  const status = document.createElement("span");
  const displayStatus = job.display_status || job.status;
  status.className = `job-status ${displayStatus}`;
  status.textContent = t(displayStatus);

  const detail = document.createElement("span");
  detail.className = "job-detail";
  detail.textContent = job.error ? t("errorPrefix", {message: job.error}) : formatDate(job.completed_at || job.queued_at || job.created_at);

  const actions = document.createElement("div");
  actions.className = "job-actions";
  if (job.can_print) actions.append(actionButton("print", job.id, "primary"));
  if (job.can_cancel) actions.append(actionButton("cancel", job.id, "quiet danger"));
  if (job.kind === "document" && job.status === "completed") {
    if (job.can_download) {
      const link = document.createElement("a");
      link.className = "button quiet";
      link.href = `/api/jobs/${encodeURIComponent(job.id)}/download`;
      link.textContent = t("download");
      actions.append(link);
    } else {
      const unavailableDownload = document.createElement("button");
      unavailableDownload.type = "button";
      unavailableDownload.className = "quiet unavailable";
      unavailableDownload.disabled = true;
      unavailableDownload.textContent = t("download");
      unavailableDownload.title = t("fileUnavailable");
      actions.append(unavailableDownload);
    }
    if (job.can_delete_file) {
      actions.append(actionButton("deleteFile", job.id, "quiet danger"));
    }
  }
  row.append(file, status, detail, actions);
  return row;
}

function actionButton(action, jobId, className) {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.action = action;
  button.dataset.jobId = jobId;
  button.className = className;
  button.textContent = t(action);
  return button;
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(language === "zh" ? "zh-CN" : "en", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function lastSuccessfulPrintTime() {
  let latest = null;
  jobs.forEach((job) => {
    if (job.status !== "completed" || !job.completed_at) return;
    const timestamp = new Date(job.completed_at).getTime();
    if (Number.isNaN(timestamp)) return;
    if (latest === null || timestamp > latest) latest = timestamp;
  });
  return latest;
}

function formatLastActive(timestamp) {
  const date = new Date(timestamp);
  if (language === "zh") {
    const pad = (value) => String(value).padStart(2, "0");
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatInactiveDuration(milliseconds) {
  const totalMinutes = Math.floor(milliseconds / 60000);
  const days = Math.floor(totalMinutes / 1440);
  const minutes = totalMinutes - days * 1440;
  if (language === "zh") return `${days}天 ${minutes}分钟`;
  return `${days} day${days === 1 ? "" : "s"} ${minutes} minute${minutes === 1 ? "" : "s"}`;
}

function updatePrinterWarning() {
  const warning = document.getElementById("printer-warning");
  const text = document.getElementById("printer-warning-text");
  const lastPrint = lastSuccessfulPrintTime();
  if (lastPrint === null || Date.now() - lastPrint <= 10 * 60 * 1000) {
    warning.hidden = true;
    return;
  }
  text.textContent = t("printerWarning", {
    time: formatLastActive(lastPrint),
    duration: formatInactiveDuration(Date.now() - lastPrint)
  });
  warning.hidden = false;
}

async function apiRequest(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.method && options.method !== "GET") headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(url, {...options, headers});
  let payload = {};
  try { payload = await response.json(); } catch (_) { /* empty response */ }
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("authentication_required");
  }
  if (!response.ok) throw new Error(payload.error || "requestFailed");
  return payload;
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
  socket.addEventListener("open", () => { reconnectDelay = 1000; });
  socket.addEventListener("message", (event) => {
    const snapshot = JSON.parse(event.data);
    if (snapshot.type === "authentication_required") {
      window.location.assign("/login");
      return;
    }
    if (snapshot.type !== "snapshot") return;
    updatePrinterStatus(snapshot.printer.status);
    printingPaused = Boolean(snapshot.paused);
    updatePauseButton();
    jobs = snapshot.jobs;
    renderJobs();
    updatePrinterWarning();
  });
  socket.addEventListener("close", () => {
    window.setTimeout(connectWebSocket, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 15000);
  });
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.lang));
});

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => {
    activeTab = button.dataset.tab;
    document.querySelectorAll("[data-tab]").forEach((tab) => {
      tab.setAttribute("aria-selected", String(tab === button));
    });
    renderJobs();
  });
});

pausePrintingButton.addEventListener("click", async () => {
  pausePrintingButton.disabled = true;
  try {
    const payload = await apiRequest("/api/pause", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({paused: !printingPaused})
    });
    printingPaused = payload.paused;
    updatePauseButton();
    showToast(t(printingPaused ? "printingPaused" : "printingResumed"));
  } catch (error) {
    showToast(t(error.message), true);
  } finally {
    pausePrintingButton.disabled = false;
  }
});

fileInput.addEventListener("change", () => {
  fileLabel.textContent = fileInput.files.length ? t("fileSelected", {name: fileInput.files[0].name}) : t("chooseFile");
});

uploadForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!fileInput.files.length) return showToast(t("missing_file"), true);
  uploadFile(fileInput.files[0]);
});

let dragDepth = 0;

uploadForm.addEventListener("dragenter", (event) => {
  event.preventDefault();
  dragDepth += 1;
  uploadForm.classList.add("dragging");
});

uploadForm.addEventListener("dragover", (event) => {
  event.preventDefault();
});

uploadForm.addEventListener("dragleave", (event) => {
  event.preventDefault();
  dragDepth -= 1;
  if (dragDepth <= 0) {
    dragDepth = 0;
    uploadForm.classList.remove("dragging");
  }
});

uploadForm.addEventListener("drop", (event) => {
  event.preventDefault();
  dragDepth = 0;
  uploadForm.classList.remove("dragging");
  const files = event.dataTransfer.files;
  if (!files.length) return;
  const transfer = new DataTransfer();
  transfer.items.add(files[0]);
  fileInput.files = transfer.files;
  fileLabel.textContent = t("fileSelected", {name: files[0].name});
  uploadFile(files[0]);
});

async function uploadFile(file) {
  uploadButton.disabled = true;
  uploadButton.textContent = t("uploading");
  const body = new FormData();
  body.append("file", file);
  try {
    await apiRequest("/api/uploads", {method: "POST", body});
    fileInput.value = "";
    fileLabel.textContent = t("chooseFile");
    activeTab = "ready";
    document.querySelector('[data-tab="ready"]').click();
    showToast(t("uploadComplete"));
  } catch (error) {
    showToast(t(error.message), true);
  } finally {
    uploadButton.disabled = false;
    uploadButton.textContent = t("upload");
  }
}

function openTestPageDialog() {
  testPageDialog.hidden = false;
  document.body.classList.add("modal-open");
  confirmTestPageButton.focus();
}

function closeTestPageDialog() {
  testPageDialog.hidden = true;
  document.body.classList.remove("modal-open");
  testPageButton.focus();
}

function openDeleteFileDialog(jobId, trigger) {
  deleteFileJobId = jobId;
  deleteFileTrigger = trigger;
  deleteFileDialog.hidden = false;
  document.body.classList.add("modal-open");
  confirmDeleteFileButton.focus();
}

function closeDeleteFileDialog() {
  deleteFileDialog.hidden = true;
  document.body.classList.remove("modal-open");
  deleteFileJobId = null;
  if (deleteFileTrigger?.isConnected) deleteFileTrigger.focus();
  deleteFileTrigger = null;
}

testPageButton.addEventListener("click", openTestPageDialog);
document.getElementById("cancel-test-page").addEventListener("click", closeTestPageDialog);
testPageDialog.addEventListener("click", (event) => {
  if (event.target === testPageDialog) closeTestPageDialog();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !testPageDialog.hidden) closeTestPageDialog();
  if (event.key === "Escape" && !deleteFileDialog.hidden) closeDeleteFileDialog();
});

document.getElementById("cancel-delete-file").addEventListener("click", closeDeleteFileDialog);
deleteFileDialog.addEventListener("click", (event) => {
  if (event.target === deleteFileDialog) closeDeleteFileDialog();
});

confirmDeleteFileButton.addEventListener("click", async () => {
  if (!deleteFileJobId) return;
  confirmDeleteFileButton.disabled = true;
  try {
    await apiRequest(`/api/jobs/${encodeURIComponent(deleteFileJobId)}/file`, {
      method: "DELETE"
    });
    closeDeleteFileDialog();
    showToast(t("fileDeleted"));
  } catch (error) {
    showToast(t(error.message), true);
  } finally {
    confirmDeleteFileButton.disabled = false;
  }
});

confirmTestPageButton.addEventListener("click", async () => {
  confirmTestPageButton.disabled = true;
  try {
    await apiRequest("/api/test-page", {method: "POST"});
    closeTestPageDialog();
    document.querySelector('[data-tab="queue"]').click();
    showToast(t("testPageQueued"));
  } catch (error) {
    showToast(t(error.message), true);
  } finally {
    confirmTestPageButton.disabled = false;
  }
});

jobList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  if (button.dataset.action === "deleteFile") {
    openDeleteFileDialog(button.dataset.jobId, button);
    return;
  }
  button.disabled = true;
  try {
    if (button.dataset.action === "print") {
      await apiRequest(`/api/jobs/${encodeURIComponent(button.dataset.jobId)}/print`, {method: "POST"});
      showToast(t("queuedMessage"));
    } else {
      await apiRequest(`/api/jobs/${encodeURIComponent(button.dataset.jobId)}`, {method: "DELETE"});
      showToast(t("canceledMessage"));
    }
  } catch (error) {
    showToast(t(error.message), true);
    button.disabled = false;
  }
});

document.getElementById("logout").addEventListener("click", async () => {
  try { await apiRequest("/logout", {method: "POST"}); } finally { window.location.assign("/login"); }
});

let toastTimer;
function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => { toast.hidden = true; }, 4000);
}

setLanguage(language);
window.setInterval(updatePrinterWarning, 60000);
connectWebSocket();
