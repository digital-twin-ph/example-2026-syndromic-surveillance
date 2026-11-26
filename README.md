# Syndromic surveillance, 2026: a made-up district's emergency departments

A worked example for [Fieldwork](https://github.com/digital-twin-ph/fieldwork). **Every visit here is made up**: no
record describes a person, and the district, its three facilities and the outbreak are invented.

Syndromic surveillance watches what people come to emergency departments with, before anyone has a diagnosis, and asks
each day whether a kind of complaint is more common than its own recent past would lead one to expect. A discharge
diagnosis follows days later, if at all. This example does that in three steps a trainee can see and change:

1. **Sort visits into syndromes** with declared rules (Apply ruleset): first with the example's own keywords ("N/V/D"
   and "vomitting" are gastrointestinal), then with four definitions the US National Syndromic Surveillance Program
   publishes, which read the discharge diagnosis as well as the complaint.
2. **Count visits per day and syndrome** (Cases by period).
3. **Flag unusual days** (Detect unusual counts): EARS C1, C2 and C3, CUSUM and EWMA.

## In Fieldwork

`fieldwork-project.json.gz` is the project, five workflows:

1. **Which syndrome does each complaint say?** The visits, and Apply ruleset with the worked definitions.
2. **Was there an unusual rise in any syndrome?** The same, counted by day and syndrome (Cases by period, each row one
   visit), then Detect unusual counts: CUSUM, the first 28 days as the baseline, starting again after a signal.
   Gastrointestinal visits signal on 7 days, from 14 April, the outbreak's second day, and on no other. Three charts:
   visits by day, one line per syndrome; gastrointestinal visits as bars, the threshold dashed over them, and a
   triangle on each day that signals; and CUSUM's running sum against its limit *h*.
3. **How do the methods differ?** Gastrointestinal visits by day through CUSUM, EWMA and EARS C2, each charted as it
   computes: its statistic against its limit, and the days that cross it.

4. **Which NSSP syndromes does each visit match?** The visits through NSSP's four definitions twice: as published, with
   ICD-10 and SNOMED CT codes, and with ICD-11 in place of ICD-10. Each visit gets a column for each definition, yes or
   no, and a column for each part of it, named as NSSP's own fact sheet names the part.
5. **Does NSSP's norovirus definition find the outbreak?** The visits Norovirus v1 matches, counted by day, then
   CUSUM over the first four weeks: 9 days signal, from 13 April, the outbreak's first day.

To try the first attempt at keywords instead, open Apply ruleset's **Configure…**, choose **JSON**, and **Upload** the
other file.

## NSSP's syndrome definitions

Four definitions from the NSSP Community of Practice's Knowledge Repository, transcribed from the query each page
publishes: **ILI CCDD v1**, **CDC Broad Acute Respiratory DD v1**, **Norovirus v1** and **CDC Measles CCDD v1**.

| Definition | Visits it matches | What it was meant to find |
| --- | --- | --- |
| ILI CCDD v1 | 2,177 | influenza-like illness: a fever and a cough or sore throat, or influenza named in words or codes |
| CDC Broad Acute Respiratory DD v1 | 2,987 | any acute respiratory illness, from the discharge diagnosis alone |
| Norovirus v1 | 223, among them 85 of the outbreak's 113 visits | norovirus, in words or the code A08.1 |
| CDC Measles CCDD v1 | 10, all 10 of the seeded measles visits; none of the 6 MMR vaccination visits | measles, but not a measles vaccination |

**What a trainee can see in them.**

- **A definition is written for its data.** NSSP writes for US records in ICD-10-CM; these visits are coded in WHO's
  ICD-10. Where the two differ, a definition finds nothing: Broad Acute Respiratory counts shortness of breath with a
  fever as R06.02 with R50.9, and WHO's ICD-10 has only R06.0.
- **One space matters.** Norovirus v1 looks for " flu " with a space each side, so "stomach flu" at the end of a
  complaint is not found, and only "stomach bug" and "stomach virus" are.
- **A diagnosis comes late, or not at all.** About one visit in eight has none, and the rest arrive up to five days
  after the visit (`diagnosis_received`). A definition reading only the diagnosis counts this week's visits next week.
- **Exclusions do work.** The measles definition leaves out every visit for MMR vaccination, by its words ("mmr shot")
  and by its codes.

**The ICD-11 version is Fieldwork's, not NSSP's.** NSSP publishes no ICD-11 codes. `data/nssp/icd11-translation.csv`
gives each ICD-10-CM code its ICD-11 codes, checked against WHO's ICD-11 release of 2026-01, with WHO's own mapping
beside it and a reason wherever the two differ. Two codes have no ICD-11 equivalent and are left out: hypoxaemia
(R09.02) and acute respiratory distress (R06.03). On these visits the two versions match the same visits: the only place
they would part, a dyspnoea with a fever, is in no visit.

**How the transcription reads NSSP's query language,** from CDC's *Free-text Coding in NSSP-ESSENCE*: a term is looked
for anywhere, ignoring capitals; an exclusion binds to the term just before it; AND binds before OR. Where it reads
differently, it says so in `data/nssp/transcription-notes.txt`:

- In ILI's `sore ^throat`, both words must be there; ESSENCE also requires them in that order.
- `[o|r]` inside brackets is read as "o or r".
- ICD-9-CM codes are left out, as visits in 2026 carry none.

## Files

| File | What it is |
| --- | --- |
| `data/visits.csv` | 24,328 visits, Monday 5 January to Sunday 28 June 2026: date, facility, age group, sex, the chief complaint as triage wrote it, age in years, and the discharge diagnosis in ICD-10, ICD-11 and SNOMED CT with the day it was received |
| `data/visits-columns.csv` | Its data dictionary |
| `data/truth.csv` | For each visit, the syndrome it was generated as, and whether it belongs to the seeded outbreak or the seeded measles cluster. **Not for the workflow**: it is what a trainee checks their syndrome definitions and their signals against |
| `data/syndromes-first-attempt.ruleset.json` | Syndrome definitions as a first attempt might write them: a few words each. Upload it into Apply ruleset's JSON view |
| `data/syndromes.ruleset.json` | The worked definitions: more words, and exclusions that keep a visit to one syndrome |
| `data/nssp-syndromes.ruleset.json` | NSSP's four definitions as Apply ruleset reads them, with ICD-10 and SNOMED CT |
| `data/nssp-syndromes-icd11.ruleset.json` | The same with ICD-11 in place of ICD-10 |
| `data/nssp/*.syntax.txt` | Each definition's query, as NSSP's page publishes it |
| `data/nssp/icd11-translation.csv` | Fieldwork's ICD-11 translation of the definitions' ICD-10-CM codes |
| `data/nssp/transcription-notes.txt` | Where the transcription reads the query differently from ESSENCE |
| `fieldwork-project.json.gz` | The Fieldwork project: the five workflows above |
| `scripts/make_visits.py`, `scripts/diagnoses.py` | The generator: standard-library Python, the same files on every run. The diagnoses step checks every code against WHO's ICD-11 files and SNOMED International's Global Patient Set, which it is given |
| `scripts/nssp_rules.py` | The transcription: NSSP's published queries into Apply ruleset's rules |
| `scripts/build_project.mjs` | Builds the project with Fieldwork's own modules and runs every workflow before writing it |

## What is built in

- About 140 visits a day, 15% more on Mondays and 15% fewer at weekends.
- Influenza-like illness falling from 18% of visits in January to 4% by June; gastrointestinal illness steady at 7%.
- **A seeded outbreak**: 113 extra gastrointestinal visits among 5 to 17-year-olds at North General, 13 to 22 April
  2026, rising to about 25 a day and falling away.
- Chief complaints as triage writes them: abbreviated, misspelled, ambiguous ("abd pain" is in `other`) and sometimes
  two problems at once ("diarrhea, fever"), so a definition built from keywords both misses and over-counts.
- **A discharge diagnosis** for each visit that has one, following its complaint ("ankle injury" is a sprained ankle),
  in WHO's ICD-10, ICD-11 and SNOMED CT. None for about one visit in eight; the rest arrive 0 to 5 days late.
  Norovirus (A08.1) is diagnosed in about one ordinary gastrointestinal visit in eleven, all year.
- **The outbreak in words NSSP's norovirus definition looks for**: about half its complaints are written "stomach bug",
  "stomach virus" or "norovirus at school", and about four in ten are diagnosed A08.1.
- **A seeded measles cluster**: 10 rash visits among children at Riverside Community, 4 to 24 May 2026, written as
  measles ("measels exposure, rash") and diagnosed B05.9; and 6 visits for MMR vaccination, which a measles definition
  should leave out.

## How good are the syndrome definitions?

Each definition is a list of words a chief complaint contains, and words it must not. Measured against `truth.csv`:

| Syndrome | First attempt: found (sensitivity) | First attempt: right when it says so (PPV) | Worked definitions |
| --- | --- | --- | --- |
| Gastrointestinal | 45% | 100% | 100%, 100% |
| Influenza-like | 38% | 90% | 100%, 100% |
| Respiratory | 37% | 76% | 100%, 100% |
| Rash | 60% | 100% | 100%, 100% |
| Injury | 46% | 100% | 100%, 100% |

The first attempt also gives 1,341 visits two syndromes ("fever and cough" is both influenza-like and respiratory),
so Apply ruleset gives them none and says so. The worked definitions find every visit because they were written
from the same list of complaints the generator draws on: real chief complaints are more varied, and no definition
is perfect. Improving the first attempt, and watching what each change does to the counts, is the exercise.

## What the methods find, on the generated syndromes

Gastrointestinal visits per day, all facilities, counted by the syndrome each visit was generated as (so before any
keyword rule): about 10 a day, about 30 at the outbreak's peak.

| Method | Days that signal | Of them, in the outbreak (13–22 April) |
| --- | --- | --- |
| EARS C1 | 5 | 2 |
| EARS C2 | 7 | 3 |
| EARS C3 | 19 | 6 |
| CUSUM, the first 28 days as baseline, starting again after a signal | 7 | 7 |
| EWMA, the first 28 days as baseline | 12 | 9; the other 3 are the days just after it, as the smoothed level comes down |

Every method finds the outbreak by its second day, 14 April. The EARS methods, holding each day to the week before it,
raise false alarms; C3, which adds three days together, raises the most. Whether a trainee's own syndrome definition
finds it as early is the first exercise.

## Licence and credit

The made-up visits and the scripts: CC BY 4.0 (`LICENSE-data`). Three things in them keep their owners' terms:

- **NSSP's syndrome definitions** (`data/nssp/*.syntax.txt`, and the rules transcribed from them) are the National
  Syndromic Surveillance Program Community of Practice's, from the NSSP Knowledge Repository
  (knowledgerepository.syndromicsurveillance.org), which states no licence for them. They are credited, not
  relicensed. NSSP and CDC do not endorse Fieldwork or this example.
- **SNOMED CT identifiers** are from SNOMED International's Global Patient Set, release of 2026-01-01, under CC BY-ND
  4.0. SNOMED CT® is a registered trademark of SNOMED International; © International Health Terminology Standards
  Development Organisation. Only identifiers are used, unaltered.
- **ICD-11 codes** are from WHO's ICD-11 for Mortality and Morbidity Statistics, release 2026-01, under CC BY-ND 3.0
  IGO. The translation in `data/nssp/icd11-translation.csv` is Fieldwork's, not WHO's or NSSP's.
