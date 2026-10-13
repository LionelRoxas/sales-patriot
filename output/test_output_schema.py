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


def test_orphan_lists_do_not_share_cages():
    vendors = load("orphan_vendors.csv")
    manufacturers = load("orphan_manufacturers.csv")
    assert not set(vendors["cage"].dropna()) & set(manufacturers["cage"].dropna())


def test_vendor_without_cage_takes_the_cage_of_its_only_namesake():
    vendors = load("orphan_vendors.csv")
    manufacturers = load("orphan_manufacturers.csv")
    unique_names = manufacturers["company_name"].str.upper().drop_duplicates(keep=False)
    no_cage = vendors.loc[vendors["cage"].isna(), "company_name"].str.upper()
    assert not set(no_cage) & set(unique_names)


def test_manufacturers_are_only_dropped_when_their_cage_is_kept():
    rejected = load("rejected.csv")
    dropped = rejected.loc[rejected["reason"].str.startswith("orphan manufacturer"), "source_id"]
    kept = set().union(*(set(load(name)["cage"].dropna()) for name in FILES))
    assert dropped.isin(kept).all()


@pytest.mark.parametrize("name", FILES)
def test_company_names_have_no_notes(name):
    names = load(name)["company_name"]
    assert not names.str.contains(r"USE CAGE CODE|PO BOX|OBSOLETE|DUPE CODE|\bCLOSED\b", case=False).any()
    assert not names.str.contains(r"[;,]$").any()


@pytest.mark.parametrize("name", FILES)
def test_contact_names_are_people(name):
    contacts = load(name)["contact_name"].dropna()
    placeholder = r"(?i)sales( dept\.?| department)?|customer service|parts|gov't sales|\**see comments\**"
    assert not contacts.str.fullmatch(placeholder).any()
    assert not contacts.str.contains(r"@|\d").any()


@pytest.mark.parametrize("name", ["orphan_vendors.csv", "linked_vendor_manufacturers.csv"])
def test_phones_are_formatted(name):
    phones = load(name)["phone"].dropna()
    assert phones.str.fullmatch(r"\d{3}-\d{3}-\d{4}").all()


def test_rejected_rows_have_a_reason():
    rejected = load("rejected.csv")
    assert list(rejected.columns) == ["source", "source_id", "company_name", "reason"]
    assert rejected["reason"].notna().all()


def test_redirected_vendors_keep_their_manufacturers():
    data = HERE.parent / "data"
    if not data.exists():
        pytest.skip("raw data not in data/")
    vendors = pd.read_csv(data / "Sales Patriot Project Vendor File_ANONYMIZED.csv", dtype=str, usecols=["VendorId", "VendorName"])
    maint = pd.read_csv(data / "Cage Maintenance_ANONYMIZED.csv", dtype=str)
    target = vendors["VendorName"].str.extract(r"(?i)\b(?:USE|SEE)\s*(?:V#|#|VC)?\s*(\d+)", expand=False)
    redirected = pd.to_numeric(vendors.loc[target.notna(), "VendorId"], errors="coerce")
    cages = maint.loc[pd.to_numeric(maint["VendorCode"], errors="coerce").isin(redirected), "CageCode"].str.strip()
    orphans = set(load("orphan_manufacturers.csv")["cage"])
    assert not cages.isin(orphans).any()


def test_every_manufacturer_row_is_accounted_for():
    source = HERE.parent / "data" / "Cage Maintenance_ANONYMIZED.csv"
    if not source.exists():
        pytest.skip("raw data not in data/")
    linked = load("linked_vendor_manufacturers.csv")
    rejected = load("rejected.csv")
    kept = (linked["role"] == "manufacturer").sum() + len(load("orphan_manufacturers.csv"))
    dropped = (rejected["source"] == "cage_maintenance").sum()
    assert kept + dropped == len(pd.read_csv(source, dtype=str))
