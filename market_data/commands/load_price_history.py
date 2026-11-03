from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from config.application_logger import ApplicationLogger
from market_data.forms import TickerForm
from market_data.services.ingestion import REQUIRED_COLUMNS, save_price_rows

CSV_COLUMNS = {
    "date": "date",
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "volume": "volume",
}


class Command(BaseCommand):
    help = "Load daily OHLCV prices from a folder of CSV files, one file per ticker (for example AAPL.csv)."

    def add_arguments(self, parser):
        parser.add_argument("folder", help="Folder that contains the CSV files.")
        parser.add_argument("--tickers", default="", help="Comma-separated tickers to load, for example AAPL,MSFT.")

    def handle(self, *args, **options):
        folder = Path(options["folder"])

        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")

        wanted_tickers = {ticker.strip().upper() for ticker in options["tickers"].split(",") if ticker.strip()}
        csv_files = sorted(folder.glob("*.csv"))

        if not csv_files:
            raise CommandError(f"No CSV files found in {folder}")

        loaded_tickers = set()
        total_inserted = 0
        total_skipped = 0

        for csv_file in csv_files:
            ticker_form = TickerForm({"ticker": csv_file.stem})

            if not ticker_form.is_valid():
                self.stdout.write(self.style.WARNING(f"Skipped {csv_file.name}: file name is not a valid ticker."))
                continue

            ticker = ticker_form.cleaned_data["ticker"]

            if wanted_tickers and ticker not in wanted_tickers:
                continue

            try:
                frame = pd.read_csv(csv_file)
            except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
                ApplicationLogger.warning(f"Could not read CSV: file={csv_file.name}, error={error}")
                self.stdout.write(self.style.WARNING(f"Skipped {csv_file.name}: could not read file."))
                continue

            frame.columns = [str(column).strip().lower() for column in frame.columns]
            frame = frame.rename(columns=CSV_COLUMNS)
            missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]

            if missing_columns:
                self.stdout.write(self.style.WARNING(f"Skipped {csv_file.name}: missing columns {missing_columns}."))
                continue

            if "volume" not in frame.columns:
                self.stdout.write(self.style.WARNING(f"{csv_file.name} has no Volume column. Volume will be empty."))

            inserted, skipped = save_price_rows(ticker, frame)
            loaded_tickers.add(ticker)
            total_inserted += inserted
            total_skipped += skipped
            self.stdout.write(f"{ticker}: inserted={inserted}, skipped={skipped}")

        for ticker in sorted(wanted_tickers - loaded_tickers):
            self.stdout.write(self.style.WARNING(f"No CSV file was loaded for {ticker}."))

        summary = f"Done. tickers={len(loaded_tickers)}, inserted={total_inserted}, skipped={total_skipped}"
        ApplicationLogger.info(f"load_price_history finished: {summary}")
        self.stdout.write(self.style.SUCCESS(summary))
