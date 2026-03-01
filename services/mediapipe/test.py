import client as mpipe

# ─── Quick usage example ──────────────────────────────────────────────────────

url = r"http://localhost:9000"
img = "frame_pn.jpg"

if __name__ == "__main__":
    client = mpipe.MPVisionClient(url, timeout=None)

    print("Health:", client.health())
    print("Models:", client.models())

    # Pose
    pose_resp = client.pose(mpipe.PoseRequest(image_path=img), render=False)
    print(f"Poses detectadas: {pose_resp.num_poses} en {pose_resp.elapsed_ms:.1f}ms")
    for i, pose in enumerate(pose_resp.poses):
        nose = next((lm for lm in pose.landmarks if lm.name == "NOSE"), None)
        if nose:
            print(f"  Pose {i} - Nariz: ({nose.x:.3f}, {nose.y:.3f})")

    # BBox
    bbox_resp = client.bbox(mpipe.BBoxRequest(image_path=img))
    print(f"Personas detectadas: {bbox_resp.num_persons}")
    for p in bbox_resp.persons:
        print(f"  BBox: ({p.x}, {p.y}) {p.width}x{p.height} score={p.score:.2f}")

    # Segmentación
    seg_resp = client.segmentation(mpipe.SegmentationRequest(
        image_path=img,
        model_name=mpipe.SegModelName.SELFIE,
        mode=mpipe.SegMode.OVERLAY,
    ))
    for seg in seg_resp.segments:
        print(f"  Segmento '{seg.name}': {seg.percentage:.1f}% ({seg.pixel_count}px)")

    # Batch
    batch_resp = client.pose_batch(mpipe.PoseBatchRequest(folder_path="pn/"), render=True)
    print(f"Batch: {batch_resp.processed}/{batch_resp.total_frames} frames procesados")
