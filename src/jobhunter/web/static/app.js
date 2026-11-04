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
  etoile: "m12 3 2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z",
  loupe: "M10.5 3a7.5 7.5 0 0 1 6 12l4.3 4.3-1.5 1.5-4.3-4.3A7.5 7.5 0 1 1 10.5 3zm0 2a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11z",
  sortie: "M14 3h7v7h-2V6.4l-8.3 8.3-1.4-1.4L17.6 5H14zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z",
  copie: "M8 3h10a2 2 0 0 1 2 2v12h-2V5H8zM5 7h10a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z",
  eclair: "M13 2 4 14h6l-1 8 9-12h-6z",
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
    { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["placeholder", "title"] });
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
  for (const a of ["placeholder", "title"]) {
    const v = e.getAttribute(a);
    if (v) { const t = traduire(v); if (t !== v) e.setAttribute(a, t); }
  }
}

function traduireSous(racine) {
  if (racine.nodeType === Node.TEXT_NODE) return traduireNoeud(racine);
  if (racine.nodeType !== Node.ELEMENT_NODE) return;
  traduireAttributs(racine);
  for (const e of racine.querySelectorAll("[placeholder], [title]")) traduireAttributs(e);
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
    svg(o.genre === "console" ? "clavier" : o.genre === "action" ? "fenetre" : "eclair"),
    h("span", {}, h("span", { class: "t" }, o.nom), h("span", { class: "sous" }, o.aide)));
  const groupe = (g) => h("div", { class: "groupe-outils" }, h("h3", {}, g.groupe), g.outils.map(outil));
  const simples = (groupes || []).filter((g) => !g.avance);
  const avances = (groupes || []).filter((g) => g.avance);
  return h("div", { class: "verre panneau large" },
    h("div", { class: "entete-panneau" }, h("h2", {}, "Outils"),
      h("span", { style: "flex:1" }),
      bouton("Ouvrir le dossier", "dossier", () => window.pywebview ? window.pywebview.api.ouvrir_dossier() : toast(HORS_APPLI, true))),
    h("div", { class: "outils" }, simples.map(groupe)),
    avances.length ? h("details", { class: "outils-avances" }, h("summary", {}, "Diagnostic (avancé)"),
      h("div", { class: "outils" }, avances.map(groupe))) : null);
}

function duree(s) {
  return s < 60 ? `${s} s` : `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")}`;
}

// --- Activity: what runs now, in a light panel that folds -----------------------------
// The user, 2026-11-02: « un panneau dédié ou une notification repliable », not a black
// console, and no toast every nine descriptions. One panel shows the task started by a
// button and the background work, each with its progress; the details fold away.
let etatTache = null;  // api.tache()
let etatFond = null;  // api.fond_etat()
let tacheMasquee = false;  // « Fermer » on a finished task: hidden until the next one
let activiteDepliee = false;
try { activiteDepliee = localStorage.getItem("jh-activite") === "1"; } catch (_) { /* no storage */ }

// The percentage a program's output says: « [12/40] », « ── 12/40 » or « 45 % ».
function avancement(lignes) {
  for (let i = lignes.length - 1; i >= Math.max(0, lignes.length - 30); i--) {
    const l = lignes[i];
    let m = l.match(/\[(\d+)\/(\d+)\]/) || l.match(/── (\d+)\/(\d+)/);
    if (m && +m[2] > 0) return Math.min(100, Math.round((100 * m[1]) / m[2]));
    m = l.match(/(\d+(?:[.,]\d+)?) ?%/);
    if (m) return Math.min(100, Math.round(parseFloat(m[1].replace(",", "."))));
  }
  return null;
}

function jauge(pct) {
  return h("div", { class: `jauge ${pct === null ? "indet" : ""}`, role: "progressbar",
    "aria-valuemin": "0", "aria-valuemax": "100", ...(pct === null ? {} : { "aria-valuenow": String(pct) }) },
  h("i", { style: pct === null ? "" : `width:${pct}%` }));
}

function dessinerActivite() {
  const p = $("tache");
  const e = etatTache && !tacheMasquee ? etatTache : null;
  const f = etatFond && etatFond.activite;
  if (!e && !f) { p.hidden = true; return; }
  p.hidden = false;
  p.classList.toggle("fini", !!(e && e.fini) && !f);
  p.classList.toggle("echec", !!(e && e.fini && e.code !== 0));
  const lignes = [];
  if (e) {
    const pct = e.fini ? null : avancement(e.lignes);
    const etat = !e.fini ? `en cours · ${duree(e.duree)}${pct === null ? "" : ` · ${pct} %`}`
      : e.code === 0 ? `terminé en ${duree(e.duree)}`
      : e.code === 3 ? "Un autre programme écrit les offres : réessaie dans un instant"
      : "arrêté avant la fin";
    lignes.push(h("div", { class: "activite-ligne" },
      h("span", { class: "point" }),
      h("div", { class: "activite-texte" }, h("div", { class: "t" }, e.libelle), h("div", { class: "s" }, etat),
        e.fini ? null : jauge(pct)),
      e.fini
        ? h("button", { class: "bouton", onclick: () => { tacheMasquee = true; dessinerActivite(); } }, "Fermer")
        : h("button", { class: "bouton", onclick: async () => { await window.pywebview.api.arreter(); suivreTache(); } }, "Arrêter")));
  }
  if (f) {
    const pct = f.total ? Math.round((100 * f.fait) / f.total) : null;
    lignes.push(h("div", { class: "activite-ligne fond-ligne" },
      h("span", { class: "point" }),
      h("div", { class: "activite-texte" }, h("div", { class: "t" }, f.libelle),
        h("div", { class: "s" }, f.total ? `en arrière-plan · ${f.fait} sur ${f.total}` : "en arrière-plan"), jauge(pct))));
  }
  const detail = e ? e.lignes.slice(-12) : (etatFond.messages || []).map((m) => `${m.heure}  ${m.texte}`);
  const plier = h("button", { class: "lien-plier", "aria-expanded": String(activiteDepliee), onclick: () => {
    activiteDepliee = !activiteDepliee;
    try { localStorage.setItem("jh-activite", activiteDepliee ? "1" : ""); } catch (_) { /* no storage */ }
    dessinerActivite();
  } }, activiteDepliee ? (e ? "Masquer ce qu'écrit le programme" : "Masquer l'historique")
    // « Voir le détail » said nothing of what unfolds (the user, 2026-11-04: « pas clair »).
    : e ? `Voir ce qu'écrit le programme (${detail.length} dernières lignes)` : `Voir l'historique (${detail.length} messages)`);
  p.replaceChildren(...lignes,
    ...(detail.length ? [plier] : []),
    ...(detail.length && activiteDepliee ? [h("div", { class: "activite-detail" }, detail.map((l) => h("div", {}, l)))] : []));
}

async function suivreTache() {
  clearTimeout(minuteurTache);
  if (!window.pywebview) return;
  const e = await window.pywebview.api.tache();
  suivreMaj(e);
  etatTache = e;
  dessinerActivite();
  if (!e) return;
  if (!e.fini) {
    tacheEnCours = true;
    minuteurTache = setTimeout(suivreTache, 1000);
  } else if (tacheEnCours) {
    tacheEnCours = false;
    redessiner();  // the data may have changed: show it
  }
}

// The update, followed on the title bar's button and in the Moteur card: its time or
// its percentage, the last line as a tooltip, then done or failed (the user,
// 2026-10-28: « avoir un temps ou un pourcentage quand on passe la souris dessus »).
// Before, the button said « Mise à jour en cours… » for good, even after a failure.
function suivreMaj(e) {
  if (!e || e.cle !== "maj") return;
  const derniere = e.lignes[e.lignes.length - 1] || "";
  const pct = (derniere.match(/(\d+) %/) || [])[1];
  const texte = !e.fini ? (pct ? `Mise à jour… ${pct} %` : `Mise à jour… ${duree(e.duree)}`)
    : e.code === 0 ? "Mise à jour faite : relance JobHunter"
    : e.code === 3 ? "Mise à jour reportée : file occupée"
    : "Mise à jour échouée";
  const info = (e.fini ? `terminée en ${duree(e.duree)}` : `en cours · ${duree(e.duree)}`) + (derniere ? ` · ${derniere}` : "");
  const b = $("maj");
  if (b) {
    b.hidden = false;
    b.onclick = clicMaj;
    b.textContent = texte;
    b.title = info;
    b.disabled = !e.fini;
    b.classList.toggle("echec", e.fini && e.code !== 0);
    b.dataset.fait = e.fini && e.code === 0 ? "1" : "";
  }
  const m = document.querySelector(".etat-maj");
  if (m) { m.textContent = `${texte} · ${info}`; m.title = info; }
  document.querySelectorAll(".bouton-maj").forEach((x) => { x.disabled = !e.fini; });
}

// --- Guided application (the desktop's Candidatures panel, web.guided) ---------------
// The program opens each ticked offer in Chrome, fills it in and stops before sending:
// the user clicks Send in Chrome, then « J'ai envoyé » here. Nothing is sent from here.
let minuteurGuidee = null;
let envoisGuidee = 0;

async function candidatureGuidee(ids) {
  if (!window.pywebview) { toast("Disponible dans l'application seulement.", true); return; }
  const n = ids.length;
  const ok = await dialogue("Candidature guidée",
    `${n} offre${n > 1 ? "s" : ""}. Chrome ouvre chaque offre, remplit le formulaire, joint CV et lettre, puis s'arrête avant l'envoi. ` +
    "Tu vérifies et cliques « Envoyer » toi-même dans Chrome, puis « J'ai envoyé » ici. JobHunter n'envoie rien.",
    null, [["Commencer", "plein", () => true]]);
  if (!ok) return;
  const r = await window.pywebview.api.candidature_guidee(ids);
  if (!r || !r.ok) { toast((r && r.erreur) || "Lancement impossible.", true); return; }
  coches.clear();
  envoisGuidee = 0;
  redessiner();
  suivreGuidee();
}

async function commandeGuidee(cmd) {
  const r = await window.pywebview.api.candidature_commande(cmd);
  if (r && !r.ok && r.erreur) toast(r.erreur, true);
  suivreGuidee();
}

async function suivreGuidee() {
  clearTimeout(minuteurGuidee);
  if (!window.pywebview) return;
  const e = await window.pywebview.api.candidature_etat();
  const p = $("guidee");
  if (!e) { p.hidden = true; return; }
  const actif = e.attente && !e.fini;
  p.hidden = false;
  p.classList.toggle("fini", e.fini);
  p.classList.toggle("a-toi", actif);
  const zone = (z) => (e.zones[z].texte ? h("div", { class: `zone-${z} ton-${e.zones[z].ton}` }, e.zones[z].texte) : null);
  const commande = (texte, cmd, classe = "") =>
    h("button", { class: `bouton ${classe}`, disabled: !actif, onclick: () => commandeGuidee(cmd) }, texte);
  p.replaceChildren(...[  // replaceChildren writes null as text: filtered below
    h("div", { class: "tache-tete" },
      h("span", { class: "point" }),
      h("div", { style: "min-width:0;flex:1" },
        h("div", { class: "t" }, `Candidature guidée · ${e.n} offre${e.n > 1 ? "s" : ""}`),
        h("div", { class: "s" }, e.fini ? "terminée" : actif ? "à toi : vérifie dans Chrome" : "le programme travaille…")),
      e.fini
        ? h("button", { class: "bouton", onclick: () => { p.hidden = true; } }, "Fermer")
        : h("button", { class: "bouton", onclick: async () => { await window.pywebview.api.candidature_arreter(); suivreGuidee(); } }, "Arrêter")),
    zone("offre"), zone("dossier"), zone("etat"), zone("resultat"),
    e.fini ? null : h("div", { class: "boutons" },
      commande("J'ai envoyé", "envoye", "plein"), commande("Sauter", "saute"),
      commande("Re-remplir", "reremplir"), commande("Rouvrir l'offre", "rouvrir")),
    e.journal.length ? h("pre", {}, e.journal.join("\n")) : null].filter(Boolean));
  if (e.envois !== envoisGuidee) { envoisGuidee = e.envois; redessinerDonnees(); }  // the tracking was written
  if (!e.fini) minuteurGuidee = setTimeout(suivreGuidee, 800);
}

// Ctrl+Enter = « J'ai envoyé », as on the desktop panel.
document.addEventListener("keydown", (e) => {
  const p = $("guidee");
  if (e.ctrlKey && e.key === "Enter" && p && !p.hidden && p.classList.contains("a-toi")) {
    e.preventDefault();
    commandeGuidee("envoye");
  }
  // Ctrl+Z = undo the last status change, outside a text field (where it undoes typing).
  const saisie = e.target && e.target.closest && e.target.closest("input, textarea, [contenteditable]");
  if (e.ctrlKey && !e.shiftKey && (e.key === "z" || e.key === "Z") && !saisie) {
    e.preventDefault();
    annulerGeste();
  }
});

// Redraws the current screen without leaving it (the drawer stays open).
function redessiner() {
  if (courant && ECRANS[courant]) ECRANS[courant].dessiner($("vue")).catch(console.error);
}

// Redraws after a change made in the background: only the screens that show data, so
// a form being typed in (profile, sources, settings) never loses what was typed.
// The lists keep where they were scrolled to: a batch of descriptions landing must not
// send the offers list back to its top while it is being read.
async function redessinerDonnees() {
  if (!["accueil", "offres", "candidatures", "relances", "documents", "stats"].includes(courant)) return;
  const vue = $("vue");
  const defilants = () => [vue, ...vue.querySelectorAll(".defile")];
  const avant = defilants().map((e) => e.scrollTop);
  await ECRANS[courant].dessiner(vue).catch(console.error);
  defilants().forEach((e, i) => { if (avant[i]) e.scrollTop = avant[i]; });
}

// --- Application status ---------------------------------------------------------------

const STATUTS = ["à postuler", "à vérifier", "postulé", "relancé", "entretien", "refus", "mauvaise", "pas intéressé", "expiré"];
const majuscule = (s) => s[0].toUpperCase() + s.slice(1);

// A call that writes: outside the application it only says so; an error becomes a toast.
// A Python exception (corrupt file, full disk) rejects the call: a toast too, never a
// silent half-done gesture (audit 2026-10-29).
async function ecrire(nom, ...args) {
  if (!window.pywebview) { toast(HORS_APPLI, true); return null; }
  let r;
  try { r = await window.pywebview.api[nom](...args); }
  catch (e) { toast(`Échec : ${(e && e.message) || e}`, true); return null; }
  if (r && r.ok === false) { toast(r.erreur || (r.erreurs || []).join(" · "), true); return null; }
  return r;
}

async function marquer(id, statut, rouvrir = true) {
  const r = await ecrire("marquer", id, statut);
  if (!r) return;
  const n = Array.isArray(id) ? id.length : 1;
  // The promised « Annuler » is a real button now, and Ctrl+Z does the same: the toast
  // used to promise it with nothing wired to annulerGeste (audit 2026-11-03).
  toast(`${n > 1 ? `${n} offres · ` : ""}${statut ? `Statut : ${statut}` : "Statut vidé"}`, false,
    ["Annuler", annulerGeste]);
  if (rouvrir && !Array.isArray(id)) ouvrirOffre(id);
  redessiner();
}

async function annulerGeste() {
  const r = await ecrire("annuler");
  if (!r) return;
  toast(`Annulé (${r.n} offre${r.n > 1 ? "s" : ""}).`);
  redessiner();
}

// A small modal window; resolves with what a button returns, null when closed.
function dialogue(titre, sous, contenu, boutons) {
  return new Promise((fin) => {
    const fond = h("div", { class: "dialogue-fond" });
    const avant = document.activeElement;
    const fermer = (v) => {
      fond.remove();
      if (avant && document.contains(avant)) avant.focus({ preventScroll: true });
      fin(v);
    };
    fond.addEventListener("click", (e) => { if (e.target === fond) fermer(null); });
    const id = `dialogue-${Date.now()}`;
    fond.append(h("div", { class: "dialogue verre", role: "dialog", "aria-modal": "true", "aria-labelledby": id },
      h("h2", { id }, titre), sous ? h("p", { class: "sous" }, sous) : null,
      contenu,
      h("div", { class: "boutons" }, bouton("Annuler", "", () => fermer(null)),
        boutons.map(([texte, classe, valeur]) => bouton(texte, "", () => {
          const v = valeur();
          if (v !== undefined) fermer(v);
        }, classe)))));
    document.body.append(fond);
    const champ = fond.querySelector("input, textarea") || fond.querySelector(".boutons button:last-child");
    if (champ) champ.focus();
    fond.addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(null); });
  });
}

async function demanderMotif(n) {
  const motifs = (await appel("motifs")) || [];
  let choix = "";
  const libre = h("input", { class: "champ-texte", placeholder: "ou une autre raison…", oninput: () => {
    choix = libre.value.trim(); liste.querySelectorAll("button").forEach((b) => b.classList.remove("on")); } });
  const liste = h("div", { class: "motifs" }, motifs.map((m) => h("button", { class: "motif", onclick: (e) => {
    choix = m; libre.value = "";
    liste.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b === e.currentTarget)); } }, m)));
  return dialogue(`Écarter ${n} offre${n > 1 ? "s" : ""}`,
    "Retirées de la file, elles ne reviennent pas à la collecte suivante. Le motif aide à comprendre ce qui ne va pas et corrige le score.",
    h("div", {}, liste, libre),
    [["Écarter", "chaud", () => (choix ? choix : (toast("Choisis un motif.", true), undefined))]]);
}

async function ecarter(ids) {
  const motif = await demanderMotif(ids.length);
  if (!motif) return;
  const r = await ecrire("ecarter", ids, motif);
  if (!r) return;
  toast(`${r.retirees} offre(s) écartée(s) — « ${motif} ». ${r.exclusions} nouvelle(s) exclusion(s).${gardees(r)}`);
  coches.clear();
  fermerTiroir();
  redessiner();
}

// Offers with an application stay in the queue with their posting (the server keeps them).
const gardees = (r) => (r.gardees ? ` ${r.gardees} gardée(s) : elles ont une candidature.` : "");

async function ajouterOffre() {
  const champ = h("input", { class: "champ-texte", placeholder: "https://…" });
  const url = await dialogue("Ajouter une offre", "Colle le lien de l'annonce : titre, entreprise et description sont lus, puis l'offre entre dans la file.",
    champ, [["Ajouter", "plein", () => champ.value.trim() || undefined]]);
  if (!url) return;
  if (await ecrire("ajouter_offre", url)) suivreTache();
}

async function declarerEnvoi(id) {
  const ok = await dialogue("Confirmer l'envoi", "As-tu envoyé cette candidature ? Rien n'est envoyé ici : c'est noté dans le suivi.",
    null, [["Oui, je l'ai envoyée", "plein", () => true]]);
  if (!ok) return;
  if (await ecrire("declarer_envoi", id)) { toast("Candidature notée comme envoyée."); ouvrirOffre(id); redessiner(); }
}

const bouton = (texte, icone, onclick, classe = "") =>
  h("button", { class: `bouton ${classe}`, onclick }, icone ? svg(icone) : null, texte);

// « Plus… »: a list of [text, icon, action] behind one button; closes on a choice or
// on a click elsewhere. It opens in the flow, on its own line: a floating menu was cut
// by the drawer's edge in a narrow window (2026-11-03).
function plus(entrees) {
  const d = h("details", { class: "plus" }, h("summary", { class: "bouton" }, "Plus…"),
    h("div", { class: "menu-plus" }, entrees.map(([t, ic, f]) => bouton(t, ic, () => { d.open = false; f(); }))));
  const dehors = (e) => { if (!d.contains(e.target)) d.open = false; };
  d.addEventListener("toggle", () => {
    if (d.open) document.addEventListener("mousedown", dehors);
    else document.removeEventListener("mousedown", dehors);
  });
  return d;
}

function segment(options, valeur, onchange) {
  return h("div", { class: "seg" }, options.map(([v, lib]) =>
    h("button", { class: v === valeur ? "on" : "", onclick: () => onchange(v) }, lib)));
}

function pagination(d, aller, taille = null) {
  return h("div", { class: "pagination" },
    h("span", {}, `${nombre(d.total)} résultat${d.total > 1 ? "s" : ""} · page ${d.page + 1} sur ${d.pages}`),
    taille,
    h("div", { class: "seg" },
      h("button", { disabled: d.page <= 0, onclick: () => aller(d.page - 1) }, "Précédente"),
      h("button", { disabled: d.page + 1 >= d.pages, onclick: () => aller(d.page + 1) }, "Suivante")));
}

// --- Drawer: one offer --------------------------------------------------------------

function fermerTiroir() {
  $("tiroir").classList.remove("ouvert", "document", "large");
  $("voile").classList.remove("ouvert");
}

// A CV or a letter in the drawer (the user, 2026-10-27): its PDF to look at, the text of
// its .docx to change. Only the paragraphs changed are written, in place (their bold and
// italics stay); the PDF is made again from the .docx.
// `o` is the offer it was made for, or null when opened from the Documents screen.
// The PDF is shown as pictures of its pages (3.73): the web view's own PDF reader is not
// always there, and the user had to open Word to see the document. In « Modifier », the
// pages stay beside the text, and an element (a bullet, a line) is removed or added.
// `focus`: the paragraph to put the cursor in after the page is drawn again.
async function voirDocument(o, chemin, titre, mode = "apercu", focus = -1) {
  const corps = $("tiroir-corps");
  $("tiroir").classList.add("ouvert", "document");
  $("voile").classList.add("ouvert");
  const retour = o
    ? h("button", { class: "bouton", onclick: () => ouvrirOffre(o.id) }, svg("fleche"), "Retour à l'offre")
    : h("button", { class: "bouton", onclick: fermerTiroir }, svg("fleche"), "Fermer");
  corps.replaceChildren(h("div", { class: "vide" }, "Chargement…"));
  if (!window.pywebview) return corps.replaceChildren(retour, h("div", { class: "vide" }, HORS_APPLI));
  const d = await window.pywebview.api.document(chemin);
  if (!d || !d.ok) return corps.replaceChildren(retour, h("div", { class: "vide" }, d ? d.erreur : "Lecture impossible."));
  const textes = [...d.paragraphes];
  const place = h("div");
  // The document as it will be sent: its pages as pictures, else the PDF, else its text.
  const pagesDoc = () => {
    if ((d.pages || []).length) {
      return h("div", { class: "apercu-pages", "aria-label": titre },
        d.pages.map((b, i) => h("img", { src: `data:image/png;base64,${b}`, alt: `${titre}, page ${i + 1}` })));
    }
    if (d.pdf) {
      const octets = Uint8Array.from(atob(d.pdf), (c) => c.charCodeAt(0));
      const url = URL.createObjectURL(new Blob([octets], { type: "application/pdf" }));
      return h("iframe", { class: "apercu-doc", src: url, title: titre });
    }
    // No PDF (no LibreOffice): its text, without the layout.
    return h("div", {},
      h("div", { class: "sous", style: "margin-bottom:12px" }, "Aperçu du texte, sans la mise en page : installe LibreOffice (libreoffice.org) pour voir le document tel qu'il sera envoyé."),
      h("div", { class: "texte-doc" }, textes.filter((t) => t.trim()).map((t) => h("p", {}, t))));
  };
  const montrer = (m) => {
    mode = d.docx ? m : "apercu";  // a PDF alone: shown, not edited
    $("tiroir").classList.toggle("large", mode === "texte");
    onglets.replaceChildren(d.docx ? segment([["apercu", "Aperçu"], ["texte", "Modifier"]], mode, montrer) : "");
    place.classList.toggle("remplit-doc", mode === "apercu");  // style.css: the pages fill the drawer
    if (mode === "apercu") return place.replaceChildren(pagesDoc());
    const ajuster = (t) => { t.style.height = "auto"; t.style.height = `${t.scrollHeight + 2}px`; };
    const zones = [];
    const lignes = textes.map((t, i) => {
      if (!t.trim()) return null;
      const z = h("textarea", {
        class: "champ-texte para-doc", rows: 1, readonly: !d.modifiables[i], "data-i": String(i),
        title: d.modifiables[i] ? null : "Contient un lien : à modifier dans Word.",
        "aria-label": `Élément ${i + 1}`,
        oninput: (e) => { textes[i] = e.target.value.replace(/\n/g, " "); ajuster(e.target); },
      }, t);
      zones.push(z);
      return h("div", { class: "ligne-doc" }, z,
        h("div", { class: "outils-ligne" },
          h("button", { class: "mini", title: "Ajouter un élément après celui-ci", "aria-label": "Ajouter un élément après", onclick: () => structurer("ajouter", i) }, "+"),
          h("button", { class: "mini", title: "Supprimer cet élément", "aria-label": "Supprimer l'élément", onclick: () => structurer("supprimer", i) }, "×")));
    }).filter(Boolean);
    place.replaceChildren(h("div", { class: "edition-cote" },
      h("div", {},
        h("div", { class: "sous", style: "margin-bottom:10px" }, "Change un texte puis « Enregistrer » ; + ajoute un élément de même forme juste après, × le retire. Le PDF est refait à chaque fois."),
        h("div", { class: "edition-doc" }, lignes),
        h("div", { class: "boutons", style: "margin-top:12px" },
          bouton("Enregistrer", "doc", () => enregistrer(), "plein"),
          bouton("Annuler les changements", "", () => voirDocument(o, chemin, titre, "texte")))),
      h("div", { class: "cote-apercu" }, pagesDoc())));
    requestAnimationFrame(() => {
      zones.forEach(ajuster);
      const z = zones.find((x) => x.dataset.i === String(focus));
      if (z) { z.focus(); z.select(); z.scrollIntoView({ block: "center" }); }
    });
  };
  const changes = () => textes.some((t, i) => t !== d.paragraphes[i]);
  // `garder`: stay in « Modifier » (the text changes saved before a + or ×).
  const enregistrer = async (garder = false) => {
    const r = await window.pywebview.api.enregistrer_document(chemin, d.paragraphes, textes);
    if (!r || !r.ok) { toast(r ? r.erreur : "Lecture impossible.", true); return false; }
    if (!r.modifies) {
      if (r.refuses || !garder) toast(r.refuses ? "Rien n'a pu être écrit : le fichier a changé, recharge-le." : "Rien n'a changé.", !!r.refuses);
      return !r.refuses;
    }
    if (garder) return true;
    toast(`${r.modifies} paragraphe(s) modifié(s)${r.pdf ? ", PDF refait" : ", PDF non refait (LibreOffice ?)"}.`);
    voirDocument(o, chemin, titre, "texte");
    return true;
  };
  const structurer = async (action, i) => {
    if (changes() && !(await enregistrer(true))) return;
    const r = await window.pywebview.api.structurer_document(chemin, action, i, textes[i], action === "ajouter" ? "Nouvel élément" : "");
    if (!r || !r.ok) return toast(r ? r.erreur : "Lecture impossible.", true);
    if (!r.pdf) toast("PDF non refait (LibreOffice ?).", true);
    voirDocument(o, chemin, titre, "texte", action === "ajouter" ? i + 1 : -1);
  };
  const onglets = h("div");
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", { style: "min-width:0" }, h("h2", {}, titre), o ? h("div", { class: "sous" }, `${o.poste} · ${o.entreprise}`) : null)),
    h("div", { class: "boutons" }, retour, onglets, bouton("Ouvrir dans Word", "sortie", () => ouvrirFichier(d.docx))),
    place);
  montrer(mode);
}

// What to check before applying (programs/reposts, 3.67): the signals said in words, not
// only as the list's ⚑ sign. Observations: they change neither the score nor the order.
function carteSignaux(o) {
  const lignes = (o.signal || "").split(" · ").filter(Boolean).map((s) => {
    const m = s.match(/^republiée ×(\d+)/);
    if (m) return ["↻", `Republiée ${m[1]} fois en 90 jours`,
      "Une annonce remise en ligne sans cesse est souvent une offre « fantôme » (pas de recrutement en cours) ou un poste difficile à pourvoir. Vérifie sur le site de l'entreprise avant d'y passer du temps."];
    if (s.startsWith("⚠")) return ["⚠", `Condition éliminatoire : ${s.slice(1).trim()}`,
      "L'annonce l'exige explicitement : vérifie que tu la remplis."];
    const [etiquette, noms] = s.split(" : ");
    if (etiquette === "même texte") return ["≡", `Même texte chez ${noms}`,
      "Souvent un cabinet ou un site d'emploi qui reprend l'offre d'un employeur : mieux vaut postuler à la source."];
    if (etiquette === "doublon") return ["≡", `En double : ${noms}`, "La même offre sous un autre nom du même groupe."];
    return ["•", s, ""];
  });
  if (!lignes.length) return null;
  return h("div", { class: "carte signaux", role: "note" }, h("h3", {}, "À vérifier avant de postuler"),
    lignes.map(([signe, titre, aide]) => h("div", { class: "signal" },
      h("span", { class: "signe", "aria-hidden": "true" }, signe),
      h("div", {}, h("div", { class: "t" }, titre), aide ? h("div", { class: "sous" }, aide) : null))));
}

async function ouvrirOffre(id) {
  const corps = $("tiroir-corps");
  $("tiroir").classList.remove("document", "large");
  corps.replaceChildren(h("div", { class: "vide" }, "Chargement…"));
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
  const o = await appel("offre", id);
  if (!o) return corps.replaceChildren(h("div", { class: "vide" }, "Offre introuvable dans la file."));
  corps.replaceChildren(...[
    h("div", { class: "fiche-tete" },
      h("span", { class: `${classeScore(o.fit)} grand-score` }, nombre(o.fit)),
      h("div", { style: "min-width:0" }, h("h2", {}, o.poste), h("div", { class: "sous" }, o.entreprise))),
    h("div", { class: "puces" },
      [o.lieu, o.contrat !== "non precise" && o.contrat, o.zone, o.date && `publiée le ${dateFr(o.date)}`, o.suivi]
        .map((t, i) => t && h("span", { class: i === 4 ? "puce chaude" : "puce" }, t)).filter(Boolean)),
    h("div", { class: "boutons" },
      bouton("Voir l'annonce", "sortie", () => ouvrir(o.url), "plein"),
      o.cv ? bouton("CV", "doc", () => voirDocument(o, o.cv, "CV")) : null,
      o.lettre ? bouton("Lettre", "doc", () => voirDocument(o, o.lettre, "Lettre")) : null,
      bouton(o.cv ? "Refaire CV et lettre" : "Préparer CV et lettre", "eclair", () => lancer("documents", o.id)),
      ["postulé", "relancé", "entretien", "refus"].includes(o.suivi) ? null
        : bouton("J'ai envoyé cette candidature", "avion", () => declarerEnvoi(o.id), "chaud")),
    h("div", { class: "boutons secondaires" },
      ["pas intéressé", "expiré", "mauvaise"].includes(o.suivi)
        ? bouton("Finalement intéressé", "fleche", () => marquer(o.id, ""))
        : bouton("Pas intéressé", "", () => marquer(o.id, "pas intéressé")),
      ["postulé", "relancé"].includes(o.suivi) ? bouton("Brouillon de relance", "cloche", () => lancer("relance", o.id)) : null,
      // « Pas intéressé » and « Écarter… » side by side read as the same button (2026-11-03):
      // the first keeps the offer, set aside, undoable; the second takes it out of the
      // queue for good, with a reason. That one goes with the rarer actions.
      plus([
        ["Retirer de la file, avec un motif…", "", () => ecarter([o.id])],
        ["Chercher sur le web", "loupe", () => ecrire("chercher_web", o.id)],
        [o.description ? "Recharger la description" : "Récupérer la description", "fleche", () => lancer("description", o.id)],
        ["J'ai un compte sur ce site", "cle", async () => {
          const r = await ecrire("compte", o.id);
          if (r) toast(r.compte ? `Compte noté pour ${r.site}.` : `Compte retiré pour ${r.site}.`);
        }],
      ])),
    (() => {
      const st = h("select", { class: "choix" }, h("option", { value: "" }, "Pas de statut"),
        STATUTS.map((s) => h("option", { value: s, selected: s === o.suivi }, majuscule(s))));
      const note = h("textarea", { class: "champ-texte", rows: 3, placeholder: "Note (contact, impression, suite…)" }, o.note || "");
      const le = h("input", { class: "champ-texte", type: "date", value: o.postule_le || "" });
      return h("div", { class: "carte suivi-fiche" }, h("h3", {}, "Suivi"),
        h("div", { class: "champs-suivi" }, h("label", {}, "Statut", st), h("label", {}, "Date", le)),
        note,
        h("div", { class: "boutons" }, bouton("Enregistrer le suivi", "", async () => {
          const r = await ecrire("suivre", o.id, { statut: st.value, note: note.value, date: le.value });
          if (r) { toast("Suivi enregistré."); ouvrirOffre(o.id); redessiner(); }
        }, "plein"), o.envoi ? h("span", { class: "sous" }, `envoi ${o.envoi}`) : null));
    })(),
    carteSignaux(o),
    o.pourquoi ? h("div", { class: "carte description" }, h("h3", {}, "Pourquoi ce score"),
      h("div", { translate: "no" }, traduireFit(o.pourquoi))) : null,
    h("div", { class: "carte description" },
      o.description ? h("div", { translate: "no" }, o.description) : "Pas de description enregistrée pour cette offre."),
    h("dl", { class: "paires" },
      h("dt", {}, "Domaine"), h("dd", {}, o.domaine ? lisible(o.domaine) : "—"),
      h("dt", {}, "Source"), h("dd", { title: o.source, class: "avec-logo" }, logoSource(o.source), o.source ? lisible(o.source.split(":")[0]) : "—"),
      h("dt", {}, "Statut"), h("dd", {}, o.statut || "—"),
      h("dt", {}, "Score fin"), h("dd", {}, o.fit_fin ? o.fit_fin.toFixed(2) : "—"),
      h("dt", {}, "Expérience"), h("dd", {}, o.exp_requise ? `${o.exp_requise} ans` : "—"),
      h("dt", {}, "Salaire"), h("dd", {}, o.salaire || "—"),
      h("dt", {}, "Télétravail"), h("dd", {}, o.teletravail || "—")),
  ].filter(Boolean));
}

// --- Screens ------------------------------------------------------------------------

const ECRANS = {};

ECRANS.accueil = {
  titre: "Accueil",
  actions: () => [],
  async dessiner(vue) {
    const d = await appel("tableau");
    const col = d.collecte;
    const dernier = col.length ? col[col.length - 1] : { n: 0 };
    const avant = col.slice(0, -1);
    const moyenne = avant.length ? avant.reduce((s, c) => s + c.n, 0) / avant.length : 0;
    // Four steps of a round size, 1, 2, 5 or 25 times a power of ten: five distinct
    // whole ticks (an empty week showed 1, 1, 1, 0, 0), and no 0, 712, 1 424, 2 136.
    const brut = Math.max(1, Math.max(0, ...col.map((c) => c.n)) / 4);
    const puissance = 10 ** Math.floor(Math.log10(brut));
    const pas = (puissance >= 10 ? [1, 2, 2.5, 5, 10] : [1, 2, 5, 10]).map((m) => m * puissance).find((x) => x >= brut);
    const max = pas * 4;
    const pleins = [];
    const barres = h("div", { class: "barres" },
      [100, 75, 50, 25, 0].map((p) => h("div", { class: "axe", style: `top:calc(${1 - p / 100} * (100% - 22px))` },
        h("span", {}, nombre(Math.round(max * p / 100))))),
      col.map((c) => {
        const plein = h("div", { class: "plein", style: "height:0" });
        pleins.push([plein, Math.max(6, 100 * c.n / max)]);
        return h("div", { class: "col", title: `${nombre(c.n)} offres le ${dateFr(c.jour)}` },
          h("div", { class: "tube" }, plein), h("div", { class: "jour" }, jourCourt(c.jour)));
      }));

    vue.replaceChildren(h("div", { class: "accueil" },
      h("div", { class: "colonne" },
        h("div", { class: "verre stats" },
          [["valise", "Offres en file", d.stats.file], ["etoile", `Notées ${d.seuil || 8}+ à traiter`, d.stats.neuf],
           ["avion", "En attente de réponse", d.stats.postulees]].map(([ic, lab, val]) =>
            h("div", { class: "stat" }, h("span", { class: "rond" }, svg(ic)),
              h("div", {}, h("div", { class: "lab" }, lab), h("div", { class: "val" }, nombre(val)))))),
        h("div", { class: "verre kpi" },
          h("div", {},
            h("div", { class: "titre-ligne", style: "margin:0" }, h("h2", {}, "Collecte du matin"),
              h("span", { class: "etiq gris" }, "7 derniers scans")),
            h("div", { class: "grand" }, `+${nombre(dernier.n)}`),
            h("div", { class: "ecart" }, moyenne
              ? `${dernier.n >= moyenne ? "+" : "−"}${Math.abs(Math.round(100 * (dernier.n - moyenne) / moyenne))} % par rapport à la moyenne`
              : ""),
            // One or two bars draw no trend: say when the curve will come instead.
            col.length >= 3 ? barres : h("div", { class: "vide" }, "La courbe apparaîtra après trois collectes.")),
          h("div", { class: "carte liste-meilleures" },
            h("div", { class: "titre-ligne", style: "margin:0" }, h("h3", {}, "Meilleures offres")),
            h("ol", {}, d.meilleures.map((o) =>
              h("li", { onclick: () => ouvrirOffre(`${o.entreprise}|${o.poste}`), title: o.poste },
                h("span", { class: classeScore(o.fit) }, nombre(o.fit)),
                h("div", { style: "min-width:0" }, h("div", { class: "t" }, o.poste), h("div", { class: "s" }, o.entreprise))))),
            h("button", { class: "bouton", style: "margin-top:18px;width:100%;justify-content:center", onclick: () => aller("offres") }, "Toutes les offres"))),
        h("div", { class: "verre panneau" },
          h("div", { class: "titre-ligne" }, h("h2", {}, "Candidatures récentes"),
            h("button", { class: "bouton", onclick: () => aller("candidatures") }, "Tout voir")),
          tableCandidatures(d.candidatures))),
      h("div", { class: "colonne" },
        h("div", { class: "sombre" }, h("h2", {}, "À faire"),
          h("ul", { class: "fil" },
            // A free key missing: for a waiter or a nurse, most of the offers.
            d.cle_conseillee ? h("li", { onclick: () => saisirCle(d.cle_conseillee.nom, () => aller("accueil")) },
              h("div", { class: "t" }, `Ajouter la clé ${d.cle_conseillee.libelle}`),
              h("div", { class: "s" }, "Gratuite, 5 minutes : beaucoup plus d'offres")) : null,
            d.a_trier ? h("li", { onclick: () => aller("tri") },
              h("div", { class: "t" }, "Trier les nouvelles offres"),
              h("div", { class: "s" }, `${nombre(d.a_trier)} offres notées ${d.seuil || 8}+ jamais ouvertes`)) : null,
            // Offers with their CV and letter ready, not applied to yet: what to do next.
            // The follow-ups left this list (the user, 2026-11-02: « pas très importantes »).
            (d.a_postuler || []).length
            ? d.a_postuler.map((o) => h("li", { onclick: () => ouvrirOffre(`${o.entreprise}|${o.poste}`) },
                h("div", { class: "t" }, `Postuler chez ${o.entreprise}`),
                h("div", { class: "s", title: o.poste }, `${nombre(o.fit)} · ${o.poste}`)))
            : d.a_trier ? null : h("li", { class: "vide" }, "Rien à faire pour l'instant"))),
        h("div", { class: "zones" }, h("h2", {}, "Par zone"), h("div", { class: "sous", style: "margin-bottom:16px" }, `offres notées ${d.seuil || 8} et plus`),
          d.zones.map((z) => h("div", { class: "zone" },
            h("div", {}, h("div", { class: "lab" }, z.zone), h("div", { class: "val" }, nombre(z.n))),
            h("div", { class: "tuile" }, h("i", { style: `width:${z.pct}%` }), h("span", {}, `${z.pct} %`))))),
        carteDocumentsAccueil(d.documents))));
    requestAnimationFrame(() => requestAnimationFrame(() => pleins.forEach(([e, p]) => { e.style.height = `${p}%`; })));
    ajusterAccueil(vue);
  },
};

// The home screen fits the window it opens in (the user, 2026-10-28: « éviter de couper
// les widgets quand on ouvre l'app »): whole items are put away, the least useful first —
// best offers beyond three, recent applications beyond one; on the right, zones beyond
// one, tasks beyond two, then the Documents button (also in the menu) — never a panel cut
// by the window's edge. Each column for itself. In one column (narrow window) the page
// scrolls.
function ajusterAccueil(vue) {
  const accueil = vue.querySelector(".accueil");
  if (!accueil) return;
  accueil.querySelectorAll(".range").forEach((e) => e.classList.remove("range"));
  if (getComputedStyle(accueil).gridTemplateColumns.split(" ").length < 2) return;
  // The visible edge, padding included (3.67: a fixed 8 px let the left column run 7 px
  // past the bottom of a low window, whose padding is 16).
  const bas = vue.getBoundingClientRect().bottom - parseFloat(getComputedStyle(vue).paddingBottom) + vue.scrollTop;
  const apres = (col, sel, garder) => [...col.querySelectorAll(sel)].slice(garder).reverse();
  const [gauche, droite] = accueil.querySelectorAll(":scope > .colonne");
  const etapes = [
    [gauche, [...apres(gauche, ".liste-meilleures li", 3), ...apres(gauche, "tbody tr", 1)]],
    [droite, [...apres(droite, ".zones:not(.documents-accueil) .zone", 1), ...apres(droite, ".fil > li", 2),
              ...droite.querySelectorAll(".documents-accueil .boutons > :last-child")]],
  ];
  for (const [col, elements] of etapes) {
    for (const e of elements) {
      if (col.getBoundingClientRect().bottom <= bas + 1) break;
      e.classList.add("range");
    }
  }
}
window.addEventListener("resize", () => { if (courant === "accueil") ajusterAccueil($("vue")); });

// Bottom right of the home screen (the user, 2026-10-27: « remplissons le bas droit »):
// how many well-scored offers have their CV and letter, and the button to prepare more.
function carteDocumentsAccueil(d) {
  if (!d) return null;
  const pct = d.bonnes ? Math.round(100 * d.prets / d.bonnes) : 0;
  return h("div", { class: "zones documents-accueil" }, h("h2", {}, "CV et lettres"),
    h("div", { class: "sous", style: "margin-bottom:16px" }, `offres notées ${d.seuil || 8} et plus · ${nombre(d.a_preparer)} à préparer`),
    h("div", { class: "zone" },
      h("div", {}, h("div", { class: "lab" }, "Prêtes"), h("div", { class: "val" }, nombre(d.prets))),
      h("div", { class: "tuile" }, h("i", { style: `width:${pct}%` }), h("span", {}, `${pct} %`))),
    h("div", { class: "boutons", style: "margin-top:14px" },
      d.a_preparer ? action("Préparer les 30 meilleures", "eclair", "documents_top", "plein") : null,
      bouton("Documents", "doc", () => aller("documents"))));
}

function tableCandidatures(lignes) {
  if (!lignes.length) return h("div", { class: "vide" }, "Aucune candidature pour l'instant.");
  return h("table", {},
    h("colgroup", {}, h("col", { style: "width:22%" }), h("col", { style: "width:34%" }), h("col", { style: "width:14%" }), h("col", { style: "width:15%" }), h("col", {})),
    h("thead", {}, h("tr", {}, ["Entreprise", "Poste", "Statut", "Le", "Score"].map((t) => h("th", {}, t)))),
    h("tbody", {}, lignes.map((c) =>
      h("tr", { onclick: () => ouvrirOffre(`${c.entreprise}|${c.poste}`) },
        h("td", {}, c.entreprise), h("td", { title: c.poste }, c.poste),
        h("td", {}, h("span", { class: `etiq ${c.statut}` }, c.statut)), h("td", { style: "white-space:nowrap" }, dateFr(c.date)),
        h("td", {}, c.fit == null ? "—" : h("div", { class: "prog", title: `${c.fit}/10` }, h("i", { style: `width:${c.fit * 10}%` })))))));
}

const sansAccent = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
// A filter of several values (the user, 2026-10-27): a button that says what is chosen,
// and a list of boxes with Apply. The list hangs on <body>: inside the filter bar, its
// scrolling and fade (mask) would clip it. Past a dozen values, a field narrows it.
const enListe = (v) => (Array.isArray(v) ? v : v ? [v] : []);
// `noms`: the name shown for a value (a domain's key -> its trade's name, 3.74).
function listeMulti(choisis, tous, valeurs, appliquer, lien = null, noms = {}) {
  const garde = new Set(choisis);
  const nom = (v) => noms[v] || v;
  const libelle = !choisis.length ? tous
    : choisis.length <= 2 ? choisis.map(nom).join(", ") : `${nom(choisis[0])} + ${choisis.length - 1}`;
  const bouton_ = h("button", { class: `choix multi${choisis.length ? " pris" : ""}`, title: choisis.join(", ") || tous }, libelle);
  const menu = h("div", { class: "menu-cherchable menu-multi" });
  const cherche = valeurs.length > 12 ? h("input", { type: "search", class: "champ-texte", placeholder: "Chercher…", autocomplete: "off" }) : null;
  const cases = h("div", { class: "cases" });
  const remplir = () => {
    const q = cherche ? sansAccent(cherche.value.trim()) : "";
    const vus = valeurs.filter((v) => sansAccent(nom(v)).includes(q));
    cases.replaceChildren(...(vus.length ? vus.slice(0, 300).map((v) => h("label", {},
      h("input", { type: "checkbox", checked: garde.has(v), onchange: (e) => { e.target.checked ? garde.add(v) : garde.delete(v); } }),
      h("span", {}, nom(v)))) : [h("div", { class: "sous" }, "Aucun résultat")]));
  };
  const placer = (e) => {
    if (e && menu.contains(e.target)) return;
    const r = bouton_.getBoundingClientRect();
    Object.assign(menu.style, { left: `${Math.max(12, Math.min(r.left, innerWidth - menu.offsetWidth - 12))}px`, top: `${r.bottom + 6}px`, minWidth: `${Math.max(r.width, 220)}px` });
  };
  const dehors = (e) => { if (!menu.contains(e.target) && !bouton_.contains(e.target)) finir(true); };
  const clavier = (e) => {
    if (e.key === "Enter") { e.preventDefault(); finir(true); } else if (e.key === "Escape") { e.stopPropagation(); finir(false); }
  };
  const finir = (garder) => {
    menu.remove();
    document.removeEventListener("scroll", placer, true);
    document.removeEventListener("mousedown", dehors, true);
    document.removeEventListener("keydown", clavier, true);
    const choix = valeurs.filter((v) => garde.has(v));
    if (garder && (choix.length !== choisis.length || choix.some((v) => !choisis.includes(v)))) appliquer(choix);
    else { garde.clear(); choisis.forEach((v) => garde.add(v)); }
  };
  if (cherche) cherche.addEventListener("input", remplir);
  menu.append(...(cherche ? [cherche] : []), cases, ...(lien ? [h("button", { class: "lien-multi", onclick: () => { finir(false); lien[1](); } }, lien[0])] : []), h("div", { class: "pied-multi" },
    h("button", { class: "bouton", onclick: () => { garde.clear(); remplir(); } }, "Tout effacer"),
    h("button", { class: "bouton plein", onclick: () => finir(true) }, "Appliquer")));
  bouton_.addEventListener("click", () => {
    if (menu.isConnected) return finir(true);
    remplir();
    document.body.append(menu);
    placer();
    document.addEventListener("scroll", placer, true);
    document.addEventListener("mousedown", dehors, true);
    document.addEventListener("keydown", clavier, true);
    (cherche || bouton_).focus();
  });
  return bouton_;
}

const filtresOffres = { texte: "", statut: "à traiter", zone: [], domaine: [], contrat: [], pays: [], region: [], fit_min: 0, jours: 0, tri: "fit", page: 0, par_page: 40 };
// The offer's age (the user, 2026-11-04: « il n'y a pas de filtre sur la date de l'offre »):
// its publication, else the day it was seen. Days; 0 = any date.
const AGES_OFFRES = [[0, "Toutes les dates"], [1, "Dernières 24 h"], [3, "3 derniers jours"], [7, "7 derniers jours"],
  [14, "14 derniers jours"], [30, "30 derniers jours"]];
// The table's optional columns (the desktop's COLS); the offer itself is always shown.
const COLONNES_OFFRES = [
  ["lieu", "Lieu", (o) => h("span", { class: "cellule-lieu", title: o.lieu }, o.lieu || "—")],
  ["zone", "Zone", (o) => (o.zone ? h("span", { class: "etiq gris" }, o.zone) : "—")],
  ["date", "Date", (o) => dateFr(o.date) || "—"],
  ["suivi", "Suivi", (o) => (o.suivi ? h("span", { class: `etiq ${o.suivi}` }, o.suivi) : "")],
  ["domaine", "Domaine", (o) => (o.domaine ? lisible(o.domaine) : "—")],
  ["contrat", "Contrat", (o) => (o.contrat ? lisible(o.contrat) : "—")],
  ["pays", "Pays", (o) => o.pays || "—"],
  ["region", "Région", (o) => o.region || "—"],
];
const TRIS_OFFRES = [["fit", "Meilleur score"], ["entreprise", "Entreprise A → Z"]];
let vuesOffres = null;  // {vues: {name: filters}, colonnes: [...]}, read once

async function choisirColonnes() {
  const visibles = new Set(vuesOffres.colonnes);
  const cases = COLONNES_OFFRES.map(([cle, nom]) => h("label", { class: "case-colonne" },
    h("input", { type: "checkbox", checked: visibles.has(cle), onchange: (e) => { e.target.checked ? visibles.add(cle) : visibles.delete(cle); } }), nom));
  const ok = await dialogue("Colonnes", "Les colonnes montrées dans le tableau ; le choix est gardé pour la prochaine fois.",
    h("div", { class: "grille-cases" }, cases), [["Appliquer", "plein", () => (visibles.size ? true : undefined)]]);
  if (!ok) return;
  vuesOffres.colonnes = COLONNES_OFFRES.map(([c]) => c).filter((c) => visibles.has(c));
  if (window.pywebview) ecrire("memoriser_colonnes", vuesOffres.colonnes);
  redessiner();
}

async function enregistrerVue() {
  const champ = h("input", { class: "champ-texte", placeholder: "par exemple : ESG à Paris, 8+" });
  const nom = await dialogue("Enregistrer la vue", "Garde les filtres et le tri de l'écran sous un nom (même nom : remplacée).",
    champ, [["Enregistrer", "plein", () => champ.value.trim() || undefined]]);
  if (!nom) return;
  const { page, ...filtres } = filtresOffres;
  if (await ecrire("enregistrer_vue", nom, filtres)) {
    vuesOffres.vues[nom] = filtres;
    toast(`Vue « ${nom} » enregistrée.`);
    redessiner();
  }
}

function menuVues() {
  const noms = Object.keys(vuesOffres.vues).sort((a, b) => a.localeCompare(b, "fr"));
  return h("select", { class: "choix", onchange: async (e) => {
    const v = e.target.value;
    e.target.value = "";
    if (v === "+") return enregistrerVue();
    if (v.startsWith("-")) {
      const nom = v.slice(1);
      const ok = await dialogue(`Supprimer la vue « ${nom} » ?`, "Seule la vue est oubliée ; les offres ne bougent pas.", null, [["Supprimer", "chaud", () => true]]);
      if (ok && await ecrire("supprimer_vue", nom)) { delete vuesOffres.vues[nom]; redessiner(); }
      return;
    }
    if (v === "*") Object.assign(filtresOffres, { texte: "", statut: "à traiter", zone: [], domaine: [], contrat: [], pays: [], region: [], fit_min: 0, jours: 0, tri: "fit" });
    else Object.assign(filtresOffres, vuesOffres.vues[v]);
    filtresOffres.page = 0;
    redessiner();
  } },
  h("option", { value: "" }, "Vues…"),
  h("option", { value: "*" }, "Tout réinitialiser"),
  noms.map((n) => h("option", { value: n }, n)),
  h("option", { value: "+" }, "Enregistrer la vue…"),
  noms.length ? h("optgroup", { label: "Supprimer" }, noms.map((n) => h("option", { value: "-" + n }, n))) : null);
}
const coches = new Set();  // ticked offers, kept across pages (the desktop's ☐ column)
ECRANS.offres = {
  titre: "Offres",
  plein: true,
  actions: () => [
    bouton("Tri du jour", "etoile", () => aller("tri")),
    bouton("Ajouter une offre", "sortie", ajouterOffre),
    action("Vérifier les offres", "loupe", "disponibilite"),
    action("Lancer la collecte", "eclair", "collecte", "plein")],
  async dessiner(vue) {
    const f = filtresOffres;
    // No score filter any more (the user, 2026-10-27): sorted by score the 7+ / 8+ buttons
    // showed the same list. A saved view that still carries one is read without it. The
    // date filter is back (2026-11-04): the queue holds 17 000 offers, not only fresh ones.
    f.fit_min = 0;
    if (!AGES_OFFRES.some(([v]) => v === Number(f.jours))) f.jours = 0;
    if (!TRIS_OFFRES.some(([v]) => v === f.tri)) f.tri = "fit";
    const relancer = () => ECRANS.offres.dessiner(vue);
    const changer = (cle, v) => { f[cle] = v; f.page = 0; relancer(); };
    if (!vuesOffres) vuesOffres = (await appel("vues")) || { vues: {}, colonnes: ["lieu", "zone", "date", "suivi"] };
    const d = await appel("offres", { ...f });
    if (d && d.noms_domaines) NOMS_DOMAINES = d.noms_domaines;
    if (d.choisis) f.pays = d.choisis.pays;  // a country outside the chosen regions is dropped
    // A column empty on the whole page (no zone set, nothing applied to) is left out.
    const cols = COLONNES_OFFRES.filter(([c]) => vuesOffres.colonnes.includes(c)
      && (!d.lignes.length || d.lignes.some((o) => o[c])));
    let minuteur;
    const champ = h("input", { type: "search", placeholder: "Poste, entreprise, ville…", value: f.texte,
      oninput: (e) => { clearTimeout(minuteur); minuteur = setTimeout(() => changer("texte", e.target.value), 250); } });
    const liste = (cle, tous, valeurs, lien, noms) => listeMulti(enListe(f[cle]), tous, valeurs || [], (v) => changer(cle, v), lien, noms);
    // Which places are priority or secondary is the profile's search (the user could not
    // find it, 2026-10-27): the zone list leads there.
    const reglerZones = ["Régler les zones…", () => aller("profil").then(() => {
      const c = document.getElementById("zones-profil");
      if (c) c.scrollIntoView({ behavior: "smooth", block: "start" });
    })];
    const ids = () => [...coches];
    const barreSel = coches.size ? h("div", { class: "barre-selection verre" },
      h("strong", {}, `${coches.size} cochée${coches.size > 1 ? "s" : ""}`),
      bouton("Candidature guidée…", "avion", () => candidatureGuidee(ids()), "plein"),
      bouton("Pas intéressé", "", () => { marquer(ids(), "pas intéressé", false); coches.clear(); }),
      bouton("Écarter…", "", () => ecarter(ids())),
      h("select", { class: "choix", onchange: (e) => { if (e.target.value) { marquer(ids(), e.target.value === "—" ? "" : e.target.value, false); coches.clear(); } } },
        h("option", { value: "" }, "Statut…"), h("option", { value: "—" }, "Vider le statut"),
        STATUTS.map((s) => h("option", { value: s }, majuscule(s)))),
      bouton("Tout décocher", "", () => { coches.clear(); relancer(); })) : null;
    const cocher = (id, e) => { e.stopPropagation(); coches.has(id) ? coches.delete(id) : coches.add(id); relancer(); };
    const tous = d.lignes.length && d.lignes.every((o) => coches.has(o.id));
    const tri = h("select", { class: "choix", onchange: (e) => changer("tri", e.target.value) },
      TRIS_OFFRES.map(([v, l]) =>
        h("option", { value: v, selected: v === f.tri }, l)));

    vue.replaceChildren(h("div", { class: "colonne" },
      // Two aligned rows (audit 2026-10-27: ten controls wrapped into two ragged rows):
      // search and display on top, the five filters on a grid of equal columns.
      h("div", { class: "filtres-offres" },
        h("div", { class: "barre-outils" },
          h("label", { class: "champ" }, svg("loupe"), champ),
          segment(d.statuts.map((s) => [s, s[0].toUpperCase() + s.slice(1)]), f.statut, (v) => changer("statut", v)),
          tri, menuVues(), bouton("Colonnes…", "", choisirColonnes)),
        h("div", { class: "grille-filtres" },
          liste("zone", "Toutes les zones", d.zones, reglerZones), liste("domaine", "Tous les domaines", d.domaines, null, d.noms_domaines || {}), liste("contrat", "Tous les contrats", d.contrats, null, Object.fromEntries((d.contrats || []).map((c) => [c, lisible(c)]))),
          liste("region", "Toutes les régions", d.regions), liste("pays", "Tous les pays", d.pays),
          h("select", { class: `choix${f.jours ? " pris" : ""}`, "aria-label": "Date de l'offre", onchange: (e) => changer("jours", Number(e.target.value)) },
            AGES_OFFRES.map(([v, l]) => h("option", { value: v, selected: v === Number(f.jours) }, l))))),
      barreSel,
      h("div", { class: "verre panneau remplit" },
        d.lignes.length ? h("div", { class: "defile" }, h("table", {},
          h("colgroup", {}, h("col", { style: "width:36px" }), h("col", { style: "width:64px" }), h("col", { style: `width:${cols.length > 4 ? 30 : 40}%` }), cols.map(() => h("col", {}))),
          h("thead", {}, h("tr", {}, h("th", {}, h("input", { type: "checkbox", class: "coche", checked: tous, title: "Cocher la page",
            onclick: () => { d.lignes.forEach((o) => (tous ? coches.delete(o.id) : coches.add(o.id))); relancer(); } })),
            ["Score", "Offre", ...cols.map(([, nom]) => nom)].map((t) => h("th", {}, t)))),
          h("tbody", {}, d.lignes.map((o) => h("tr", { onclick: () => ouvrirOffre(o.id), class: coches.has(o.id) ? "cochee" : "" },
            h("td", { onclick: (e) => cocher(o.id, e) }, h("input", { type: "checkbox", class: "coche", checked: coches.has(o.id), "aria-label": `Cocher : ${o.poste}` })),
            h("td", {}, h("span", { class: classeScore(o.fit), title: `Score ${nombre(o.fit)} sur 10` }, nombre(o.fit))),
            h("td", {}, h("div", { class: "cellule-offre" },
              h("div", {}, h("div", { class: "t", title: o.poste }, o.alerte ? h("span", { class: "alerte", title: o.signal }, o.alerte + " ") : null, o.poste),
                h("div", { class: "s avec-logo" }, logoSource(o.source), h("span", { class: "coupe" }, o.entreprise))))),
            cols.map(([, , cellule]) => h("td", {}, cellule(o))))))))
        : h("div", { class: "vide" }, "Aucune offre ne correspond à ces filtres."),
        pagination(d, (p) => { f.page = p; relancer(); vue.scrollTop = 0; },
          h("select", { class: "choix", onchange: (e) => { changer("par_page", Number(e.target.value)); garderReglage({ par_page: f.par_page }); } },
            [20, 40, 100, 200].map((n) => h("option", { value: n, selected: n === (d.par_page || f.par_page) }, `${n} par page`)))))));
    if (f.texte) { champ.focus(); champ.setSelectionRange(f.texte.length, f.texte.length); }
  },
};

// A column shows the cards that fit in the window; the rest unfold on demand, so that no
// column has to be scrolled to find an offer (the user, 2026-10-27) and the board is not
// cut at the bottom when the screen opens (2026-10-28). Unfolded columns stay so while
// the app is open, and scroll inside themselves.
const deroulees = new Set();
function ajusterKanban(vue) {
  for (const col of vue.querySelectorAll(".colonne-k")) {
    const bouton = col.querySelector(".deplier-k");
    if (!bouton || deroulees.has(col.dataset.statut)) continue;
    const cartes = [...col.querySelectorAll(".fiche-k")];
    cartes.forEach((c) => { c.hidden = false; });
    bouton.hidden = true;
    let n = cartes.length;
    while (n > 1 && col.scrollHeight > col.clientHeight + 1) {
      cartes[--n].hidden = true;
      bouton.hidden = false;
      bouton.textContent = `Voir les ${cartes.length - n} autres`;
    }
  }
}
window.addEventListener("resize", () => { if (courant === "candidatures") ajusterKanban($("vue")); });
ECRANS.candidatures = {
  titre: "Candidatures",
  plein: true,
  actions: () => [bouton("Relances", "cloche", () => aller("relances")),
    bouton("Lire les réponses par mail", "cloche", ouvrirCourriels)],
  async dessiner(vue) {
    const d = await appel("candidatures");
    // A card dragged to another column takes its status (the user, 2026-10-27), as the
    // drawer's status list would: same undo, same date of change.
    let tiree = null;
    const cible = (c) => STATUTS.includes(c.statut) ? {
      ondragover: (ev) => { if (tiree && tiree.statut !== c.statut) { ev.preventDefault(); ev.currentTarget.classList.add("survol"); } },
      ondragleave: (ev) => { if (!ev.currentTarget.contains(ev.relatedTarget)) ev.currentTarget.classList.remove("survol"); },
      ondrop: (ev) => {
        ev.preventDefault();
        ev.currentTarget.classList.remove("survol");
        if (tiree && tiree.statut !== c.statut) marquer(tiree.id, c.statut, false);
        tiree = null;
      },
    } : {};
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "tableau-kanban" }, d.colonnes.map((c) =>
        h("div", { class: c.entrees.length ? "verre colonne-k" : "verre colonne-k vide-k", "data-statut": c.statut, ...cible(c) },
          h("div", { class: "entete" }, h("h3", {}, c.statut[0].toUpperCase() + c.statut.slice(1)),h("span", { class: "compte" }, c.entrees.length)),
          c.entrees.length ? [...c.entrees.map((e) => h("div", { class: "carte fiche-k", draggable: "true", onclick: () => ouvrirOffre(e.id),
            ondragstart: (ev) => { tiree = e; ev.dataTransfer.effectAllowed = "move"; ev.dataTransfer.setData("text/plain", e.id); ev.currentTarget.classList.add("tiree"); },
            ondragend: (ev) => { ev.currentTarget.classList.remove("tiree"); } },
            h("div", { class: "t", title: e.poste }, e.poste), h("div", { class: "s" }, e.entreprise),
            h("div", { class: "bas" }, h("span", { title: dateFr(e.date) }, e.jours != null ? `J+${e.jours}` : (dateFr(e.date) || "—")),
              e.relance_due ? h("span", { class: e.brouillon ? "etiq gris" : "etiq" }, e.brouillon ? "Brouillon prêt" : "Relance due") : null,
              e.fit == null ? null : h("div", { class: "prog", title: `${e.fit}/10` }, h("i", { style: `width:${e.fit * 10}%` }))))),
            c.entrees.length > 1 ? h("button", { class: "bouton deplier-k", onclick: () => {
              deroulees.has(c.statut) ? deroulees.delete(c.statut) : deroulees.add(c.statut);
              ECRANS.candidatures.dessiner(vue);
            } }, "Replier") : null]
          : h("div", { class: "vide" }, "Vide")))),
      d.ecartees ? h("div", { class: "sous" }, `${d.ecartees} offres écartées (mauvaise, pas intéressé, expirée) ne sont pas montrées.`) : null));
    ajusterKanban(vue);
  },
};

// The daily triage (3.80): the good offers never opened, one at a time, best first.
// Opening one marks it seen (api.offre), so the next draw shows the next one.
let triGeste = null;
ECRANS.tri = {
  titre: "Tri du jour",
  actions: () => [bouton("Toutes les offres", "", () => aller("offres"))],
  async dessiner(vue) {
    triGeste = null;
    const d = await appel("a_trier");
    const id = d && d.ids[0];
    const o = id ? await appel("offre", id) : null;
    if (courant !== "tri") return;
    if (!o) {
      vue.replaceChildren(h("div", { class: "tri" }, h("div", { class: "verre panneau tri-fin" },
        h("h2", {}, "Tri terminé"),
        h("p", { class: "sous" }, "Plus de nouvelle offre bien notée à regarder. La prochaine collecte en apportera d'autres."),
        h("div", { class: "boutons" }, bouton("Voir les offres", "", () => aller("offres"), "plein")))));
      return;
    }
    const garder = () => redessiner();
    const rejeter = () => marquer(id, "pas intéressé", false);
    triGeste = { garder, rejeter };
    vue.replaceChildren(h("div", { class: "tri" },
      h("div", { class: "sous" }, `${nombre(d.total)} à trier · → ou Entrée : garder · X : pas intéressé`),
      h("div", { class: "verre panneau tri-carte" },
        h("div", { class: "fiche-tete" },
          h("span", { class: `${classeScore(o.fit)} grand-score` }, nombre(o.fit)),
          h("div", { style: "min-width:0" }, h("h2", {}, o.poste), h("div", { class: "sous" }, o.entreprise))),
        h("div", { class: "puces" },
          [o.lieu, o.contrat !== "non precise" && lisible(o.contrat), o.zone, o.date && `publiée le ${dateFr(o.date)}`]
            .filter(Boolean).map((t) => h("span", { class: "puce" }, t))),
        o.pourquoi ? h("div", { class: "carte description" }, h("h3", {}, "Pourquoi ce score"),
          h("div", { translate: "no" }, traduireFit(o.pourquoi))) : null,
        h("div", { class: "carte description tri-texte" },
          o.description ? h("div", { translate: "no" }, o.description) : "Pas de description enregistrée pour cette offre."),
        h("div", { class: "boutons" },
          bouton("Garder", "fleche", garder, "plein"),
          bouton("Pas intéressé", "", rejeter),
          bouton(o.cv ? "Refaire CV et lettre" : "Préparer CV et lettre", "eclair", async () => { await lancer("documents", id); garder(); }),
          bouton("Voir l'annonce", "sortie", () => ouvrir(o.url)),
          plus([
            ["Retirer de la file, avec un motif…", "", () => ecarter([id])],
            ["Tout le détail", "doc", () => ouvrirOffre(id)],
          ])))));
  },
};
document.addEventListener("keydown", (e) => {
  if (courant !== "tri" || !triGeste || e.ctrlKey || e.altKey || e.metaKey) return;
  if (e.target && e.target.closest && e.target.closest("input, textarea, select, [contenteditable], button, summary")) return;
  if ($("tiroir").classList.contains("ouvert") || document.querySelector(".dialogue")) return;
  const geste = e.key === "ArrowRight" || e.key === "Enter" ? triGeste.garder
    : e.key === "x" || e.key === "X" ? triGeste.rejeter : null;
  if (!geste) return;
  e.preventDefault();
  triGeste = null;  // one key, one offer: a held key does not run through the list
  geste();
});

ECRANS.relances = {
  titre: "Relances",
  // Held in the window: the lists and the draft scroll inside their panels (2026-10-28).
  plein: true,
  actions: () => [action("Écrire les brouillons du jour", "eclair", "brouillons", "plein")],
  async dessiner(vue) {
    const d = await appel("relances");
    const apercu = h("div", { class: "carte apercu" }, h("div", { class: "vide" }, "Choisis un brouillon pour le lire."));
    const copier = h("button", { class: "bouton", disabled: true }, svg("copie"), "Copier le texte");
    let texte = "";
    copier.onclick = async () => {
      try { await navigator.clipboard.writeText(texte); copier.lastChild.textContent = "Copié"; } catch (e) { console.error(e); }
    };
    const lignes = d.brouillons.map((b) => {
      const l = h("div", { class: "ligne-brouillon", title: b.nom },
        h("div", { style: "min-width:0" }, h("div", { class: "t" }, b.titre.replace(/^Relance J(\d+) /, "")), h("div", { class: "s" }, `J+${(b.nom.match(/^Relance_J(\d+)/) || [])[1] || "?"} · ${dateFr(b.date)}`)));
      l.onclick = async () => {
        lignes.forEach((x) => x.classList.remove("on"));
        l.classList.add("on");
        texte = (await appel("brouillon", b.nom)) || "";
        apercu.replaceChildren(texte ? h("div", { translate: "no" }, texte) : h("div", { class: "vide" }, "Brouillon vide ou illisible."));
        copier.disabled = !texte;
        copier.lastChild.textContent = "Copier le texte";
      };
      return l;
    });
    vue.replaceChildren(h("div", { class: "relances" },
      h("div", { class: "colonne" },
        h("div", { class: "sombre" }, h("h2", {}, "À relancer"), h("div", { class: "sous", style: "color:#8f8783" }, "postulées depuis 7 jours et plus"),
          h("ul", { class: "fil" }, d.dues.length
            ? d.dues.map((r) => h("li", { onclick: () => ouvrirOffre(`${r.entreprise}|${r.poste}`) },
                h("div", { class: "t" }, r.entreprise), h("div", { class: "s", title: r.poste }, `${r.jours} j · ${r.poste}`)))
            : h("li", { class: "vide" }, "Rien à relancer")))),
      h("div", { class: "relances-droite" },
        h("div", { class: "verre panneau" },
          h("div", { class: "titre-ligne" }, h("h2", {}, "Brouillons"), h("span", { class: "compte" }, d.brouillons.length)),
          h("div", { class: "liste-brouillons" }, lignes.length ? lignes : h("div", { class: "vide" }, "Aucun brouillon."))),
        h("div", { class: "colonne" },
          apercu,
          h("div", { class: "boutons" }, copier),
          h("div", { class: "sous" }, "L'envoi reste ton geste : copie, relis, envoie depuis ta messagerie.")))));
  },
};

const filtresDocs = { texte: "", genre: "", en_cours: false, page: 0 };
ECRANS.documents = {
  titre: "Documents",
  plein: true,
  // After a change of template, the documents already made are made again (the user,
  // 2026-10-27: the letters need the same tool as the CVs).
  // Shown only when there is something to redo (the user, 2026-10-28: the buttons
  // were there, and did nothing, before the first document).
  actions: () => [],
  async dessiner(vue) {
    const f = filtresDocs;
    const relancer = () => ECRANS.documents.dessiner(vue);
    const d = await appel("documents", { ...f });
    const ex = d.existants || {};
    if (courant === "documents") $("actions").replaceChildren(
      ex.CV ? action("Refaire les CV", "fleche", "regenerer_cv") : "",
      ex.Lettre ? action("Refaire les lettres", "fleche", "regenerer_lettres") : "");
    let minuteur;
    const champ = h("input", { type: "search", placeholder: "Entreprise, poste…", value: f.texte,
      oninput: (e) => { clearTimeout(minuteur); minuteur = setTimeout(() => { f.texte = e.target.value; f.page = 0; relancer(); }, 250); } });
    // A click shows the document and lets its text be changed, as from an offer; the PDF
    // is made again from the .docx, which stays the file to edit (the user, 2026-10-27).
    const voir = (x) => (x.modifiable ? voirDocument(null, x.chemin, `${x.genre} · ${x.nom}`) : ouvrirFichier(x.chemin));
    const dossiers = (d.dossiers || []).map((x) => bouton(x.genre === "CV" ? "Dossier des CV" : "Dossier des lettres", "sortie",
      () => ecrire("ouvrir_dossier_documents", x.genre)));
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "barre-outils" }, h("label", { class: "champ", style: "max-width:460px" }, svg("loupe"), champ),
        segment([["", "Tous"], ["CV", "CV"], ["Lettre", "Lettres"]], f.genre, (v) => { f.genre = v; f.page = 0; relancer(); }),
        segment([["", "Toutes les offres"], ["oui", "Candidatures envoyées"]], f.en_cours ? "oui" : "", (v) => { f.en_cours = !!v; f.page = 0; relancer(); }),
        ...dossiers,
        h("span", { class: "sous", title: (d.dossiers || []).map((x) => x.chemin).join(" · ") }, `${nombre(d.total)} documents`)),
      h("div", { class: "verre panneau remplit" },
        d.fichiers.length ? h("div", { class: "defile" }, h("table", {},
          h("colgroup", {}, h("col", { style: "width:12%" }), h("col", {}), h("col", { style: "width:16%" }), h("col", { style: "width:14%" })),
          h("thead", {}, h("tr", {}, ["Type", "Document", "Offre", "Le"].map((t) => h("th", {}, t)))),
          h("tbody", {}, d.fichiers.map((x) => h("tr", { onclick: () => voir(x), title: x.modifiable ? "Voir et modifier" : "Ouvrir" },
            h("td", {}, h("span", { class: x.genre === "CV" ? "etiq" : "etiq gris" }, x.genre)),
            h("td", { title: x.nom }, x.nom),
            // The offer it was made for, with its status: a click opens it.
            h("td", {}, x.offre ? h("button", { class: "lien", title: "Ouvrir l'offre",
              onclick: (e) => { e.stopPropagation(); ouvrirOffre(x.offre); } },
              x.statut ? majuscule(x.statut) : "Ouvrir") : "—"),
            h("td", {}, dateFr(x.date)))))))
        : (ex.CV || ex.Lettre) ? h("div", { class: "vide" }, f.en_cours ? "Aucun document d'une candidature envoyée." : "Aucun document pour cette recherche.")
        : premiersDocuments(),
        d.fichiers.length ? pagination(d, (p) => { f.page = p; relancer(); vue.scrollTop = 0; }) : null)));
    if (f.texte) { champ.focus(); champ.setSelectionRange(f.texte.length, f.texte.length); }
  },
};

// No document yet: what makes them, and the two buttons to get there (the user,
// 2026-10-28: « si aucun document créé, explique ce qu'il faut faire »).
function premiersDocuments() {
  return h("div", { class: "premiers-docs" },
    h("h2", {}, "Pas encore de CV ni de lettre"),
    h("p", { class: "sous" }, "JobHunter écrit un CV et une lettre sur mesure pour chaque offre bien notée (8 et plus), à partir de ton CV de base et de ton profil."),
    h("ol", {},
      h("li", {}, "Trouve des offres : « Lancer la collecte » (quelques minutes)."),
      h("li", {}, "Prépare les documents : « Préparer des CV et lettres… », ou depuis une offre."),
      h("li", {}, "Relis-les ici : un clic ouvre le document pour le lire ou modifier son texte.")),
    h("div", { class: "boutons" },
      action("Lancer la collecte", "eclair", "collecte", "plein"),
      bouton("Préparer des CV et lettres…", "doc", () => ACTIONS_OUTILS.documents())));
}

const carte = (titre, ...contenu) => h("div", { class: "verre panneau" }, h("div", { class: "titre-ligne" }, h("h2", {}, titre)), ...contenu);
const puces = (liste, classe = "puce") => liste.length
  ? h("div", { class: "puces" }, liste.map((t) => h("span", { class: classe }, t)))
  : h("div", { class: "sous" }, "—");

// --- Editing: chips, places, save bar --------------------------------------------------

// Calls an API method that writes; in the browser preview, says it cannot.
// A list of words edited in place: × removes, Enter adds. A long list shows its first
// fifteen; what is typed also filters, so a word is found among two hundred.
const PUCES_MAX = 15;
function editeurPuces(liste, sale, placeholder = "Ajouter…") {
  const boite = h("div", { class: "puces-edit" });
  let filtre = "";
  let tout = false;
  const dessiner = (focus = false) => {
    const champ = h("input", {
      placeholder, value: filtre,
      title: liste.length > PUCES_MAX ? "Entrée ajoute le mot ; taper filtre la liste" : "",
      oninput: (e) => { filtre = e.target.value; dessiner(true); },
      onkeydown: (e) => {
        const v = e.target.value.trim();
        if (e.key === "Enter" && v) {
          e.preventDefault();
          if (!liste.some((x) => x.toLowerCase() === v.toLowerCase())) { liste.push(v); sale(); }
          filtre = "";
          dessiner(true);
        } else if (e.key === "Backspace" && !e.target.value && liste.length && liste.length <= PUCES_MAX) {
          liste.pop(); sale(); dessiner(true);
        }
      },
    });
    const f = filtre.trim().toLowerCase();
    const vus = liste.map((x, i) => [x, i]).filter(([x]) => !f || x.toLowerCase().includes(f) || motLisible(x).toLowerCase().includes(f));
    const montres = f || tout ? vus : vus.slice(0, PUCES_MAX);
    const reste = vus.length - montres.length;
    boite.replaceChildren(...montres.map(([x, i]) => h("span", { class: "puce modifiable", title: x }, motLisible(x),
      h("button", { title: "Retirer", onclick: () => { liste.splice(i, 1); sale(); dessiner(); } }, "×"))),
      reste ? h("button", { class: "lien", onclick: () => { tout = true; dessiner(); } }, `+ ${reste} autres`)
        : tout && !f && liste.length > PUCES_MAX ? h("button", { class: "lien", onclick: () => { tout = false; dessiner(); } }, "Replier") : "",
      champ);
    if (focus) { champ.focus(); champ.selectionStart = champ.selectionEnd = champ.value.length; }
  };
  dessiner();
  return boite;
}

// Places: chips of {entree, libelle}, and a field that suggests places as you type.
const GENRES_LIEU = { ville: "ville et alentours", region: "région" };
function editeurLieux(liste, sale) {
  // A region holds its cities, a city does not hold its region: each choice says which.
  const genre = (x) => (GENRES_LIEU[x.genre] ? h("span", { class: "genre-lieu" }, GENRES_LIEU[x.genre]) : null);
  const boite = h("div", { class: "puces-edit lieux" });
  const suggestions = h("div", { class: "suggestions" });
  let minuteur;
  const dessiner = (focus = false) => {
    const champ = h("input", {
      placeholder: "Ville, région, pays…",
      oninput: (e) => {
        clearTimeout(minuteur);
        const q = e.target.value;
        minuteur = setTimeout(async () => {
          const r = q.trim().length < 2 ? [] : (await appel("lieux", q)) || [];
          suggestions.replaceChildren(...r.map((s) => h("button", {
            onclick: () => {
              const cle = JSON.stringify(s.entree).toLowerCase();
              if (!liste.some((x) => JSON.stringify(x.entree).toLowerCase() === cle)) { liste.push(s); sale(); }
              suggestions.replaceChildren();
              dessiner(true);
            },
          }, s.libelle, genre(s))));
        }, 200);
      },
      onkeydown: (e) => {
        if (e.key === "Enter") { e.preventDefault(); suggestions.querySelector("button")?.click(); }
        if (e.key === "Escape") suggestions.replaceChildren();
      },
    });
    boite.replaceChildren(...liste.map((x, i) => h("span", { class: "puce modifiable chaude" }, x.libelle, genre(x),
      h("button", { title: "Retirer", onclick: () => { liste.splice(i, 1); sale(); dessiner(); } }, "×"))), champ);
    if (focus) champ.focus();
  };
  dessiner();
  return h("div", { class: "lieux-boite" }, boite, suggestions);
}

// "Enregistrer" + a message; enabled once something changed.
function barreEnregistrer(enregistrer) {
  const msg = h("span", { class: "sous" });
  const b = h("button", { class: "bouton plein", disabled: true }, "Enregistrer");
  b.onclick = async () => {
    b.disabled = true;
    msg.textContent = "Enregistrement…";
    let r = null;
    try { r = await enregistrer(); }
    catch (e) { r = { ok: false, erreur: `Échec : ${(e && e.message) || e}` }; }
    if (r && r.ok) {
      msg.textContent = r.message || "Enregistré.";
    } else {
      msg.textContent = "";
      b.disabled = false;
      if (r) toast((r.erreurs || [r.erreur]).join(" · "), true);
    }
  };
  return {
    el: h("div", { class: "barre-enreg" }, b, msg),
    sale: () => { b.disabled = false; msg.textContent = "Modifications non enregistrées"; },
  };
}

const sousTitre = (t, marge = "16px 0 8px") => h("div", { class: "sous", style: `margin:${marge}` }, t);
const avecBak = (r) => r && r.ok ? { ...r, message: "Enregistré (l'ancienne version est gardée)." } : r;

ECRANS.profil = {
  titre: "Profil",
  actions: () => [
    bouton("Gérer les profils", "profil", gererProfils, "plein"),
    bouton("Profil avancé", "doc", profilAvance)],
  async dessiner(vue) {
    const [p, rech, comp] = await Promise.all([appel("profil"), appel("recherche"), appel("competences")]);

    // Identity and languages.
    const id = { ...p.identite, langues: [...p.langues] };
    const bId = barreEnregistrer(() => ecrire("enregistrer_identite", id).then(avecBak));
    const champ = (cle, lib) => h("label", { class: "champ-form" }, h("span", {}, lib),
      h("input", { value: id[cle] || "", oninput: (e) => { id[cle] = e.target.value; bId.sale(); } }));
    const carteId = h("div", { class: "verre panneau" },
      h("div", { class: "identite" }, h("span", { class: "avatar" }, (id.prenom || "?")[0]),
        h("div", { style: "min-width:0" }, h("div", { class: "nom" }, `${id.prenom} ${id.nom}`), h("div", { class: "sous" }, id.ville))),
      h("div", { class: "formulaire" }, champ("prenom", "Prénom"), champ("nom", "Nom"), champ("ville", "Ville"),
        champ("email", "Mail"), champ("linkedin", "LinkedIn")),
      sousTitre("Langues parlées (codes : fr, en, de…)"), editeurPuces(id.langues, bId.sale, "code…"),
      bId.el);

    // The search: keywords, titles, places.
    const r = rech || { mots_cles: [], garder: [], ecarter: [], prioritaires: [], secondaires: [] };
    const bR = barreEnregistrer(async () => {
      const res = await ecrire("enregistrer_recherche", r);
      if (res && res.ok) {
        res.message = "Enregistré (l'ancienne version est gardée). Effet à la prochaine collecte."
          + (res.zones ? " Zones des offres en cours de mise à jour." : "");
        if (res.zones) suivreTache();
      }
      return res;
    });
    const carteRech = h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Ma recherche")),
      h("div", { class: "deux-colonnes" },
        h("div", {},
          sousTitre(`Mots-clés de collecte · ${r.mots_cles.length}`, "0 0 8px"), editeurPuces(r.mots_cles, bR.sale, "nouveau mot-clé…"),
          Object.assign(sousTitre("Zones prioritaires"), { id: "zones-profil" }), editeurLieux(r.prioritaires, bR.sale),
          sousTitre("Zones secondaires"), editeurLieux(r.secondaires, bR.sale)),
        h("div", {},
          sousTitre("Intitulés à garder (un mot du titre suffit ; * = début de mot ; re: = motif)", "0 0 8px"), editeurPuces(r.garder, bR.sale, "mot d'intitulé…"),
          sousTitre("Intitulés à écarter"), editeurPuces(r.ecarter, bR.sale, "mot à écarter…"))),
      bR.el);

    // Skills: words searched in the postings, and the axes they count for.
    const liste = comp ? comp.liste : [];
    const axes = comp ? comp.axes : [];
    const corps = h("div", { class: "liste-comp" });
    const bC = barreEnregistrer(async () => {
      const res = avecBak(await ecrire("enregistrer_competences", liste));
      if (res && res.ok) {
        // The axes of the offers changed: their fit follows only once recomputed.
        if (!bC.el.querySelector(".rescore")) bC.el.append(bouton("Recalculer les scores", "fleche", () => lancer("rescore"), "rescore"));
      }
      return res;
    });
    const dessinerComp = () => corps.replaceChildren(...liste.map((c, i) => h("div", { class: "ligne-comp" },
      h("div", { class: "nom-comp" }, c.nom, c.base ? h("span", { class: "etiq gris", title: "Compétence de base du CV" }, "base") : null),
      h("div", { class: "axes-comp" }, axes.map((a) => h("button", {
        class: `bascule ${c.axes.includes(a) ? "on" : ""}`,
        title: "Compte pour cet axe du score",
        onclick: () => { c.axes = c.axes.includes(a) ? c.axes.filter((x) => x !== a) : [...c.axes, a]; bC.sale(); dessinerComp(); },
      }, a))),
      editeurPuces(c.synonymes, bC.sale, "mot cherché…"),
      c.base ? h("span") : h("button", { class: "retirer", title: "Retirer la compétence", onclick: () => { liste.splice(i, 1); bC.sale(); dessinerComp(); } }, "×"))));
    dessinerComp();
    const nouvelle = h("input", { placeholder: "Nouvelle compétence…", onkeydown: (e) => {
      const v = e.target.value.trim();
      if (e.key !== "Enter" || !v) return;
      if (liste.some((c) => c.nom.toLowerCase() === v.toLowerCase())) return toast("Elle existe déjà.", true);
      liste.push({ nom: v, axes: [], synonymes: [v.toLowerCase()], en: "", base: false });
      e.target.value = "";
      bC.sale();
      dessinerComp();
    } });
    const carteComp = h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Compétences"), h("span", { class: "compte" }, liste.length)),
      h("div", { class: "sous", style: "margin:-6px 0 14px" }, "Les mots cherchés dans les annonces, et les axes du score pour lesquels chaque compétence compte."),
      corps,
      h("label", { class: "champ", style: "margin-top:14px" }, svg("etoile"), nouvelle),
      bC.el);

    // CVs and letters first, side by side (the user, 2026-11-02: « mettre ajout lettre
    // de motivation plus haut dans le panneau profil à côté de CV »).
    vue.replaceChildren(h("div", { class: "grille" },
      carteId,
      h("div", { class: "pile" },
        carte("Score : réglages", h("dl", { class: "paires" }, Object.entries(p.scoring).map(([k, v]) =>
          [h("dt", {}, k.replaceAll("_", " ")), h("dd", {}, String(v))])))),
      await carteMetiers(),
      carteRech,
      carteComp,
      await cartePoids(),
      carte("Outils", puces(p.outils))));
  },
};

let ongletSources = "recherche";
ECRANS.sources = {
  titre: "Sources",
  plein: () => ongletSources !== "recherche",
  actions: () => [action("Lancer la collecte", "eclair", "collecte", "plein")],
  async dessiner(vue) {
    const tete = segment([["recherche", "Mots-clés et rendement"], ["entreprises", "Entreprises suivies"], ["vues", "Entreprises vues"],
      ["sites", "Sites d'offres"], ["acces", "Accès et clés"]], ongletSources, (v) => { ongletSources = v; ECRANS.sources.dessiner(vue); });
    const corps = h("div", { class: "corps-onglet" });
    vue.classList.toggle("plein", ECRANS.sources.plein());
    vue.replaceChildren(h("div", { class: "colonne" }, h("div", { class: "barre-outils" }, tete), corps));
    await ONGLETS_SOURCES[ongletSources](corps);
  },
};

const ONGLETS_SOURCES = {};
ONGLETS_SOURCES.recherche = async (vue) => {
  {
    const s = await appel("sources");
    const max = Math.max(1, ...s.rendement.map((r) => r.nouvelles));
    const ats = Object.values(s.ats).reduce((a, b) => a + b, 0);

    const mots = [...s.mots_cles];
    const bM = barreEnregistrer(async () => {
      const r = await appel("recherche");
      if (!r) return ecrire("recherche");
      return avecBak(await ecrire("enregistrer_recherche", { ...r, mots_cles: mots }));
    });
    const excl = { contrats_exclus: [...s.contrats_exclus], pays_exclus: [...s.pays_exclus] };
    const bE = barreEnregistrer(() => ecrire("enregistrer_exclusions", excl));

    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "verre stats" },
        [["loupe", "Mots-clés", s.mots_cles.length], ["sources", "Sources actives", s.rendement.length], ["valise", "Sites carrières suivis", ats]]
          .map(([ic, lab, val]) => h("div", { class: "stat" }, h("span", { class: "rond" }, svg(ic)),
            h("div", {}, h("div", { class: "lab" }, lab), h("div", { class: "val" }, nombre(val)))))),
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Rendement des sources"), h("span", { class: "etiq gris" }, "dernières collectes")),
        s.rendement.length ? h("table", {},
          h("colgroup", {}, h("col", { style: "width:20%" }), h("col", { style: "width:14%" }), h("col", { style: "width:14%" }), h("col", { style: "width:30%" }), h("col", {})),
          h("thead", {}, h("tr", {}, ["Source", "Ramenées", "Nouvelles", "", "Dernier passage"].map((t) => h("th", {}, t)))),
          h("tbody", {}, s.rendement.map((r) => h("tr", {},
            h("td", {}, h("span", { class: "avec-logo" }, logoSource(r.source), lisible(r.source))), h("td", {}, nombre(r.ramenees)), h("td", {}, nombre(r.nouvelles)),
            h("td", {}, h("div", { class: "prog" }, h("i", { style: `width:${100 * r.nouvelles / max}%` }))),
            h("td", {}, `${dateFr(r.dernier)} `, r.verdict ? h("span", { class: r.verdict === "ok" ? "etiq gris" : "etiq" }, r.verdict) : null)))))
        : h("div", { class: "vide" }, "Pas encore de journal de rendement.")),
      h("div", { class: "grille" },
        h("div", { class: "verre panneau large" },
          h("div", { class: "titre-ligne" }, h("h2", {}, "Mots-clés de collecte"), h("span", { class: "compte" }, mots.length)),
          editeurPuces(mots, bM.sale, "nouveau mot-clé…"), bM.el),
        carte("Exclusions", sousTitre("Contrats", "0 0 8px"), editeurPuces(excl.contrats_exclus, bE.sale, "type de contrat…"),
          sousTitre("Pays"), editeurPuces(excl.pays_exclus, bE.sale, "pays…"), bE.el),
        carte("Sites carrières (ATS)", h("dl", { class: "paires" }, Object.entries(s.ats).map(([k, v]) =>
          [h("dt", {}, lisible(k)), h("dd", {}, `${v} entreprises`)]))))));
  }
};

// --- Statuses from emails (Candidatures) -----------------------------------------------

ACTIONS_OUTILS.courriels = () => ouvrirCourriels();
function ouvrirCourriels() {
  const corps = $("tiroir-corps");
  const liste = h("div", { class: "colonne" });
  const info = h("div", { class: "sous" }, "Choisis d'où lire tes courriels. Rien n'est écrit sans ton clic « Appliquer ».");
  const lire = async (source) => {
    info.textContent = "Lecture des courriels…";
    liste.replaceChildren();
    // Not ecrire(): its toast would leave "Lecture des courriels…" standing, as if the
    // reading never ended (the user, 2026-10-27). The reason stays here, in full.
    if (!window.pywebview) { info.textContent = HORS_APPLI; return; }
    const r = await window.pywebview.api.lire_courriels(source);
    if (!r || !r.ok) { info.textContent = !r ? "Lecture impossible." : r.annule ? "Aucun fichier choisi." : r.erreur; return; }
    info.textContent = `${nombre(r.lus)} courriels lus · ${r.propositions.length} statut(s) proposé(s).`;
    liste.replaceChildren(...r.propositions.map((p, i) => {
      const [entreprise, poste] = p.oid.split("|");
      const ligne = h("div", { class: "carte proposition" },
        h("div", { class: "t" }, entreprise), h("div", { class: "s" }, poste),
        h("div", { class: "puces", style: "margin:8px 0" }, h("span", { class: "puce" }, p.actuel || "sans statut"), "→", h("span", { class: "puce chaude" }, p.propose)),
        h("div", { class: "sous" }, `« ${p.raison} » — ${p.de}, ${dateFr(p.le) || p.le}`),
        h("div", { class: "sous", title: p.sujet }, p.sujet),
        h("div", { class: "boutons", style: "margin-top:10px" },
          bouton("Appliquer", "avion", async () => {
            const a = await ecrire("appliquer_proposition", i);
            if (!a) return;
            if (!a.ok) return toast(a.erreur, true);
            toast(`${entreprise} : ${p.propose}`);
            ligne.remove();
            redessiner();
          }, "plein"),
          bouton("Ignorer", null, () => ligne.remove())));
      return ligne;
    }));
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Statuts depuis mes courriels"), h("div", { class: "sous" }, "Lecture seule : rien n'est envoyé."))),
    h("div", { class: "boutons" },
      bouton("Fichier .mbox…", "doc", () => lire("mbox")),
      bouton("Dossier .eml…", "doc", () => lire("eml")),
      bouton("Gmail (lecture seule)", "cloche", () => lire("gmail"))),
    info, liste);
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
}

// --- Companies, job boards, access and keys (the desktop's panels) ------------------

// Sector lists (sources.company_lists): tick a sector to collect its companies, then
// untick one company inside it if needed. Any profession gets companies in two clicks,
// not only finance (the user, 2026-10-27).
function carteListes(listes, rafraichir) {
  const lignes = listes.map((l) => {
    const suivies = l.entreprises.filter((e) => e.suivie).length;
    const detail = h("div", { class: "entreprises-liste", hidden: true },
      l.entreprises.map((e) => h("label", { class: `case${l.active ? "" : " pale"}` },
        h("input", { type: "checkbox", checked: e.suivie, disabled: !l.active, onchange: async (ev) => {
          const r = await ecrire("suivre_dans_liste", e.outil, e.cle, ev.target.checked);
          if (r) rafraichir(); else ev.target.checked = !ev.target.checked;
        } }), e.nom)));
    return h("div", { class: `liste-secteur${l.active ? " active" : ""}` },
      h("div", { class: "tete-liste" },
        h("label", { class: "case" },
          h("input", { type: "checkbox", checked: l.active, onchange: async (ev) => {
            const r = await ecrire("activer_liste", l.id, ev.target.checked);
            if (r) { toast(r.message); rafraichir(); } else ev.target.checked = !ev.target.checked;
          } }),
          h("span", { class: "t" }, l.titre)),
        h("span", { class: "sous" }, l.active ? `${suivies} sur ${l.entreprises.length} entreprises` : `${l.entreprises.length} entreprises`),
        bouton("Voir les entreprises", "", () => { detail.hidden = !detail.hidden; })),
      h("div", { class: "sous" }, l.description), detail);
  });
  return h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Listes par secteur")),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Coche les secteurs à collecter. Dans une liste, décoche une entreprise pour la laisser de côté ; ses offres déjà en file restent."),
    ...lignes);
}

ONGLETS_SOURCES.entreprises = async (vue) => {
  const [d, listes] = await Promise.all([appel("entreprises"), appel("listes_entreprises")]);
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  let filtre = "";
  const ouverts = new Set();
  const corps = h("tbody");
  const compte = h("span", { class: "sous" });
  const dessiner = () => {
    const f = filtre.toLowerCase();
    const lignes = d.lignes.filter((l) => !f || `${l.nom} ${l.outil} ${(l.flux || [l]).map((x) => x.lien).join(" ")}`.toLowerCase().includes(f));
    compte.textContent = `${lignes.length} / ${d.lignes.length} entreprises (${nombre(d.lignes.reduce((s, l) => s + (l.flux || [l]).length, 0))} flux) · ${nombre(d.lignes.reduce((s, l) => s + l.offres, 0))} offres en file`
      + (d.muettes ? ` · ${d.muettes} muette(s) depuis ${d.muet_jours} j` : "");
    // One row per company; its feeds (API, site…) open under it when it has several.
    const actions = (x, nom) => [
      bouton("", "sortie", () => ecrire("ouvrir_lien", x.lien), "icone"),
      x.site ? null : bouton(x.suspendue ? "Reprendre" : "Suspendre", "", async () => {
        const r = await ecrire("suspendre_entreprise", x.id);
        if (r) { toast(r.message); ONGLETS_SOURCES.entreprises(vue); }
      }),
      bouton("Retirer", "", async () => {
        const ok = await dialogue(`Ne plus suivre « ${nom} » ?`, "Son adresse de flux sera retirée ; « Suspendre » la garde.", null, [["Retirer", "chaud", () => true]]);
        if (!ok) return;
        const r = await ecrire("retirer_entreprise", x.id);
        if (r) { toast(r.message); ONGLETS_SOURCES.entreprises(vue); }
      })];
    const etat = (x) => x.suspendue
      ? h("span", { class: "etiq gris", title: x.collecte }, x.auto ? "suspendue auto" : "suspendue")
      : x.collecte;
    corps.replaceChildren(...lignes.flatMap((l) => {
      const plusieurs = (l.flux || []).length > 1;
      const tete = h("tr", { class: l.offres ? "" : "pale" },
        h("td", {}, h("div", { class: "t" }, l.nom,
          l.ajoutee ? [" ", h("span", { class: "etiq", title: l.ajoutee }, "suivie auto")] : null)),
        h("td", {}, l.outil),
        h("td", {}, etat(l)),
        h("td", { class: "num" }, nombre(l.offres)),
        h("td", { class: "num" }, l.fit ?? "—"),
        h("td", {}, l.derniere || "—"),
        h("td", { class: "actions-ligne" }, ...(plusieurs
          ? [bouton("", "sortie", () => ecrire("ouvrir_lien", l.lien), "icone"),
            bouton(`${l.flux.length} flux ${ouverts.has(l.id) ? "▴" : "▾"}`, "", () => {
              ouverts.has(l.id) ? ouverts.delete(l.id) : ouverts.add(l.id);
              dessiner();
            })]
          : actions(l, l.nom))));
      if (!plusieurs || !ouverts.has(l.id)) return [tete];
      return [tete, ...l.flux.map((x) => h("tr", { class: `sous-ligne${x.offres ? "" : " pale"}` },
        h("td", {}, h("div", { class: "sous" }, "↳ ", x.lien || x.id)),
        h("td", {}, x.outil),
        h("td", {}, etat(x)),
        h("td", { class: "num" }, nombre(x.offres)),
        h("td", { class: "num" }, x.fit ?? "—"),
        h("td", {}, x.derniere || "—"),
        h("td", { class: "actions-ligne" }, ...actions(x, l.nom))))];
    }));
  };
  const champ = h("input", { class: "champ-texte", placeholder: "Adresse de sa page carrière, ou nom de l'entreprise (annuaire)" });
  const ajouter = async () => {
    const v = champ.value.trim();
    if (!v) return;
    if (!/^https?:\/\//.test(v)) return ouvrirAnnuaire(v, () => ONGLETS_SOURCES.entreprises(vue));
    const r = await ecrire("suivre_entreprise", v);
    if (r) { toast(r.message); ONGLETS_SOURCES.entreprises(vue); }
  };
  champ.addEventListener("keydown", (e) => { if (e.key === "Enter") ajouter(); });
  dessiner();
  vue.replaceChildren(h("div", { class: "colonne" }, listes ? carteListes(listes, () => ONGLETS_SOURCES.entreprises(vue)) : null, h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Entreprises suivies"), compte),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Chaque entreprise est lue par son outil de recrutement (API publique) ou, à défaut, par son site carrière. Les sites d'offres généraux (LinkedIn, WTJ…) sont dans « Sites d'offres »."),
    h("div", { class: "ligne-ajout" }, champ, bouton("Ajouter", "", ajouter, "plein"), bouton("Annuaire…", "loupe", () => ouvrirAnnuaire(champ.value.trim(), () => ONGLETS_SOURCES.entreprises(vue)))),
    h("label", { class: "champ", style: "margin:12px 0" }, svg("loupe"), h("input", { type: "search", placeholder: "Filtrer : entreprise, outil ou adresse", oninput: (e) => { filtre = e.target.value; dessiner(); } })),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Entreprise", "Lue par", "Dernière collecte", "Offres", "Score max", "Dernière", ""].map((t) => h("th", {}, t)))),
      corps)))));
};

// Every company a collection has seen, kept after its offers leave the queue (the user,
// 2026-10-27: « note l'entreprise quelque part pour trouver ses offres »).
ONGLETS_SOURCES.vues = async (vue) => {
  const d = await appel("entreprises_vues");
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  let filtre = "";
  const corps = h("tbody");
  const compte = h("span", { class: "sous" });
  const offres = (l) => {
    Object.assign(filtresOffres, { texte: l.nom, statut: "toutes", page: 0 });
    aller("offres");
  };
  const dessiner = () => {
    const f = filtre.toLowerCase();
    const lignes = d.lignes.filter((l) => !f || `${l.nom} ${l.sites.join(" ")} ${l.outil || ""}`.toLowerCase().includes(f));
    compte.textContent = `${nombre(lignes.length)} / ${nombre(d.lignes.length)} entreprises`;
    corps.replaceChildren(...lignes.slice(0, 300).map((l) => h("tr", { class: l.offres ? "" : "pale" },
      h("td", {}, h("div", { class: "t" }, l.nom)),
      h("td", { class: "num" }, nombre(l.offres)),
      h("td", { class: "num" }, l.fit ?? "—"),
      h("td", {}, l.sites.join(", ") || "—"),
      h("td", {}, l.derniere || "—"),
      h("td", { class: "actions-ligne" },
        l.offres ? bouton("Ses offres", "loupe", () => offres(l)) : null,
        l.suivie ? h("span", { class: "etiq gris" }, "suivie")
          : l.url_flux ? bouton(`Suivre (${l.outil})`, "", async () => {
            const r = await ecrire("suivre_entreprise", l.url_flux);
            if (r) { toast(r.message); ONGLETS_SOURCES.vues(vue); }
          }) : null))));
  };
  dessiner();
  vue.replaceChildren(h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Entreprises vues"), compte,
      bouton("Chercher leurs offres", "loupe", () => lancer("sites_carrieres")),
      bouton("Suivre celles à score ≥ 7", "etoile", async () => {
        const n = d.lignes.filter((l) => l.url_flux && !l.suivie && (l.fit || 0) >= 7).length;
        if (!n) return toast("Aucune entreprise bien notée à suivre.");
        const ok = await dialogue(`Suivre ${n} entreprise(s) ?`, "Chacune est d'abord vérifiée : une requête à son outil de recrutement, suivie seulement si elle a des offres ouvertes.", null, [["Suivre", "", () => true]]);
        if (!ok) return;
        const r = await ecrire("suivre_vues", 7);
        if (r) { toast(r.message); ONGLETS_SOURCES.vues(vue); }
      })),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Chaque collecte note les entreprises de ses offres, même écartées ou fermées depuis. « Chercher leurs offres » demande à 150 d'entre elles, chaque matin aussi, ce qu'elles ont d'ouvert sur leur site carrière : par leur outil de recrutement, par freehire, sinon en devinant leur outil par leur nom (annuaire Workday compris) ou en lisant leur page carrière. L'outil trouvé est retenu pour la fois suivante. « Suivre » lit ensuite ses offres à chaque collecte, quand son lien d'offre donne son outil de recrutement."),
    h("label", { class: "champ", style: "margin:12px 0" }, svg("loupe"), h("input", { type: "search", placeholder: "Filtrer : entreprise, site ou outil", oninput: (e) => { filtre = e.target.value; dessiner(); } })),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Entreprise", "Offres", "Score max", "Vue sur", "Dernière fois", ""].map((t) => h("th", {}, t)))),
      corps))));
};

async function ouvrirAnnuaire(texte, apres) {
  const champ = h("input", { class: "champ-texte", value: texte || "", placeholder: "Nom de l'entreprise" });
  const liste = h("div", { class: "motifs" });
  let minuteur;
  const chercher = async () => {
    const r = (await appel("annuaire", champ.value)) || [];
    liste.replaceChildren(...(r.length ? r.map((e) => h("button", { class: "motif", disabled: e.suivi, onclick: async () => {
      const x = await ecrire("suivre_annuaire", e.outil, e.jeton);
      if (x) { toast(x.message); e.suivi = true; chercher(); apres && apres(); }
    } }, `${e.nom} · ${e.outil_nom}${e.suivi ? " (déjà suivie)" : ""}`)) : [h("div", { class: "sous" }, "Aucune entreprise de ce nom dans les annuaires Lever, Ashby, Greenhouse, Workday.")]));
  };
  champ.addEventListener("input", () => { clearTimeout(minuteur); minuteur = setTimeout(chercher, 250); });
  chercher();
  const workday = h("div", { class: "sous", style: "margin-top:12px" }, "Workday : son annuaire se construit sur ton PC, depuis Common Crawl (archive publique du web).",
    bouton("Construire l'annuaire Workday", "fleche", () => lancer("annuaire_workday")));
  await dialogue("Annuaire des entreprises", "Lever, Ashby, Greenhouse et Workday : clique une entreprise pour la suivre.", h("div", {}, champ, liste, workday), []);
}

ONGLETS_SOURCES.sites = async (vue) => {
  const d = await appel("sites_offres");
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  const genre = h("select", { class: "choix" }, d.types.map((t) => h("option", { value: t }, t === "board" ? "site d'offres (adresse)" : `${t} (slug)`)));
  const champ = h("input", { class: "champ-texte", placeholder: "https://… ou le slug de l'entreprise" });
  const ajouter = async () => {
    if (await ecrire("ajouter_site_offres", genre.value, champ.value)) { toast("Ajouté."); ONGLETS_SOURCES.sites(vue); }
  };
  champ.addEventListener("keydown", (e) => { if (e.key === "Enter") ajouter(); });
  vue.replaceChildren(h("div", { class: "verre panneau" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Sites d'offres et flux ATS"), h("span", { class: "compte" }, d.lignes.length)),
    h("div", { class: "sous", style: "margin:4px 0 12px" }, "Un slug ATS est lu par son API ; un site d'offres est lu par « Scrape les sites »."),
    h("div", { class: "ligne-ajout" }, genre, champ, bouton("Ajouter", "", ajouter, "plein")),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Type", "Source", "Offres en file", ""].map((t) => h("th", {}, t)))),
      h("tbody", {}, d.lignes.map((l) => h("tr", {},
        h("td", {}, l.type), h("td", {}, l.source), h("td", { class: "num" }, nombre(l.offres)),
        h("td", { class: "actions-ligne" },
          bouton("", "sortie", () => ecrire("ouvrir_lien", l.lien), "icone"),
          bouton("Retirer", "", async () => {
            const ok = await dialogue(`Retirer « ${l.source} » ?`, "Ses offres déjà en file restent.", null, [["Retirer", "chaud", () => true]]);
            if (ok && await ecrire("retirer_site_offres", l.type, l.type === "board" ? l.lien : l.source)) ONGLETS_SOURCES.sites(vue);
          })))))))));
};

ONGLETS_SOURCES.acces = async (vue) => {
  const d = await appel("acces");
  if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  const recharger = () => ONGLETS_SOURCES.acces(vue);
  vue.replaceChildren(h("div", { class: "grille" },
    h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Collecte des offres"),
        h("span", { class: "sous" }, "Appels d'API aujourd'hui (tous profils) : " + d.quotas.map((q) => `${q.nom} ${q.n}${q.plafond ? "/" + q.plafond : ""}`).join(" · "))),
      h("div", { class: "sous", style: "margin:4px 0 12px" }, "État de la dernière collecte de chaque source. Un refus n'est pas réessayé avant 30 jours."),
      h("table", { class: "tableau-simple" },
        h("thead", {}, h("tr", {}, ["Source", "Accès", "Dernier état", "Collecte du", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, d.sources.map((s) => h("tr", {},
          h("td", {}, s.libelle), h("td", {}, s.acces),
          h("td", {}, h("span", { class: `etat-source ${s.gravite}` }, s.etat)), h("td", {}, s.le || "—"),
          h("td", { class: "actions-ligne" },
            s.cle ? bouton("Saisir la clé", "cle", () => saisirCle(s.source, recharger)) : null,
            s.cle ? bouton("Tester", "", async () => { const r = await ecrire("tester_cle", s.source); if (r) toast(r.message, !r.reussi); }) : null,
            bouton("Collecter", "eclair", async () => { if (await ecrire("collecter_source", s.source)) suivreTache(); }, s.bloque ? "" : "plein")))))),
      h("div", { class: "boutons", style: "margin-top:12px" }, bouton("Rendement des sources", "", async () => { if (await ecrire("rendement_sources")) suivreTache(); }))),
    h("div", { class: "verre panneau large" },
      h("div", { class: "titre-ligne" }, h("h2", {}, "Connexions pour candidater")),
      h("div", { class: "sous", style: "margin:4px 0 12px" }, "Tu te connectes toi-même ; les mots de passe restent dans le navigateur."),
      h("table", { class: "tableau-simple" },
        h("thead", {}, h("tr", {}, ["Site", "Identifiant", "Session", "Vérifiée le", ""].map((t) => h("th", {}, t)))),
        h("tbody", {}, d.connexions.map((c) => h("tr", {},
          h("td", {}, c.site), h("td", {}, c.identifiant || "—"),
          h("td", {}, h("span", { class: `etat-source ${c.gravite}` }, c.session)), h("td", {}, c.le || "—"),
          h("td", { class: "actions-ligne" }, bouton("Ouvrir la connexion", "sortie", async () => {
            if (await ecrire("connexion", c.site)) toast("Console ouverte : connecte-toi dans le navigateur.");
          })))))),
      h("div", { class: "boutons", style: "margin-top:12px" }, bouton("Vérifier les sessions", "", async () => {
        if (await ecrire("connexion", "", true)) toast("Vérification lancée dans une console.");
      })))));
};

// A key is typed here and goes straight to its file; it is never shown again.
async function saisirCle(nom, apres) {
  const c = await ecrire("cle_champs", nom);
  if (!c) return;
  const champs = c.champs.map((x) => [x.nom, h("input", { class: "champ-texte", type: x.secret ? "password" : "text", autocomplete: "off",
    placeholder: c.deja ? "laisser vide : garder la valeur enregistrée" : "" })]);
  const valeurs = await dialogue(`Clé ${c.libelle}`, `${c.deja ? "Une clé est déjà enregistrée. " : ""}Crée-la sur ${c.obtenir}. Elle va dans son fichier, jamais ailleurs.`,
    h("div", { class: "formulaire" }, champs.map(([n, e]) => h("label", { class: "champ-form" }, n, e))),
    [["Enregistrer", "plein", () => Object.fromEntries(champs.map(([n, e]) => [n, e.value]))]]);
  champs.forEach(([, e]) => { e.value = ""; });
  if (!valeurs) return;
  if (await ecrire("saisir_cle", nom, valeurs)) { toast(`Clé ${c.libelle} enregistrée.`); apres && apres(); }
}

// --- Statistics (the desktop's Stats panel) -----------------------------------------

ECRANS.stats = {
  titre: "Statistiques",
  actions: () => [bouton("Rafraîchir", "fleche", () => redessiner())],
  async dessiner(vue) {
    const d = await appel("stats");
    if (!d) return vue.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
    const pc = (p) => (p == null ? "" : `${Math.round(p * 100)} %`);
    const e = d.entonnoir;
    const barres = (s) => {
      const max = Math.max(1, ...s.lignes.map((l) => (typeof l.n === "number" ? l.n : 0)));
      return h("div", { class: "verre panneau" }, h("div", { class: "titre-ligne" }, h("h2", {}, s.titre)),
        s.lignes.map((l) => h("div", { class: "ligne-barre" },
          h("span", { class: "nom", title: lisible(l.nom) }, lisible(l.nom)),
          h("span", { class: "piste" }, h("span", { class: "rempli", style: `width:${100 * l.n / max}%` })),
          h("span", { class: "num" }, `${nombre(l.n)} ${pc(l.part)}`))));
    };
    // No hole between panels (the user, 2026-10-27): the sections go into three stacks of
    // about the same height, the longest first, and the last panel of each stack grows.
    const piles = [[], [], []];
    const hauteur = (pile) => pile.reduce((n, s) => n + s.lignes.length + 3, 0);
    [...d.sections].sort((a, b) => b.lignes.length - a.lignes.length)
      .forEach((s) => piles.reduce((m, p) => (hauteur(p) < hauteur(m) ? p : m)).push(s));
    const parChamp = (ch, titre) => (e.par[ch].length < 2 ? null : h("div", {}, h("h3", {}, titre),
      h("dl", { class: "paires alignees" }, e.par[ch].map((x) => [h("dt", {}, x.val),
        h("dd", {}, `${x.env} envoyée(s) · ${x.rep} réponse(s), ${x.ent} entretien(s) · ${pc(x.rep / x.env)}`)]))));
    // The applications sent make a fourth stack, on the left, instead of a full-width band:
    // the screen holds in a 1280 × 720 window when it opens (the user, 2026-10-28).
    const envoyees = e ? h("div", { class: "verre panneau envoyees" },
        h("div", {}, h("h2", {}, "Candidatures envoyées"),
          h("dl", { class: "paires alignees" },
            h("dt", {}, "Taux de réponse"), h("dd", {}, e.taux != null ? pc(e.taux) : "—"),
            h("dt", {}, "Sans réponse depuis 30 jours"), h("dd", {}, String(e.silence)),
            h("dt", {}, "Délai médian de réponse"), h("dd", {}, e.delai_median == null ? "—" : `${Math.round(e.delai_median)} j (sur ${e.n_delais} réponse(s) datée(s))`))),
        parChamp("contrat", "Par contrat"), parChamp("domaine", "Par domaine")) : null;
    vue.replaceChildren(h("div", { class: "colonne" },
      h("div", { class: "cartes-stats" }, d.cartes.map((c) => h("div", { class: "verre carte-stat" },
        h("div", { class: "chiffre" }, nombre(c.n)), h("div", { class: "sous" }, c.nom)))),
      h("div", { class: "piles-stats" }, envoyees ? h("div", { class: "pile" }, envoyees) : null,
        piles.filter((p) => p.length).map((p) => h("div", { class: "pile" }, p.map(barres))))));
  },
};

// --- Workshop: fit weights, base CV, recipes, documents to compare, CV/letters in bulk --

// The desktop's Profil → Fit tab: each slider recomputes the queue at once, nothing written.
async function cartePoids() {
  const d = await appel("poids");
  if (!d) return null;
  const valeurs = Object.fromEntries(d.curseurs.map((c) => [c.cle, c.v]));
  const resume = h("div", { class: "sous", style: "margin:10px 0" }, "Lecture de la file…");
  const histo = h("div", { class: "histo" });
  let minuteur, essais = 0;
  const recalculer = async () => {
    const b = await appel("bilan_poids", valeurs);
    if (!b) return;
    if (!b.pret) {
      resume.textContent = b.erreur ? `Lecture de la file impossible (${b.erreur}).` : "Lecture de la file… (une trentaine de secondes la première fois)";
      if (!b.erreur && essais++ < 200) minuteur = setTimeout(recalculer, 1500);
      return;
    }
    const e = b.essai, s = b.enregistre;
    resume.textContent = `${nombre(e.n)} offres · score moyen ${e.moyenne.toFixed(2)} (enregistré ${s.moyenne.toFixed(2)}) · à 8 et plus : ${nombre(e.haut)} (enregistré ${nombre(s.haut)})`;
    const max = Math.max(1, ...e.repartition, ...s.repartition);
    histo.replaceChildren(...e.repartition.map((n, i) => h("div", { class: "histo-col", title: `score ${i + 1} : ${n} (enregistré : ${s.repartition[i]})` },
      h("div", { class: "histo-barres" },
        h("span", { class: "apres", style: `height:${100 * n / max}%` }),
        h("span", { class: "avant", style: `height:${100 * s.repartition[i] / max}%` })),
      h("span", { class: "sous" }, String(i + 1)))));
  };
  const planifier = () => { clearTimeout(minuteur); minuteur = setTimeout(recalculer, 80); };
  const groupes = [
    ["axes", "Poids des axes", "Combien compte chaque axe du profil quand l'annonce cite ses compétences."],
    ["cible", "Score qui vaut 10", "La somme pondérée des axes qui donne 10. Plus bas : les notes montent."],
    ["titre", "Intitulé", "Ajouté ou retiré selon les mots du titre de l'offre."],
    ["exp", "Expérience demandée", "Retiré quand l'annonce demande au moins ce nombre d'années."],
  ];
  const blocs = groupes.map(([g, titre, sous]) => {
    const cs = d.curseurs.filter((c) => c.groupe === g);
    if (!cs.length) return null;
    return h("div", { class: "groupe-poids" }, h("h3", {}, titre), h("div", { class: "sous" }, sous),
      cs.map((c) => {
        const val = h("span", { class: "num" }, String(c.v));
        const curseur = h("input", { type: "range", min: c.b[0], max: c.b[1], step: c.b[2], value: c.v,
          oninput: (ev) => { valeurs[c.cle] = Number(ev.target.value); val.textContent = ev.target.value; planifier(); } });
        return h("label", { class: "ligne-poids" }, h("span", {}, c.nom), curseur, val);
      }));
  });
  recalculer();
  const enregistrer = async () => {
    const r = await ecrire("enregistrer_poids", valeurs);
    if (!r) return;
    toast("Poids enregistrés (l'ancienne version est gardée).");
    const ok = await dialogue("Recalculer les scores ?", "Recalculer maintenant le score enregistré de chaque offre de ta file ? Le tableau et le tri l'utilisent.",
      null, [["Recalculer", "plein", () => true]]);
    if (ok) lancer("rescore");
    redessiner();
  };
  return h("div", { class: "verre panneau large" }, h("div", { class: "titre-ligne" }, h("h2", {}, "Score : les poids")),
    h("div", { class: "sous", style: "margin-bottom:10px" }, "Chaque curseur recalcule la file aussitôt, sans rien écrire. Barres claires : les poids enregistrés."),
    h("div", { class: "poids" }, blocs), resume, histo,
    h("div", { class: "boutons", style: "margin-top:12px" },
      bouton("Enregistrer", "", enregistrer, "plein"),
      bouton("Annuler les modifications", "", () => redessiner()),
      bouton("Relire la file", "fleche", async () => { if (await ecrire("relire_composantes")) { essais = 0; resume.textContent = "Lecture de la file…"; setTimeout(recalculer, 1500); } })));
}

// Trades (3.74): one CV and one letter each. A trade is a domain of the profile: added
// here, it shows in the Offres screen's domain filter once the offers are classed again.
async function choixFichier(nom, ...args) {
  if (!window.pywebview) { toast(HORS_APPLI, true); return null; }
  let r;
  try { r = await window.pywebview.api[nom](...args); } catch (e) { toast(`Échec : ${(e && e.message) || e}`, true); return null; }
  if (!r || r.annule) return null;
  if (!r.ok) { toast(r.erreur || "Échec.", true); return null; }
  return r;
}

// A title word as the user reads it: « re:\b(isr|(?<![a-z])csrd(?![a-z]))\b » shows as
// « isr · csrd » (the user, 2026-11-04: the raw patterns ran over the card). The chip's
// tooltip keeps the pattern itself.
function motLisible(mot) {
  if (!mot.startsWith("re:")) return mot;
  const s = mot.slice(3).replace(/\(\?<?[!=][^)]*\)/g, "").replace(/\\b/g, "").replace(/\(\?:/g, "(")
    .replace(/\\(.)/g, "$1").replace(/[()^$?+*]/g, "");
  return s.split("|").map((x) => x.trim()).filter(Boolean).join(" · ");
}

async function carteMetiers() {
  const m = (await appel("metiers")) || { metiers: [] };
  const vrais = m.metiers.filter((x) => x.cle !== "General");
  const refaire = async (genre) => {
    const [titre, cle] = genre === "cv" ? ["Refaire les CV ?", "regenerer_cv"] : ["Refaire les lettres ?", "regenerer_lettres"];
    const ok = await dialogue(titre, "Refaire maintenant ceux déjà préparés pour les offres ?", null, [["Refaire", "plein", () => true]]);
    if (ok) lancer(cle);
  };
  const changer = async (x, genre) => {
    const r = await choixFichier(genre === "cv" ? "cv_metier" : "lettre_metier", x.cle);
    if (!r) return;
    toast(genre === "cv" ? `CV de « ${x.libelle} » : ${r.nom}.`
      : r.parcours ? `Lettre de « ${x.libelle} » : ${r.nom}. Son paragraphe de parcours est repris.` : `Lettre de « ${x.libelle} » : ${r.nom}. Aucun paragraphe de parcours reconnu.`);
    redessiner();
    refaire(genre);
  };
  const champsMetier = (x) => {
    const nom = h("input", { class: "champ-texte", value: x ? x.libelle : "", placeholder: "Ex. : Contrôle de gestion" });
    const mots = h("input", { class: "champ-texte", value: x ? x.mots.join(", ") : "", placeholder: "Ex. : contrôleur de gestion, contrôle de gestion, fp&a" });
    const bloc = h("div", { class: "formulaire" },
      h("label", { class: "champ-form" }, h("span", {}, "Nom du métier"), nom),
      x && x.cle === "General" ? null : h("label", { class: "champ-form" }, h("span", {}, "Mots du titre des offres (séparés par des virgules)"), mots));
    return { bloc, nom, mots };
  };
  const ajouter = async () => {
    const c = champsMetier(null);
    const v = await dialogue("Ajouter un métier", "Un CV pour un autre métier, et sa lettre si tu veux : les offres dont le titre contient un de ces mots le prennent. Choisis ensuite le CV.",
      c.bloc, [["Choisir le CV…", "plein", () => (c.nom.value.trim() && c.mots.value.trim() ? [c.nom.value, c.mots.value] : (toast("Il faut un nom et au moins un mot.", true), undefined))]]);
    if (!v) return;
    const r = await choixFichier("ajouter_metier", v[0], v[1]);
    if (!r) return;
    toast(`Métier ajouté, CV : ${r.cv}. Les offres prennent leur domaine…`);
    lancer("domaines");
    redessiner();
    const lettre = await dialogue("Ajouter sa lettre ?", "Ta lettre pour ce métier : son paragraphe de parcours sera repris dans les lettres de ses offres.", null, [["Choisir la lettre…", "plein", () => true]]);
    if (lettre) changer({ cle: r.cle, libelle: v[0] }, "lettre");
  };
  const modifier = async (x) => {
    const c = champsMetier(x);
    const ok = await dialogue(`Modifier « ${x.libelle} »`, null, c.bloc, [["Enregistrer", "plein", () => true]]);
    if (!ok) return;
    if (await ecrire("renommer_metier", x.cle, c.nom.value, c.mots.value)) { lancer("domaines"); redessiner(); }
  };
  const retirer = async (x) => {
    const ok = await dialogue(`Retirer « ${x.libelle} » ?`, "Ses offres passent aux autres métiers. Son CV et sa lettre restent dans leurs dossiers.", null, [["Retirer", "plein", () => true]]);
    if (ok && await ecrire("retirer_metier", x.cle)) { lancer("domaines"); redessiner(); }
  };
  const doc = (x, genre) => {
    const [lib, nom, chemin] = genre === "cv" ? ["CV", x.cv, x.cv_chemin] : ["Lettre", x.lettre, x.lettre_chemin];
    return h("div", { class: "doc-metier" },
      h("span", { class: "lab" }, lib),
      h("span", { class: `t ${nom ? "" : "vide-doc"}`, title: nom || "" }, nom || "aucune"),
      chemin ? h("button", { class: "lien", onclick: () => voirDocument(null, chemin, nom) }, "Voir") : null,
      h("button", { class: "lien", onclick: () => changer(x, genre) }, nom ? "Changer…" : "Ajouter…"));
  };
  return h("div", { class: "verre panneau large" },
    h("div", { class: "titre-ligne" }, h("h2", {}, "Mes métiers : CV et lettre"), h("span", { class: "compte" }, vrais.length),
      h("span", { style: "flex:1" }), bouton("Ajouter un métier…", "doc", ajouter, "plein")),
    h("div", { class: "sous", style: "margin:-6px 0 14px" }, "Chaque métier a son CV et sa lettre ; une offre prend le métier dont un mot est dans son titre. Chaque métier est un domaine du filtre des offres."),
    h("div", { class: "metiers" }, m.metiers.map((x) => h("div", { class: "metier" },
      h("div", { class: "metier-tete" },
        h("div", { style: "min-width:0" }, h("div", { class: "t" }, x.cle === "General" ? `${x.libelle} (le reste)` : x.libelle),
          h("div", { class: "sous", title: x.mots.map(motLisible).join(" · ") }, x.cle === "General" ? "les offres qu'aucun métier ne prend" : x.mots.map(motLisible).join(" · "))),
        h("div", { class: "outils-metier" },
          h("button", { class: "lien", onclick: () => modifier(x) }, "Modifier"),
          x.cle !== "General" && vrais.length > 1 ? h("button", { class: "lien", onclick: () => retirer(x) }, "Retirer") : null)),
      doc(x, "cv"), doc(x, "lettre")))),
    phrase(m));
}

// The sentence about you that every letter repeats, under the trades (was the « Lettre de
// motivation » card: one place for letters, 3.75).
function phrase(m) {
  const fr = h("textarea", { class: "champ-texte", rows: 3 }, m.phrase_fr || "");
  const en = h("textarea", { class: "champ-texte", rows: 3 }, m.phrase_en || "");
  const enregistrer = async () => {
    if (!await ecrire("enregistrer_phrases_lettre", fr.value, en.value)) return;
    toast("Enregistré (l'ancienne version est gardée).");
    const refaire = await dialogue("Refaire les lettres ?", "Refaire maintenant les lettres déjà préparées pour les offres ?", null, [["Refaire les lettres", "plein", () => true]]);
    if (refaire) lancer("regenerer_lettres");
  };
  return h("details", { class: "phrase-lettres" },
    h("summary", {}, "Ta phrase sur toi, reprise dans toutes les lettres"),
    h("label", { class: "champ-bloc" }, h("span", { class: "sous" }, "En français"), fr),
    h("label", { class: "champ-bloc" }, h("span", { class: "sous" }, "En anglais"), en),
    h("div", { class: "boutons" }, bouton("Enregistrer", "", enregistrer, "plein"),
      m.exemple ? bouton("Voir la dernière lettre", "doc", () => voirDocument(null, m.exemple, "Lettre")) : null));
}

// The whole profile as a form (3.74): what « Fichier du profil (avancé) » opened in
// Notepad. Each value keeps its type; lists of words are one per line.
async function profilAvance() {
  const r = await ecrire("profil_avance");
  if (!r) return;
  const donnees = structuredClone(r.profil);
  const corps = $("tiroir-corps");
  $("tiroir").classList.add("ouvert", "document");
  $("tiroir").classList.remove("large");
  $("voile").classList.add("ouvert");
  const nomLisible = (k) => String(k).replaceAll("_", " ");
  const scalaire = (v) => v === null || ["string", "number", "boolean"].includes(typeof v);
  const champ = (parent, cle, libelle) => {
    const v = parent[cle];
    if (typeof v === "boolean") {
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle),
        h("input", { type: "checkbox", checked: v, onchange: (e) => { parent[cle] = e.target.checked; } }));
    }
    if (typeof v === "number") {
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle),
        h("input", { class: "champ-texte av-nombre", type: "number", step: "any", value: String(v),
          oninput: (e) => { const n = parseFloat(e.target.value); if (!Number.isNaN(n)) parent[cle] = n; } }));
    }
    if (typeof v === "string" || v === null) {
      const long = (v || "").length > 70;
      const z = h(long ? "textarea" : "input", { class: "champ-texte", rows: long ? 3 : null, value: long ? null : (v || ""),
        oninput: (e) => { parent[cle] = e.target.value; } }, long ? v : null);
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle), z);
    }
    if (Array.isArray(v) && v.every(scalaire) && (v.length === 0 || v.every((x) => typeof x === "string"))) {
      const z = h("textarea", { class: "champ-texte", rows: Math.min(8, Math.max(2, v.length + 1)),
        oninput: (e) => { parent[cle] = e.target.value.split("\n").map((s) => s.trim()).filter(Boolean); } }, v.join("\n"));
      return h("label", { class: "av-ligne" }, h("span", { class: "av-cle" }, libelle, h("span", { class: "sous" }, " · un par ligne")), z);
    }
    if (Array.isArray(v)) {
      return h("details", { class: "av-groupe" }, h("summary", {}, `${libelle} · ${v.length}`),
        v.map((x, i) => (scalaire(x) ? champ(v, i, `${i + 1}`)
          : h("details", { class: "av-groupe" }, h("summary", {}, (x && (x.libelle || x.nom || x.cle)) || `${i + 1}`),
            Object.keys(x).map((k) => champ(x, k, nomLisible(k)))))));
    }
    return h("details", { class: "av-groupe" }, h("summary", {}, libelle), Object.keys(v).map((k) => champ(v, k, nomLisible(k))));
  };
  const enregistrer = async () => {
    const e = await ecrire("enregistrer_profil_avance", donnees);
    if (!e) return;
    toast("Profil enregistré (l'ancienne version est gardée).");
    fermerTiroir();
    redessiner();
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Profil avancé"),
      h("div", { class: "sous" }, "Tout le profil, rubrique par rubrique. Les rubriques ne s'ajoutent ni ne se retirent ici ; le profil d'avant est gardé à chaque enregistrement."))),
    h("div", { class: "boutons" }, bouton("Enregistrer", "doc", enregistrer, "plein"), bouton("Fermer", "", fermerTiroir)),
    h("div", { class: "avance" }, Object.keys(donnees).map((k) => champ(donnees, k, nomLisible(k)))));
}

ACTIONS_OUTILS.profils = gererProfils;

ACTIONS_OUTILS.documents = async () => {
  const reste = await ecrire("documents_restants");
  if (reste == null) return;
  const champ = h("input", { class: "champ-texte", type: "number", min: 1, max: 1000, value: Math.min(reste || 30, 50), style: "width:120px" });
  const n = await dialogue("CV et lettres", `Combien d'offres traiter ? ${reste} offre(s) à score 8 et plus attendent encore leurs documents.`,
    champ, [["Préparer", "plein", () => Number(champ.value) || undefined]]);
  if (n && await ecrire("documents_lot", n)) suivreTache();
};

ACTIONS_OUTILS.recettes = async () => {
  const r = await ecrire("recettes");
  if (!r) return;
  const corps = $("tiroir-corps");
  const zone = h("textarea", { class: "zone-code", rows: 8, spellcheck: "false" });
  zone.value = r.texte;
  const etat = h("div", { class: "sous" }, "");
  const corpsTable = h("tbody");
  const apercu = async () => {
    const a = await appel("apercu_recettes", zone.value);
    if (!a) return null;
    if (!a.ok) { toast(a.erreurs.join(" · "), true); return null; }
    etat.textContent = `${a.n} changement(s), ${a.ecartes} écarté(s). Rien n'est écrit.`;
    const raison = { candidature: "candidature : gardé", doublon: "doublon : gardé" };
    corpsTable.replaceChildren(...a.lignes.map((c) => h("tr", { class: c.ecarte ? "pale" : "" },
      h("td", {}, c.champ), h("td", {}, c.avant), h("td", {}, c.apres), h("td", {}, raison[c.ecarte] || ""))));
    return a;
  };
  const appliquer = async () => {
    const x = await ecrire("appliquer_recettes", zone.value);
    if (!x) return;
    if (x.tache) { fermerTiroir(); suivreTache(); } else toast(x.message);
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Recettes de nettoyage"),
      h("div", { class: "sous" }, "Une règle par ligne : champ | valeur à remplacer | nouvelle valeur. « re: » introduit un motif. Une offre à laquelle tu as postulé n'est jamais renommée."))),
    zone, etat,
    h("div", { class: "boutons" }, bouton("Aperçu", "loupe", apercu), bouton("Enregistrer et appliquer", "", appliquer, "plein")),
    h("div", { class: "defile" }, h("table", { class: "tableau-simple" },
      h("thead", {}, h("tr", {}, ["Champ", "Avant", "Après", "Remarque"].map((t) => h("th", {}, t)))), corpsTable)));
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
};

ACTIONS_OUTILS.comparer = async () => {
  const corps = $("tiroir-corps");
  const liste = h("div", { class: "liste-profils" });
  const diff = h("div", { class: "diff" });
  let choisi = null;
  const montrer = async (i) => {
    choisi = i;
    for (const el of liste.children) el.classList.toggle("on", Number(el.dataset.i) === i);
    const d = await ecrire("diff_document", i);
    if (!d) return diff.replaceChildren();
    diff.replaceChildren(...d.lignes.map(([g, p]) => h("p", { class: `diff-${{ "-": "moins", "+": "plus", "=": "egal" }[g]}` }, { "-": "− ", "+": "+ ", "=": "" }[g] + p)));
  };
  const remplir = async () => {
    const docs = (await ecrire("a_comparer")) || [];
    choisi = null;
    diff.replaceChildren(docs.length ? "" : h("div", { class: "sous" }, "Aucun document en attente de comparaison."));
    liste.replaceChildren(...docs.map((d) => h("div", { class: "ligne-profil", "data-i": d.i, onclick: () => montrer(d.i), style: "cursor:pointer" },
      h("span", {}, d.doc), h("span", { class: "etiq gris" }, `${d.ecart} paragraphe(s)`))));
    if (docs.length) montrer(docs[0].i);
  };
  const choisir = async (prendre) => {
    if (choisi == null) return;
    const r = await ecrire("choisir_version", choisi, prendre);
    if (r) { toast(r.message); remplir(); }
  };
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Documents à comparer"),
      h("div", { class: "sous" }, "Tu as retouché ces documents ; une version plus récente attend à côté. Rouge : seulement dans ta version. Vert : seulement dans la nouvelle. Celle que tu ne gardes pas est mise de côté, jamais supprimée."))),
    liste,
    h("div", { class: "boutons" }, bouton("Prendre la nouvelle version", "", () => choisir(true), "plein"), bouton("Garder ma version", "", () => choisir(false))),
    diff);
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
  remplir();
};

// Maintenance's cards, at the end of Réglages (the user, 2026-11-04: « maintenance et
// réglages dans le même panneau »): engine, backups, last collection, data, tools.
async function cartesMaintenance() {
  const m = await appel("maintenance");
  if (!m) return [];
  const c = m.collecte;
  return [
    h("div", { class: "pile" },
      h("div", { class: "sombre" }, h("h2", {}, "Moteur"), h("div", { class: "chiffre", style: "margin-top:14px" }, m.version),
        h("div", { class: "sous", style: "color:#8f8783" }, "version installée"),
        h("div", { class: "actions-col" }, bouton("Chercher une mise à jour", "fleche", verifierMaj, "plein bouton-maj")),
        h("div", { class: "sous etat-maj", style: "color:#8f8783;margin-top:8px" })),
      carte("Sauvegardes", h("div", { class: "sous", style: "margin:0 0 10px" }, "une par jour, sept jours glissants"), puces(m.sauvegardes))),
    carte("Dernière collecte",
      h("div", { class: c.etat === "ok" ? "etat ok" : "etat" }, c.etat === "ok" ? "Réussie" : (c.etat ? lisible(c.etat) : "inconnue")),
      h("dl", { class: "paires", style: "margin-top:14px" },
        h("dt", {}, "Début"), h("dd", {}, c.debut || "—"), h("dt", {}, "Fin"), h("dd", {}, c.fin || "—"),
        h("dt", {}, "Erreurs"), h("dd", {}, String(c.erreurs)), h("dt", {}, "Dernier succès"), h("dd", {}, c.dernier_succes || "—"))),
    carte("Données",
      h("dl", { class: "paires" },
        h("dt", {}, "Offres"), h("dd", {}, nombre(m.offres)), h("dt", {}, "Candidatures"), h("dd", {}, `${nombre(m.candidatures)} suivies · ${nombre(m.envoyees)} envoyées`),
        m.tailles.map((t) => [h("dt", {}, t.nom), h("dd", {}, taille(t.octets))])),
      m.archivables ? h("div", { class: "actions-col" }, bouton(`Archiver ${nombre(m.archivables)} vieilles offres…`, "corbeille", () => archiverVieilles(m.archivables))) : null,
      m.effacable ? h("div", { class: "actions-col" }, bouton("Effacer mes données…", "corbeille", () => effacerDonnees(m))) : null,
      m.desinstallable ? h("div", { class: "actions-col" }, bouton("Désinstaller JobHunter…", "corbeille", () => desinstaller(m))) : null),
    carteOutils(await appel("outils")),
  ];
}

// Old offers nobody will read: a button, never a nightly job (api.archiver says why).
async function archiverVieilles(n) {
  const ok = await dialogue("Archiver les vieilles offres ?",
    `${nombre(n)} offres collectées il y a plus de 60 jours, notées sous le seuil, jamais ouvertes et sans candidature ` +
    "quittent la file. Elles sont d'abord copiées dans la corbeille de JobHunter et la collecte ne les reprend pas.",
    null, [["Archiver", "plein", () => true]]);
  if (!ok) return;
  const r = await ecrire("archiver", 60);
  if (r) { toast(`${nombre(r.n)} offres archivées.${gardees(r)}`); redessiner(); }
}

// Uninstalling keeps Documents/JobHunter: this starts again from nothing (Recycle Bin).
async function effacerDonnees(m) {
  const ok = await dialogue("Effacer mes données ?",
    `Le profil, les CV, les lettres, les ${nombre(m.offres)} offres et les ${nombre(m.candidatures)} candidatures suivies ` +
    "partent à la Corbeille, la collecte du matin est arrêtée et JobHunter se ferme. " +
    "Tant que la Corbeille n'est pas vidée, on peut tout restaurer.",
    null, [["Effacer et fermer", "plein", () => true]]);
  if (!ok) return;
  const r = await appel("effacer_donnees");
  if (r && !r.ok) toast(r.message, true);
}

// Uninstalling from Windows kept the data (2026-11-04): this removes both at once.
async function desinstaller(m) {
  const sous = m.effacable
    ? `JobHunter est retiré de cet ordinateur. Le profil, les CV, les lettres, les ${nombre(m.offres)} offres et les ${nombre(m.candidatures)} candidatures suivies partent à la Corbeille, d'où on peut les restaurer tant qu'elle n'est pas vidée.`
    : "JobHunter est retiré de cet ordinateur. Tes données restent dans leur dossier : il n'est pas celui de l'application.";
  const ok = await dialogue("Désinstaller JobHunter ?", sous, null, [["Désinstaller", "plein", () => true]]);
  if (!ok) return;
  const r = await appel("desinstaller");
  if (r && !r.ok) toast(r.message, true);
}

// --- Navigation ---------------------------------------------------------------------

let courant = null;
// Display settings: --t drives every see-through surface of the native window (style.css).
let reglagesCourants = null;
function appliquerReglages(r) {
  if (!r) return;
  reglagesCourants = r;
  document.body.classList.toggle("menu-replie", r.menu === "etroit");
  if (r.par_page) filtresOffres.par_page = r.par_page;
  document.body.style.setProperty("--t", String(r.verre / 100));
  document.body.classList.toggle("sans-fond", r.fond === "aucun");
  document.body.dataset.teinte = r.teinte || "terre";
  modeAffiche = r.mode || "auto";
  appliquerMode();
  document.body.style.setProperty("--police", (POLICES.find(([v]) => v === r.police) || POLICES[0])[2]);
}

// One display setting changed outside the settings screen (menu, page size): the whole
// set goes back, since a missing key would be reset to its default.
async function garderReglage(maj) {
  if (!reglagesCourants || !window.pywebview) return;
  reglagesCourants = { ...reglagesCourants, ...maj };
  reglagesCourants = (await window.pywebview.api.regler(reglagesCourants)) || reglagesCourants;
}

// The side menu folded to its icons, for more room (the user, 2026-10-27).
function basculerMenu() {
  const replie = document.body.classList.toggle("menu-replie");
  garderReglage({ menu: replie ? "etroit" : "large" });
}

// Light or dark: "auto" follows Windows (WebView2 passes its setting to the page).
let modeAffiche = "auto";
const systemeSombre = window.matchMedia("(prefers-color-scheme: dark)");
function appliquerMode() {
  const sombre = modeAffiche === "sombre" || (modeAffiche === "auto" && systemeSombre.matches);
  document.documentElement.classList.toggle("mode-sombre", sombre);  // not "sombre": the dark card
}
systemeSombre.addEventListener("change", appliquerMode);
appliquerMode();
const MODES = [["auto", "Comme Windows"], ["clair", "Clair"], ["sombre", "Sombre"]];

// [value, label, CSS stack]: fonts every Windows 11 has, nothing to download.
const POLICES = [
  ["segoe", "Segoe", '"Segoe UI Variable Display", "Segoe UI", system-ui, sans-serif'],
  ["bahnschrift", "Bahnschrift", 'Bahnschrift, "Segoe UI", sans-serif'],
  ["corbel", "Corbel", 'Corbel, "Segoe UI", sans-serif'],
  ["sitka", "Sitka", '"Sitka Text", Sitka, Georgia, serif'],
  ["georgia", "Georgia", 'Georgia, "Times New Roman", serif'],
];
// [value, label, the three colours of its swatch]
const TEINTES = [
  ["terre", "Terre", ["#eaa476", "#c98366", "#a8766b"]],
  ["vert", "Vert", ["#a9d4b4", "#6fa98a", "#4e7f6a"]],
  ["bleu", "Bleu", ["#9fc4ec", "#6b97cf", "#4b6fa8"]],
  ["noir", "Noir et blanc", ["#d4d4d4", "#5e5e5e", "#161616"]],
];

const FONDS = [["acrylique", "Acrylique"], ["net", "Net"], ["mica", "Mica"], ["aucun", "Aucun"]];

ECRANS.reglages = {
  titre: "Réglages",
  actions: () => [],
  async dessiner(vue) {
    let r = (await appel("reglages")) || { fond: "acrylique", verre: 50, teinte: "terre", police: "segoe", mode: "auto" };
    const enregistrer = async (maj) => {
      r = { ...r, ...maj };
      appliquerReglages(r);
      if (window.pywebview) r = await window.pywebview.api.regler(r);
    };
    const valeur = h("span", { class: "compte" }, `${r.verre} %`);
    const curseur = h("input", {
      type: "range", min: 0, max: 100, step: 5, value: r.verre, class: "curseur",
      style: `--p:${r.verre}%`, disabled: r.fond === "aucun",
      oninput: (e) => {
        const v = Number(e.target.value);
        valeur.textContent = `${v} %`;
        e.target.style.setProperty("--p", `${v}%`);
        appliquerReglages({ ...r, verre: v });
      },
      onchange: (e) => enregistrer({ verre: Number(e.target.value) }),
    });
    const place = h("div");
    const dessinerFond = () => place.replaceChildren(segment(FONDS, r.fond, async (v) => {
      await enregistrer({ fond: v });
      curseur.disabled = v === "aucun";
      dessinerFond();
    }));
    dessinerFond();
    const teintes = h("div", { class: "nuancier" });
    const dessinerTeintes = () => teintes.replaceChildren(...TEINTES.map(([v, lib, c]) =>
      h("button", { class: `nuance ${v === r.teinte ? "on" : ""}`, title: lib, onclick: async () => { await enregistrer({ teinte: v }); dessinerTeintes(); } },
        h("span", { class: "pastille", style: `background:linear-gradient(135deg, ${c[0]}, ${c[1]} 55%, ${c[2]})` }), lib)));
    dessinerTeintes();
    const placeMode = h("div");
    const dessinerMode = () => placeMode.replaceChildren(segment(MODES, r.mode || "auto", async (v) => { await enregistrer({ mode: v }); dessinerMode(); }));
    dessinerMode();
    const polices = h("div", { class: "polices" });
    const dessinerPolices = () => polices.replaceChildren(...POLICES.map(([v, lib, pile]) =>
      h("button", { class: `police ${v === r.police ? "on" : ""}`, onclick: async () => { await enregistrer({ police: v }); dessinerPolices(); } },
        h("span", { class: "exemple", style: `font-family:${pile}` }, "Aa"), lib)));
    dessinerPolices();
    vue.replaceChildren(h("div", { class: "grille" },
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Apparence")),
        h("div", { class: "reglage" },
          h("div", {}, h("div", { class: "nom-reglage" }, "Fond de la fenêtre"),
            h("div", { class: "sous" }, "Acrylique : le bureau, flouté. Net : le bureau tel quel. Mica : une teinte douce. Aucun : opaque.")),
          place),
        h("div", { class: "reglage" },
          h("div", { class: "titre-ligne" }, h("div", { class: "nom-reglage" }, "Transparence"), valeur),
          h("div", { class: "ligne-curseur" }, h("span", {}, "Opaque"), curseur, h("span", {}, "Verre")),
          h("div", { class: "sous" }, "Combien le bureau transparaît derrière le fond de la fenêtre ; les cartes et les textes restent nets. La force du flou acrylique est fixée par Windows."))),
      h("div", { class: "verre panneau" },
        h("div", { class: "titre-ligne" }, h("h2", {}, "Couleurs et police")),
        h("div", { class: "reglage" }, h("div", { class: "nom-reglage" }, "Mode"), placeMode),
        h("div", { class: "reglage" }, h("div", { class: "nom-reglage" }, "Couleur"), teintes),
        h("div", { class: "reglage" }, h("div", { class: "nom-reglage" }, "Police"), polices)),
      await cartesParametres(),
      ...(await cartesMaintenance()),
      window.pywebview ? null : h("div", { class: "verre panneau" },
        h("div", { class: "sous" }, "Aperçu navigateur : ces réglages ne s'enregistrent que dans l'application."))));
  },
};

// The desktop's Paramètres page: language, update, daily collection, profiles.
async function verifierMaj(ev) {
  if (!window.pywebview) return toast(HORS_APPLI, true);
  const b = ev && ev.currentTarget;
  if (b) b.disabled = true;
  let v = {};
  try { v = (await window.pywebview.api.mise_a_jour()) || {}; }
  catch (e) { v = {}; }
  finally { if (b) b.disabled = false; }
  if (!v.derniere) return toast("Impossible de joindre le serveur des mises à jour : réessaie plus tard.", true);
  if (v.store) {
    // Installed from here, no Store window (3.74): JobHunter closes and opens again.
    if (!v.nouvelle) return toast(`À jour : ${v.installee}.`);
    const ok = await dialogue(`Version ${v.derniere} disponible`, `Installée : ${v.installee}. JobHunter se ferme pendant l'installation puis se rouvre de lui-même.`,
      null, [["Installer", "plein", () => true]]);
    if (ok) await lancer("maj");
    return;
  }
  // v.attente: the latest, published but not signed yet (its author signs within the hour)
  const suite = v.attente ? ` La ${v.attente} sera proposée dès que son auteur l'aura signée.` : "";
  if (!v.nouvelle) return toast(`À jour : ${v.installee}.${suite}`);
  const ok = await dialogue(`Version ${v.derniere} disponible`, `Installée : ${v.installee}. Elle est vérifiée (signature) avant d'être installée ; relance JobHunter ensuite.${suite}`,
    null, [["Installer", "plein", () => true]]);
  if (!ok) return;
  await lancer("maj");  // suivreTache → suivreMaj: the button and the Moteur card follow it
}

// At start-up: a newer signed version shows as a button in the title bar.
async function annonceMaj() {
  const v = await appel("annonce_maj").catch(() => null);
  if (!v) return;
  const b = $("maj");
  b.textContent = `Mettre à jour (${v.derniere})`;
  b.title = `Version installée : ${v.installee}`;
  b.hidden = false;
  b.onclick = clicMaj;
}
function clicMaj(ev) {
  if (ev.currentTarget.dataset.fait) return toast("Ferme JobHunter puis rouvre-le : la nouvelle version démarre.");
  return verifierMaj(ev);
}

async function cartesParametres() {
  const p = await appel("parametres");
  if (!p) return null;
  const relire = () => redessiner();
  const langue = h("select", { class: "choix", onchange: async (e) => {
    if (await ecrire("choisir_langue", e.target.value)) location.reload();  // the page redraws in it
  } }, Object.entries(p.langues).map(([c, n]) => h("option", { value: c, selected: c === p.langue }, n)));
  const heure = h("input", { class: "champ-texte", type: "time", value: "08:00", style: "width:120px" });
  const planif = !p.planif.disponible
    ? h("div", { class: "sous" }, "Planification disponible sous Windows (ailleurs : schedule.sh).")
    : p.planif.planifiee
      ? h("div", { class: "ligne-actions" }, h("span", { class: "etat ok" }, "Planifiée"),
          bouton("Retirer la collecte automatique", "", async () => {
            const ok = await dialogue("Retirer la collecte automatique ?", "Les offres ne seront plus collectées chaque jour.", null, [["Retirer", "chaud", () => true]]);
            if (ok && await ecrire("planifier", "")) { toast("Collecte automatique retirée."); relire(); }
          }))
      : h("div", { class: "ligne-actions" }, h("span", { class: "etat" }, "Pas planifiée"), heure,
          bouton("Collecter chaque jour à cette heure", "eclair", async () => {
            const r = await ecrire("planifier", heure.value);
            if (r) { toast(r.message || "Collecte planifiée."); relire(); }
          }, "plein"));
  return [
    h("div", { class: "pile" },
      carte("Langue",
        h("div", { class: "sous", style: "margin-bottom:10px" }, "Langue de l'interface, dans les deux fenêtres. Les lettres et les messages gardent la leur."), langue)),
    carte("Collecte automatique",
      h("div", { class: "sous", style: "margin-bottom:10px" }, "Chaque jour à l'heure choisie, l'ordinateur collecte les offres de tous tes profils, même si JobHunter est fermé."),
      planif),
  ];
}

// The Profiles panel (the user, 2026-10-27: « gérer les profils doit mener au panneau
// profils pour en changer un ou en rajouter un »): open one, add one, rename, archive.
async function gererProfils() {
  const corps = $("tiroir-corps");
  $("tiroir").classList.add("ouvert");
  $("voile").classList.add("ouvert");
  const p = await appel("parametres");
  if (!p) return corps.replaceChildren(h("div", { class: "vide" }, HORS_APPLI));
  const liste = p.profils.length ? p.profils : [{ slug: "", nom: "Principal" }];
  const nomDe = (x) => (!x.slug && p.titulaire) || x.nom;
  corps.replaceChildren(
    h("div", { class: "fiche-tete" }, h("div", {}, h("h2", {}, "Profils"),
      h("div", { class: "sous" }, "Un profil = une recherche à part : un autre métier, une autre ville, ou une autre personne. Chacun a ses offres, ses CV et ses lettres ; les clés des sites restent communes. Changer de profil relance la fenêtre."))),
    h("div", { class: "liste-profils" }, liste.map((x) =>
      h("div", { class: `ligne-profil ${x.slug === p.actif ? "on" : ""}` },
        h("span", { class: "t", translate: "no" }, nomDe(x)),
        x.slug === p.actif ? h("span", { class: "etiq gris" }, "ouvert")
          : bouton("Ouvrir", "sortie", () => ecrire("changer_profil", x.slug))))),
    h("div", { class: "boutons" },
      bouton("Nouveau profil depuis un CV…", "profil", () => { fermerTiroir(); nouveauProfil(); }, "plein"),
      p.actif ? bouton("Renommer", "", async () => {
        const champ = h("input", { class: "champ-texte", value: (p.profils.find((x) => x.slug === p.actif) || {}).nom || "" });
        const nom = await dialogue("Renommer le profil", "Seul le nom affiché change ; son dossier reste le même.", champ, [["Renommer", "plein", () => champ.value.trim() || undefined]]);
        if (nom && await ecrire("renommer_profil", nom)) gererProfils();
      }) : null,
      p.actif ? bouton("Archiver ce profil", "", async () => {
        const ok = await dialogue("Archiver ce profil ?", "Il est déplacé dans profiles/_archives (rien n'est supprimé), puis le profil principal s'ouvre.", null, [["Archiver", "chaud", () => true]]);
        if (ok) ecrire("archiver_profil");
      }) : null));
}

async function nouveauProfil() {
  const champ = h("input", { class: "champ-texte", placeholder: "par exemple : Chargée RSE à Lyon" });
  const nom = await dialogue("Nouveau profil", "1. Donne-lui un nom. 2. Choisis le CV de cette recherche (.docx ou .pdf). 3. La fenêtre s'ouvre sur ce nouveau profil, avec un formulaire rempli d'après le CV : vérifie, complète, valide. Ton profil actuel ne change pas.",
    champ, [["Choisir le CV…", "plein", () => champ.value.trim() || undefined]]);
  if (!nom) return;
  await ecrire("nouveau_profil", nom);  // the window restarts in the new profile's folder
}

async function aller(nom) {
  if (nom === "maintenance") nom = "reglages";  // merged into Réglages (3.82): a saved screen
  if (!ECRANS[nom]) nom = "accueil";
  courant = nom;
  fermerTiroir();
  // Relances: a page of Candidatures; the daily triage, one of Offres.
  const lien = { relances: "candidatures", tri: "offres" }[nom] || nom;
  for (const a of document.querySelectorAll(".menu a")) {
    a.classList.toggle("actif", a.dataset.ecran === lien);
    if (a.dataset.ecran === lien) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  const e = ECRANS[nom];
  $("titre").textContent = e.titre;
  $("actions").replaceChildren(...e.actions());
  const vue = $("vue");
  vue.scrollTop = 0;
  // A list screen keeps its filters in place: its list scrolls inside its panel, not the
  // page (the user, 2026-10-27). style.css: .vue.plein.
  vue.classList.toggle("plein", typeof e.plein === "function" ? e.plein() : !!e.plein);
  vue.dataset.ecran = nom;  // style.css: .vue[data-ecran=…]
  try { localStorage.setItem("jh-ecran", nom); } catch (_) { /* no storage: fine */ }
  // A screen reading the whole queue takes a second: the old one stayed in place under
  // the new title, as if the click had done nothing (2026-11-03). Past 150 ms, say so.
  const attente = setTimeout(() => {
    if (courant === nom) vue.replaceChildren(h("div", { class: "vide chargement" }, "Chargement…"));
  }, 150);
  try {
    await e.dessiner(vue);
  } catch (err) {
    console.error(err);
    vue.replaceChildren(h("div", { class: "vide" }, "Impossible de charger cet écran."));
  } finally {
    clearTimeout(attente);
  }
}

// Top left: the open profile, a round badge and its name; a click lists the others.
// The main profile shows its holder's name ("Principal" says little).
async function marqueProfil() {
  let p;
  try { p = await appel("parametres"); } catch (_) { return; }  // preview: "JobHunter" stays
  if (!p) return;
  const liste = p.profils.length ? p.profils : [{ slug: "", nom: "Principal" }];
  const ouvert = liste.find((x) => x.slug === p.actif) || liste[0];
  const nom = (!ouvert.slug && p.titulaire) || ouvert.nom;
  const initiales = (n) => n.split(/[\s\-_]+/).filter(Boolean).slice(0, 2).map((m) => m[0].toUpperCase()).join("");
  const rond = (n) => h("span", { class: "rond-profil", translate: "no" }, initiales(n));
  const menu = h("div", { class: "menu-profils" });
  // A press inside the badge or the list keeps it open: closing on it removed the list
  // before its click, and « Gérer les profils… » did nothing (the user, 2026-10-27).
  const fermer = (e) => {
    if (e && (marque.contains(e.target) || menu.contains(e.target))) return;
    menu.remove();
    document.removeEventListener("mousedown", fermer);
  };
  const marque = h("button", { class: "marque", title: "Changer de profil", onclick: () => {
    if (menu.isConnected) return fermer();
    menu.replaceChildren(
      h("div", { class: "titre-profils" }, "Profils"),
      ...liste.map((x) => {
        const n = (!x.slug && p.titulaire) || x.nom;
        return h("button", { class: x.slug === p.actif ? "on" : "", onclick: () => {
          fermer();
          if (x.slug !== p.actif) ecrire("changer_profil", x.slug);
        } }, rond(n), h("span", { translate: "no" }, n), x.slug === p.actif ? h("span", { class: "etiq gris" }, "ouvert") : null);
      }),
      h("button", { class: "gerer", onclick: () => { fermer(); gererProfils(); } }, "Gérer les profils…"));
    marque.after(menu);
    document.addEventListener("mousedown", fermer);
  } }, rond(nom), h("span", { class: "nom-profil", translate: "no" }, nom));
  document.querySelector(".menu .marque").replaceWith(marque);
}

async function demarrer() {
  // The language first: the first screen is drawn already translated.
  await appel("textes").then(chargerCatalogue).catch(() => { /* French */ });
  for (const a of document.querySelectorAll(".menu a[data-icone]")) {
    a.prepend(svg(a.dataset.icone));
    a.href = `#${a.dataset.ecran}`;  // a link with an address: reached by Tab, opened by Enter
    a.addEventListener("click", (e) => { e.preventDefault(); aller(a.dataset.ecran); });
  }
  suivreTiroir();
  marqueProfil();
  $("menu").append(h("button", { class: "replier", title: "Replier ou déplier le menu", onclick: basculerMenu },
    svg("panneau"), h("span", {}, "Replier le menu")));
  $("voile").addEventListener("click", fermerTiroir);
  $("fermer-tiroir").addEventListener("click", fermerTiroir);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermerTiroir(); });
  let debut = "accueil";
  try { debut = localStorage.getItem("jh-ecran") || debut; } catch (_) { /* no storage */ }
  aller(debut);
}

// --- The welcome (3.78): a folder without a profile, before the application ---------
// jobhunter.web.onboarding answers. A previous folder's data to take back, or the CV
// (chosen, or dropped: pywebview gives the dropped file's path to Python, which calls
// cvDepose), then the form prefilled from it; once the profile is written the window
// restarts on it. Until 3.77 these were customtkinter windows before this one.
let enBienvenue = false;

async function bienvenue(b) {
  enBienvenue = true;
  document.body.classList.add("sans-profil");
  await appel("textes").then(chargerCatalogue).catch(() => { /* French */ });
  if (b.message) toast(b.message.replace(/^!/, ""), b.message.startsWith("!"));
  if (b.cv) formulaireProfil(b.cv);
  else if (b.reprise && b.reprise.length) ecranReprise(b);
  else ecranCv();
}

function carteBienvenue(...enfants) {
  $("vue").replaceChildren(h("div", { class: "bienvenue" }, h("div", { class: "verre panneau" }, ...enfants)));
}

const plusTard = () => appel("plus_tard");

function ecranReprise(b) {
  const msg = h("p", { class: "erreur-texte", role: "alert" });
  const reprendre = async (dossier) => {
    msg.textContent = "Copie en cours…";
    const r = await appel("reprendre", dossier);
    if (r && r.ok === false) msg.textContent = r.erreur;
  };
  carteBienvenue(
    h("h1", { class: "grand-titre" }, "Bon retour"),
    h("p", { class: "sous" }, "Ce dossier est vide, mais un autre JobHunter a déjà ton profil. Reprends ses données (profil, CV, offres, candidatures) : elles sont copiées ici, l'ancien dossier ne change pas."),
    h("div", { class: "reprises" }, b.reprise.map((r) => h("div", { class: "reprise" },
      h("div", { class: "coupe" }, h("div", { translate: "no" }, r.dossier), h("div", { class: "sous" }, `profil du ${r.date}`)),
      bouton("Reprendre", "", () => reprendre(r.dossier), "plein")))),
    msg,
    h("div", { class: "boutons" },
      bouton("Autre dossier…", "", async () => {
        const c = await appel("choisir_ancien_dossier");
        if (c && c.erreur) msg.textContent = c.erreur;
        else if (c && c.dossier) reprendre(c.dossier);
      }),
      bouton("Nouveau profil", "", () => ecranCv())));
}

function ecranCv(erreur = "") {
  const msg = h("p", { class: "erreur-texte", role: "alert" }, erreur);
  const choisir = async () => {
    const c = await appel("choisir_cv");
    if (c && c.erreur) msg.textContent = c.erreur;
    else if (c && c.cv) formulaireProfil(c.cv);
  };
  const zone = h("div", { class: "depot-cv", tabindex: 0, role: "button", onclick: choisir,
    onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); choisir(); } } },
  h("strong", {}, "Dépose ton CV ici"), h("span", {}, "PDF ou Word"));
  for (const t of ["dragenter", "dragover"]) zone.addEventListener(t, (e) => { e.preventDefault(); zone.classList.add("survol"); });
  for (const t of ["dragleave", "drop"]) zone.addEventListener(t, () => zone.classList.remove("survol"));
  carteBienvenue(
    h("h1", { class: "grand-titre" }, "Bienvenue"),
    h("p", { class: "sous" }, "Aucun profil pour l'instant. Donne ton CV, en PDF (ou en Word) : JobHunter le lit puis te pose quelques questions."),
    zone, msg,
    h("div", { class: "boutons" }, bouton("Choisir mon CV…", "", choisir, "plein"), bouton("Plus tard", "", plusTard)));
}

// Called by Python (web/__main__.py) with the path of a file dropped on the window.
function cvDepose(chemin) {
  if (!enBienvenue) return;
  if (/\.(pdf|docx)$/i.test(chemin || "")) formulaireProfil(chemin);
  else ecranCv("Ce n'est pas un CV PDF ou Word : dépose-en un autre.");
}

async function formulaireProfil(cv) {
  carteBienvenue(h("h1", { class: "grand-titre" }, "Lecture du CV…"));
  const l = await appel("lire_cv", cv);
  if (!l || !l.ok) return ecranCv((l && l.erreur) || "");
  const p = l.propositions;
  const rep = { ...p, villes: "", secondaires: [], etranger: false, pays_etrangers: "" };
  const msg = h("p", { class: "erreur-texte", role: "alert" });
  const champ = (cle, lib, type = "text") => h("label", { class: "champ-form" }, h("span", {}, lib),
    h("input", { type, value: rep[cle] ?? "", oninput: (e) => { rep[cle] = e.target.value; } }));
  const coches = (cle) => h("div", { class: "secteurs" }, l.secteurs.map(([code, lib]) =>
    h("label", { class: "case-colonne" }, h("input", { type: "checkbox", checked: rep[cle].includes(code),
      onchange: (e) => { rep[cle] = e.target.checked ? [...rep[cle], code] : rep[cle].filter((x) => x !== code); } }), lib)));
  const coche = (cle, lib) => h("label", { class: "case-colonne" },
    h("input", { type: "checkbox", checked: !!rep[cle], onchange: (e) => { rep[cle] = e.target.checked; } }), lib);
  const pays = h("label", { class: "champ-form", hidden: true }, h("span", {}, "Pays ou régions"),
    h("input", { placeholder: "ex. : Suisse, Belgique, Europe, monde", oninput: (e) => { rep.pays_etrangers = e.target.value; } }));
  const ou = h("div", { class: "ou" });
  const dessinerOu = () => ou.replaceChildren(segment([[false, `Seulement en ${l.pays}`], [true, "Aussi à l'étranger"]], rep.etranger,
    (v) => { rep.etranger = v; pays.hidden = !v; dessinerOu(); }));
  dessinerOu();
  const genre = h("div", {});
  const dessinerGenre = () => genre.replaceChildren(segment([["m", "« diplômé »"], ["f", "« diplômée »"]], rep.genre,
    (v) => { rep.genre = v; dessinerGenre(); }));
  dessinerGenre();
  const parcours = h("textarea", { class: "champ-texte", rows: 5, oninput: (e) => { rep.parcours = e.target.value; } });
  parcours.value = rep.parcours || "";
  const source = h("span", { class: "sous" }, "Tiré de ton CV. Tu as déjà une lettre que tu aimes ? Reprends-en le paragraphe.");
  const word = l.pdf ? [
    h("div", { class: "boutons" }, coche("word", "Adapter mon CV à chaque offre"),
      bouton("Voir la version Word", "", async () => {
        const r = await appel("apercu_word", cv);
        if (r && r.ok === false) msg.textContent = r.erreur;
      })),
    h("p", { class: "sous" }, "Un PDF ne se modifie pas : il partirait identique pour chaque offre. JobHunter en refait une version Word, plus sobre, où les compétences demandées passent en premier. Ton PDF reste à côté ; décoche pour l'envoyer tel quel."),
  ] : [];
  const boutons = h("div", { class: "boutons" },
    bouton("Créer mon profil", "", async () => {
      msg.textContent = "";
      boutons.querySelectorAll("button").forEach((b) => { b.disabled = true; });
      const attente = h("p", { class: "sous" }, "Création du profil…");
      boutons.after(attente);
      const r = await appel("creer_mon_profil", cv, rep);
      if (!r || r.ok === false) {
        attente.remove();
        boutons.querySelectorAll("button").forEach((b) => { b.disabled = false; });
        msg.textContent = (r && r.erreur) || "Le profil n'a pas été créé.";
      }
    }, "plein"),
    bouton("Choisir un autre CV…", "", () => ecranCv()),
    bouton("Plus tard", "", plusTard));
  carteBienvenue(
    h("h1", { class: "grand-titre" }, "Ton profil"),
    h("p", { class: "sous", translate: "no" }, l.nom),
    l.peu ? h("p", { class: "erreur-texte" }, l.peu) : null,
    h("p", { class: "sous" }, "Vérifie et complète : rien n'est écrit tant que tu n'as pas validé."),
    h("div", { class: "formulaire" },
      champ("prenom", "Prénom"), champ("nom", "Nom"), champ("email", "Email"), champ("telephone", "Téléphone"),
      champ("ville", "Ville"), champ("metiers", "Métiers visés"), champ("annees", "Années d'expérience", "number"),
      h("div", { class: "champ-form" }, h("span", {}, "Accords"), genre)),
    h("p", { class: "sous" }, "Métiers séparés par des virgules ; années d'expérience stages compris ; les accords sont ceux de tes lettres."),
    sousTitre("Secteurs prioritaires"), coches("prioritaires"),
    sousTitre("Secteurs secondaires (facultatif)"), coches("secondaires"),
    h("label", { class: "champ-form" }, h("span", {}, "Autres villes"),
      h("input", { placeholder: "facultatif, séparées par des virgules", oninput: (e) => { rep.villes = e.target.value; } })),
    sousTitre("Où chercher"), ou, pays,
    coche("entreprises", "Suivre les ~90 entreprises de finance / ESG proposées"),
    sousTitre("Ton CV et tes lettres"), ...word,
    h("p", { class: "sous" }, "Le paragraphe de parcours de tes lettres"), parcours,
    h("div", { class: "boutons" }, bouton("Reprendre celui de ma lettre…", "", async () => {
      const r = await appel("parcours_de_ma_lettre");
      if (!r || r.annule) return;
      if (r.erreur) { source.textContent = r.erreur; return; }
      parcours.value = r.parcours; rep.parcours = r.parcours;
      source.textContent = `Repris de ${r.source}. Relis-le.`;
    }), source),
    msg, boutons);
}

// Native window: no Windows frame, our own title bar over a see-through background.
function natif() {
  document.body.classList.add("natif");
  appel("reglages").then(appliquerReglages).catch(() => { /* defaults from style.css */ });
  // Remote Desktop: no blur, no motion (style.css, body.leger).
  appel("session").then((s) => document.body.classList.toggle("leger", !!(s && s.distance))).catch(() => {});
  suivreTache();  // a task started before a reload keeps being followed
  for (const b of document.querySelectorAll(".feux button")) {
    b.addEventListener("click", () => window.pywebview.api.fenetre(b.dataset.action).then(iconePlein));
  }
  $("barre").addEventListener("dblclick", (e) => {
    if (!e.target.closest("button")) window.pywebview.api.fenetre("agrandir").then(iconePlein);
  });
  window.pywebview.api.fenetre("etat").then(iconePlein);
  window.pywebview.api.bienvenue().then((b) => {
    if (b && !b.profil) return bienvenue(b);  // no profile yet: the welcome (3.78)
    if (b && b.message) toast(b.message.replace(/^!/, ""), b.message.startsWith("!"));
    demarrer();
    annonceMaj();
  }).catch(() => { demarrer(); annonceMaj(); });  // never a blank window
  window.pywebview.api.demarrage().then((m) => { if (m) toast(m, m.startsWith("!")); });
  suivreFond();
}

// Full screen: the button shows two windows (« back to a window »), as Windows does;
// in a window, one square (the user, 2026-11-02).
function iconePlein(plein) {
  const b = document.querySelector('.feux [data-action="agrandir"]');
  if (!b || typeof plein !== "boolean") return;
  b.innerHTML = plein
    ? '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="4" width="6" height="6" rx="1.2"/><path d="M4 4V3.2C4 2.5 4.5 2 5.2 2H8.8C9.5 2 10 2.5 10 3.2V6.8C10 7.5 9.5 8 8.8 8H8"/></svg>'
    : '<svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2.5" y="2.5" width="7" height="7" rx="1.5"/></svg>';
  b.title = plein ? "Revenir à une fenêtre" : "Plein écran";
  b.setAttribute("aria-label", b.title);
}

// The background work (web.background): its news as toasts, the screen redrawn when
// it changed the data (descriptions, synced documents, new offers).
let versionFond = null;  // null until the first poll: no redraw at start
let vuFond = null;  // the last message seen; null until the first poll (no old news)
async function suivreFond() {
  const e = await window.pywebview.api.fond_etat().catch(() => null);
  if (e) {
    const m = e.messages[e.messages.length - 1];
    const cle = m ? m.heure + m.texte : "";
    // Only a failure is worth a toast: the progress is in the activity panel.
    if (vuFond !== null && cle && cle !== vuFond && m.texte.startsWith("!")) toast(m.texte, true);
    vuFond = cle;
    if (versionFond !== null && e.version !== versionFond) redessinerDonnees();
    versionFond = e.version;
    etatFond = e;
    dessinerActivite();
  }
  // Every 2 s while something runs in the background (its progress bar), else 20 s.
  setTimeout(suivreFond, e && e.activite ? 2000 : 20000);
}

if (window.pywebview) natif();
else window.addEventListener("pywebviewready", natif);
// Outside pywebview the event never comes: start on the demo after a short wait.
setTimeout(() => { if (!window.pywebview && !courant) demarrer(); }, 300);
