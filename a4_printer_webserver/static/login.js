const translations = {
  en: {
    protected: "Protected printer access",
    password: "Password",
    passwordPlaceholder: "Enter password",
    signIn: "Sign in",
    invalid_password: "The password is incorrect.",
    invalid_request: "The request expired. Please try again."
  },
  zh: {
    protected: "受保护的打印机入口",
    password: "登录密码",
    passwordPlaceholder: "请输入密码",
    signIn: "登录",
    invalid_password: "密码不正确。",
    invalid_request: "请求已失效，请重试。"
  }
};

function preferredLanguage() {
  const saved = localStorage.getItem("printer-language");
  if (saved === "en" || saved === "zh") return saved;
  return navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en";
}

function setLanguage(language) {
  const strings = translations[language];
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = strings[element.dataset.i18n];
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = strings[element.dataset.i18nPlaceholder];
  });
  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.classList.toggle("active", button.dataset.lang === language);
    button.setAttribute("aria-pressed", String(button.dataset.lang === language));
  });
  const error = document.querySelector("[data-error]");
  if (error) error.textContent = strings[error.dataset.error] || strings.invalid_request;
  localStorage.setItem("printer-language", language);
}

document.querySelectorAll("[data-lang]").forEach((button) => {
  button.addEventListener("click", () => setLanguage(button.dataset.lang));
});
setLanguage(preferredLanguage());
