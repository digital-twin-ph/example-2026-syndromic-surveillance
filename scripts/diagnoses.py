"""Discharge diagnoses for the made-up visits, in three code systems, and the seeded events NSSP's definitions are tried on.

Added 2026-11-26 for NSSP's syndrome definitions, which read the discharge diagnosis as well as the chief complaint. Each
draw uses a random sequence of its own, so the visits make_visits.py drew before are unchanged except where said:

- **A discharge diagnosis** for each visit, from the syndrome it was generated as: one code, sometimes two, written in
  WHO's ICD-10 (`discharge_diagnosis_icd10`), in ICD-11 (`discharge_diagnosis_icd11`) and in SNOMED CT
  (`discharge_diagnosis_snomed`), codes separated by semicolons. ICD-10 here is WHO's, not the United States' ICD-10-CM
  that NSSP's definitions are written in: where the two differ (R06.0 against R06.00 and R06.02), a definition written
  for one finds nothing in the other, which is part of what the example shows.
- **Missing and late.** About one visit in eight has no diagnosis at all. The rest arrive 0 to 5 days after the visit,
  in `diagnosis_received`, as a feed fills in after discharge.
- **Norovirus** is diagnosed in about one ordinary gastrointestinal visit in eleven (A08.1), all year. In the outbreak
  make_visits.py seeds at North General, about half the complaints are written as NSSP's norovirus terms find them
  ("stomach bug", "norovirus at school"), and about four in ten are diagnosed A08.1.
- **A measles cluster**, 4 to 24 May 2026 at Riverside Community among children under 18: rash visits rewritten as
  measles complaints and diagnosed B05.9; and a few visits for MMR vaccination, which NSSP's measles definition is
  written to leave out.

Every ICD-10 and ICD-11 code below is checked, when this runs, against WHO's 2026-01 mapping and tabulation; every SNOMED
CT concept is looked up by its fully specified name in SNOMED International's Global Patient Set (GPS, CC BY-ND 4.0), and
the run stops on a name it cannot find. Set ICD11_DIR to the folder holding WHO's tabulation and mapping text files,
and GPS_FILE to the GPS release's tab-separated file.
"""
import csv, datetime as dt, os, random

# (ICD-10, ICD-11, SNOMED CT fully specified name) for each diagnosis a visit can carry.
DX = {
    'influenza_unidentified': ('J11.1', '1E32', 'Influenza (disorder)'),
    'influenza_seasonal': ('J10.1', '1E30', 'Influenza caused by Influenza A virus (disorder)'),
    'uri': ('J06.9', 'CA07.0', 'Acute upper respiratory infection (disorder)'),
    'fever': ('R50.9', 'MG26', 'Fever (finding)'),
    'bronchitis': ('J20.9', 'CA42.Z', 'Acute bronchitis (disorder)'),
    'pneumonia': ('J18.9', 'CA40.Z', 'Pneumonia (disorder)'),
    'dyspnoea': ('R06.0', 'MD11.5', 'Dyspnea (finding)'),
    'cough': ('R05', 'MD12', 'Cough (finding)'),
    'asthma': ('J45.9', 'CA23.32', 'Asthma (disorder)'),
    'copd_exacerbation': ('J44.1', 'CA22.0', 'Acute exacerbation of chronic obstructive pulmonary disease (disorder)'),
    'viral_gastro': ('A08.4', '1A2Z', 'Viral gastroenteritis (disorder)'),
    'gastro': ('A09', '1A40.Z', 'Gastroenteritis presumed infectious (disorder)'),
    'vomiting': ('R11', 'MD90.1', 'Vomiting (disorder)'),
    'norovirus': ('A08.1', '1A23', 'Inflammation of intestine caused by Norovirus (disorder)'),
    'rash': ('R21', 'ME62.Y', 'Eruption of skin (disorder)'),
    'urticaria': ('L50.9', 'EB0Y', 'Urticaria (disorder)'),
    'measles': ('B05.9', '1F03.0', 'Measles (disorder)'),
    'mmr_given': ('Z27.4', 'QC03.4', 'Measles, mumps and rubella vaccination given (situation)'),
    'ankle_sprain': ('S93.4', 'ND14.7Z', 'Sprain of ankle (disorder)'),
    'finger_wound': ('S61.0', 'NC52.0Z', 'Laceration of finger (disorder)'),
    'wrist_fracture': ('S52.5', 'NC32.5Z', 'Fracture of distal end of radius (disorder)'),
    'concussion': ('S06.0', 'NA07.0Z', 'Concussion injury of brain (disorder)'),
    'burn': ('T30.0', 'NE11', 'Burn injury (morphologic abnormality)'),
    'open_wound': ('T14.1', 'ND56.1', 'Open wound (disorder)'),
    'chest_pain': ('R07.4', 'MD30.Z', 'Chest pain (finding)'),
    'abdominal_pain': ('R10.4', 'MD81.4', 'Abdominal pain (finding)'),
    'headache': ('R51', '8A8Z', 'Headache (finding)'),
    'uti': ('N39.0', 'GC08.Z', 'Urinary tract infectious disease (disorder)'),
    'dizziness': ('R42', 'MB48.Z', 'Dizziness (finding)'),
    'anxiety': ('F41.9', '6B0Z', 'Anxiety disorder (disorder)'),
    'syncope': ('R55', 'MG45.Z', 'Syncope and collapse (finding)'),
    'toothache': ('K08.8', 'DA0A.Z', 'Toothache (finding)'),
    'repeat_prescription': ('Z76.0', 'QB92', 'Renewal of prescription (procedure)'),
    'eye_pain': ('H57.1', 'MC18', 'Pain in eye (finding)'),
    'earache': ('H92.0', 'AB70.2', 'Otogenic otalgia (finding)'),
    'palpitations': ('R00.2', 'MC81.2', 'Palpitations (finding)'),
    'malaise': ('R53', 'MG4Y', 'Malaise (finding)'),
    'low_back_pain': ('M54.5', 'ME84.2Z', 'Low back pain (finding)'),
    'dysuria': ('R30.0', 'MF50.7', 'Dysuria (finding)'),
}
# Which diagnoses each generated syndrome is given, with weights; a second code is added sometimes, as a fever beside
# influenza is.
BY_SYNDROME = {
    'influenza-like': [('influenza_unidentified', 4), ('influenza_seasonal', 2), ('uri', 3), ('fever', 1)],
    'respiratory': [('bronchitis', 3), ('pneumonia', 2), ('dyspnoea', 2), ('cough', 2), ('asthma', 2), ('copd_exacerbation', 1)],
    # Norovirus is diagnosed year-round, not only in an outbreak: about one gastrointestinal visit in eleven.
    'gastrointestinal': [('viral_gastro', 4), ('gastro', 4), ('vomiting', 2), ('norovirus', 1)],
    'rash': [('rash', 3), ('urticaria', 2)],
    'injury': [('ankle_sprain', 3), ('finger_wound', 3), ('wrist_fracture', 2), ('concussion', 2), ('burn', 1), ('open_wound', 2)],
    'other': [('chest_pain', 3), ('abdominal_pain', 3), ('headache', 3), ('uti', 2), ('dizziness', 2), ('anxiety', 1),
              ('syncope', 1), ('toothache', 1), ('repeat_prescription', 1), ('eye_pain', 1), ('earache', 1),
              ('palpitations', 1), ('malaise', 1), ('low_back_pain', 1), ('dysuria', 1)],
}
# A complaint that names its problem is diagnosed as that problem, so a visit reads as one story: "ankle injury" as a
# sprain, not a concussion. Complaints not listed take a diagnosis drawn for their syndrome.
BY_COMPLAINT = {
    'fall': 'wrist_fracture', 'laceration to hand': 'finger_wound', 'MVC': 'concussion', 'ankle injury': 'ankle_sprain',
    'fx wrist?': 'wrist_fracture', 'head injury': 'concussion', 'dog bite': 'open_wound', 'burn to arm': 'burn',
    'back pain after lifting': 'low_back_pain', 'knee pain s/p fall': 'open_wound', 'cut finger': 'finger_wound',
    'chest pain': 'chest_pain', 'abd pain': 'abdominal_pain', 'abdominal pain': 'abdominal_pain', 'headache': 'headache',
    'dizziness': 'dizziness', 'UTI sx': 'uti', 'dysuria': 'dysuria', 'med refill': 'repeat_prescription',
    'anxiety': 'anxiety', 'syncope': 'syncope', 'eye pain': 'eye_pain', 'tooth pain': 'toothache', 'weakness': 'malaise',
    'palpitations': 'palpitations', 'ear pain': 'earache', 'back pain': 'low_back_pain',
    'shortness of breath': 'dyspnoea', 'SOB': 'dyspnoea', 'difficulty breathing': 'dyspnoea', 'wheezing': 'asthma',
    'asthma exacerbation': 'asthma', 'COPD flare': 'copd_exacerbation', 'cough x1 week': 'bronchitis',
    'hives': 'urticaria',
}
SECOND = {'influenza-like': ('fever', 0.35), 'respiratory': ('cough', 0.25), 'gastrointestinal': ('vomiting', 0.2)}
NOROVIRUS_COMPLAINTS = ['stomach bug', 'stomach virus', 'norovirus at school', 'noro v outbreak at school', 'stomach bug, vomiting']
MEASLES_WINDOW = (dt.date(2026, 5, 4), dt.date(2026, 5, 24))
MEASLES_COMPLAINTS = ['rash and fever, measles?', 'measels exposure, rash', 'fever rash cough, ?measles', 'rubeola rash',
                      'rash fever conjunctivitis']
MMR_COMPLAINTS = ['MMR vaccine', 'mmr shot', 'measles vaccine due']

def weighted(rng, pairs):
    total = sum(w for _, w in pairs)
    u, t = rng.random() * total, 0.0
    for value, w in pairs:
        t += w
        if u < t:
            return value
    return pairs[-1][0]

def check_codes():
    """Every ICD-10 code in WHO's 2026-01 mapping, mapped to the ICD-11 code given; every ICD-11 code in the tabulation;
    every SNOMED CT name in the GPS. Returns {name: concept id}."""
    folder, gps = os.environ.get('ICD11_DIR'), os.environ.get('GPS_FILE')
    if not folder or not gps:
        raise SystemExit('Set ICD11_DIR (WHO ICD-11 2026-01 tabulation and mapping) and GPS_FILE (the SNOMED CT GPS).')
    tab = {r['Code'] for r in csv.DictReader(open(os.path.join(folder, 'tab', 'SimpleTabulation-ICD-11-MMS-en.txt'),
                                                  encoding='utf-8-sig'), delimiter='\t') if r.get('Code')}
    mapped = {r['icd10Code']: r['icd11Code'] for r in csv.DictReader(open(os.path.join(folder, 'map', '10To11MapToOneCategory.txt'),
                                                                         encoding='utf-8-sig'), delimiter='\t') if r['icd10Code']}
    problems = []
    for key, (icd10, icd11, _) in DX.items():
        if icd10 not in mapped:
            problems.append(f'{key}: {icd10} is not in WHO ICD-10')
        elif mapped[icd10] != icd11:
            problems.append(f'{key}: WHO maps {icd10} to {mapped[icd10]}, not {icd11}')
        if icd11 not in tab:
            problems.append(f'{key}: {icd11} is not in ICD-11 2026-01')
    concepts = {}
    with open(gps, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            if row.get('Active') == '1':  # an inactive concept is not one a record would be coded with now
                concepts.setdefault(row['FSN'].strip(), row['ConceptID'].strip())
    ids = {}
    for key, (_, _, fsn) in DX.items():
        if fsn in concepts:
            ids[fsn] = concepts[fsn]
        else:
            problems.append(f'{key}: "{fsn}" is not a fully specified name in the GPS')
    if problems:
        raise SystemExit('\n'.join(problems))
    return ids

def add(visits, truth, start, days):
    ids = check_codes()
    tby = {t['visit_id']: t for t in truth}
    dx_rng, late_rng, rewrite_rng = random.Random(20261126), random.Random(20261127), random.Random(20261128)
    # The measles cluster: rash visits of children at Riverside in the window, about 12 of them.
    candidates = [v for v in visits if tby[v['visit_id']]['syndrome_generated'] == 'rash' and v['facility'] == 'Riverside Community'
                  and v['age_group'] in ('0-4', '5-17') and MEASLES_WINDOW[0].isoformat() <= v['date'] <= MEASLES_WINDOW[1].isoformat()]
    measles = set(v['visit_id'] for v in rewrite_rng.sample(candidates, min(12, len(candidates))))
    others = [v for v in visits if tby[v['visit_id']]['syndrome_generated'] == 'other' and v['age_group'] in ('0-4', '5-17')]
    mmr = set(v['visit_id'] for v in rewrite_rng.sample(others, 6))
    for v in visits:
        t = tby[v['visit_id']]
        syndrome, seeded = t['syndrome_generated'], int(t['seeded_outbreak'])
        t['seeded_measles'] = int(v['visit_id'] in measles)
        if v['visit_id'] in measles:
            v['chief_complaint'] = rewrite_rng.choice(MEASLES_COMPLAINTS)
            codes = ['measles'] + (['fever'] if rewrite_rng.random() < 0.5 else [])
        elif v['visit_id'] in mmr:
            v['chief_complaint'] = rewrite_rng.choice(MMR_COMPLAINTS)
            codes = ['mmr_given']
        elif seeded:
            if rewrite_rng.random() < 0.5:
                v['chief_complaint'] = rewrite_rng.choice(NOROVIRUS_COMPLAINTS)
            codes = ['norovirus' if rewrite_rng.random() < 0.4 else weighted(dx_rng, BY_SYNDROME['gastrointestinal'])]
        else:
            drawn = weighted(dx_rng, BY_SYNDROME[syndrome])  # drawn always, so the sequence is the same for every visit
            codes = [BY_COMPLAINT.get(v['chief_complaint'], drawn)]
            second = SECOND.get(syndrome)
            if second and dx_rng.random() < second[1] and second[0] not in codes:
                codes.append(second[0])
        u = late_rng.random()
        if u < 0.12:
            for k in ('discharge_diagnosis_icd10', 'discharge_diagnosis_icd11', 'discharge_diagnosis_snomed', 'diagnosis_received'):
                v[k] = ''
            continue
        delay = 0 if u < 0.60 else 1 if u < 0.78 else 2 if u < 0.88 else late_rng.randint(3, 5)
        v['discharge_diagnosis_icd10'] = ';'.join(DX[c][0] for c in codes)
        v['discharge_diagnosis_icd11'] = ';'.join(DX[c][1] for c in codes)
        v['discharge_diagnosis_snomed'] = ';'.join(ids[DX[c][2]] for c in codes)
        v['diagnosis_received'] = (dt.date.fromisoformat(v['date']) + dt.timedelta(days=delay)).isoformat()
    return {'measles': len(measles), 'mmr': len(mmr)}

COLUMNS = [
    ['discharge_diagnosis_icd10', 'Discharge diagnosis (ICD-10)', '',
     "WHO ICD-10 codes, separated by semicolons; empty where none was received"],
    ['discharge_diagnosis_icd11', 'Discharge diagnosis (ICD-11)', '',
     'ICD-11 codes (2026-01), separated by semicolons; the same diagnoses as the ICD-10 column'],
    ['discharge_diagnosis_snomed', 'Discharge diagnosis (SNOMED CT)', '',
     "SNOMED CT concept identifiers from SNOMED International's Global Patient Set, separated by semicolons"],
    ['diagnosis_received', 'Diagnosis received', '', 'The day the discharge diagnosis reached the feed, YYYY-MM-DD'],
]
