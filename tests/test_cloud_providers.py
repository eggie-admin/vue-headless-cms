from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.cloud.google import build_veo_request
from app.cloud.huggingface import REPO_ID
from app.cloud.models import DriveArchiveRequest, VeoGenerateRequest


class CloudProviderContractTests(unittest.TestCase):
    def test_veo_request_is_pinned_and_vertical(self) -> None:
        env = {
            "GOOGLE_CLOUD_PROJECT": "cathedral-test",
            "GOOGLE_CLOUD_LOCATION": "us-central1",
            "GOOGLE_VEO_MODEL": "veo-3.1-generate-001",
            "GOOGLE_VEO_OUTPUT_GCS_URI": "gs://cathedral-test/video",
        }
        with patch.dict(os.environ, env, clear=False):
            url, body = build_veo_request(
                VeoGenerateRequest(prompt="Detroit rain on steel", aspect_ratio="9:16", duration_seconds=8)
            )
        self.assertTrue(url.startswith("https://us-central1-aiplatform.googleapis.com/"))
        self.assertIn("veo-3.1-generate-001:predictLongRunning", url)
        self.assertEqual(body["parameters"]["aspectRatio"], "9:16")
        self.assertEqual(body["parameters"]["durationSeconds"], 8)
        self.assertEqual(body["parameters"]["storageUri"], "gs://cathedral-test/video")

    def test_last_frame_requires_first_frame(self) -> None:
        with self.assertRaises(ValidationError):
            VeoGenerateRequest(prompt="test", last_frame_gcs_uri="gs://bucket/last.png")

    def test_drive_archive_requires_canonical_gcs_uri(self) -> None:
        with self.assertRaises(ValidationError):
            DriveArchiveRequest(gcs_uri="https://example.com/video.mp4", name="video.mp4")

    def test_hf_repo_id_is_bounded(self) -> None:
        self.assertIsNotNone(REPO_ID.fullmatch("google/gemma-3-4b-it"))
        self.assertIsNone(REPO_ID.fullmatch("../../etc/passwd"))


if __name__ == "__main__":
    unittest.main()
