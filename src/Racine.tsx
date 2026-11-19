import React from "react";
import { Composition } from "remotion";
import { Actu, Plan } from "./Actu";

const vide: Plan = {
  fps: 24, duree: 48, titre: "Titre", date: "", sources: [], audio: "", mascotte: {}, parole: [],
  scenes: [], sous_titres: [], graine: 1,
};

export const Racine: React.FC = () => (
  <Composition
    id="Actu"
    component={Actu}
    width={1080}
    height={1920}
    fps={24}
    durationInFrames={48}
    defaultProps={vide}
    calculateMetadata={({ props }) => ({ durationInFrames: props.duree, fps: props.fps })}
  />
);
