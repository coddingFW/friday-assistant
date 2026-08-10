import { useEffect, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/examples/jsm/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { audioPlayer } from "../services/audioPlayer";
import type { StatusState } from "../types";

const LABELS: Record<StatusState, string> = {
  idle: "Pronta",
  thinking: "Pensando…",
  searching: "Buscando…",
  responding: "Respondendo…",
};

// Amplitude máxima do lip-sync no blendshape `jawOpen` (0..1).
const JAW_OPEN_MAX = 0.7;

/**
 * Avatar 3D do Friday: rosto humano realista (modelo `facecap.glb`, ARKit
 * blendshapes, MIT). A fala é animada pelo blendshape `jawOpen` conforme a
 * amplitude do áudio; pisca sozinho pelos `eyeBlink_*`; em "pensando" levanta as
 * sobrancelhas (`browInnerUp`) e inclina levemente a cabeça. A cabeça faz um
 * leve balanço idle. Roda 100% offline via WebGL.
 *
 * O modelo usa texturas KTX2 (transcoder em `public/basis/`) e geometria
 * comprimida com Meshopt — por isso o loader precisa do `KTX2Loader` e do
 * `MeshoptDecoder`.
 */
export function Avatar3D({ status }: { status: StatusState }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const statusRef = useRef<StatusState>(status);
  statusRef.current = status;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const size = 240;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size);
    renderer.setClearAlpha(0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(28, 1, 0.01, 100);

    // Ambiente discreto (reflexos suaves na pele), sem lavar as cores.
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environmentIntensity = 0.4;

    // Iluminação neutra de estúdio.
    const hemi = new THREE.HemisphereLight(0xffffff, 0x2a2a3a, 0.9);
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.6);
    keyLight.position.set(-1.0, 1.4, 2.2);
    const fillLight = new THREE.DirectionalLight(0xdfeaff, 0.5);
    fillLight.position.set(1.5, 0.4, 1.0);
    const rimLight = new THREE.DirectionalLight(0x88aaff, 0.5); // contorno frio suave
    rimLight.position.set(0.2, 1.2, -2.0);
    scene.add(hemi, keyLight, fillLight, rimLight);

    // Post-processing: bloom bem sutil só para um leve glow de contorno.
    const composer = new EffectComposer(renderer);
    composer.setSize(size, size);
    composer.addPass(new RenderPass(scene, camera));
    const bloom = new UnrealBloomPass(new THREE.Vector2(size, size), 0.12, 0.6, 0.9);
    composer.addPass(bloom);

    let face: THREE.Mesh | null = null;
    let morphIndex: Record<string, number> = {};
    let model: THREE.Object3D | null = null;
    let disposed = false;

    const setMorph = (name: string, value: number) => {
      const i = morphIndex[name];
      if (i !== undefined && face?.morphTargetInfluences) {
        face.morphTargetInfluences[i] = value;
      }
    };

    const ktx2 = new KTX2Loader().setTranscoderPath("/basis/").detectSupport(renderer);
    const loader = new GLTFLoader().setKTX2Loader(ktx2).setMeshoptDecoder(MeshoptDecoder);
    loader.load(
      "/models/facecap.glb",
      (gltf) => {
        if (disposed) return;
        model = gltf.scene;
        scene.add(model);
        model.updateWorldMatrix(true, true);

        // O rosto é a única malha com blendshapes (mesh_2, 52 morphs ARKit).
        model.traverse((o) => {
          const mesh = o as THREE.Mesh;
          if (mesh.isMesh && mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
            face = mesh;
            morphIndex = mesh.morphTargetDictionary;
          }
        });

        // Enquadramento a partir do bounding box: rosto de frente (+Z), mirando
        // um pouco acima do centro para pegar cabeça + parte do pescoço.
        const box = new THREE.Box3().setFromObject(model);
        const bbSize = box.getSize(new THREE.Vector3());
        const bbCenter = box.getCenter(new THREE.Vector3());
        const fovRad = (camera.fov * Math.PI) / 180;
        const target = new THREE.Vector3(bbCenter.x, bbCenter.y + bbSize.y * 0.06, bbCenter.z);
        const dist = (bbSize.y * 0.72) / 2 / Math.tan(fovRad / 2);
        camera.position.set(target.x, target.y, box.max.z + dist);
        camera.lookAt(target);
      },
      undefined,
      (err) => console.error("[Avatar3D] falha ao carregar o modelo:", err),
    );

    const clock = new THREE.Clock();
    let jawCur = 0;
    let browCur = 0;
    let tiltCur = 0;
    let nextBlinkAt = 1.5;
    let blinkStart = -1;
    let raf = 0;

    const animate = () => {
      raf = requestAnimationFrame(animate);
      const dt = clock.getDelta();
      const t = clock.elapsedTime;

      if (face) {
        const thinking =
          statusRef.current === "thinking" || statusRef.current === "searching";

        // Lip-sync: abre a boca (`jawOpen`) conforme a amplitude, com suavização.
        const jawTarget = Math.min(1, audioPlayer.amplitude()) * JAW_OPEN_MAX;
        jawCur += (jawTarget - jawCur) * Math.min(1, dt * 18);
        setMorph("jawOpen", jawCur);

        // Piscar: pulso rápido dos dois olhos em intervalos ~irregulares.
        if (blinkStart < 0 && t >= nextBlinkAt) blinkStart = t;
        let blink = 0;
        if (blinkStart >= 0) {
          const p = (t - blinkStart) / 0.16; // duração ~160ms
          if (p >= 1) {
            blinkStart = -1;
            nextBlinkAt = t + 2.5 + Math.random() * 3.5;
          } else {
            blink = Math.sin(p * Math.PI); // 0 → 1 → 0
          }
        }
        setMorph("eyeBlink_L", blink);
        setMorph("eyeBlink_R", blink);

        // "Pensando": sobrancelhas internas levantadas (`browInnerUp`).
        const browTarget = thinking ? 0.5 : 0;
        browCur += (browTarget - browCur) * Math.min(1, dt * 6);
        setMorph("browInnerUp", browCur);
      }

      // Cabeça (raiz do modelo): balanço idle + leve inclinação em "pensando".
      if (model) {
        const thinking =
          statusRef.current === "thinking" || statusRef.current === "searching";
        const swayY = Math.sin(t * 0.5) * 0.05;
        const swayX = Math.sin(t * 0.33) * 0.02;
        const tiltTarget = thinking ? 0.1 : 0;
        tiltCur += (tiltTarget - tiltCur) * Math.min(1, dt * 4);
        model.rotation.set(swayX, swayY, tiltCur + Math.sin(t * 1.5) * (thinking ? 0.03 : 0));
      }

      composer.render();
    };
    animate();

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      composer.dispose();
      pmrem.dispose();
      ktx2.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className="avatar3d">
      <div className="avatar3d__stage">
        <div ref={mountRef} className="avatar3d__canvas" />
      </div>
      <div className="avatar__label">{LABELS[status]}</div>
    </div>
  );
}
