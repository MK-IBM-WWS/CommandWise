"use strict";
const $ = id => document.getElementById(id);
const labels = {debian: "Debian", fedora: "Fedora", arch: "Arch Linux"};
const thread = $("thread"), hist = $("hist"), sample = thread.innerHTML;

function activate(a) {
  hist.querySelectorAll("a").forEach(x => x.classList.toggle("on", x === a));
  thread.innerHTML = a.hasAttribute("data-sample") ? sample : "";
}

$("new-chat").onclick = () => $("new-dialog").showModal();
$("cancel-new").onclick = () => $("new-dialog").close();
$("new-form").onsubmit = e => {
  e.preventDefault();
  const a = document.createElement("a"), t = document.createElement("span"), s = document.createElement("small");
  a.href = "#";
  t.textContent = "Новый чат";
  s.textContent = labels[$("distribution").value];
  a.append(t, s);
  hist.querySelector("h2").after(a);
  activate(a);
  $("new-dialog").close();
  $("question").focus();
};
hist.onclick = e => {
  const a = e.target.closest("a");
  if (a) { e.preventDefault(); activate(a); }
};
