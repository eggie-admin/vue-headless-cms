from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.cms.models import CmsUpsert
from app.cms.store import CmsConflictError, delete_document, get_document, list_documents, runtime_manifest, upsert_document


class CmsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["CMS_STATE_DB"] = str(pathlib.Path(self.tempdir.name) / "cms.sqlite3")

    def tearDown(self) -> None:
        os.environ.pop("CMS_STATE_DB", None)
        self.tempdir.cleanup()

    def test_seeded_documents_exist(self):
        ids = {item.id for item in list_documents()}
        self.assertTrue({"ui-manifest", "scene-manifest", "content"}.issubset(ids))

    def test_revisioned_update_and_conflict(self):
        created = upsert_document("test-doc", CmsUpsert(kind="content", title="Test", payload={"value": 1}))
        self.assertEqual(created.revision, 1)
        updated = upsert_document("test-doc", CmsUpsert(kind="content", title="Test", payload={"value": 2}, expected_revision=1))
        self.assertEqual(updated.revision, 2)
        with self.assertRaises(CmsConflictError):
            upsert_document("test-doc", CmsUpsert(kind="content", title="Stale", payload={}, expected_revision=1))

    def test_runtime_manifest_and_delete(self):
        upsert_document("asset-manifest", CmsUpsert(kind="asset_manifest", title="Assets", payload={"items": []}))
        manifest = runtime_manifest()
        self.assertGreaterEqual(manifest.revision, 4)
        self.assertIsNotNone(get_document("asset-manifest"))
        self.assertTrue(delete_document("asset-manifest", expected_revision=1))
        self.assertIsNone(get_document("asset-manifest"))


if __name__ == "__main__":
    unittest.main()
