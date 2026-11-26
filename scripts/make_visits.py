"""Synthetic emergency department visits for Fieldwork's syndromic surveillance worked example.

Every visit is made up: no record describes a person. 25 weeks, Monday 5 January to Sunday 28 June 2026, at three
made-up facilities. Each visit has a date, a facility, an age group, a sex and a chief complaint written as triage staff
write them: short, abbreviated, sometimes misspelled, sometimes naming two problems.

What is built in, so a trainee can see what a syndrome definition and a detection method catch and miss:

- About 140 visits a day, 15% more on Mondays and 15% fewer at weekends.
- Influenza-like illness falling from 18% of visits in January to 4% by June; gastrointestinal illness steady at 7%.
- A seeded outbreak: extra gastrointestinal visits among 5 to 17-year-olds at North General, 13 to 22 April 2026,
  rising to about 25 a day and falling away, as a school norovirus outbreak would.

data/visits.csv holds what a surveillance system would receive. data/truth.csv holds, for each visit, the syndrome it
was generated as and whether it belongs to the seeded outbreak: kept apart, as truth is never in the data.

python3 scripts/make_visits.py   (standard library only; seed 20261121, so the files are the same on every run)
"""
import csv, datetime as dt, math, os, random
import diagnoses

R = random.Random(20261121)
START, DAYS = dt.date(2026, 1, 5), 175
FACILITIES = [('North General', 0.45), ('Riverside Community', 0.35), ('East Urgent Care', 0.20)]
AGES = [('0-4', 0.10), ('5-17', 0.14), ('18-44', 0.36), ('45-64', 0.22), ('65+', 0.18)]
OUTBREAK = (dt.date(2026, 4, 13), dt.date(2026, 4, 22))

# Chief complaints by syndrome, as triage writes them. Some are ambiguous on purpose ("abd pain"), some name two
# problems, some are misspelled: a syndrome definition built from keywords meets all three.
COMPLAINTS = {
    'gastrointestinal': ['vomiting', 'vomiting and diarrhea', 'N/V/D', 'n/v', 'diarrhea x2 days', 'diarrhoea', 'vomitting',
                         'stomach flu', 'abd pain and vomiting', 'gastroenteritis', 'nausea, vomiting', 'diarrhea, fever',
                         'throwing up since last night', 'GI upset', 'emesis x3'],
    'influenza-like': ['fever and cough', 'fevr and cough', 'flu like symptoms', 'flu sx', 'fever, body aches', 'cough fever chills',
                       'ILI', 'fever sore throat cough', 'high fever cough', 'influenza'],
    'respiratory': ['shortness of breath', 'SOB', 'difficulty breathing', 'wheezing', 'asthma exacerbation', 'cough x1 week',
                    'chest congestion', 'COPD flare'],
    'injury': ['fall', 'laceration to hand', 'MVC', 'ankle injury', 'fx wrist?', 'head injury', 'dog bite', 'burn to arm',
               'back pain after lifting', 'knee pain s/p fall', 'cut finger'],
    'rash': ['rash', 'itchy rash', 'rash and fever', 'hives', 'skin rash x3d'],
    'other': ['chest pain', 'abd pain', 'headache', 'dizziness', 'UTI sx', 'med refill', 'anxiety', 'syncope', 'eye pain',
              'tooth pain', 'weakness', 'palpitations', 'ear pain', 'back pain', 'dysuria', 'abdominal pain'],
}

def pick(pairs):
    u, t = R.random(), 0.0
    for value, w in pairs:
        t += w
        if u < t:
            return value
    return pairs[-1][0]

def poisson(lam):
    # Knuth's method in pieces, for means of a hundred and more.
    n = 0
    while lam > 30:
        n += poisson(30); lam -= 30
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= R.random()
        if p <= L:
            return n + k
        k += 1

def shares(day):
    """Each syndrome's share of a day's ordinary visits."""
    f = day / (DAYS - 1)
    ili = 0.18 - 0.14 * f
    fixed = {'gastrointestinal': 0.07, 'influenza-like': ili, 'respiratory': 0.10, 'injury': 0.22, 'rash': 0.02}
    fixed['other'] = 1 - sum(fixed.values())
    return list(fixed.items())

def outbreak_extra(date):
    """Extra gastrointestinal visits at North General among 5 to 17-year-olds: a rise, a peak, a fall."""
    if not OUTBREAK[0] <= date <= OUTBREAK[1]:
        return 0
    d = (date - OUTBREAK[0]).days
    return poisson(25 * math.exp(-((d - 4) ** 2) / 8))

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, '..', 'data')
    visits, truth, n = [], [], 0
    for day in range(DAYS):
        date = START + dt.timedelta(days=day)
        weekday = date.weekday()
        mean = 140 * (1.15 if weekday == 0 else 0.85 if weekday >= 5 else 1.0)
        rows = [(pick(shares(day)), pick(FACILITIES), pick(AGES), False) for _ in range(poisson(mean))]
        rows += [('gastrointestinal', 'North General', '5-17', True) for _ in range(outbreak_extra(date))]
        R.shuffle(rows)
        for syndrome, facility, age, seeded in rows:
            n += 1
            vid = f'V{n:06d}'
            visits.append({'visit_id': vid, 'date': date.isoformat(), 'facility': facility, 'age_group': age,
                           'sex': R.choice(['F', 'M']), 'chief_complaint': R.choice(COMPLAINTS[syndrome])})
            truth.append({'visit_id': vid, 'syndrome_generated': syndrome, 'seeded_outbreak': int(seeded)})
    # AGE IN YEARS, drawn within each visit's age group by a random sequence of its own, so adding it changed no visit.
    ages = random.Random(20261122)
    bounds = {'0-4': (0, 4), '5-17': (5, 17), '18-44': (18, 44), '45-64': (45, 64), '65+': (65, 95)}
    for v in visits:
        lo, hi = bounds[v['age_group']]
        v['age_years'] = ages.randint(lo, hi)
    # DISCHARGE DIAGNOSES AND THE SEEDED MEASLES CLUSTER (2026-11-26), each drawn by sequences of their own: scripts/diagnoses.py.
    seeded_events = diagnoses.add(visits, truth, START, DAYS)
    with open(os.path.join(out, 'visits.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(visits[0]))
        w.writeheader(); w.writerows(visits)
    with open(os.path.join(out, 'truth.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(truth[0]))
        w.writeheader(); w.writerows(truth)
    with open(os.path.join(out, 'visits-columns.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['variable', 'label', 'unit', 'description'])
        w.writerows([
            ['visit_id', 'Visit', '', 'A made-up identifier, one per visit'],
            ['date', 'Date of visit', '', 'The day the visit began, YYYY-MM-DD'],
            ['facility', 'Facility', '', 'One of three made-up emergency departments'],
            ['age_group', 'Age group', '', '0-4, 5-17, 18-44, 45-64 or 65+ years'],
            ['age_years', 'Age', 'years', 'Age in completed years, within the age group'],
            ['sex', 'Sex', '', 'F or M, as recorded at triage'],
            ['chief_complaint', 'Chief complaint', '', 'Free text as triage wrote it: abbreviated, sometimes misspelled'],
        ] + diagnoses.COLUMNS)
    seeded = sum(t['seeded_outbreak'] for t in truth)
    print(f'{len(visits)} visits over {DAYS} days, {seeded} of them the seeded outbreak; '
          f'{seeded_events["measles"]} seeded measles visits, {seeded_events["mmr"]} MMR vaccination visits')

if __name__ == '__main__':
    main()
