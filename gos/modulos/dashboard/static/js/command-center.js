/**
 * GOS Command Center — escena 3D holográfica (Three.js + bloom)
 */
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

const root = document.getElementById("scene-root");

let renderer, scene, camera, composer, clock;
let scoreGroup, arcGroup, floorMesh;
let barMeshes = [];
let arcMeshes = [];
let animTargets = [];
let pointer = { x: 0, y: 0 };
let activeCode = null;

export function initScene() {
  clock = new THREE.Clock();
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x030712, 0.028);

  camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
  camera.position.set(0, 9.5, 16);
  camera.lookAt(0, 1.2, 0);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  root.appendChild(renderer.domElement);

  const ambient = new THREE.AmbientLight(0x335577, 0.55);
  scene.add(ambient);
  const key = new THREE.PointLight(0x00e5ff, 2.2, 40);
  key.position.set(-6, 10, 6);
  scene.add(key);
  const fill = new THREE.PointLight(0xff2d95, 1.4, 36);
  fill.position.set(8, 6, -4);
  scene.add(fill);
  const rim = new THREE.PointLight(0xb8ff3c, 0.9, 30);
  rim.position.set(0, 4, -8);
  scene.add(rim);

  _buildFloor();
  _buildBackdrop();

  scoreGroup = new THREE.Group();
  scoreGroup.position.set(0, 0, 1.5);
  scene.add(scoreGroup);

  arcGroup = new THREE.Group();
  arcGroup.position.set(-5.5, 0, -1.5);
  scene.add(arcGroup);

  const renderPass = new RenderPass(scene, camera);
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.85, 0.55, 0.22);
  composer = new EffectComposer(renderer);
  composer.addPass(renderPass);
  composer.addPass(bloom);

  window.addEventListener("resize", onResize);
  window.addEventListener("pointermove", (e) => {
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.y = -(e.clientY / window.innerHeight) * 2 + 1;
  });
  onResize();
  animate();
}

function _buildFloor() {
  const geo = new THREE.PlaneGeometry(40, 40, 40, 40);
  const mat = new THREE.MeshStandardMaterial({
    color: 0x06101f,
    metalness: 0.7,
    roughness: 0.35,
    transparent: true,
    opacity: 0.92,
  });
  floorMesh = new THREE.Mesh(geo, mat);
  floorMesh.rotation.x = -Math.PI / 2;
  scene.add(floorMesh);

  const grid = new THREE.GridHelper(36, 36, 0x00e5ff, 0x12304a);
  grid.material.transparent = true;
  grid.material.opacity = 0.35;
  grid.position.y = 0.01;
  scene.add(grid);

  // anillo holográfico
  const ringGeo = new THREE.RingGeometry(4.2, 4.35, 96);
  const ringMat = new THREE.MeshBasicMaterial({
    color: 0x00e5ff,
    transparent: true,
    opacity: 0.45,
    side: THREE.DoubleSide,
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.03;
  scene.add(ring);

  const ring2 = ring.clone();
  ring2.scale.set(1.35, 1.35, 1.35);
  ring2.material = ringMat.clone();
  ring2.material.color.set(0xff2d95);
  ring2.material.opacity = 0.25;
  scene.add(ring2);
}

function _buildBackdrop() {
  const panel = new THREE.Mesh(
    new THREE.PlaneGeometry(22, 10),
    new THREE.MeshBasicMaterial({
      color: 0x0a1a33,
      transparent: true,
      opacity: 0.55,
    })
  );
  panel.position.set(0, 5, -8);
  scene.add(panel);

  // mini barras de fondo (decorativas)
  const bg = new THREE.Group();
  bg.position.set(4.5, 0.1, -6.5);
  for (let i = 0; i < 18; i++) {
    const h = 0.4 + Math.sin(i * 0.7) * 0.5 + Math.random() * 1.8;
    const m = new THREE.Mesh(
      new THREE.BoxGeometry(0.22, 1, 0.22),
      new THREE.MeshStandardMaterial({
        color: new THREE.Color().setHSL(0.52 + (i % 5) * 0.05, 0.9, 0.5),
        emissive: new THREE.Color().setHSL(0.52 + (i % 5) * 0.05, 0.95, 0.35),
        emissiveIntensity: 0.9,
        metalness: 0.4,
        roughness: 0.25,
      })
    );
    m.position.set(i * 0.32 - 2.5, h / 2, 0);
    m.scale.y = h;
    bg.add(m);
  }
  scene.add(bg);
}

function _clearGroup(group, store) {
  const children = [...group.children];
  for (const c of children) {
    group.remove(c);
    c.geometry?.dispose();
    if (Array.isArray(c.material)) c.material.forEach((m) => m.dispose());
    else c.material?.dispose();
  }
  store.length = 0;
}

function _makeBarMaterial(hex) {
  const color = new THREE.Color(hex);
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color.clone(),
    emissiveIntensity: 0.85,
    metalness: 0.55,
    roughness: 0.2,
    transparent: true,
    opacity: 0.95,
  });
}

/** Actualiza barras 3D con datos del summary API */
export function updateScene(data, focusCode = null) {
  if (!scoreGroup) return;
  activeCode = focusCode;
  _rebuildScoreBars(data, focusCode);
  _rebuildArc(data, focusCode);
}

function _rebuildScoreBars(data, focusCode) {
  animTargets = animTargets.filter((t) => arcMeshes.includes(t.mesh));
  _clearGroup(scoreGroup, barMeshes);

  const modules = (data.modules || []).filter((m) => m.ok !== false);
  const spacing = 1.35;
  const startX = -((modules.length - 1) * spacing) / 2;

  modules.forEach((mod, i) => {
    const score = Math.max(0, Math.min(100, Number(mod.score) || 0));
    const h = 0.35 + (score / 100) * 5.2;
    const mat = _makeBarMaterial(mod.color || "#00e5ff");
    if (focusCode && focusCode !== mod.code) {
      mat.opacity = 0.35;
      mat.emissiveIntensity = 0.35;
    }
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(0.7, 1, 0.7), mat);
    mesh.position.set(startX + i * spacing, 0, 0);
    mesh.scale.y = 0.01;
    mesh.userData = { targetH: h, code: mod.code };
    scoreGroup.add(mesh);
    barMeshes.push(mesh);
    animTargets.push({ mesh, targetH: h });

    const cap = new THREE.Mesh(
      new THREE.BoxGeometry(0.74, 0.06, 0.74),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: focusCode && focusCode !== mod.code ? 0.15 : 0.55,
      })
    );
    cap.position.y = 0.5;
    mesh.add(cap);
  });

  for (let i = 0; i < 5; i++) {
    const marker = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.08, 0.18, 12),
      new THREE.MeshStandardMaterial({
        color: 0x2afadf,
        emissive: 0x2afadf,
        emissiveIntensity: 1.2,
      })
    );
    marker.position.set(6.5 + (i % 3) * 0.55, 0.12, -1 + Math.floor(i / 3) * 0.7);
    scoreGroup.add(marker);
  }
}

function _rebuildArc(data, focusCode) {
  animTargets = animTargets.filter((t) => barMeshes.includes(t.mesh));
  _clearGroup(arcGroup, arcMeshes);

  const modules = (data.modules || []).filter((m) => m.ok !== false);
  const focused =
    modules.find((m) => m.code === focusCode) ||
    modules.find((m) => (m.bars || []).length) ||
    modules[0];
  const bars = (focused?.bars || []).slice(0, 16);
  const maxVal = Math.max(1, ...bars.map((b) => Number(b.value) || 0));
  const radius = 3.2;
  const span = Math.PI * 1.15;
  const startA = -Math.PI / 2 - span / 2;

  bars.forEach((b, i) => {
    const t = bars.length === 1 ? 0.5 : i / (bars.length - 1);
    const angle = startA + t * span;
    const val = Number(b.value) || 0;
    const h = 0.25 + (val / maxVal) * 3.4;
    const color = focused?.color || "#ff9f1c";
    const mat = _makeBarMaterial(color);
    mat.emissiveIntensity = 0.7;
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(0.28, 1, 0.28), mat);
    mesh.position.set(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
    mesh.lookAt(0, 0, 0);
    mesh.scale.y = 0.01;
    arcGroup.add(mesh);
    arcMeshes.push(mesh);
    animTargets.push({ mesh, targetH: h });
  });
}

export function setFocus(code, data = null) {
  activeCode = code;
  barMeshes.forEach((mesh) => {
    const on = !code || mesh.userData.code === code;
    mesh.material.opacity = on ? 0.95 : 0.32;
    mesh.material.emissiveIntensity = on ? 0.95 : 0.3;
    const cap = mesh.children[0];
    if (cap?.material) cap.material.opacity = on ? 0.55 : 0.15;
  });
  if (data) _rebuildArc(data, code);
}

function onResize() {
  const w = root.clientWidth || window.innerWidth;
  const h = root.clientHeight || window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
  composer.setSize(w, h);
}

function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();

  animTargets.forEach(({ mesh, targetH }) => {
    const cur = mesh.scale.y;
    const next = cur + (targetH - cur) * 0.06;
    mesh.scale.y = next;
    mesh.position.y = next / 2;
  });

  scoreGroup.rotation.y = Math.sin(t * 0.25) * 0.08 + pointer.x * 0.12;
  arcGroup.rotation.y = t * 0.12;
  camera.position.x += (pointer.x * 1.8 - camera.position.x) * 0.03;
  camera.position.y += (9.5 + pointer.y * 0.8 - camera.position.y) * 0.03;
  camera.lookAt(0, 1.4, 0);

  if (floorMesh) {
    floorMesh.rotation.z = Math.sin(t * 0.15) * 0.01;
  }

  composer.render();
}
