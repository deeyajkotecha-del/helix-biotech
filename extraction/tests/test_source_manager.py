import json
import pytest
from extraction.source_manager import SourceManager
from extraction.exceptions import DuplicateSourceError


def _meta(name="Corp Deck", date="2026-01", type_="corporate_presentation"):
    return {"name": name, "date": date, "type": type_}


class TestRegisterSource:
    def test_creates_index_if_not_exists(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        index = json.loads((tmp_path / "KYMR" / "sources" / "index.json").read_text())
        assert len(index["sources"]) == 1
        assert index["sources"][0]["id"] == "src1"

    def test_adds_to_existing_index(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        sm.register_source("KYMR", "src2", _meta(name="Investor Day"))
        index = json.loads((tmp_path / "KYMR" / "sources" / "index.json").read_text())
        assert len(index["sources"]) == 2
        ids = {s["id"] for s in index["sources"]}
        assert ids == {"src1", "src2"}

    def test_creates_metadata_json(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        meta_path = tmp_path / "KYMR" / "sources" / "src1" / "metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["id"] == "src1"
        assert meta["name"] == "Corp Deck"
        assert meta["type"] == "corporate_presentation"
        assert meta["company"] == "KYMR"
        assert meta["date"] == "2026-01"
        assert meta["total_slides"] is None
        assert meta["extraction_status"] == "pending"
        assert meta["verification_status"] == "unverified"
        assert meta["slide_map"] == {}

    def test_prevents_duplicate_source_id(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        with pytest.raises(DuplicateSourceError):
            sm.register_source("KYMR", "src1", _meta())

    def test_overwrite_allows_duplicate(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        sm.register_source("KYMR", "src1", _meta(name="Updated"), overwrite=True)
        meta = sm.get_source("KYMR", "src1")
        assert meta["name"] == "Updated"
        index = json.loads((tmp_path / "KYMR" / "sources" / "index.json").read_text())
        assert len(index["sources"]) == 1

    def test_validates_ticker_format(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid ticker"):
            sm.register_source("kymr", "src1", _meta())
        with pytest.raises(ValueError, match="Invalid ticker"):
            sm.register_source("TOOLONG", "src1", _meta())

    def test_validates_required_fields(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        with pytest.raises(ValueError, match="name"):
            sm.register_source("KYMR", "src1", {"date": "2026-01", "type": "press_release"})
        with pytest.raises(ValueError, match="date"):
            sm.register_source("KYMR", "src1", {"name": "X", "type": "press_release"})
        with pytest.raises(ValueError, match="type"):
            sm.register_source("KYMR", "src1", {"name": "X", "date": "2026-01"})

    def test_validates_source_type(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        with pytest.raises(ValueError, match="Invalid source type"):
            sm.register_source("KYMR", "src1", _meta(type_="invalid_type"))


class TestGetSource:
    def test_get_source_returns_metadata(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        meta = sm.get_source("KYMR", "src1")
        assert meta["id"] == "src1"
        assert meta["company"] == "KYMR"

    def test_get_source_not_found(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            sm.get_source("KYMR", "nonexistent")


class TestListSources:
    def test_list_sources_empty(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        assert sm.list_sources("KYMR") == []


class TestUpdateSource:
    def test_update_source(self, tmp_path):
        sm = SourceManager(data_root=str(tmp_path))
        sm.register_source("KYMR", "src1", _meta())
        sm.update_source("KYMR", "src1", {"total_slides": 67, "name": "Updated Name"})

        meta = sm.get_source("KYMR", "src1")
        assert meta["total_slides"] == 67
        assert meta["name"] == "Updated Name"

        # Check index was synced
        sources = sm.list_sources("KYMR")
        assert sources[0]["total_slides"] == 67
        assert sources[0]["name"] == "Updated Name"
