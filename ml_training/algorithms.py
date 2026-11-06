from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def build_random_forest():
    return RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        min_samples_leaf=50,
        n_jobs=-1,
        random_state=42,
    )


def build_logistic_regression():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def build_gradient_boosting():
    return HistGradientBoostingClassifier(
        max_iter=200,
        learning_rate=0.05,
        max_leaf_nodes=31,
        min_samples_leaf=200,
        early_stopping=False,
        random_state=42,
    )