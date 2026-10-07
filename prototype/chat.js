"use strict";
const $ = id => document.getElementById(id);
const labels = {debian: "Debian", ubuntu: "Ubuntu", fedora: "Fedora", arch: "Arch Linux"};
const releases = {
  debian: ["13", "12"],
  ubuntu: ["24.04"],
  fedora: ["версия из будущего корпуса"],
  arch: ["snapshot из будущего корпуса"]
};
const thread = $("thread"), hist = $("hist"), sample = thread.innerHTML;

function options() {
  $("release").replaceChildren(...releases[$("distribution").value].map(r => {
    const o = document.createElement("option");
    o.value = o.textContent = r;
    return o;
  }));
}
function activate(a) {
  hist.querySelectorAll("a").forEach(x => x.classList.toggle("on", x === a));
  thread.innerHTML = a.hasAttribute("data-sample") ? sample : "";
}

$("distribution").onchange = options;
options();
$("new-chat").onclick = () => $("new-dialog").showModal();
$("cancel-new").onclick = () => $("new-dialog").close();
$("new-form").onsubmit = e => {
  e.preventDefault();
  const a = document.createElement("a"), t = document.createElement("span"), s = document.createElement("small");
  a.href = "#";
  t.textContent = "Новый чат";
  s.textContent = labels[$("distribution").value] + " · " + $("release").value;
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
