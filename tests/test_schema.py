"""Error codes of the resource.v1 record and lineage manifest contracts (schema.py)."""

from __future__ import annotations

import unittest
from typing import Any

from book_data_api.config import DATASET_NAME, SCHEMA_VERSION
from book_data_api.schema import (
    DataContractError,
    error_payload,
    validate_bronze_document,
    validate_manifest,
    validate_record,
    validate_records,
)


def record(**changes: Any) -> dict[str, Any]:
    base = {
        "id": "resource-001",
        "name": "Ledger Lens",
        "category": "finance",
        "observed_at": "2026-10-01T00:00:00Z",
        "source_url": "https://example.invalid/ledger-lens",
    }
    base.update(changes)
    return base


def manifest(**changes: Any) -> dict[str, Any]:
    base = {
        "manifest_version": "1",
        "source": "local-sanitized-fixture",
        "dataset": DATASET_NAME,
        "source_object": "data/landing/source_records.json",
        "bronze_object": "data/bronze/resource_records.v1.json",
        "source_sha256": "a" * 64,
        "bronze_sha256": "b" * 64,
        "record_count": 2,
    }
    base.update(changes)
    return base


class SchemaTests(unittest.TestCase):
    def assert_code(self, code: str, call: Any, *args: Any, **kwargs: Any) -> DataContractError:
        with self.assertRaises(DataContractError) as raised:
            call(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def test_valid_record_is_returned_unchanged(self) -> None:
        self.assertEqual(validate_record(record(), index=0), record())

    def test_record_must_be_an_object(self) -> None:
        self.assert_code("SCHEMA001", validate_record, ["not", "an", "object"], index=3)

    def test_extra_or_missing_fields_are_refused_with_both_lists(self) -> None:
        error = self.assert_code("SCHEMA002", validate_record, record(owner="x"), index=1)
        self.assertIn("owner", error.details["actual_fields"])
        self.assertNotIn("owner", error.details["expected_fields"])

    def test_observed_at_needs_iso_8601_with_a_timezone(self) -> None:
        self.assert_code("SCHEMA003", validate_record, record(observed_at="yesterday"), index=0)
        self.assert_code("SCHEMA003", validate_record, record(observed_at="2026-10-01T00:00:00"), index=0)

    def test_records_must_be_an_array_without_duplicate_ids(self) -> None:
        self.assert_code("SCHEMA004", validate_records, {"records": []})
        self.assert_code("SCHEMA005", validate_records, [record(), record()])

    def test_bronze_document_pins_schema_version_and_dataset(self) -> None:
        good = {"schema_version": SCHEMA_VERSION, "dataset": DATASET_NAME, "records": [record()]}
        self.assertEqual(validate_bronze_document(good)[2], [record()])
        self.assert_code("SCHEMA011", validate_bronze_document, {**good, "schema_version": "resource.v2"})
        self.assert_code("SCHEMA012", validate_bronze_document, {**good, "dataset": "other"})

    def test_manifest_digests_must_be_lowercase_sha256(self) -> None:
        self.assertEqual(validate_manifest(manifest()), manifest())
        self.assert_code("LINEAGE014", validate_manifest, manifest(source_sha256="A" * 64))
        self.assert_code("LINEAGE014", validate_manifest, manifest(bronze_sha256="b" * 63))

    def test_manifest_record_count_must_be_a_non_negative_integer(self) -> None:
        self.assert_code("LINEAGE015", validate_manifest, manifest(record_count=-1))
        self.assert_code("LINEAGE015", validate_manifest, manifest(record_count="2"))
        # bool is an int subclass in Python; a manifest saying `true` is not a count.
        self.assert_code("LINEAGE015", validate_manifest, manifest(record_count=True))

    def test_error_payload_is_the_stable_envelope(self) -> None:
        self.assertEqual(
            error_payload("SCHEMA001", "bad", None),
            {"error": {"code": "SCHEMA001", "message": "bad", "details": {}}},
        )


if __name__ == "__main__":
    unittest.main()
