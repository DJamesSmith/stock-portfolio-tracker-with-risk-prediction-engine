import json

import joblib
from django.conf import settings
from django.utils import timezone

MODEL_PREFIXES = {
    "risk": "risk-rf",
    "forecast": "forecast-hgb",
}


def get_model_folder(model_type):
    folder = settings.ML_MODELS_DIR / model_type
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def list_versions(model_type):
    folder = get_model_folder(model_type)
    return sorted(path.stem for path in folder.glob("*.joblib"))


def get_latest_version(model_type):
    versions = list_versions(model_type)

    if not versions:
        return None

    return versions[-1]


def get_next_version(model_type):
    today = timezone.now().strftime("%Y.%m.%d")
    version_start = f"{MODEL_PREFIXES[model_type]}-{today}-"
    count = 0

    for version in list_versions(model_type):
        if version.startswith(version_start):
            count += 1

    return f"{version_start}{count + 1:02d}"


def save_model(model_type, model, metadata):
    version = get_next_version(model_type)
    folder = get_model_folder(model_type)
    metadata["model_version"] = version

    joblib.dump(model, folder / f"{version}.joblib")

    with open(folder / f"{version}.json", "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    return version


def load_metadata(model_type, version):
    path = get_model_folder(model_type) / f"{version}.json"

    if not path.exists():
        raise FileNotFoundError(f"No metadata file found for {model_type} model {version}.")

    with open(path, encoding="utf-8") as file:
        return json.load(file)


def load_model(model_type, version=None):
    if version is None:
        version = get_latest_version(model_type)

    if version is None:
        raise FileNotFoundError(f"No trained {model_type} model found. Train one on the ML Training page.")

    path = get_model_folder(model_type) / f"{version}.joblib"

    if not path.exists():
        raise FileNotFoundError(f"No {model_type} model file found for version {version}.")

    return joblib.load(path), load_metadata(model_type, version)