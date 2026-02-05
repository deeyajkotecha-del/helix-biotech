"""
Tests for Helix data files and server pages.
"""
import unittest
import json
from pathlib import Path

# FastAPI TestClient
from fastapi.testclient import TestClient


# Path to data directory
DATA_DIR = Path(__file__).parent.parent / "data"
COMPANIES_DIR = DATA_DIR / "companies"


class TestDataFiles(unittest.TestCase):
    """Validates all JSON files parse correctly."""

    def test_all_json_files_parse(self):
        """Every .json file in data/ should be valid JSON."""
        json_files = list(DATA_DIR.rglob("*.json"))
        self.assertGreater(len(json_files), 0, "No JSON files found in data/")

        errors = []
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                errors.append(f"{json_file}: {e}")

        if errors:
            self.fail(f"JSON parse errors:\n" + "\n".join(errors))

    def test_company_directories_have_company_json(self):
        """Each company directory should have a company.json file."""
        company_dirs = [
            d for d in COMPANIES_DIR.iterdir()
            if d.is_dir() and d.name not in ("TEMPLATE", "__pycache__")
        ]

        missing = []
        for company_dir in company_dirs:
            company_json = company_dir / "company.json"
            if not company_json.exists():
                missing.append(str(company_dir))

        if missing:
            self.fail(f"Missing company.json in: {missing}")


class TestRequiredFields(unittest.TestCase):
    """Checks company JSONs have required fields."""

    REQUIRED_COMPANY_FIELDS = ["ticker", "name"]
    REQUIRED_ASSET_FIELDS = ["name", "stage"]

    def _get_company_dirs(self):
        """Get all company directories (excluding TEMPLATE)."""
        return [
            d for d in COMPANIES_DIR.iterdir()
            if d.is_dir() and d.name not in ("TEMPLATE", "__pycache__")
        ]

    def test_company_json_has_required_fields(self):
        """Each company.json should have ticker and name."""
        errors = []
        for company_dir in self._get_company_dirs():
            company_json = company_dir / "company.json"
            if not company_json.exists():
                continue

            with open(company_json) as f:
                data = json.load(f)

            for field in self.REQUIRED_COMPANY_FIELDS:
                if field not in data:
                    errors.append(f"{company_dir.name}/company.json missing '{field}'")

        if errors:
            self.fail("\n".join(errors))

    def test_asset_json_has_required_fields(self):
        """Each asset .json should have name and stage."""
        errors = []
        for company_dir in self._get_company_dirs():
            asset_files = [
                f for f in company_dir.glob("*.json")
                if f.name != "company.json"
            ]

            for asset_file in asset_files:
                with open(asset_file) as f:
                    data = json.load(f)

                # Check in root or under 'asset' key
                asset_data = data.get("asset", data)

                for field in self.REQUIRED_ASSET_FIELDS:
                    if field not in asset_data:
                        errors.append(f"{company_dir.name}/{asset_file.name} missing '{field}'")

        if errors:
            self.fail("\n".join(errors))

    def test_kymr_has_assets(self):
        """KYMR should have at least 3 asset files."""
        kymr_dir = COMPANIES_DIR / "KYMR"
        asset_files = [f for f in kymr_dir.glob("*.json") if f.name != "company.json"]
        self.assertGreaterEqual(len(asset_files), 3, f"KYMR should have at least 3 assets, found {len(asset_files)}")


class TestServerPages(unittest.TestCase):
    """Starts the FastAPI app with TestClient and checks pages return 200."""

    @classmethod
    def setUpClass(cls):
        """Import app and create test client."""
        # Import here to avoid import errors if app has issues
        from main import app
        cls.client = TestClient(app)

    def _get_companies(self):
        """Get list of company tickers."""
        return [
            d.name for d in COMPANIES_DIR.iterdir()
            if d.is_dir() and d.name not in ("TEMPLATE", "__pycache__")
        ]

    def _get_company_assets(self, ticker):
        """Get list of asset IDs for a company."""
        company_dir = COMPANIES_DIR / ticker
        return [
            f.stem for f in company_dir.glob("*.json")
            if f.name != "company.json"
        ]

    def test_companies_list_page(self):
        """GET /api/clinical/companies/html should return 200."""
        response = self.client.get("/api/clinical/companies/html")
        self.assertEqual(response.status_code, 200,
            f"Companies list page failed: {response.status_code}")

    def test_all_company_pages_return_200(self):
        """Every company page should return 200, not 500."""
        errors = []
        for ticker in self._get_companies():
            url = f"/api/clinical/companies/{ticker}/html"
            response = self.client.get(url)
            if response.status_code != 200:
                errors.append(f"{url}: {response.status_code}")

        if errors:
            self.fail(f"Company pages with errors:\n" + "\n".join(errors))

    def test_all_asset_pages_return_200(self):
        """Every asset page should return 200, not 500."""
        errors = []
        for ticker in self._get_companies():
            for asset_id in self._get_company_assets(ticker):
                url = f"/api/clinical/companies/{ticker}/assets/{asset_id}/html"
                response = self.client.get(url)
                if response.status_code != 200:
                    errors.append(f"{url}: {response.status_code}")

        if errors:
            self.fail(f"Asset pages with errors:\n" + "\n".join(errors))

    def test_kymr_specific_assets(self):
        """KYMR assets kt621, kt579, kt485 should all return 200."""
        kymr_assets = ["kt621", "kt579", "kt485"]
        for asset_id in kymr_assets:
            url = f"/api/clinical/companies/KYMR/assets/{asset_id}/html"
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200,
                f"KYMR asset {asset_id} failed: {response.status_code}")


if __name__ == "__main__":
    unittest.main()
