// JobHunter web interface: eight screens over the Python API (window.pywebview.api).
// Opened as a plain file it falls back to demo.json, so the page can be looked at in a
// browser. Offer titles come from the web: every text goes through textContent.
"use strict";

const ICONES = {
  maison: "M4 11.2 12 4l8 7.2V19a1.5 1.5 0 0 1-1.5 1.5H15v-5h-6v5H5.5A1.5 1.5 0 0 1 4 19z",
  valise: "M9 4h6a2 2 0 0 1 2 2v1h2.5A1.5 1.5 0 0 1 21 8.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5v-10A1.5 1.5 0 0 1 4.5 7H7V6a2 2 0 0 1 2-2zm0 3h6V6H9z",
  avion: "M3.4 11.2 19.6 4.3c.8-.3 1.5.4 1.2 1.2l-6.9 16.2c-.3.8-1.5.7-1.7-.1l-1.6-6-6-1.6c-.8-.2-.9-1.4-.1-1.7z",
  cloche: "M12 3a6 6 0 0 1 6 6v3.5l1.6 2.6c.4.7-.1 1.4-.9 1.4H5.3c-.8 0-1.3-.7-.9-1.4L6 12.5V9a6 6 0 0 1 6-6zm-2.5 15h5a2.5 2.5 0 0 1-5 0z",
  doc: "M7 3h7l5 5v11.5A1.5 1.5 0 0 1 17.5 21h-10A1.5 1.5 0 0 1 6 19.5v-15A1.5 1.5 0 0 1 7 3zm6.5 1.5V9H18z",
  profil: "M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm-8 8.2C4 16.8 7.6 14 12 14s8 2.8 8 6.2c0 .4-.4.8-.8.8H4.8c-.4 0-.8-.4-.8-.8z",
  sources: "M5 4h14a2 2 0 0 1 2 2v3H3V6a2 2 0 0 1 2-2zm-2 7h18v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  cle: "M20.5 6.6 17 10.1l-3.1-3.1 3.5-3.5a5.5 5.5 0 0 0-7 7L3.6 17.3a1.9 1.9 0 0 0 2.7 2.7l6.8-6.8a5.5 5.5 0 0 0 7.4-6.6z",
  loupe: "M10.5 3a7.5 7.5 0 0 1 6 12l4.3 4.3-1.5 1.5-4.3-4.3A7.5 7.5 0 1 1 10.5 3zm0 2a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11z",
  sortie: "M14 3h7v7h-2V6.4l-8.3 8.3-1.4-1.4L17.6 5H14zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z",
  copie: "M8 3h10a2 2 0 0 1 2 2v12h-2V5H8zM5 7h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z",
  // No star nor lightning (the user, 2026-11-05: « trouve autre chose qui est plus cohérent
  // avec ce à quoi c'est lié »): each icon says what its button does.
  collecte: "M11 3h2v9.2l3.3-3.3 1.4 1.4L12 16 6.3 10.3l1.4-1.4 3.3 3.3zM4 14h2v4h12v-4h2v4.5A1.5 1.5 0 0 1 18.5 20h-13A1.5 1.5 0 0 1 4 18.5z",
  horloge: "M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm0 2a8 8 0 1 0 0 16 8 8 0 0 0 0-16zM11 7h2v4.6l3.2 3.2-1.4 1.4-3.8-3.8z",
  plume: "M16.5 3.5a2.1 2.1 0 0 1 3 0l1 1a2.1 2.1 0 0 1 0 3L9 19l-5 1.5L5.5 15.5z",
  lancer: "M8 4.5v15c0 .8.9 1.3 1.6.8l11-7.5a1 1 0 0 0 0-1.6l-11-7.5C8.9 3.2 8 3.7 8 4.5z",
  entonnoir: "M3 4h18l-7 8.5V19l-4 2v-8.5z",
  cible: "M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zm0 2a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 1.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3z",
  signet: "M6 3h12a1 1 0 0 1 1 1v17l-7-4.5L5 21V4a1 1 0 0 1 1-1z",
  graphique: "M4 13h4v7H4zm6-9h4v16h-4zm6 5h4v11h-4z",
  plus: "M11 4h2v7h7v2h-7v7h-2v-7H4v-2h7z",
  fleche: "M12 4a8 8 0 1 1-7.7 10h2.1A6 6 0 1 0 12 6V9L7.5 5 12 1z",
  dossier: "M3 6.5A1.5 1.5 0 0 1 4.5 5H9l2 2h8.5A1.5 1.5 0 0 1 21 8.5v10a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z",
  clavier: "M4 6h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2zm1 3v2h2V9zm4 0v2h2V9zm4 0v2h2V9zm4 0v2h2V9zM7 13v2h10v-2z",
  fenetre: "M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 5v9h14V9z",
  panneau: "M5 4h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm5 2v12h9V6z",
  reglage: "M3 6h9v2H3zm14 0h4v2h-4zM3 16h4v2H3zm8 0h10v2H11zM12 4h4v6h-4zM7 14h4v6H7z",
  corbeille: "M9 3h6l1 2h4v2H4V5h4zM6 9h12l-.9 10.6A1.5 1.5 0 0 1 15.6 21H8.4a1.5 1.5 0 0 1-1.5-1.4z",
};

function svg(nom) {
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  s.setAttribute("aria-hidden", "true");  // an icon beside its text: the text names it
  s.setAttribute("focusable", "false");
  const p = document.createElementNS(ns, "path");
  p.setAttribute("d", ICONES[nom] || "");
  s.appendChild(p);
  return s;
}

// h("div", {class: "x"}, "texte", enfant…) — builds an element; strings become text nodes.
function h(tag, attrs, ...enfants) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of enfants.flat(Infinity)) if (c != null && c !== false) e.append(c instanceof Node ? c : String(c));
  if (tag === "tr" && attrs && attrs.onclick) e.classList.add("cliquable");  // hover only where a click does something
  accessible(e, attrs || {});
  return e;
}

// --- Where an offer comes from (3.67) ------------------------------------------------
// The source's logo beside its name. Logos from Simple Icons (simple-icons.org, CC0,
// v13.21.0), drawn in the text's colour; a source without one gets its initial.
const LOGOS_SOURCES = {
  glassdoor: "M14.1093.0006c-.0749-.0074-.1348.0522-.1348.127v3.451c0 .0673.0537.1194.121.127 2.619.172 4.6092.9501 4.6092 3.6814H13.086a.1343.1343 0 0 0-.1348.1347v8.9644c0 .0748.06.1347.1348.1347h10.0034c.0748 0 .1347-.0599.1347-.1347V7.342c0-2.2374-.7996-4.0558-2.4159-5.3279C19.3191.8469 17.0874.1428 14.1093.0006ZM.9107 7.387a.1342.1342 0 0 0-.1347.1347v8.9566c0 .0748.06.1347.1347.1347h5.6189c0 2.7313-1.9902 3.5094-4.6091 3.6815-.0674.0075-.1192.0596-.1192.127v3.451c0 .0747.06.1343.1348.1269 2.9781-.1422 5.2078-.8463 6.6969-2.0136 1.6163-1.272 2.4159-3.0905 2.4159-5.3278V7.5217a.1343.1343 0 0 0-.1348-.1347z",
  greenhouse: "M16.279 7.13c0 1.16-.49 2.185-1.293 2.987-.891.891-2.184 1.114-2.184 1.872 0 1.025 1.65.713 3.231 2.295 1.048 1.047 1.694 2.43 1.694 4.034C17.727 21.482 15.187 24 12 24c-3.187 0-5.727-2.518-5.727-5.68 0-1.607.646-2.989 1.694-4.036 1.582-1.582 3.23-1.27 3.23-2.295 0-.758-1.292-.98-2.183-1.872-.802-.802-1.293-1.827-1.293-3.03 0-2.318 1.895-4.19 4.212-4.19.446 0 .847.067 1.181.067.602 0 .914-.268.914-.691 0-.245-.112-.557-.112-.891 0-.758.647-1.382 1.427-1.382s1.404.646 1.404 1.426c0 .825-.647 1.204-1.137 1.382-.401.134-.713.312-.713.713 0 .758 1.382 1.493 1.382 3.61zm-.446 11.19c0-2.206-1.627-3.99-3.833-3.99-2.206 0-3.833 1.784-3.833 3.99 0 2.184 1.627 3.989 3.833 3.989 2.206 0 3.833-1.808 3.833-3.99zM14.518 7.086c0-1.404-1.136-2.562-2.518-2.562S9.482 5.682 9.482 7.086 10.618 9.65 12 9.65s2.518-1.159 2.518-2.563z",
  indeed: "M11.566 21.5633v-8.762c.2553.0231.5009.0346.758.0346 1.2225 0 2.3739-.3206 3.3506-.8928v9.6182c0 .8219-.1957 1.4287-.5757 1.8338-.378.4033-.8808.6049-1.491.6049-.6007 0-1.0766-.2016-1.468-.6183-.3781-.4032-.5739-1.01-.5739-1.8184zM11.589.5659c2.5447-.8929 5.4424-.8449 7.6186.987.405.3687.8673.8334 1.0515 1.3806.2207.6913-.7695-.073-.9057-.167-.71-.4532-1.4182-.8334-2.2127-1.0946C12.8614.3873 8.8122 2.709 6.2945 6.315c-1.0516 1.5939-1.7367 3.2721-2.299 5.1174-.0614.2017-.1094.4647-.2207.6413-.1113.2036-.048-.5453-.048-.5702.0845-.7623.2438-1.4997.4414-2.237C5.3292 5.3375 7.897 2.0655 11.5891.5658zm4.9281 7.0587c0 1.6686-1.353 3.0224-3.0205 3.0224-1.6677 0-3.0186-1.3538-3.0186-3.0224 0-1.6687 1.351-3.0224 3.0186-3.0224 1.6676 0 3.0205 1.3518 3.0205 3.0224Z",
  linkedin: "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
  oracle: "M16.412 4.412h-8.82a7.588 7.588 0 0 0-.008 15.176h8.828a7.588 7.588 0 0 0 0-15.176zm-.193 12.502H7.786a4.915 4.915 0 0 1 0-9.828h8.433a4.914 4.914 0 1 1 0 9.828z",
  personio: "M21.603 24H2.47v-1.563h19.133Zm-6.167-4.044c.557.145 1.137-.244 1.303-.867.166-.624-.157-1.25-.713-1.39-.556-.142-1.137.24-1.304.865-.167.624.156 1.25.714 1.39zM22.37.676c-1.737-1.347-5.387-.43-8.145.576A41.707 41.705 0 0 0 5.64 5.625C3.624 6.985 1.135 8.987.748 10.814a1.43 1.43 0 0 0 .28 1.263c.505.59 1.354.576 1.516.568a.781.781 0 0 0 .51-1.368.783.783 0 0 0-.58-.193.877.877 0 0 1-.181-.016c.58-2.136 6.69-6.232 12.47-8.342 3.858-1.408 5.964-1.342 6.649-.81.284.22.433.487.23 1.062-.545 1.535-3.2 3.96-7.108 6.48-.725.467-1.434.898-2.11 1.29.544-1.92 1.1-3.88 1.582-5.561a.782.782 0 0 0-1.504-.43 2070.72 2070.634 0 0 0-2.002 7.05c-1.564.811-2.754 1.3-3.22 1.366a.783.783 0 0 0-1.025 1.095c.134.226.4.476.929.476.088 0 .177-.007.264-.02.54-.073 1.417-.395 2.485-.884-.758 2.702-1.373 4.975-1.407 5.282a.781.781 0 0 0 .69.858.668.668 0 0 0 .087 0 .783.783 0 0 0 .775-.685c.062-.38.822-3.133 1.746-6.42a58.241 58.239 0 0 0 4.01-2.401c5.435-3.587 7.007-5.917 7.362-7.241.277-1.02-.017-1.93-.825-2.557z",
  sap: "M0 6.064v11.872h12.13L24 6.064zm3.264 2.208h.005c.863.001 1.915.245 2.676.633l-.82 1.43c-.835-.404-1.255-.442-1.73-.467-.708-.038-1.064.215-1.069.488-.007.332.669.633 1.305.838.964.306 2.19.715 2.377 1.9L7.77 8.437h2.046l2.064 5.576-.007-5.575h2.37c2.257 0 3.318.764 3.318 2.519 0 1.575-1.09 2.514-2.936 2.514h-.763l-.01 2.094-3.588-.003-.25-.908c-.37.122-.787.189-1.23.189-.456 0-.885-.071-1.263-.2l-.358.919-2 .006.09-.462c-.029.025-.057.05-.087.074-.535.43-1.208.629-2.037.644l-.213.002a5.075 5.075 0 0 1-2.581-.675l.73-1.448c.79.467 1.286.572 1.956.558.347-.007.598-.07.761-.239a.557.557 0 0 0 .156-.369c.007-.376-.53-.553-1.185-.756-.531-.164-1.135-.389-1.606-.735-.559-.41-.825-.924-.812-1.65a1.99 1.99 0 0 1 .566-1.377c.519-.537 1.357-.863 2.363-.863zm10.597 1.67v1.904h.521c.694 0 1.247-.23 1.248-.964 0-.709-.554-.94-1.248-.94zm-5.087.767l-.748 2.362c.223.085.481.133.757.133.268 0 .52-.047.742-.126l-.736-2.37z",
  welcometothejungle: "M22.62 3.783c-1.115-1.811-4.355-2.604-6.713-.265-.132.135-.306.548.218 1.104 1.097 1.149 6.819 7.046 4.702 12.196-1.028 2.504-3.953 2.073-5.052-2.076a23.184 23.184 0 0 1-.473-9.367s.105-.394-.065-.52c-.117-.087-.305-.05-.547.33-.06.096-.048.076-.106.178l-.003.002c-1.622 2.688-3.272 5.874-4.049 7.07.38-1.803-.101-4.283-.85-6.359l-.142-.375c-.692-1.776-1.524-2.974-1.776-3.245-.03-.033-.105-.094-.353-.094H.398c-.49 0-.448.412-.293.561 1.862 2.178 7.289 10.343 4.773 18.355-.194.619.11.944.612.305 2.206-2.81 4.942-7.598 6.925-11.187-.437 1.245-.822 2.63-1.028 4.083-.435 3.064.487 5.37 1.162 6.58.345.619.803.998 1.988.824 6.045-.885 8.06-6.117 8.805-8.77 1.357-4.839.363-7.568-.722-9.33",
  xing: "M18.188 0c-.517 0-.741.325-.927.66 0 0-7.455 13.224-7.702 13.657.015.024 4.919 9.023 4.919 9.023.17.308.436.66.967.66h3.454c.211 0 .375-.078.463-.22.089-.151.089-.346-.009-.536l-4.879-8.916c-.004-.006-.004-.016 0-.022L22.139.756c.095-.191.097-.387.006-.535C22.056.078 21.894 0 21.686 0h-3.498zM3.648 4.74c-.211 0-.385.074-.473.216-.09.149-.078.339.02.531l2.34 4.05c.004.01.004.016 0 .021L1.86 16.051c-.099.188-.093.381 0 .529.085.142.239.234.45.234h3.461c.518 0 .766-.348.945-.667l3.734-6.609-2.378-4.155c-.172-.315-.434-.659-.962-.659H3.648v.016z",
};
const FAMILLES_SOURCES = [
  [/linkedin/, "linkedin"], [/glassdoor/, "glassdoor"], [/indeed/, "indeed"],
  [/wttj|welcome ?to ?the ?jungle/, "welcometothejungle"], [/greenhouse/, "greenhouse"],
  [/personio/, "personio"], [/oracle/, "oracle"], [/sfrss|successfactors/, "sap"], [/xing/, "xing"],
];
function logoSource(source) {
  const s = String(source || "").toLowerCase();
  if (!s) return null;
  const famille = (FAMILLES_SOURCES.find(([rx]) => rx.test(s)) || [])[1];
  const pastille = h("span", { class: "logo-source", "aria-hidden": "true" });
  if (famille) {
    const ns = "http://www.w3.org/2000/svg";
    const g = document.createElementNS(ns, "svg");
    g.setAttribute("viewBox", "0 0 24 24");
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", LOGOS_SOURCES[famille]);
    g.appendChild(p);
    pastille.append(g);
  } else {
    pastille.classList.add("initiale");
    // The platform's initial: "workday:pwc" is Workday, "sites-carrieres:teamtailor" Teamtailor.
    const plateforme = s.startsWith("sites-carrieres:") ? s.slice(16) : s.split(":")[0];
    pastille.textContent = (plateforme.match(/[a-z]/) || ["?"])[0].toUpperCase();
  }
  return pastille;
}

// --- Accessibility (3.67) -----------------------------------------------------------
// What a mouse can click, the keyboard reaches too (Tab, then Enter or Space), and what
// shows only an icon says its name to a screen reader.
const CLIQUABLES = new Set(["tr", "li", "div"]);
function accessible(e, attrs) {
  if (attrs.onclick && CLIQUABLES.has(e.localName) && !attrs.tabindex) {
    e.tabIndex = 0;
    if (e.localName !== "tr" && !attrs.role) e.setAttribute("role", "button");
    e.addEventListener("keydown", (ev) => {
      if (ev.target !== e || (ev.key !== "Enter" && ev.key !== " ")) return;
      ev.preventDefault();
      e.click();
    });
  }
  if (e.localName === "button" && attrs.title && !attrs["aria-label"] && !e.textContent.trim()) {
    e.setAttribute("aria-label", attrs.title);
  }
}

// The drawer is a dialog: it takes the focus when it opens, gives it back when it closes.
function suivreTiroir() {
  const t = $("tiroir");
  let avant = null;
  new MutationObserver(() => {
    const ouvert = t.classList.contains("ouvert");
    if (ouvert === (t.getAttribute("aria-hidden") === "false")) return;
    t.setAttribute("aria-hidden", ouvert ? "false" : "true");
    if (ouvert) {
      avant = document.activeElement;
      $("fermer-tiroir").focus({ preventScroll: true });
    } else if (avant && document.contains(avant)) {
      avant.focus({ preventScroll: true });
    }
  }).observe(t, { attributes: true, attributeFilter: ["class"] });
}

// A text cut by the layout shows in full in its tooltip.
document.addEventListener("mouseover", (ev) => {
  const el = ev.target.closest && ev.target.closest("td, .t, .s, .nom, dd");
  if (el && !el.title && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)) {
    el.title = el.textContent.trim();
  }
});

const $ = (id) => document.getElementById(id);

// --- Interface language (jobhunter.web.i18n) ----------------------------------------
// The page is written in French. In another language, what it shows is translated as it
// appears: text nodes, placeholders and tooltips, by exact text or by template ("{n}
// offre{s}"), the programs' output line by line. Free text (descriptions, letters, CVs)
// sits under translate="no" and is never touched.
let LANGUE = "fr";
let LOCALE = "fr-FR";
let TEXTES = new Map();
let MODELES = [];
let FIT = [];  // the fit explanation's own templates (too general for the rest)

function chargerCatalogue(c) {
  if (!c || c.langue === "fr") return;
  LANGUE = c.langue;
  LOCALE = { en: "en-GB", de: "de-DE", es: "es-ES" }[c.langue] || "fr-FR";
  document.documentElement.lang = c.langue;
  TEXTES = new Map(Object.entries(c.textes));
  const compiler = ([fr, cible]) => {
    const morceaux = fr.split(/\{(\w+)\}/);
    const noms = morceaux.filter((_, i) => i % 2);
    const fixes = morceaux.filter((_, i) => i % 2 === 0);
    const motif = new RegExp("^" + morceaux.map((m, i) => (i % 2 ? "([\\s\\S]*?)" : m.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))).join("") + "$");
    // A cheap test before the regex: the longest fixed piece must be in the text.
    return { motif, noms, cible, fixe: fixes.join("").length, lettres: /[A-Za-zÀ-ÿ]/.test(fixes.join("")), indice: fixes.reduce((a, b) => (b.length > a.length ? b : a), "") };
  };
  // Most fixed text first: "score {n}" would also match "score 1 : 0 (enregistré : 0)".
  const precis = (a, b) => b.fixe - a.fixe;
  // A template with no letter of its own ("{a} : {b}") would only copy its holes.
  MODELES = c.modeles.map(compiler).filter((m) => m.lettres).sort(precis);
  FIT = (c.fit || []).map(compiler).sort(precis);
  traduireSous(document.body);
  new MutationObserver(observerTraduction).observe(document.body,
    { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "title", "data-aide"] });
}

// One text (without its edge spaces) in the interface language, or null if unknown.
function traduction(s, modeles = MODELES) {
  const exact = TEXTES.get(s);
  if (exact !== undefined) return exact;
  for (const m of modeles) {
    if (!s.includes(m.indice)) continue;
    const r = m.motif.exec(s);
    if (!r) continue;
    const vals = Object.fromEntries(m.noms.map((n, i) => [n, r[i + 1]]));
    return m.cible.replace(/\{(\w+)\}/g, (_, n) => (n in vals ? (TEXTES.get(vals[n].trim()) ?? vals[n]) : ""));
  }
  return null;
}

// The fit explanation (scoring.fit.expliquer), line by line, as the desktop's.
const traduireFit = (texte) => (LANGUE === "fr" ? texte
  : texte.split("\n").map((l) => {
    const c = l.trim();
    const t = c ? traduction(c, FIT) : null;
    return t == null ? l : l.replace(c, t);
  }).join("\n"));

function traduire(s) {
  const coeur = s.trim();
  if (!coeur || !/[A-Za-zÀ-ÿ]/.test(coeur)) return s;
  const t = traduction(coeur);
  return t == null ? s : s.slice(0, s.indexOf(coeur)) + t + s.slice(s.indexOf(coeur) + coeur.length);
}

const ecrits = new WeakMap();  // node → the text we wrote: our own change is not redone
function traduireNoeud(n) {
  if (ecrits.get(n) === n.data) return;
  const parent = n.parentElement;
  if (!parent || parent.closest("[translate=no], script, style, textarea")) return;
  // Programs' output: one line at a time (the task panel's <pre>).
  const t = parent.closest("pre") ? n.data.split("\n").map(traduire).join("\n") : traduire(n.data);
  if (t !== n.data) n.data = t;
  ecrits.set(n, n.data);
}

function traduireAttributs(e) {
  if (e.closest("[translate=no]")) return;
  for (const a of ["placeholder", "title", "data-aide"]) {
    const v = e.getAttribute(a);
    if (v) { const t = traduire(v); if (t !== v) e.setAttribute(a, t); }
  }
}

function traduireSous(racine) {
  if (racine.nodeType === Node.TEXT_NODE) return traduireNoeud(racine);
  if (racine.nodeType !== Node.ELEMENT_NODE) return;
  traduireAttributs(racine);
  for (const e of racine.querySelectorAll("[placeholder], [title], [data-aide]")) traduireAttributs(e);
  const w = document.createTreeWalker(racine, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) traduireNoeud(n);
}

function observerTraduction(changes) {
  for (const c of changes) {
    if (c.type === "characterData") traduireNoeud(c.target);
    else if (c.type === "attributes") traduireAttributs(c.target);
    else c.addedNodes.forEach(traduireSous);
  }
}

const nombre = (n) => Number(n || 0).toLocaleString(LOCALE);
// The engine's keys, as a person reads them: « non precise », « ESG_Finance_Durable »,
// « sites-carrieres », « en_cours » showed as such on five screens (2026-11-03).
const NOMS_LISIBLES = {
  "non precise": "Non précisé", "en_cours": "En cours", linkedin: "LinkedIn", ats: "ATS",
  "sites-carrieres": "Sites carrières", wtj: "Welcome to the Jungle", efc: "eFinancialCareers",
  francetravail: "France Travail", ft: "France Travail", vie: "V.I.E", apec: "APEC", eures: "EURES",
  smartrecruiters: "SmartRecruiters", successfactors: "SuccessFactors", workday: "Workday",
  glassdoor: "Glassdoor", adzuna: "Adzuna", jooble: "Jooble", arbeitsagentur: "Arbeitsagentur",
  usajobs: "USAJOBS", hellowork: "HelloWork", indeed: "Indeed", talent: "Talent.com",
};
let NOMS_DOMAINES = {};  // the profile's domain names, from the offers screen's answer
const lisible = (v) => {
  const s = String(v ?? "");
  return NOMS_DOMAINES[s] || NOMS_LISIBLES[s.toLowerCase()] || s.replace(/_/g, " ");
};
const taille = (o) => (o < 1e6 ? `${Math.max(1, Math.round(o / 1024))} Ko` : `${(o / 1e6).toLocaleString(LOCALE, { maximumFractionDigits: 1 })} Mo`);
const JOURS = ["di", "lu", "ma", "me", "je", "ve", "sa"];
const jourCourt = (iso) => {
  const d = new Date(iso + "T12:00:00");
  if (isNaN(d)) return iso;
  const jour = LANGUE === "fr" ? JOURS[d.getDay()] : d.toLocaleDateString(LOCALE, { weekday: "short" }).replace(".", "");
  return `${jour} ${d.getDate()}`;
};
const dateFr = (iso) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "");
const classeScore = (f) => (f >= 8 ? "score" : f >= 5 ? "score moyen" : "score faible");

// --- Data access: Python when in the native window, demo.json otherwise ---------------

let DEMO = null;
async function appel(nom, ...args) {
  if (window.pywebview) return window.pywebview.api[nom](...args);
  if (!DEMO) DEMO = await (await fetch("demo.json")).json();
  return DEMO[nom] ?? null;
}

function ouvrir(url) {
  if (!url) return;
  if (window.pywebview) window.pywebview.api.ouvrir(url);
  else if (/^https?:\/\//.test(url)) window.open(url, "_blank", "noopener");
}
const ouvrirFichier = (chemin) => window.pywebview && window.pywebview.api.ouvrir_fichier(chemin);

// A short message at the bottom of the window, gone after a few seconds. `geste`:
// [label, function] — a button in the message (« Annuler »), which then stays longer.
function toast(texte, erreur = false, geste = null) {
  const t = h("div", { class: `toast ${erreur ? "erreur" : ""}`, role: erreur ? "alert" : "status" }, texte);
  if (geste) {
    const [libelle, fn] = geste;
    t.append(h("button", { class: "toast-geste", onclick: () => { t.remove(); fn(); } }, libelle));
  }
  document.body.append(t);
  const duree = geste ? 7000 : 3800;
  setTimeout(() => t.classList.add("parti"), duree);
  setTimeout(() => t.remove(), duree + 500);
}
const HORS_APPLI = "Aperçu navigateur : les actions ne tournent que dans l'application.";

// --- Tasks: one program at a time, followed in the task panel ------------------------

let minuteurTache = null;
let tacheEnCours = false;

async function lancer(cle, ident = "") {
  if (!window.pywebview) return toast(HORS_APPLI, true);
  const r = await window.pywebview.api.lancer(cle, ident);
  if (!r.ok) { toast(r.erreur, true); return false; }
  tacheMasquee = false;
  suivreTache();
  return true;
}
const action = (texte, icone, cle, classe = "") => bouton(texte, icone, () => lancer(cle), classe);

// The Outils menu (tools_catalog, the desktop's list): a program, a console, or a page.
const ACTIONS_OUTILS = {};
async function lancerOutil(libelle) {
  if (!window.pywebview) return toast(HORS_APPLI, true);
  const r = await window.pywebview.api.lancer_outil(libelle);
  if (!r.ok) return toast(r.erreur, true);
  if (r.action) return ACTIONS_OUTILS[r.action] ? ACTIONS_OUTILS[r.action]() : toast(`${libelle} : pas encore dans cette fenêtre.`, true);
  if (r.console) return toast("Une fenêtre s'est ouverte : réponds-y au clavier.");
  suivreTache();
}
function carteOutils(groupes) {
  const outil = (o) => h("button", { class: "outil-ligne", onclick: () => lancerOutil(o.libelle) },
    svg(o.genre === "console" ? "clavier" : o.genre === "action" ? "fenetre" : "lancer"),
    h("span", {}, h("span", { class: "t" }, o.nom), h("span", { class: "sous" }, o.aide)));
  const groupe = (g) => h("div", { class: `groupe-outils${g.outils.length >= 4 ? " large" : ""}` },
    h("h3", {}, g.groupe), g.outils.map(outil));
  // One-tool groups stack in one cell, where the first of them stands (style.css .pile-outils).
  const cellules = (liste) => {
    const pile = h("div", { class: "pile-outils" });
    const out = [];
    for (const g of liste) {
      if (g.outils.length > 1) out.push(groupe(g));
      else { if (!pile.childElementCount) out.push(pile); pile.append(groupe(g)); }
    }
    return out;
  };
  const simples = cellules((groupes || []).filter((g) => !g.avance));
  const avances = cellules((groupes || []).filter((g) => g.avance));
  return h("div", { class: "verre panneau large" },
    h("div", { class: "entete-panneau" }, h("h2", {}, "Outils"),
      h("span", { style: "flex:1" }),
      bouton("Ouvrir le dossier", "dossier", () => window.pywebview ? window.pywebview.api.ouvrir_dossier() : toast(HORS_APPLI, true))),
    h("div", { class: "outils" }, simples),
    avances.length ? h("details", { class: "outils-avances" }, h("summary", {}, "Diagnostic (avancé)"),
      h("div", { class: "outils" }, avances)) : null);
}

function duree(s) {
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")}`;
}
