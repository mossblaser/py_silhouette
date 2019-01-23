Rudamentary tests
=================

The following test procedure is designed to test the key functions
of the library and its interactions with real Silhouette hardware.

Since the library is almost entirely a thin wrapper around the underlying
hardware commands, no unit tests have been provided and all formal testing is
via [`test_sheet.py`](./test_sheet.py) and manual inspection of the associated
prepared printed sheet [`test_sheet.svg`](./test_sheet.svg).

1. Print out [`test_sheet.svg`](./test_sheet.svg) or
   [`test_sheet.pdf`](./test_sheet.pdf) on white A4 paper, taking care not to
   adjust the scaling during printing.
2. Attach printout to a Silhouette cutting sheet and put aside.
3. Insert a pen tool into your Silhouette plotter, attach to a PC and power on.
4. Run `python test_sheet.py` and follow the prompts being sure to verify the
   outcomes are as expected.

This is all very crude but hopefully sufficient...
