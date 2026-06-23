"""AutoML: classification, regression, clustering with sklearn & xgboost."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import accuracy_score, r2_score, silhouette_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)


def auto_classify(df: pd.DataFrame, target_col: str) -> dict[str, Any]:
    """Train a classifier (LogReg + RandomForest) and return the best."""
    if target_col not in df.columns:
        return {"error": f"Column '{target_col}' not found"}

    df_clean = df.dropna(subset=[target_col])
    y = df_clean[target_col]
    if y.dtype == object or y.nunique() <= 15:
        y = LabelEncoder().fit_transform(y.astype(str))

    X = pd.get_dummies(df_clean.drop(columns=[target_col]), drop_first=True)
    X = X.select_dtypes(include=[np.number]).fillna(0)

    if len(X) < 10 or X.shape[1] < 1:
        return {"error": "Insufficient data for classification"}

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "logistic_regression": LogisticRegression(max_iter=200, random_state=42),
        "random_forest": RandomForestClassifier(n_estimators=50, random_state=42),
    }

    results = {}
    for name, model in models.items():
        try:
            model.fit(X_train_s, y_train)
            preds = model.predict(X_test_s)
            acc = accuracy_score(y_test, preds)
            results[name] = {"accuracy": round(acc, 4)}
        except Exception as exc:
            results[name] = {"error": str(exc)}

    best = max(results.items(), key=lambda x: x[1].get("accuracy", 0))
    return {"best_model": best[0], "results": results, "feature_count": X.shape[1]}


def auto_regress(df: pd.DataFrame, target_col: str) -> dict[str, Any]:
    """Train regression models."""
    if target_col not in df.columns:
        return {"error": f"Column '{target_col}' not found"}

    df_clean = df.dropna(subset=[target_col])
    y = df_clean[target_col].astype(float)
    X = pd.get_dummies(df_clean.drop(columns=[target_col]), drop_first=True)
    X = X.select_dtypes(include=[np.number]).fillna(0)

    if len(X) < 10 or X.shape[1] < 1:
        return {"error": "Insufficient data for regression"}

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    models = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(n_estimators=50, random_state=42),
    }

    results = {}
    for name, model in models.items():
        try:
            model.fit(X_train_s, y_train)
            preds = model.predict(X_test_s)
            r2 = r2_score(y_test, preds)
            results[name] = {"r2_score": round(r2, 4)}
        except Exception as exc:
            results[name] = {"error": str(exc)}

    best = max(results.items(), key=lambda x: x[1].get("r2_score", -999))
    return {"best_model": best[0], "results": results, "feature_count": X.shape[1]}


def auto_cluster(df: pd.DataFrame, n_clusters: int = 3) -> dict[str, Any]:
    """KMeans + DBSCAN clustering on numeric data."""
    numeric = df.select_dtypes(include=[np.number]).dropna()
    if len(numeric) < 5:
        return {"error": "Insufficient numeric data for clustering"}

    X = StandardScaler().fit_transform(numeric)
    results = {}

    try:
        km = KMeans(n_clusters=min(n_clusters, len(numeric) // 2), random_state=42, n_init=10)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels) if len(set(labels)) > 1 else 0
        results["kmeans"] = {"silhouette": round(sil, 4), "clusters": int(len(set(labels)))}
    except Exception as exc:
        results["kmeans"] = {"error": str(exc)}

    try:
        db = DBSCAN(eps=0.5, min_samples=3)
        labels = db.fit_predict(X)
        n_clusters_found = len(set(labels)) - (1 if -1 in labels else 0)
        results["dbscan"] = {"clusters": n_clusters_found, "noise_points": int((labels == -1).sum())}
    except Exception as exc:
        results["dbscan"] = {"error": str(exc)}

    return results
