import pandas as pd
import numpy as np


def calculate_demographic_parity(df, target_col, sensitive_col):
    """
    Calculate the selection rate for each group in the sensitive column.
    Returns a dict {group_name: selection_rate} where selection_rate = count(target==1) / count(group).
    """
    groups = df[sensitive_col].unique()
    parity = {}
    for group in groups:
        group_df = df[df[sensitive_col] == group]
        total = len(group_df)
        if total == 0:
            parity[str(group)] = 0.0
        else:
            positive = len(group_df[group_df[target_col] == 1])
            parity[str(group)] = round(positive / total, 4)
    return parity


def calculate_disparate_impact(df, target_col, sensitive_col):
    """
    Calculate the disparate impact ratio: min_rate / max_rate.
    < 0.8 = biased, 0.8 - 1.2 = fair, > 1.2 = reverse bias.
    """
    parity = calculate_demographic_parity(df, target_col, sensitive_col)
    rates = list(parity.values())
    if not rates:
        return 1.0
    max_rate = max(rates)
    min_rate = min(rates)
    if max_rate == 0:
        return 1.0
    return round(min_rate / max_rate, 4)


def calculate_overall_fairness_score(demographic_parity, disparate_impact):
    """
    Calculate an overall fairness score from 0-100.

    The disparate impact ratio determines the base score band.
    Demographic parity variance provides a minor adjustment (±5 pts).

    Disparate impact mapping:
        DI < 0.6       → score  0 - 30   (heavily biased)
        DI 0.6 - 0.8   → score 30 - 50   (biased)
        DI 0.8 - 1.0   → score 75 - 100  (fair, improving toward perfect)
        DI 1.0 - 1.2   → score 100 - 75  (fair, slight over-representation)
        DI > 1.2        → score 40 - 60   (reverse bias)
    """
    # --- Base score from disparate impact (determines the band) ---
    di = disparate_impact
    if di <= 0.0:
        base_score = 0.0
    elif di < 0.6:
        # 0 → 0, 0.6 → 30  (linear interpolation)
        base_score = (di / 0.6) * 30.0
    elif di < 0.8:
        # 0.6 → 30, 0.8 → 50
        base_score = 30.0 + ((di - 0.6) / 0.2) * 20.0
    elif di <= 1.0:
        # 0.8 → 75, 1.0 → 100
        base_score = 75.0 + ((di - 0.8) / 0.2) * 25.0
    elif di <= 1.2:
        # 1.0 → 100, 1.2 → 75
        base_score = 100.0 - ((di - 1.0) / 0.2) * 25.0
    elif di <= 2.0:
        # 1.2 → 60, 2.0 → 40
        base_score = 60.0 - ((di - 1.2) / 0.8) * 20.0
    else:
        base_score = 40.0

    # --- Small adjustment from demographic parity variance (±5 pts) ---
    rates = list(demographic_parity.values())
    if len(rates) <= 1:
        dp_adjustment = 5.0  # single group = no variance = small bonus
    else:
        variance = np.var(rates)
        # variance 0 → +5, variance >= 0.1 → -5
        dp_adjustment = 5.0 - (variance / 0.1) * 10.0
        dp_adjustment = max(-5.0, min(5.0, dp_adjustment))

    total = int(round(base_score + dp_adjustment))
    return max(0, min(100, total))


# ═══════════════════════════════════════════════════════════════════════════
#  NEW METRICS
# ═══════════════════════════════════════════════════════════════════════════

def calculate_statistical_significance(df, target_col, sensitive_col):
    """
    Chi-squared test for independence between the target and sensitive columns.
    Determines if the observed bias is statistically significant or could be due to chance.
    """
    try:
        from scipy.stats import chi2_contingency
        contingency = pd.crosstab(df[sensitive_col], df[target_col])
        chi2, p_value, dof, _ = chi2_contingency(contingency)
        return {
            'chi2': round(float(chi2), 4),
            'p_value': round(float(p_value), 6),
            'dof': int(dof),
            'significant': bool(p_value < 0.05),
            'confidence': 'High' if p_value < 0.01 else 'Moderate' if p_value < 0.05 else 'Low'
        }
    except Exception:
        return {
            'chi2': 0, 'p_value': 1.0, 'dof': 0,
            'significant': False, 'confidence': 'N/A'
        }


def calculate_representation_balance(df, sensitive_col):
    """
    Calculate how balanced group representation is using normalized entropy.
    100 = perfectly balanced, 0 = completely imbalanced.
    """
    counts = df[sensitive_col].value_counts()
    total = len(df)
    n_groups = len(counts)

    imbalance_ratio = round(float(counts.max() / counts.min()), 2) if counts.min() > 0 else 999.0

    proportions = (counts / total).values
    if n_groups > 1:
        max_entropy = np.log(n_groups)
        actual_entropy = -np.sum(proportions * np.log(proportions + 1e-10))
        balance_score = round(float(actual_entropy / max_entropy * 100), 1)
    else:
        balance_score = 100.0

    return {
        'balance_score': balance_score,
        'imbalance_ratio': imbalance_ratio,
        'largest_group': str(counts.idxmax()),
        'smallest_group': str(counts.idxmin()),
        'largest_pct': round(float(counts.max() / total * 100), 1),
        'smallest_pct': round(float(counts.min() / total * 100), 1),
    }


def calculate_max_disparity(demographic_parity):
    """
    Find the pair of groups with the maximum outcome disparity.
    Returns the gap and the advantaged/disadvantaged groups.
    """
    groups = list(demographic_parity.keys())
    rates = list(demographic_parity.values())
    if len(groups) < 2:
        return {
            'gap': 0, 'gap_pct': 0,
            'advantaged_group': groups[0] if groups else '',
            'disadvantaged_group': groups[0] if groups else '',
            'advantaged_rate': rates[0] if rates else 0,
            'disadvantaged_rate': rates[0] if rates else 0
        }

    max_idx = int(np.argmax(rates))
    min_idx = int(np.argmin(rates))
    gap = rates[max_idx] - rates[min_idx]

    return {
        'gap': round(float(gap), 4),
        'gap_pct': round(float(gap * 100), 1),
        'advantaged_group': groups[max_idx],
        'advantaged_rate': round(float(rates[max_idx]), 4),
        'disadvantaged_group': groups[min_idx],
        'disadvantaged_rate': round(float(rates[min_idx]), 4)
    }


def calculate_feature_correlations(df, sensitive_col):
    """
    Detect proxy features that correlate with the sensitive attribute.
    High correlation means the feature may act as a proxy for the protected class.
    """
    numeric_df = df.select_dtypes(include=[np.number])

    if df[sensitive_col].dtype == 'object':
        encoded = pd.Categorical(df[sensitive_col]).codes
    else:
        encoded = df[sensitive_col].values

    correlations = {}
    for col in numeric_df.columns:
        if col == sensitive_col:
            continue
        try:
            corr = float(np.corrcoef(encoded, numeric_df[col].values)[0, 1])
            if np.isnan(corr):
                continue
            correlations[col] = {
                'correlation': round(abs(corr), 4),
                'direction': 'positive' if corr > 0 else 'negative',
                'is_proxy': abs(corr) > 0.3,
                'raw': round(corr, 4)
            }
        except Exception:
            continue

    # Sort by absolute correlation descending
    correlations = dict(sorted(
        correlations.items(),
        key=lambda x: x[1]['correlation'],
        reverse=True
    ))
    return correlations


def calculate_group_statistics(df, target_col, sensitive_col):
    """
    Calculate detailed per-group statistics for the breakdown table.
    """
    stats = {}
    total_dataset = len(df)

    for group in df[sensitive_col].unique():
        gdf = df[df[sensitive_col] == group]
        n = len(gdf)
        pos = int((gdf[target_col] == 1).sum())
        neg = n - pos

        stats[str(group)] = {
            'count': n,
            'positive': pos,
            'negative': neg,
            'positive_rate': round(pos / n, 4) if n > 0 else 0,
            'pct_of_dataset': round(n / total_dataset * 100, 1)
        }

    return stats


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def run_full_analysis(df, target_col, sensitive_col):
    """
    Run a complete bias analysis and return a comprehensive result dict.
    """
    # Ensure target column is numeric binary
    df = df.copy()
    unique_vals = df[target_col].unique()

    # Convert yes/no or true/false to 1/0
    mapping = {}
    for val in unique_vals:
        val_str = str(val).strip().lower()
        if val_str in ('yes', 'true', '1', '1.0'):
            mapping[val] = 1
        elif val_str in ('no', 'false', '0', '0.0'):
            mapping[val] = 0

    if mapping:
        df[target_col] = df[target_col].map(mapping)

    # Ensure numeric
    df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
    df = df.dropna(subset=[target_col])
    df[target_col] = df[target_col].astype(int)

    # ── Core metrics (existing) ──────────────────────────────────────────
    demographic_parity = calculate_demographic_parity(df, target_col, sensitive_col)
    disparate_impact = calculate_disparate_impact(df, target_col, sensitive_col)
    fairness_score = calculate_overall_fairness_score(demographic_parity, disparate_impact)

    # Determine verdict
    if fairness_score < 50:
        verdict = 'biased'
    elif fairness_score < 75:
        verdict = 'warning'
    else:
        verdict = 'fair'

    # Group counts for composition chart
    group_counts = df[sensitive_col].value_counts().to_dict()
    group_counts = {str(k): int(v) for k, v in group_counts.items()}

    # Positive rate
    positive_rate = round(df[target_col].mean(), 4)

    # ── New metrics ──────────────────────────────────────────────────────
    stat_significance = calculate_statistical_significance(df, target_col, sensitive_col)
    representation = calculate_representation_balance(df, sensitive_col)
    max_disparity = calculate_max_disparity(demographic_parity)
    feature_correlations = calculate_feature_correlations(df, sensitive_col)
    group_stats = calculate_group_statistics(df, target_col, sensitive_col)

    return {
        # Core
        'demographic_parity': demographic_parity,
        'disparate_impact': disparate_impact,
        'fairness_score': fairness_score,
        'verdict': verdict,
        'dataset_size': len(df),
        'groups': list(demographic_parity.keys()),
        'group_counts': group_counts,
        'target_col': target_col,
        'sensitive_col': sensitive_col,
        'positive_rate': positive_rate,
        'num_groups': len(demographic_parity),
        'analysis_timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
        # New
        'stat_significance': stat_significance,
        'representation': representation,
        'max_disparity': max_disparity,
        'feature_correlations': feature_correlations,
        'group_stats': group_stats,
    }
