from flask import Blueprint, render_template, session, request, jsonify
import os, json

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat')
def chat_page():
    analysis = session.get('analysis', {})
    return render_template('chat.html', analysis=analysis)

@chat_bp.route('/chat/message', methods=['POST'])
def chat_message():
    data = request.get_json()
    user_message = data.get('message', '')
    history = data.get('history', [])
    analysis = session.get('analysis', {})

    # Validate API key before attempting the call
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not api_key or api_key in ('your_gemini_api_key_here', ''):
        reply = get_fallback_reply(user_message, analysis)
        return jsonify({'reply': reply, 'error': None})

    system_prompt = build_system_prompt(analysis)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Convert history from OpenAI/Anthropic format to Gemini format
        gemini_history = []
        for msg in history:
            role = 'user' if msg['role'] == 'user' else 'model'
            gemini_history.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg['content'])]
                )
            )

        chat = client.chats.create(
            model='gemini-2.5-flash',
            history=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
        
        response = chat.send_message(user_message)
        reply = response.text
        return jsonify({'reply': reply, 'error': None})
    except Exception as e:
        return jsonify({'reply': None, 'error': str(e)})


def build_system_prompt(analysis):
    """Build the expert fairness analyst system prompt with full context awareness."""
    if analysis:
        report_context = json.dumps(analysis, indent=2)
    else:
        report_context = "No analysis run yet — guide the user to run one."

    return f"""You are FairSight AI, an expert bias detection 
assistant. Your job is to guide users through detecting bias in 
their data or AI models through friendly conversation.

CONVERSATION FLOW — follow this order:
1. Greet and ask: do they have a CSV dataset or a trained ML model?
2. Ask what domain it is (hiring, loans, healthcare, education, etc.)
3. Ask what sensitive attribute they want to check 
   (gender, race, age, disability, income, religion, etc.)
4. Ask how many rows approximately
5. Based on their answers, tell them EXACTLY what to do:
   - Which page to go to (/upload or /model-upload)
   - What to upload
   - What to type in the sensitive column field
6. After they say they ran it, ask what the fairness score was
7. Then explain what that score means in simple words
8. Give 3 specific actionable fixes for their exact situation
9. Offer to explain any metric in detail

RULES:
- Ask ONE question at a time — never multiple
- Use simple language — no jargon unless explained
- Be encouraging and friendly
- Keep responses under 120 words unless explaining a result
- Use bullet points only for fix suggestions
- If user shares their fairness score, give a detailed 
  interpretation specific to their domain
- If user seems confused, offer to start over simply

Current report in session (may be empty if not run yet):
{report_context}
"""


def get_fallback_reply(question, analysis):
    """
    Expert-level rule-based replies when the Gemini API key is unavailable.
    Matches the elite analyst persona with structured, data-driven responses.
    """
    q = question.lower().strip()
    score = analysis.get('fairness_score', None)
    di = analysis.get('disparate_impact', None)
    verdict = analysis.get('verdict', 'N/A')
    target = analysis.get('target_col', 'N/A')
    sensitive = analysis.get('sensitive_col', 'N/A')
    parity = analysis.get('demographic_parity', {})
    dataset_size = analysis.get('dataset_size', 'N/A')
    group_counts = analysis.get('group_counts', {})

    # No analysis data available
    if not analysis or not parity:
        return ("🔍 **Insight**\n"
                "No analysis data loaded yet. I need a bias audit report to give you actionable insights.\n\n"
                "🛠 **Recommended Actions**\n"
                "- Navigate to **Upload** or **Model Audit** to run an analysis\n"
                "- Try the **Load Demo Dataset** option for a quick start\n"
                "- Come back here once you have results — I'll break them down for you\n\n"
                "💡 **Tip**: The demo dataset has deliberate gender bias baked in — great for learning how bias detection works.")

    # Compute group analysis
    min_group = min(parity, key=parity.get)
    max_group = max(parity, key=parity.get)
    min_rate = parity[min_group]
    max_rate = parity[max_group]
    gap = abs(max_rate - min_rate)
    gap_pct = gap * 100

    # Determine risk level
    if isinstance(score, (int, float)):
        if score < 50:
            risk = "**🔴 HIGH** — Well below acceptable thresholds"
        elif score < 75:
            risk = "**🟡 MEDIUM** — Near boundary, requires monitoring"
        else:
            risk = "**🟢 LOW** — Within acceptable fairness bounds"
    else:
        risk = "**Unknown** — Score not available"

    # ── Topic Matching ──

    # Fairness Score
    if any(kw in q for kw in ['fairness score', 'score', 'overall', 'how fair', 'what is my score']):
        if isinstance(score, (int, float)):
            if score < 50:
                return (f"🔍 **Insight**\n"
                        f"Your fairness score is **{score}/100** — this is critically low. "
                        f"The model is systematically disadvantaging the **\"{min_group}\"** group, "
                        f"with a selection rate of only **{min_rate:.1%}** compared to **{max_rate:.1%}** for \"{max_group}\". "
                        f"That's a **{gap_pct:.1f}pp gap**.\n\n"
                        f"⚠️ **Risk Level**\n{risk}\n\n"
                        f"🛠 **Recommended Actions**\n"
                        f"- **Rebalance** your training data — \"{min_group}\" is underrepresented\n"
                        f"- **Audit proxy variables** — features correlating with `{sensitive}` amplify bias\n"
                        f"- **Apply fairness constraints** (e.g., equalized odds) during model training\n"
                        f"- **Adjust decision thresholds** per group to equalize selection rates\n\n"
                        f"💡 **Micro-insight**: A {gap_pct:.1f}pp gap this large typically indicates systemic sampling bias, not random noise.")
            elif score < 75:
                return (f"🔍 **Insight**\n"
                        f"Your fairness score is **{score}/100** — moderate bias detected. "
                        f"The gap between \"{max_group}\" ({max_rate:.1%}) and \"{min_group}\" ({min_rate:.1%}) "
                        f"is **{gap_pct:.1f}pp**. Not critical, but trending toward actionable disparity.\n\n"
                        f"⚠️ **Risk Level**\n{risk}\n\n"
                        f"🛠 **Recommended Actions**\n"
                        f"- **Investigate proxy features** that may correlate with `{sensitive}`\n"
                        f"- **Run counterfactual analysis** — swap `{sensitive}` values and check outcome changes\n"
                        f"- **Set up automated monitoring** to catch drift before it worsens\n\n"
                        f"💡 **Tip**: Moderate bias often hides in feature interactions — check 2nd-order correlations.")
            else:
                return (f"🔍 **Insight**\n"
                        f"Your fairness score is **{score}/100** — within the fair range. "
                        f"Selection rates across `{sensitive}` groups are well-balanced, "
                        f"with only a **{gap_pct:.1f}pp** difference.\n\n"
                        f"⚠️ **Risk Level**\n{risk}\n\n"
                        f"🛠 **Recommended Actions**\n"
                        f"- **Continue monitoring** — fairness can drift with new data\n"
                        f"- **Document compliance** — create a model card with these metrics\n"
                        f"- **Test edge cases** — fairness at aggregate level doesn't guarantee subgroup fairness\n\n"
                        f"💡 **Tip**: Schedule quarterly fairness audits to maintain this benchmark.")
        return f"Your fairness score is **{score}/100**. Run an analysis to get deeper insights."

    # Disparate Impact
    if any(kw in q for kw in ['disparate impact', 'di ratio', 'impact ratio', 'what is di']):
        di_val = di if di else 'N/A'
        di_status = "within fair range" if isinstance(di, (int, float)) and 0.8 <= di <= 1.2 else "outside acceptable range"
        return (f"🔍 **Insight**\n"
                f"Your disparate impact ratio is **{di_val}** — {di_status}. "
                f"This measures the ratio of selection rates: "
                f"min({min_rate:.1%}) / max({max_rate:.1%}) = **{di_val}**.\n\n"
                f"The **4/5ths Rule** (used in US employment law):\n"
                f"- **DI < 0.8** → Legally actionable bias ⚠️\n"
                f"- **0.8 ≤ DI ≤ 1.2** → Fair range ✅\n"
                f"- **DI > 1.2** → Reverse bias (majority disadvantaged)\n\n"
                f"⚠️ **Risk Level**\n{risk}\n\n"
                f"🛠 **Recommended Actions**\n"
                f"- Review features that correlate with `{sensitive}` — these are likely proxy variables\n"
                f"- Consider **reweighting** training samples to equalize group representation\n"
                f"- Apply **post-processing calibration** to adjust model output probabilities\n\n"
                f"💡 **Legal context**: Under the 4/5ths rule, a DI below 0.8 can trigger regulatory scrutiny.")

    # Most affected group
    if any(kw in q for kw in ['most affected', 'which group', 'disadvantaged', 'who is hurt', 'impacted group']):
        group_size_info = ""
        if group_counts:
            min_count = group_counts.get(min_group, '?')
            max_count = group_counts.get(max_group, '?')
            group_size_info = f" Dataset has **{min_count}** {min_group} vs **{max_count}** {max_group} records."

        return (f"🔍 **Insight**\n"
                f"The **most disadvantaged group** is **\"{min_group}\"** with a selection rate of "
                f"**{min_rate:.1%}**, compared to **{max_rate:.1%}** for \"{max_group}\". "
                f"That's a **{gap_pct:.1f}pp gap** in positive outcomes for `{target}`.{group_size_info}\n\n"
                f"⚠️ **Risk Level**\n{risk}\n\n"
                f"🛠 **Recommended Actions**\n"
                f"- **Oversample** \"{min_group}\" using SMOTE or similar techniques\n"
                f"- **Check if `{target}` criteria** inherently disadvantage \"{min_group}\"\n"
                f"- **Apply group-specific thresholds** to equalize selection rates\n"
                f"- **Audit historical data** — was \"{min_group}\" historically underrepresented?\n\n"
                f"💡 **Pattern recognition**: This disparity pattern often stems from historical data collection bias rather than genuine group differences.")

    # Fix / Recommendations
    if any(kw in q for kw in ['fix', 'recommend', 'improve', 'solution', 'action', 'what should', 'how to fix', 'remediat']):
        if isinstance(score, (int, float)) and score < 50:
            return (f"🔍 **Insight**\n"
                    f"With a score of **{score}/100** and DI of **{di}**, this model requires urgent intervention. "
                    f"The \"{min_group}\" group is being systematically disadvantaged.\n\n"
                    f"⚠️ **Risk Level**\n{risk}\n\n"
                    f"🛠 **Recommended Actions** (Priority Order)\n"
                    f"1. **Data Rebalancing** — Use SMOTE oversampling for \"{min_group}\" or undersample \"{max_group}\"\n"
                    f"2. **Proxy Variable Audit** — Identify and remove features that correlate with `{sensitive}` (e.g., zip code → race, name → gender)\n"
                    f"3. **Fairness-Aware Training** — Apply in-processing constraints like equalized odds or demographic parity\n"
                    f"4. **Threshold Calibration** — Adjust decision boundaries per group to equalize positive prediction rates\n"
                    f"5. **Post-Processing** — Apply reject option classification to recalibrate borderline decisions\n\n"
                    f"💡 **Critical note**: Start with #2 (proxy audit) — it's the highest-ROI fix and often resolves 40-60% of measurable bias.")
        elif isinstance(score, (int, float)) and score < 75:
            return (f"🔍 **Insight**\n"
                    f"Score of **{score}/100** indicates moderate bias. The gap of {gap_pct:.1f}pp "
                    f"between groups is concerning but correctable.\n\n"
                    f"⚠️ **Risk Level**\n{risk}\n\n"
                    f"🛠 **Recommended Actions**\n"
                    f"1. **Counterfactual Testing** — Swap `{sensitive}` values and measure outcome delta\n"
                    f"2. **Feature Importance Audit** — Check if `{sensitive}` or its proxies rank high in feature importance\n"
                    f"3. **Calibration Plots** — Verify model is well-calibrated across groups\n"
                    f"4. **Monitoring Pipeline** — Set automated alerts for when DI drops below 0.8\n\n"
                    f"💡 **Tip**: Document your findings — model cards with fairness metrics are becoming regulatory requirements.")
        else:
            return (f"🔍 **Insight**\n"
                    f"Your model is performing well at **{score}/100**. Current bias levels are acceptable.\n\n"
                    f"⚠️ **Risk Level**\n{risk}\n\n"
                    f"🛠 **Maintenance Actions**\n"
                    f"- **Schedule quarterly audits** — fairness can degrade with data drift\n"
                    f"- **Test on subgroups** — aggregate fairness can mask subgroup disparities\n"
                    f"- **Build a model card** documenting current fairness metrics for compliance\n"
                    f"- **A/B test** before deploying updates to ensure fairness is maintained\n\n"
                    f"💡 **Proactive tip**: Consider intersectional analysis (e.g., gender × race) to catch hidden subgroup bias.")

    # Legal risks
    if any(kw in q for kw in ['legal', 'compliance', 'regulation', 'lawsuit', 'risk', 'liability']):
        legal_risk = "HIGH" if isinstance(di, (int, float)) and di < 0.8 else "MODERATE" if isinstance(di, (int, float)) and di < 1.0 else "LOW"
        return (f"🔍 **Insight**\n"
                f"Legal risk assessment based on current metrics: **{legal_risk}**. "
                f"Disparate impact of **{di}** "
                f"{'violates' if isinstance(di, (int, float)) and di < 0.8 else 'is near'} the 4/5ths rule threshold.\n\n"
                f"⚠️ **Regulatory Framework**\n"
                f"- **US**: Title VII, EEOC 4/5ths rule (DI < 0.8 = prima facie discrimination)\n"
                f"- **EU**: AI Act classifies hiring/lending as high-risk — fairness audits mandatory\n"
                f"- **NYC**: Local Law 144 requires annual bias audits for automated hiring tools\n\n"
                f"🛠 **Compliance Actions**\n"
                f"- Document this audit with timestamps (you have: {analysis.get('analysis_timestamp', 'N/A')})\n"
                f"- Create a public-facing model card with fairness metrics\n"
                f"- Implement a bias monitoring pipeline with alerting\n"
                f"- Maintain audit trail showing remediation efforts\n\n"
                f"💡 **Note**: Demonstrating awareness and active mitigation significantly reduces legal exposure.")

    # Explain concepts
    if any(kw in q for kw in ['what is', 'explain', 'define', 'meaning', 'how does', 'tell me about']):
        # Demographic parity
        if any(kw in q for kw in ['demographic parity', 'parity', 'selection rate']):
            return (f"🔍 **Insight**\n"
                    f"**Demographic Parity** means each group should receive positive outcomes at roughly equal rates. "
                    f"In your report:\n"
                    + "\n".join(f"- **{g}**: {r:.1%}" for g, r in parity.items()) +
                    f"\n\nThe gap of **{gap_pct:.1f}pp** between \"{max_group}\" and \"{min_group}\" "
                    f"{'exceeds' if gap_pct > 10 else 'is near'} acceptable thresholds.\n\n"
                    f"⚠️ **Risk Level**\n{risk}\n\n"
                    f"💡 **Context**: Perfect demographic parity (0% gap) isn't always the goal — "
                    f"the key is whether the gap reflects legitimate criteria or systemic bias.")

        # Fairness
        if any(kw in q for kw in ['fairness', 'fair', 'bias']):
            return (f"🔍 **Insight**\n"
                    f"**Algorithmic fairness** ensures ML models don't systematically disadvantage protected groups. "
                    f"There are multiple definitions:\n"
                    f"- **Demographic Parity** — Equal selection rates across groups\n"
                    f"- **Equalized Odds** — Equal TPR and FPR across groups\n"
                    f"- **Individual Fairness** — Similar individuals get similar outcomes\n\n"
                    f"Your report uses demographic parity and disparate impact. "
                    f"Current score: **{score}/100**, verdict: **{verdict}**.\n\n"
                    f"💡 **Key insight**: No single metric captures all fairness — "
                    f"but disparate impact + demographic parity together give a strong signal.")

    # Summary / overview
    if any(kw in q for kw in ['summary', 'overview', 'tell me everything', 'full report', 'summarize', 'break down']):
        return (f"🔍 **Full Report Summary**\n\n"
                f"📊 **Metrics**\n"
                f"- Fairness Score: **{score}/100**\n"
                f"- Disparate Impact: **{di}**\n"
                f"- Verdict: **{verdict}**\n"
                f"- Dataset: **{dataset_size}** records\n"
                f"- Target: `{target}` | Sensitive: `{sensitive}`\n\n"
                f"📈 **Group Selection Rates**\n"
                + "\n".join(f"- **{g}**: {r:.1%}" for g, r in parity.items()) +
                f"\n\n🚨 **Key Finding**\n"
                f"The \"{min_group}\" group has a **{gap_pct:.1f}pp lower** selection rate than \"{max_group}\". "
                f"{'This indicates significant systemic bias.' if isinstance(score, (int, float)) and score < 50 else 'This warrants investigation.' if isinstance(score, (int, float)) and score < 75 else 'This is within acceptable bounds.'}\n\n"
                f"⚠️ **Risk Level**\n{risk}\n\n"
                f"🛠 **Top 3 Actions**\n"
                f"1. Audit proxy variables correlated with `{sensitive}`\n"
                f"2. Rebalance training data for \"{min_group}\"\n"
                f"3. Apply fairness constraints during model training")

    # Greeting
    if any(kw in q for kw in ['hello', 'hi', 'hey', 'help', 'what can you do']):
        return (f"👋 I'm **FairSight AI** — your fairness audit analyst.\n\n"
                f"I've analyzed your current report and here's the snapshot:\n"
                f"- **Score**: {score}/100 | **DI**: {di} | **Verdict**: {verdict}\n"
                f"- **Most impacted**: \"{min_group}\" at {min_rate:.1%} vs \"{max_group}\" at {max_rate:.1%}\n\n"
                f"Ask me about:\n"
                f"- 📊 Your **fairness score** or **disparate impact**\n"
                f"- 🚨 Which **group is most affected**\n"
                f"- 🛠 **Specific fixes** to reduce bias\n"
                f"- ⚖️ **Legal risks** and compliance\n"
                f"- 📋 A full **report summary**\n\n"
                f"I don't do generic — every answer is tied to your actual data.")

    # Default / catch-all — still provide value
    return (f"🔍 **Insight**\n"
            f"Let me contextualize that with your current data:\n"
            f"- **Score**: {score}/100 | **DI**: {di} | **Verdict**: {verdict}\n"
            f"- **Gap**: {gap_pct:.1f}pp between \"{max_group}\" ({max_rate:.1%}) and \"{min_group}\" ({min_rate:.1%})\n\n"
            f"⚠️ **Risk Level**\n{risk}\n\n"
            f"I specialize in fairness analysis. Try asking me:\n"
            f"- \"Why is my fairness score low?\"\n"
            f"- \"Which group is most affected?\"\n"
            f"- \"What fixes should I apply?\"\n"
            f"- \"What are the legal risks?\"\n"
            f"- \"Give me a full summary\"\n\n"
            f"💡 Every answer I give is **data-driven** — tied directly to your audit metrics.")
