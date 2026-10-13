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
.venv/Scripts/jupyter notebook firms_cleaning.ipynb       # Restart & Run All, takes about 40 seconds
.venv/Scripts/python -m pytest output                     # checks the output schema
```

## Output

| File | Rows | Cage filled |
|---|---|---|
| `output/linked_vendor_manufacturers.csv` | 10,346 (3,638 vendors) | 76% |
| `output/orphan_vendors.csv` | 13,787 | 36% |
| `output/orphan_manufacturers.csv` | 10,729 | 100% |
| `output/rejected.csv` | 3,533 | rows that were dropped, with the reason |

The linked list has two extra columns: `link_id` (the vendor id) and `role` (`vendor` or `manufacturer`).
The vendor row comes first in each group.

## Decisions

- **Quality over quantity.** A vendor only gets a cage when the match is certain: either one of its own
  manufacturers has the same name, or its name matches exactly one firm in the cages table (or exactly one
  active firm). Otherwise the cage is left empty. No fuzzy matching.
- **Names are compared on a normalised key** (uppercase, no punctuation, no INC/LLC/CORP/etc.).
  The output keeps the original names.
- **Vendor codes are matched as numbers.** `VendorCode` is `2538.0` and `VendorId` is `002538`.
- **Manufacturers whose vendor has no name** (vendors 0, 2 and 5 cover about 3,500 rows) have no real parent,
  so they are treated as orphans.
- **A vendor linked only to its own cage** represents itself, so it is an orphan vendor rather than a one-row group.
- **Linked firms win duplicates.** An orphan whose cage or name is already in the linked list is dropped, and
  an orphan manufacturer that is already an orphan vendor is dropped too.
- **Nothing is dropped silently.** Every removed row is in `output/rejected.csv`.

The source data is anonymised, so emails often don't match the company they belong to.
