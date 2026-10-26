// Home screen. Data comes from Python (window.pywebview.api.tableau); opened as a
// plain file it falls back to demo.json, so the page can be looked at in a browser.
// Offer titles come from the web: every text goes through textContent, never innerHTML.
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
  coche: "M12 3a9 9 0 1 1 0 18 9 9 0 0 1 0-18zm-1.2 12.3 5.2-5.2-1.3-1.3-3.9 3.9-1.8-1.8-1.3 1.3z",
  etoile: "m12 3 2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z",
};

function svg(nom) {
  const ns = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(ns, "svg");
  s.setAttribute("viewBox", "0 0 24 24");
  const p = document.createElementNS(ns, "path");
  p.setAttribute("d", ICONES[nom] || "");
  s.appendChild(p);
  return s;
}

// h("div", {class: "x"}, "texte", enfant…) — builds an element; strings become text nodes.
function h(tag, attrs, ...enfants) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v;
    else if (k === "style") e.style.cssText = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const c of enfants) if (c != null) e.append(c instanceof Node ? c : String(c));
  return e;
}

const nombre = (n) => Number(n || 0).toLocaleString("fr-FR");
const JOURS = ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."];
const jourCourt = (iso) => {
  const d = new Date(iso + "T12:00:00");
  return isNaN(d) ? iso : `${JOURS[d.getDay()]} ${d.getDate()}`;
};
const dateFr = (iso) => (iso ? iso.split("-").reverse().slice(0, 2).join("/") : "");

function ouvrir(url) {
  if (window.pywebview) window.pywebview.api.ouvrir(url);
  else if (/^https?:\/\//.test(url)) window.open(url, "_blank", "noopener");
}

function dessiner(d) {
  const stats = document.getElementById("stats");
  stats.replaceChildren(
    ...[
      ["valise", "Offres en file", d.stats.file],
      ["etoile", "Notées 9 à traiter", d.stats.neuf],
      ["avion", "En attente de réponse", d.stats.postulees],
    ].map(([ic, lab, val]) =>
      h("div", { class: "stat" }, h("span", { class: "rond" }, svg(ic)),
        h("div", {}, h("div", { class: "lab" }, lab), h("div", { class: "val" }, nombre(val))))
    )
  );

  const col = d.collecte;
  const dernier = col.length ? col[col.length - 1] : { n: 0 };
  const avant = col.slice(0, -1);
  const moyenne = avant.length ? avant.reduce((s, c) => s + c.n, 0) / avant.length : 0;
  document.getElementById("dernier").textContent = `+${nombre(dernier.n)}`;
  document.getElementById("ecart").textContent = moyenne
    ? `${dernier.n >= moyenne ? "+" : "−"}${Math.abs(Math.round(100 * (dernier.n - moyenne) / moyenne))} % par rapport à la moyenne`
    : "";

  const max = Math.max(1, ...col.map((c) => c.n));
  const barres = document.getElementById("barres");
  const axes = [100, 75, 50, 25, 0].map((p) =>
    h("div", { class: "axe", style: `top:${(1 - p / 100) * 168}px` },
      h("span", {}, nombre(Math.round(max * p / 100)))));
  const cols = col.map((c) => {
    const plein = h("div", { class: "plein", style: "height:0" });
    requestAnimationFrame(() => requestAnimationFrame(() => {
      plein.style.height = `${Math.max(6, 100 * c.n / max)}%`;
    }));
    return h("div", { class: "col", title: `${nombre(c.n)} offres` },
      h("div", { class: "tube" }, plein), h("div", { class: "jour" }, jourCourt(c.jour)));
  });
  barres.replaceChildren(...axes, ...cols);

  document.getElementById("meilleures").replaceChildren(
    ...d.meilleures.map((o, i) =>
      h("li", { onclick: () => ouvrir(o.url), title: o.poste },
        h("span", { class: "score" }, nombre(o.fit), h("b", {}, i + 1)),
        h("div", { style: "min-width:0" },
          h("div", { class: "t" }, o.poste),
          h("div", { class: "s" }, o.entreprise))))
  );

  const relances = document.getElementById("relances");
  relances.replaceChildren(
    ...(d.relances.length
      ? d.relances.map((r) =>
          h("li", {}, h("div", { class: "t" }, `Relancer ${r.entreprise}`),
            h("div", { class: "s", title: r.poste }, `${r.jours} j · ${r.poste}`)))
      : [h("li", { class: "vide" }, "Rien à relancer aujourd'hui")])
  );

  document.getElementById("zones").replaceChildren(
    ...d.zones.map((z) =>
      h("div", { class: "zone" },
        h("div", {}, h("div", { class: "lab" }, z.zone), h("div", { class: "val" }, nombre(z.n))),
        h("div", { class: "tuile" }, h("i", { style: `width:${z.pct}%` }), h("span", {}, `${z.pct} %`))))
  );

  document.getElementById("candidatures").replaceChildren(
    ...d.candidatures.map((c) =>
      h("tr", {},
        h("td", {}, c.entreprise),
        h("td", { title: c.poste }, c.poste),
        h("td", {}, h("span", { class: `etiq ${c.statut}` }, c.statut)),
        h("td", {}, dateFr(c.date)),
        h("td", {}, c.fit == null ? "—"
          : h("div", { class: "prog", title: `${c.fit}/10` }, h("i", { style: `width:${c.fit * 10}%` })))))
  );
}

function icones() {
  for (const a of document.querySelectorAll(".menu a[data-icone]")) a.prepend(svg(a.dataset.icone));
}

async function charger() {
  try {
    if (window.pywebview) return dessiner(await window.pywebview.api.tableau());
    const r = await fetch("demo.json");
    if (r.ok) dessiner(await r.json());
  } catch (e) {
    console.error(e);
  }
}

icones();
if (window.pywebview) charger();
else window.addEventListener("pywebviewready", charger);
// Outside pywebview the event never comes: load the demo after a short wait.
setTimeout(() => { if (!window.pywebview) charger(); }, 300);
