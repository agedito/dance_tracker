import json
import urllib

from services.mediapipe.requests import *


# ─── Client ───────────────────────────────────────────────────────────────────

class MPVisionClient:
    """
    Cliente para la MPVision API.

    Args:
        base_url: URL base del servidor, ej: "http://localhost:8000"
        timeout:  Timeout en segundos para las peticiones (default: 30)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _post(self, path: str, body: dict, params: dict | None = None) -> dict:
        url = self.base_url + path
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                url += "?" + query

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = json.loads(e.read()) if e.fp else str(e)
            raise MPVisionError(e.code, detail) from e

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(self.base_url + path)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = json.loads(e.read()) if e.fp else str(e)
            raise MPVisionError(e.code, detail) from e

    def _build_params(self, render: bool, output_name: Optional[str]) -> dict:
        params: dict = {"render": str(render).lower()}
        if output_name is not None:
            params["output_name"] = output_name
        return params

    # ── Endpoints ─────────────────────────────────────────────────────────────

    def health(self) -> dict:
        """Comprueba que el servidor está levantado."""
        return self._get("/health")

    def models(self) -> dict:
        """Lista los modelos disponibles."""
        return self._get("/models")

    def pose(
            self,
            request: PoseRequest,
            render: bool = True,
            output_name: Optional[str] = None,
    ) -> PoseDetectionResponse:
        """Detecta poses humanas en una imagen."""
        raw = self._post("/pose", request.to_dict(), self._build_params(render, output_name))
        return PoseDetectionResponse.from_dict(raw)

    def bbox(
            self,
            request: BBoxRequest,
            render: bool = True,
            output_name: Optional[str] = None,
    ) -> BBoxDetectionResponse:
        """Detecta bounding boxes de personas en una imagen."""
        raw = self._post("/bbox", request.to_dict(), self._build_params(render, output_name))
        return BBoxDetectionResponse.from_dict(raw)

    def segmentation(
            self,
            request: SegmentationRequest,
            render: bool = True,
            output_name: Optional[str] = None,
    ) -> SegmentationResponse:
        """Segmenta personas en una imagen."""
        raw = self._post("/segmentation", request.to_dict(), self._build_params(render, output_name))
        return SegmentationResponse.from_dict(raw)

    def pose_batch(
            self,
            request: PoseBatchRequest,
            render: bool = True,
            output_name: Optional[str] = None,
    ) -> BatchResponse:
        """Detecta poses en todos los frames de una carpeta."""
        raw = self._post("/pose/batch", request.to_dict(), self._build_params(render, output_name))
        return BatchResponse.from_dict(raw)

    def bbox_batch(
            self,
            request: BBoxBatchRequest,
            render: bool = True,
            output_name: Optional[str] = None,
    ) -> BatchResponse:
        """Detecta bounding boxes en todos los frames de una carpeta."""
        raw = self._post("/bbox/batch", request.to_dict(), self._build_params(render, output_name))
        return BatchResponse.from_dict(raw)

    def segmentation_batch(
            self,
            request: SegBatchRequest,
            render: bool = True,
            output_name: Optional[str] = None,
    ) -> BatchResponse:
        """Segmenta personas en todos los frames de una carpeta."""
        raw = self._post("/segmentation/batch", request.to_dict(), self._build_params(render, output_name))
        return BatchResponse.from_dict(raw)
