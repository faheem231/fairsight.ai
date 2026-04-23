import pandas as pd
import numpy as np
import os


def generate_hiring_demo():
    """
    Generate a 300-row DataFrame with deliberate gender bias for demonstration.
    Columns: age, gender, education, years_experience, skills_score, interview_score, hired
    - gender: 60% Male, 40% Female
    - hired rate: Male=65%, Female=30% (clear bias)
    - skills_score: 50-100, NO gender difference
    - interview_score: females scored ~10pt lower artificially
    - age: 22-55, normally distributed mean 35
    - education: Bachelor 50%, Master 35%, PhD 15%
    """
    np.random.seed(42)
    n = 300

    # Gender distribution: 60% Male, 40% Female
    n_male = int(n * 0.6)
    n_female = n - n_male
    genders = ['Male'] * n_male + ['Female'] * n_female
    np.random.shuffle(genders)
    genders = np.array(genders)

    # Age: normally distributed, mean 35, std 8, clipped to 22-55
    ages = np.random.normal(35, 8, n).astype(int)
    ages = np.clip(ages, 22, 55)

    # Education: Bachelor 50%, Master 35%, PhD 15%
    education_choices = np.random.choice(
        ['Bachelor', 'Master', 'PhD'],
        size=n,
        p=[0.50, 0.35, 0.15]
    )

    # Years of experience: correlated with age
    years_experience = np.maximum(0, ages - 22 + np.random.randint(-3, 4, n))
    years_experience = np.clip(years_experience, 0, 30)

    # Skills score: 50-100, NO gender difference
    skills_score = np.random.uniform(50, 100, n).round(1)

    # Interview score: 50-100, females artificially scored ~10 points lower
    interview_score = np.random.uniform(60, 100, n).round(1)
    for i in range(n):
        if genders[i] == 'Female':
            interview_score[i] = max(50, interview_score[i] - np.random.uniform(8, 14))
    interview_score = interview_score.round(1)

    # Hired: Males 65% rate, Females 30% rate (clear bias)
    hired = np.zeros(n, dtype=int)
    for i in range(n):
        if genders[i] == 'Male':
            hired[i] = 1 if np.random.random() < 0.65 else 0
        else:
            hired[i] = 1 if np.random.random() < 0.30 else 0

    df = pd.DataFrame({
        'age': ages,
        'gender': genders,
        'education': education_choices,
        'years_experience': years_experience,
        'skills_score': skills_score,
        'interview_score': interview_score,
        'hired': hired
    })

    # Save to demo directory
    if os.environ.get('VERCEL'):
        demo_dir = '/tmp/demo'
    else:
        demo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'demo')
    os.makedirs(demo_dir, exist_ok=True)
    filepath = os.path.join(demo_dir, 'hiring_bias_demo.csv')
    df.to_csv(filepath, index=False)

    return filepath
