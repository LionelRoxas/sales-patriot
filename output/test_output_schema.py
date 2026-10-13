from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).parent
FIRM_COLUMNS = ["company_name", "cage", "email", "phone", "contact_name"]
LINKED_COLUMNS = FIRM_COLUMNS + ["link_id", "role"]

FILES = {
    "orphan_manufacturers.csv": FIRM_COLUMNS,
    "orphan_vendors.csv": FIRM_COLUMNS,
    "linked_vendor_manufacturers.csv": LINKED_COLUMNS,
}


def load(name):
    return pd.read_csv(HERE / name, dtype=str)


@pytest.mark.parametrize("name, columns", FILES.items())
def test_columns(name, columns):
    assert list(load(name).columns) == columns


@pytest.mark.parametrize("name", FILES)
def test_every_row_has_a_company_name(name):
    assert load(name)["company_name"].notna().all()


@pytest.mark.parametrize("name", FILES)
def test_cage_codes_are_five_characters(name):
    cages = load(name)["cage"].dropna()
    assert cages.str.fullmatch(r"[A-Z0-9]{5}").all()


@pytest.mark.parametrize("name", FILES)
def test_emails_look_like_emails(name):
    emails = load(name)["email"].dropna()
    assert emails.str.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}").all()


@pytest.mark.parametrize("name", ["orphan_manufacturers.csv", "orphan_vendors.csv"])
def test_no_duplicate_cages_in_orphan_lists(name):
    assert not load(name)["cage"].dropna().duplicated().any()


def test_each_link_group_has_one_vendor_first():
    linked = load("linked_vendor_manufacturers.csv")
    assert linked["link_id"].notna().all()
    assert set(linked["role"]) == {"vendor", "manufacturer"}
    for _, group in linked.groupby("link_id", sort=False):
        assert list(group["role"]).count("vendor") == 1
        assert group["role"].iloc[0] == "vendor"
        assert len(group) > 1


def test_orphans_are_not_in_linked_list():
    linked_cages = set(load("linked_vendor_manufacturers.csv")["cage"].dropna())
    for name in ["orphan_manufacturers.csv", "orphan_vendors.csv"]:
        assert not set(load(name)["cage"].dropna()) & linked_cages


def test_orphan_lists_do_not_share_firms():
    vendors = load("orphan_vendors.csv")
    manufacturers = load("orphan_manufacturers.csv")
    assert not set(vendors["cage"].dropna()) & set(manufacturers["cage"].dropna())
    names = lambda df: set(df["company_name"].str.upper().str.strip())
    assert not names(vendors) & names(manufacturers)


def test_every_manufacturer_row_is_accounted_for():
    source = HERE.parent / "data" / "Cage Maintenance_ANONYMIZED.csv"
    if not source.exists():
        pytest.skip("raw data not in data/")
    linked = load("linked_vendor_manufacturers.csv")
    rejected = load("rejected.csv")
    kept = (linked["role"] == "manufacturer").sum() + len(load("orphan_manufacturers.csv"))
    dropped = (rejected["source"] == "cage_maintenance").sum()
    assert kept + dropped == len(pd.read_csv(source, dtype=str))
