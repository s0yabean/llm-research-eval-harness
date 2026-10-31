# Data (SYNTHETIC)

Every company, UEN, address, domain and page in this folder is invented. Postal codes are in the
9xxxxx range, which no real Singapore address uses, and UENs start with `SYN`. The real golden set
(real firms, labelled by hand) is private.

The synthetic set copies the method and composition of the real one: 20 flagged rows, 30 random
rows and 10 blank rows for development, plus 25 holdout rows (2 labelled `unsure`). Each row's
`scenario` names the failure type it reproduces. Regenerate with `python3 data/build_synthetic.py`.
