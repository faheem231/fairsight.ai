import os
import json


def get_ai_suggestions(bias_report: dict) -> list:
    """
    Use Gemini AI to generate fix recommendations based on the bias report.
    Returns a list of recommendation dicts with keys: title, description, severity, icon.
    Falls back to rule-based suggestions if the API key is missing or the call fails.
    """
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()

    if not api_key or api_key in ('your_gemini_api_key_here', ''):
        return get_fallback_suggestions(bias_report)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Prepare a clean, serialisable summary for the prompt
        report_summary = {
            'fairness_score':      bias_report.get('fairness_score', 0),
            'disparate_impact':    bias_report.get('disparate_impact', 0),
            'demographic_parity':  bias_report.get('demographic_parity', {}),
            'verdict':             bias_report.get('verdict', 'unknown'),
            'dataset_size':        bias_report.get('dataset_size', 0),
            'target_col':          bias_report.get('target_col', ''),
            'sensitive_col':       bias_report.get('sensitive_col', ''),
            'groups':              bias_report.get('groups', []),
            'positive_rate':       bias_report.get('positive_rate', 0),
        }

        system_instruction = (
            'You are an AI fairness and bias expert. '
            'Analyze the bias report and return ONLY a valid JSON array '
            'of exactly 5 fix recommendations. '
            'Each item must have these exact keys: '
            'title (string), description (2-3 sentence string), '
            'severity (exactly one of: CRITICAL, RECOMMENDED, OPTIONAL), '
            'icon (single emoji). '
            'Return ONLY the JSON array. No markdown, no explanation, no code fences.'
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=json.dumps(report_summary),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
        )
        
        response_text = response.text.strip()

        # Strip markdown code fences if the model adds them anyway
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            lines = lines[1:]                          # drop opening fence line
            if lines and lines[-1].strip().startswith('```'):
                lines = lines[:-1]                     # drop closing fence
            response_text = '\n'.join(lines).strip()

        suggestions = json.loads(response_text)

        if not isinstance(suggestions, list) or len(suggestions) == 0:
            return get_fallback_suggestions(bias_report)

        # Sanitise and normalise each suggestion
        valid_severities = {'CRITICAL', 'RECOMMENDED', 'OPTIONAL'}
        cleaned = []
        for s in suggestions:
            if not isinstance(s, dict):
                continue
            s['severity']    = s.get('severity', 'RECOMMENDED').upper()
            if s['severity'] not in valid_severities:
                s['severity'] = 'RECOMMENDED'
            s['icon']        = s.get('icon') or '🔧'
            s['title']       = s.get('title') or 'Recommendation'
            s['description'] = s.get('description') or 'Review and address potential bias in the dataset.'
            cleaned.append(s)

        return cleaned[:6]   # cap at 6

    except json.JSONDecodeError as e:
        print(f'[FairSight] Gemini response was not valid JSON: {e}')
        return get_fallback_suggestions(bias_report)
    except Exception as e:
        print(f'[FairSight] Gemini API error: {e}')
        return get_fallback_suggestions(bias_report)


def get_fallback_suggestions(bias_report: dict) -> list:
    """
    Intelligent, data-driven fallback suggestions used when Gemini API is unavailable.
    """
    score            = bias_report.get('fairness_score', 50)
    disparate_impact = bias_report.get('disparate_impact', 1.0)
    target_col       = bias_report.get('target_col', 'target')
    sensitive_col    = bias_report.get('sensitive_col', 'group')
    parity           = bias_report.get('demographic_parity', {})

    # Find most and least favoured groups
    if parity:
        max_group = max(parity, key=parity.get)
        min_group = min(parity, key=parity.get)
        max_rate  = parity[max_group]
        min_rate  = parity[min_group]
    else:
        max_group = 'majority'
        min_group = 'minority'
        max_rate  = 0.5
        min_rate  = 0.3

    suggestions = []

    # ── Critical bias ─────────────────────────────────────────────────────────
    if score < 50:
        suggestions.append({
            'icon': '🚨',
            'title': 'Immediate Bias Remediation Required',
            'description': (
                f'The dataset shows significant bias with a disparate impact ratio of {disparate_impact:.4f}. '
                f'The "{min_group}" group has a {target_col} rate of {min_rate:.1%} compared to '
                f'{max_rate:.1%} for "{max_group}". Immediate intervention is required before using '
                f'this data for any decision-making.'
            ),
            'severity': 'CRITICAL'
        })
        suggestions.append({
            'icon': '⚖️',
            'title': 'Apply Re-sampling Techniques',
            'description': (
                f'Use oversampling (SMOTE) for the underrepresented "{min_group}" group or '
                f'undersampling for the "{max_group}" group to balance selection rates. '
                f'This can help achieve demographic parity without discarding valuable data.'
            ),
            'severity': 'CRITICAL'
        })
    elif score < 75:
        suggestions.append({
            'icon': '⚡',
            'title': 'Address Moderate Bias Patterns',
            'description': (
                f'The dataset exhibits moderate bias with a fairness score of {score}/100. '
                f'While not severely biased, the selection rate gap between groups warrants attention. '
                f'Review the {target_col} criteria for unintentional {sensitive_col}-based filtering.'
            ),
            'severity': 'RECOMMENDED'
        })

    # ── Always-present recommendations ───────────────────────────────────────
    suggestions.append({
        'icon': '🔍',
        'title': 'Audit Feature Correlations',
        'description': (
            f'Investigate whether other features in the dataset serve as proxies for {sensitive_col}. '
            f'Correlated features can introduce indirect bias even after removing the sensitive attribute. '
            f'Use correlation analysis and feature importance ranking to surface hidden relationships.'
        ),
        'severity': 'RECOMMENDED'
    })

    suggestions.append({
        'icon': '📊',
        'title': 'Implement Ongoing Fairness Monitoring',
        'description': (
            f'Set up automated fairness monitoring to track demographic parity and disparate impact over time. '
            f'Bias can drift as new data is collected. '
            f'Establish threshold alerts when the fairness score drops below 75.'
        ),
        'severity': 'RECOMMENDED'
    })

    suggestions.append({
        'icon': '🧪',
        'title': 'Conduct Counterfactual Testing',
        'description': (
            f'Perform counterfactual fairness tests by swapping {sensitive_col} values and checking '
            f'if {target_col} outcomes change. If outcomes differ significantly, the model or process '
            f'relies on protected attributes directly or through proxies.'
        ),
        'severity': 'OPTIONAL'
    })

    if score >= 75:
        suggestions.append({
            'icon': '✅',
            'title': 'Document Fairness Compliance',
            'description': (
                f'The dataset appears fair with a score of {score}/100. '
                f'Document the current fairness metrics, create a model card, '
                f'and establish a baseline for future comparisons. Regular re-evaluation is still recommended.'
            ),
            'severity': 'OPTIONAL'
        })

    return suggestions[:5]
