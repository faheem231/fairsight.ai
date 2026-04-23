import pickle
import pandas as pd
import numpy as np
from core.bias_analyzer import (
    calculate_demographic_parity,
    calculate_disparate_impact,
    calculate_overall_fairness_score,
    calculate_statistical_significance,
    calculate_representation_balance,
    calculate_max_disparity,
    calculate_feature_correlations,
    calculate_group_statistics,
)

def load_model(filepath):
    with open(filepath, 'rb') as f:
        model = pickle.load(f)
    return model

def run_model_bias_analysis(model_path, csv_path, sensitive_col):
    model = load_model(model_path)
    df = pd.read_csv(csv_path)

    if sensitive_col not in df.columns:
        raise ValueError(f"Sensitive column '{sensitive_col}' not found in CSV")

    sensitive_values = df[sensitive_col].copy()

    # Keep ONLY numeric columns — strictly drop all strings/objects
    feature_df = df.select_dtypes(include=[np.number]).copy()

    # Also drop sensitive col if it ended up numeric (e.g. encoded)
    if sensitive_col in feature_df.columns:
        feature_df = feature_df.drop(columns=[sensitive_col])

    # ── Match the model's expected features ──────────────────────────────
    try:
        expected = list(model.feature_names_in_)
        available = [f for f in expected if f in feature_df.columns]
        missing = [f for f in expected if f not in feature_df.columns]
        if missing:
            raise ValueError(
                f"Model expects columns not in your CSV: {', '.join(missing)}. "
                f"Your CSV has: {', '.join(feature_df.columns.tolist())}. "
                f"Make sure the test CSV matches the data the model was trained on."
            )
        feature_df = feature_df[expected]
    except AttributeError:
        # Older sklearn model without feature_names_in_
        pass

    try:
        predictions = model.predict(feature_df)
    except ValueError as e:
        error_str = str(e)
        if "Feature names" in error_str or "feature names" in error_str or "not match" in error_str:
            raise ValueError(
                f"Dataset mismatch: The columns in your CSV don't match what the model was trained on. "
                f"Original error from model: {error_str}"
            )
        raise

    result_df = pd.DataFrame({
        sensitive_col: sensitive_values,
        'prediction': predictions
    })

    # ── Core metrics ─────────────────────────────────────────────────────
    demographic_parity = calculate_demographic_parity(result_df, 'prediction', sensitive_col)
    disparate_impact = calculate_disparate_impact(result_df, 'prediction', sensitive_col)
    fairness_score = calculate_overall_fairness_score(demographic_parity, disparate_impact)

    verdict = 'biased' if fairness_score < 50 else 'warning' if fairness_score < 75 else 'fair'

    # ── New metrics ──────────────────────────────────────────────────────
    stat_significance = calculate_statistical_significance(result_df, 'prediction', sensitive_col)
    representation = calculate_representation_balance(df, sensitive_col)
    max_disparity = calculate_max_disparity(demographic_parity)
    feature_correlations = calculate_feature_correlations(df, sensitive_col)
    group_stats = calculate_group_statistics(result_df, 'prediction', sensitive_col)

    # Group counts
    group_counts = df[sensitive_col].value_counts().to_dict()
    group_counts = {str(k): int(v) for k, v in group_counts.items()}

    return {
        'demographic_parity': demographic_parity,
        'disparate_impact': round(float(disparate_impact), 4),
        'fairness_score': int(fairness_score),
        'verdict': verdict,
        'dataset_size': len(df),
        'groups': list(demographic_parity.keys()),
        'group_counts': group_counts,
        'target_col': 'model_prediction',
        'sensitive_col': sensitive_col,
        'positive_rate': round(float(np.mean(predictions)), 4),
        'analysis_type': 'model',
        'dataset_name': 'Model Bias Analysis',
        'analysis_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        # New metrics
        'stat_significance': stat_significance,
        'representation': representation,
        'max_disparity': max_disparity,
        'feature_correlations': feature_correlations,
        'group_stats': group_stats,
    }