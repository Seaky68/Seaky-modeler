import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Audio, Img, continueRender, delayRender, staticFile, useCurrentFrame,
} from "remotion";

// ------------------------------------------------------------------ types
export type Acteur = {
  src: string; pos: string; x: number; sol: number; hauteur: number;
  entree: string; f_entree: number; action: string; f_action: number; graine: number;
};
export type Scene = { debut: number; fin: number; decor: string; mascotte: string; acteurs: Acteur[]; graine: number };
export type Mot = { texte: string; debut: number; fin: number };
export type Groupe = { debut: number; fin: number; mots: Mot[] };
export type Plan = {
  fps: number; duree: number; titre: string; date: string; sources: string[]; audio: string;
  mascotte: Record<string, string>; parole: number[][]; scenes: Scene[]; sous_titres: Groupe[]; graine: number;
};

// ------------------------------------------------------------------ outils stop-motion
// Tout bouge « en deux » : une nouvelle pose toutes les 2 images (12 poses par seconde), comme en stop-motion.
const pas = (f: number) => f - (f % 2);
const alea = (a: number, b: number) => {
  const x = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return x - Math.floor(x);
};
// la pâte « vit » : petit décalage différent à chaque pose, comme une figurine touchée entre deux photos
const vibre = (graine: number, f: number, force = 1) => {
  const p = pas(f) / 2;
  return {
    dx: (alea(graine, p) - 0.5) * 3 * force,
    dy: (alea(graine + 7, p) - 0.5) * 3 * force,
    rot: (alea(graine + 13, p) - 0.5) * 0.7 * force,
    s: 1 + (alea(graine + 21, p) - 0.5) * 0.008 * force,
  };
};
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const sortieRebond = (t: number) => {
  const c1 = 1.9, c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
const sortieDouce = (t: number) => 1 - Math.pow(1 - t, 3);

const BRUN = "#3b2416";
const POLICE = "Fredoka";

// ------------------------------------------------------------------ police
const usePolice = () => {
  const [poignee] = useState(() => delayRender("police"));
  useEffect(() => {
    const fichiers = ["fonts/Fredoka-Bold.woff2", "fonts/Fredoka-Bold-ext.woff2"];
    Promise.all(
      fichiers.map((f) => new FontFace(POLICE, `url(${staticFile(f)}) format('woff2')`, { weight: "700" }).load()),
    )
      .then((liste) => {
        liste.forEach((x) => (document.fonts as unknown as { add: (f: FontFace) => void }).add(x));
        continueRender(poignee);
      })
      .catch(() => continueRender(poignee));
  }, [poignee]);
};

// ------------------------------------------------------------------ décor
const Decor: React.FC<{ scene: Scene; f: number }> = ({ scene, f }) => {
  const local = pas(f - scene.debut);
  const duree = Math.max(1, scene.fin - scene.debut);
  const t = clamp(local / duree);
  const v = vibre(scene.graine, f, 0.6);
  const zoom = 1.06 + 0.07 * t;
  const sens = scene.graine % 2 ? 1 : -1;
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img
        src={staticFile(scene.decor)}
        style={{
          width: "100%", height: "100%", objectFit: "cover",
          transform: `translate(${v.dx + sens * 30 * t}px, ${v.dy - 18 * t}px) rotate(${v.rot * 0.4}deg) scale(${zoom})`,
          filter: "saturate(1.08)",
        }}
      />
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------------ acteurs (figurines détourées)
const ActeurVue: React.FC<{ a: Acteur; f: number }> = ({ a, f }) => {
  const p = pas(f) - a.f_entree;
  if (p < 0) return null;
  let x = 0, y = 0, sx = 1, sy = 1, rot = 0, ombre = 1;

  // entrée
  if (a.entree === "pop") {
    const t = clamp(p / 8);
    const s = t < 1 ? Math.max(0, sortieRebond(t)) : 1;
    sx = s; sy = s;
  } else if (a.entree === "tombe") {
    if (p < 8) {
      const t = p / 8;
      y = -1500 * (1 - t * t);
      sy = 1.12; sx = 0.92;
      ombre = 0.3 + 0.7 * t;
    } else if (p < 10) { sx = 1.28; sy = 0.74; }
    else if (p < 12) { sx = 0.9; sy = 1.1; }
    else if (p < 14) { sx = 1.04; sy = 0.97; }
  } else {
    const dir = a.entree === "glisse_gauche" ? -1 : 1;
    if (p < 14) {
      const t = sortieDouce(p / 14);
      x = dir * 760 * (1 - t);
      y = -Math.abs(Math.sin((p / 2) * 1.3)) * 34 * (1 - t);
      rot = dir * -6 * (1 - t);
    }
  }

  // action sur un mot
  const q = pas(f) - a.f_action;
  if (a.f_action > 0 && q >= 0) {
    if (a.action === "saute" && q < 16) {
      if (q < 2) { sx *= 1.15; sy *= 0.85; }
      else if (q < 14) {
        const t = (q - 2) / 12;
        y -= Math.sin(t * Math.PI) * 210;
        sy *= 1.08; sx *= 0.94;
        ombre *= 1 - 0.5 * Math.sin(t * Math.PI);
      } else { sx *= 1.2; sy *= 0.82; }
    } else if (a.action === "tremble" && q < 16) {
      x += (q % 4 < 2 ? -10 : 10);
      rot += (q % 4 < 2 ? -3 : 3);
    } else if (a.action === "tourne" && q < 12) {
      sx *= Math.cos((q / 12) * Math.PI * 2);
      if (Math.abs(sx) < 0.15) sx = sx < 0 ? -0.15 : 0.15;
    } else if (a.action === "grossit") {
      const s = 1 + 0.22 * (q < 10 ? Math.max(0, sortieRebond(q / 10)) : 1);
      sx *= s; sy *= s;
    }
  }

  // respiration + vibration de la pâte
  const v = vibre(a.graine, f, 1.2);
  sy *= 1 + 0.012 * Math.sin((pas(f) / 2) * 0.9 + a.graine);
  const largeurOmbre = a.hauteur * 0.62;
  return (
    <>
      <div
        style={{
          position: "absolute", left: a.x - largeurOmbre / 2 + x, top: a.sol - 18,
          width: largeurOmbre, height: 40, borderRadius: "50%",
          background: "radial-gradient(ellipse at center, rgba(30,15,5,0.55), rgba(30,15,5,0) 70%)",
          opacity: ombre, transform: `scaleX(${Math.abs(sx)})`,
        }}
      />
      <div
        style={{
          position: "absolute", left: a.x - 600, top: a.sol - a.hauteur, width: 1200, height: a.hauteur,
          display: "flex", justifyContent: "center", alignItems: "flex-end",
          transformOrigin: "50% 100%",
          transform: `translate(${x + v.dx}px, ${y + v.dy}px) rotate(${rot + v.rot}deg) scale(${sx * v.s}, ${sy * v.s})`,
        }}
      >
        <Img
          src={staticFile(a.src)}
          style={{ height: "100%", maxWidth: 760, objectFit: "contain", filter: "drop-shadow(6px 10px 10px rgba(40,20,5,0.35))" }}
        />
      </div>
    </>
  );
};

// ------------------------------------------------------------------ Pâtou, la mascotte
const Mascotte: React.FC<{ plan: Plan; scene: Scene; f: number }> = ({ plan, scene, f }) => {
  const p = pas(f);
  const parle = plan.parole.some(([a, b]) => f >= a && f < b);
  const ouverte = parle && Math.floor(p / 4) % 2 === 0;
  const expr = scene.mascotte || "neutre";
  const src = plan.mascotte[`${expr}_${ouverte ? "ouverte" : "fermee"}`] || plan.mascotte.neutre_fermee;
  if (!src) return null;
  const entree = clamp((p - 4) / 8);
  if (p < 4) return null;
  const s = entree < 1 ? Math.max(0, sortieRebond(entree)) : 1;
  const v = vibre(plan.graine + 99, f, 1);
  const bob = ouverte ? -8 : 0;
  // petit sursaut à chaque changement de scène
  const depuis = p - pas(scene.debut);
  const sursaut = scene.debut > 0 && depuis >= 0 && depuis < 6 ? (depuis < 2 ? 0.88 : depuis < 4 ? 1.08 : 1) : 1;
  return (
    <div
      style={{
        position: "absolute", left: 28, top: 1190, width: 330, height: 340,
        display: "flex", justifyContent: "center", alignItems: "flex-end", transformOrigin: "50% 100%",
        transform: `translate(${v.dx}px, ${v.dy + bob}px) rotate(${v.rot}deg) scale(${s * v.s}, ${s * v.s * sursaut})`,
      }}
    >
      <div style={{ position: "absolute", bottom: -10, width: 230, height: 36, borderRadius: "50%",
        background: "radial-gradient(ellipse at center, rgba(30,15,5,0.5), rgba(30,15,5,0) 70%)" }} />
      <Img src={staticFile(src)} style={{ height: "100%", maxWidth: 330, objectFit: "contain",
        filter: "drop-shadow(5px 8px 8px rgba(40,20,5,0.35))" }} />
    </div>
  );
};

// ------------------------------------------------------------------ textes
const contour = (px: number): React.CSSProperties => ({
  WebkitTextStroke: `${px}px ${BRUN}`, paintOrder: "stroke fill",
});

const SousTitres: React.FC<{ plan: Plan; f: number }> = ({ plan, f }) => {
  const g = plan.sous_titres.find((x) => f >= x.debut && f < x.fin);
  if (!g) return null;
  const p = pas(f) - pas(g.debut);
  const s = p < 6 ? Math.max(0.5, sortieRebond(clamp(p / 6))) : 1;
  const rot = (alea(g.debut, 3) - 0.5) * 5;
  const v = vibre(g.debut, f, 0.7);
  return (
    <div style={{
      position: "absolute", top: 330, left: 60, width: 960, display: "flex", flexWrap: "wrap",
      justifyContent: "center", columnGap: 44, rowGap: 4,
      transform: `translate(${v.dx}px, ${v.dy}px) rotate(${rot}deg) scale(${s})`,
    }}>
      {g.mots.map((m, i) => {
        const actif = f >= m.debut && (f < m.fin + 2 || i === g.mots.length - 1);
        return (
          <span key={i} style={{
            display: "inline-block", fontFamily: POLICE, fontWeight: 700, fontSize: 96,
            lineHeight: 1.15, color: actif ? "#ffd23f" : "#fffaf0", ...contour(16),
            transform: `scale(${actif ? 1.12 : 1}) rotate(${(alea(g.debut, i) - 0.5) * 6}deg)`,
            textShadow: "0 8px 0 rgba(59,36,22,0.55)",
          }}>{m.texte}</span>
        );
      })}
    </div>
  );
};

const Titre: React.FC<{ plan: Plan; f: number }> = ({ plan, f }) => {
  const fin = Math.round(2.6 * plan.fps);
  const p = pas(f);
  if (p > fin + 6) return null;
  let s = p < 10 ? Math.max(0, sortieRebond(clamp(p / 10))) : 1;
  let sy = 1;
  if (p > fin) { const t = (p - fin) / 6; s *= 1 - t; sy = 1 + 0.3 * t; }
  const v = vibre(7, f, 1);
  return (
    <AbsoluteFill style={{ alignItems: "center", top: 600, height: 520 }}>
      <div style={{ transform: `translate(${v.dx}px, ${v.dy}px) rotate(${-2 + v.rot}deg) scale(${s}, ${s * sy})`,
        display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div style={{
          background: "#f2672e", color: "#fffaf0", fontFamily: POLICE, fontWeight: 700, fontSize: 44,
          padding: "10px 34px", borderRadius: 40, border: `7px solid ${BRUN}`, marginBottom: -14, zIndex: 2,
          transform: "rotate(3deg)", boxShadow: `0 8px 0 ${BRUN}`,
        }}>L'ACTU EN PÂTE · {plan.date}</div>
        <div style={{
          background: "#fff3d6", border: `9px solid ${BRUN}`, borderRadius: 60, padding: "48px 50px 40px",
          width: 900, boxShadow: `0 16px 0 ${BRUN}, inset 0 -14px 0 rgba(200,150,90,0.35), inset 0 10px 0 rgba(255,255,255,0.6)`,
          fontFamily: POLICE, fontWeight: 700, fontSize: 84, lineHeight: 1.08, color: BRUN, textAlign: "center",
        }}>{plan.titre}</div>
      </div>
    </AbsoluteFill>
  );
};

const Badge: React.FC<{ plan: Plan; f: number }> = ({ plan, f }) => {
  const debut = Math.round(2.6 * plan.fps) + 4;
  const p = pas(f) - debut;
  if (p < 0) return null;
  const s = p < 8 ? Math.max(0, sortieRebond(clamp(p / 8))) : 1;
  const derniere = plan.scenes[plan.scenes.length - 1];
  const sources = derniere && f >= derniere.debut + 10 && plan.sources.length;
  return (
    <div style={{ position: "absolute", top: 160, left: 40, transformOrigin: "0 50%",
      transform: `rotate(-3deg) scale(${s})` }}>
      <div style={{ display: "inline-block", background: "#f2672e", color: "#fffaf0", fontFamily: POLICE, fontWeight: 700,
        fontSize: 40, padding: "8px 28px", borderRadius: 34, border: `6px solid ${BRUN}`, boxShadow: `0 7px 0 ${BRUN}` }}>
        L'ACTU EN PÂTE
      </div>
      {sources ? (
        <div style={{ marginTop: 14, display: "inline-block", marginLeft: 10, background: "#fff3d6", color: BRUN,
          fontFamily: POLICE, fontWeight: 700, fontSize: 30, padding: "6px 22px", borderRadius: 26,
          border: `5px solid ${BRUN}`, transform: "rotate(2deg)" }}>
          Sources : {plan.sources.join(", ")}
        </div>
      ) : null}
    </div>
  );
};

// ------------------------------------------------------------------ transition « boule de pâte »
const COULEURS = ["#f2672e", "#4aa3df", "#f7c440", "#7cc36a", "#e05a8a"];
const Transition: React.FC<{ plan: Plan; f: number }> = ({ plan, f }) => {
  const p = pas(f);
  const coupe = plan.scenes.slice(1).map((s) => s.debut).find((c) => Math.abs(p - c) <= 8);
  if (coupe === undefined) return null;
  const d = Math.abs(p - coupe);
  const r = 1250 * sortieDouce(clamp(1 - d / 8));
  if (r < 5) return null;
  const i = plan.scenes.findIndex((s) => s.debut === coupe);
  const coul = COULEURS[i % COULEURS.length];
  const pts: string[] = [];
  const n = 28;
  for (let k = 0; k <= n; k++) {
    const a = (k / n) * Math.PI * 2;
    const rr = r * (1 + 0.06 * Math.sin(a * 5 + i) + 0.03 * (alea(i * 50 + k, pas(f)) - 0.5));
    pts.push(`${540 + Math.cos(a) * rr},${960 + Math.sin(a) * rr}`);
  }
  return (
    <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
      <defs>
        <radialGradient id="bp" cx="40%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity={0.35} />
          <stop offset="60%" stopColor="#ffffff" stopOpacity={0} />
          <stop offset="100%" stopColor="#000000" stopOpacity={0.25} />
        </radialGradient>
      </defs>
      <polygon points={pts.join(" ")} fill={coul} stroke={BRUN} strokeWidth={10} strokeLinejoin="round" />
      <polygon points={pts.join(" ")} fill="url(#bp)" />
    </svg>
  );
};

// ------------------------------------------------------------------ lumière de plateau et grain de pellicule
const Lumiere: React.FC<{ f: number; graine: number }> = ({ f, graine }) => {
  const p = pas(f) / 2;
  const scintille = (alea(graine + 5, p) - 0.5) * 0.05;
  return (
    <>
      <AbsoluteFill style={{
        background: "radial-gradient(ellipse at 50% 40%, rgba(255,240,210,0) 45%, rgba(60,30,10,0.38) 100%)",
      }} />
      <AbsoluteFill style={{ background: scintille > 0 ? "#fff6e0" : "#1a0d05", opacity: Math.abs(scintille) }} />
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, opacity: 0.07, mixBlendMode: "overlay" }}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={p % 50} /></filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </>
  );
};

// ------------------------------------------------------------------ composition
export const Actu: React.FC<Plan> = (plan) => {
  usePolice();
  const f = useCurrentFrame();
  const scene = plan.scenes.find((s) => f >= s.debut && f < s.fin) || plan.scenes[plan.scenes.length - 1];
  if (!scene) return <AbsoluteFill style={{ background: "#f2d6a2" }} />;
  return (
    <AbsoluteFill style={{ background: "#2b1a10" }}>
      <Decor scene={scene} f={f} />
      {scene.acteurs.map((a, i) => <ActeurVue key={i} a={a} f={f} />)}
      <Lumiere f={f} graine={plan.graine} />
      <Mascotte plan={plan} scene={scene} f={f} />
      <SousTitres plan={plan} f={f} />
      <Badge plan={plan} f={f} />
      <Titre plan={plan} f={f} />
      <Transition plan={plan} f={f} />
      {plan.audio ? <Audio src={staticFile(plan.audio)} /> : null}
    </AbsoluteFill>
  );
};
