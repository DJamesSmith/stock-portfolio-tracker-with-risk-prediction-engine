from django.core.management.base import BaseCommand, CommandError

from analytics.training.train_forecast import train_forecast_model
from analytics.training.train_risk import train_risk_model
from config.application_logger import ApplicationLogger
from market_data.forms import TickerForm


class Command(BaseCommand):
    help = "Train the risk and/or forecast models from PriceHistory and save them with a metrics report."

    def add_arguments(self, parser):
        parser.add_argument("--model", choices=["risk", "forecast", "all"], default="all", help="Which model to train.")
        parser.add_argument("--tickers", default="", help="Optional comma-separated tickers, for example AAPL,MSFT.")

    def get_tickers(self, raw_tickers):
        tickers = []

        for raw_ticker in raw_tickers.split(","):
            if not raw_ticker.strip():
                continue

            ticker_form = TickerForm({"ticker": raw_ticker})

            if not ticker_form.is_valid():
                raise CommandError(f"Invalid ticker: {raw_ticker}")

            tickers.append(ticker_form.cleaned_data["ticker"])

        return tickers

    def print_window(self, metadata):
        for split_name in ["train", "validation", "test"]:
            window = metadata["training_window"][split_name]
            self.stdout.write(f"  {split_name}: {window['start']} to {window['end']} ({window['rows']} rows)")

    def print_risk_result(self, metadata):
        forest = metadata["metrics"]["test"]
        baseline = metadata["baseline"]["metrics"]["test"]

        self.stdout.write(self.style.SUCCESS(f"Risk model saved: {metadata['model_version']}"))
        self.print_window(metadata)
        self.stdout.write(f"  Random Forest       test accuracy={forest['accuracy']} macro_f1={forest['macro_f1']}")
        self.stdout.write(f"  Logistic Regression test accuracy={baseline['accuracy']} macro_f1={baseline['macro_f1']}")

        for label, scores in forest["per_class"].items():
            self.stdout.write(f"  {label:<7} precision={scores['precision']} recall={scores['recall']} f1={scores['f1']}")

        self.stdout.write(f"  {metadata['comparison']['note']}")

    def print_forecast_result(self, metadata):
        model = metadata["metrics"]["test"]
        always_up = metadata["baselines"]["always_up"]["test"]
        previous = metadata["baselines"]["previous_day_direction"]["test"]

        self.stdout.write(self.style.SUCCESS(f"Forecast model saved: {metadata['model_version']}"))
        self.print_window(metadata)
        self.stdout.write(f"  Gradient Boosting test accuracy={model['accuracy']} f1={model['f1']} roc_auc={model['roc_auc']}")
        self.stdout.write(f"  Always Up         test accuracy={always_up['accuracy']} f1={always_up['f1']} roc_auc={always_up['roc_auc']}")
        self.stdout.write(f"  Previous Day      test accuracy={previous['accuracy']} f1={previous['f1']} roc_auc={previous['roc_auc']}")
        self.stdout.write(f"  {metadata['comparison']['note']}")

    def handle(self, *args, **options):
        tickers = self.get_tickers(options["tickers"])
        model_choice = options["model"]

        try:
            if model_choice in ["risk", "all"]:
                self.stdout.write("Training risk model...")
                self.print_risk_result(train_risk_model(tickers))

            if model_choice in ["forecast", "all"]:
                self.stdout.write("Training forecast model...")
                self.print_forecast_result(train_forecast_model(tickers))
        except ValueError as error:
            ApplicationLogger.error(f"train_models failed: model={model_choice}, error={error}")
            raise CommandError(str(error))

        ApplicationLogger.info(f"train_models finished: model={model_choice}, tickers={tickers or 'all'}")