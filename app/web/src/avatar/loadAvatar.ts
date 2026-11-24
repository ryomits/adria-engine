import { VRM, VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

export async function loadAvatar(url: string): Promise<VRM> {
  const loader = new GLTFLoader();
  loader.register((parser) => new VRMLoaderPlugin(parser));
  const gltf = await loader.loadAsync(url);
  const vrm: unknown = gltf.userData.vrm;
  if (!(vrm instanceof VRM)) throw new Error(`${url} is not a VRM file`);
  VRMUtils.removeUnnecessaryVertices(gltf.scene);
  VRMUtils.combineSkeletons(gltf.scene);
  VRMUtils.rotateVRM0(vrm); // VRM 0.x faces -Z; make every model face +Z
  vrm.scene.traverse((obj) => {
    obj.frustumCulled = false;
  });
  return vrm;
}
