import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from automation.search_archive import (
    ArtifactCollision,
    ArtifactMissing,
    ContentAddressedArchive,
    InvalidArtifactPath,
)
from automation.search_recovery import InjectedFault
from automation.search_types import ArtifactRef, hash_bytes


class TestSearchArchive(unittest.TestCase):
    def test_deduplicates_and_verifies_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            first = archive.put_text("hello")
            second = archive.put_text("hello")
            self.assertEqual(first, second)
            self.assertEqual(archive.verify(first), b"hello")

    def test_collision_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            archive._digest = lambda data: "a" * 64  # type: ignore[method-assign]
            archive.put_bytes(b"one", category="objects", suffix=".bin")
            with self.assertRaises(ArtifactCollision):
                archive.put_bytes(b"two", category="objects", suffix=".bin")

    def test_fault_before_rename_has_no_authoritative_artifact(self) -> None:
        seen = []

        def fault(point, path):
            seen.append((point, path))
            if point == "before_artifact_rename":
                raise InjectedFault(point)

        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory, fault_hook=fault)
            with self.assertRaises(InjectedFault):
                archive.put_text("interrupted")
            self.assertEqual(list((Path(directory) / "artifacts").rglob("*.c")), [])
            self.assertIn("before_artifact_rename", [item[0] for item in seen])

    def test_verify_rejects_file_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external = Path(outside) / "outside.bin"
            data = b"outside"
            external.write_bytes(data)
            destination = root / "artifacts" / "objects"
            destination.mkdir(parents=True)
            link = destination / "escape.bin"
            try:
                link.symlink_to(external)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlinks unavailable: " + str(exc))
            reference = ArtifactRef(
                hash_bytes(data),
                "artifacts/objects/escape.bin",
                "application/octet-stream",
                len(data),
            )
            with self.assertRaises(InvalidArtifactPath):
                ContentAddressedArchive(root).verify(reference)

    def test_publication_rejects_file_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            data = b"publication must stay inside"
            external = Path(outside) / "outside.bin"
            external.write_bytes(b"untouched")
            archive = ContentAddressedArchive(root)
            destination = archive._path_for(archive._digest(data), "objects", ".bin")
            destination.parent.mkdir(parents=True)
            try:
                destination.symlink_to(external)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlinks unavailable: " + str(exc))
            with self.assertRaises(InvalidArtifactPath):
                archive.put_bytes(data, category="objects", suffix=".bin")
            self.assertEqual(external.read_bytes(), b"untouched")

    def test_publication_rejects_directory_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            category = root / "artifacts" / "objects"
            category.parent.mkdir(parents=True)
            try:
                category.symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlinks unavailable: " + str(exc))
            with self.assertRaises(InvalidArtifactPath):
                ContentAddressedArchive(root).put_bytes(
                    b"must stay inside",
                    category="objects",
                    suffix=".bin",
                )
            self.assertEqual(tuple(Path(outside).iterdir()), ())

    def test_collision_that_vanishes_is_not_returned_as_a_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = ContentAddressedArchive(directory)
            data = b"race"
            digest = archive._digest(data)
            destination = archive._path_for(digest, "objects", ".bin")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            temporary = destination.parent / ".race.tmp"
            temporary.write_bytes(data)

            def vanished_link(source, target):
                Path(target).unlink()
                raise FileExistsError(target)

            with patch("automation.search_archive.os.link", side_effect=vanished_link):
                with self.assertRaises(ArtifactMissing):
                    archive._publish_exclusive(temporary, destination, data)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
