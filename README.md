# sales-patriot

Cleans a client's supplier data into three lists of firms for the `firms` table
(`company_name, cage, email, phone, contact_name`):

- **Linked vendor-manufacturers**: each vendor followed by the manufacturers it represents, grouped by `link_id`
- **Orphan vendors**: vendors with no linked manufacturers
- **Orphan manufacturers**: manufacturers with no vendor

All the work is in [`firms_cleaning.ipynb`](firms_cleaning.ipynb), which reads top to bottom:
load, inspect, clean, match, build, save.

## Run it

Put the three source files in `data/` (they aren't committed; the cages file is ~590 MB):

```
data/Sales Patriot Project Vendor File_ANONYMIZED.csv
data/Cage Maintenance_ANONYMIZED.csv
data/cages_ANONYMIZED.csv
```

Then:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # bin/ instead of Scripts/ on Mac/Linux
.venv/Scripts/jupyter notebook firms_cleaning.ipynb       # Restart & Run All, takes about a minute
.venv/Scripts/python -m pytest output                     # checks the output files
```

## Output

| File | Rows | Cage filled |
|---|---|---|
| `output/linked_vendor_manufacturers.csv` | 10,382 (3,641 vendors) | 77% |
| `output/orphan_vendors.csv` | 13,811 | 37% |
| `output/orphan_manufacturers.csv` | 10,803 | 100% |
| `output/rejected.csv` | 3,707 | rows that were dropped, with the reason |

The linked list has two extra columns: `link_id` (the vendor id) and `role` (`vendor` or `manufacturer`).
The vendor row comes first in each group.

## Decisions

- A cage code identifies one firm, so the same cage means the same firm. Two rows with the same name
  but different cages are kept as two firms (often separate sites or divisions).
- A vendor only gets a cage when the match is certain: one of its own manufacturers has the same name,
  its name matches exactly one firm in the cages table (or exactly one active firm), or exactly one of the
  client's unlinked manufacturers has its name. Otherwise the cage is left empty. No fuzzy matching.
- Names are compared on a normalised key (uppercase, no punctuation, no INC/LLC/CORP/etc.).
  The output keeps the original names, minus notes like "USE CAGE CODE 3T9T9 FOR CATALOGING" or a PO box.
- Vendor codes are matched as numbers: `VendorCode` is `2538.0` and `VendorId` is `002538`.
- Vendors marked do-not-use, inactive or closed are dropped. If the name points to another vendor
  ("GRAYBAR - USE 001270"), its manufacturers move to that vendor.
- Manufacturers whose vendor has no name (vendors 0, 2 and 5, about 3,500 rows) have no real parent,
  so they are orphans.
- A manufacturer row with its vendor's own cage is the vendor itself, not a child. Its email fills the
  vendor's if that is empty. A vendor linked only to itself is an orphan vendor.
- Linked firms win: an orphan with a cage already in the linked list is dropped, and so is an orphan vendor
  with no cage whose name is in the linked list. Between the orphan lists the vendor wins, since it has the
  contact details.
- A vendor can also appear as a manufacturer under another vendor (27 cages). Both relationships are real,
  so both rows stay.
- Contacts that are a department ("SALES", "CUSTOMER SERVICE") are left empty, and extensions are removed.
  Phones are kept only as 10-digit US numbers, so international numbers and numbers with extensions are dropped.
- Nothing is dropped silently. Every removed row is in `output/rejected.csv`, and with the raw files in
  `data/` a test checks that the cage maintenance row counts add up.

The source data is anonymised, so emails often don't match the company they belong to.
