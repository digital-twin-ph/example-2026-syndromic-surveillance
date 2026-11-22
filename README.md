# Syndromic surveillance, 2026: a made-up district's emergency departments

A worked example for [Fieldwork](https://github.com/digital-twin-ph/fieldwork). **Every visit here is made up**: no
record describes a person, and the district, its three facilities and the outbreak are invented.

Syndromic surveillance watches what people come to emergency departments with, before anyone has a diagnosis, and asks
each day whether a kind of complaint is more common than its own recent past would lead one to expect. This example
does that in three steps a trainee can see and change:

1. **Sort chief complaints into syndromes** with declared keyword rules (Apply ruleset): "N/V/D" and "vomitting" are
   gastrointestinal, "fevr and cough" is influenza-like.
2. **Count visits per day and syndrome** (Cases by period).
3. **Flag unusual days** (Detect unusual counts): EARS C1, C2 and C3, CUSUM and EWMA.

## In Fieldwork

`fieldwork-project.json.gz` is the project, three workflows built from an empty canvas:

1. **Which syndrome does each complaint say?** The visits, and Apply ruleset with the worked definitions.
2. **Was there an unusual rise in any syndrome?** The same, counted by day and syndrome (Cases by period, each row one
   visit), then Detect unusual counts: CUSUM, the first 28 days as the baseline, starting again after a signal.
   Gastrointestinal visits signal on 7 days, from 14 April, the outbreak's second day, and on no other. Three charts:
   visits by day, one line per syndrome; gastrointestinal visits as bars, the threshold dashed over them, and a
   triangle on each day that signals; and CUSUM's running sum against its limit *h*.
3. **How do the methods differ?** Gastrointestinal visits by day through CUSUM, EWMA and EARS C2, each charted as it
   computes: its statistic against its limit, and the days that cross it.

To try the first attempt instead, open Apply ruleset's **Configure…**, choose **JSON**, and **Upload** the other file.

## Files

| File | What it is |
| --- | --- |
| `data/visits.csv` | 24,328 visits, Monday 5 January to Sunday 28 June 2026: date, facility, age group, sex, the chief complaint as triage wrote it, and age in years |
| `data/visits-columns.csv` | Its data dictionary |
| `data/truth.csv` | For each visit, the syndrome it was generated as and whether it belongs to the seeded outbreak. **Not for the workflow**: it is what a trainee checks their syndrome definitions and their signals against |
| `data/syndromes-first-attempt.ruleset.json` | Syndrome definitions as a first attempt might write them: a few words each. Upload it into Apply ruleset's JSON view |
| `data/syndromes.ruleset.json` | The worked definitions: more words, and exclusions that keep a visit to one syndrome |
| `fieldwork-project.json.gz` | The Fieldwork project: the three workflows above |
| `scripts/make_visits.py` | The generator: standard-library Python, seed 20261121, the same files on every run |

## What is built in

- About 140 visits a day, 15% more on Mondays and 15% fewer at weekends.
- Influenza-like illness falling from 18% of visits in January to 4% by June; gastrointestinal illness steady at 7%.
- **A seeded outbreak**: 113 extra gastrointestinal visits among 5 to 17-year-olds at North General, 13 to 22 April
  2026, rising to about 25 a day and falling away.
- Chief complaints as triage writes them: abbreviated, misspelled, ambiguous ("abd pain" is in `other`) and sometimes
  two problems at once ("diarrhea, fever"), so a definition built from keywords both misses and over-counts.

## How good are the syndrome definitions?

Each definition is a list of words a chief complaint contains, and words it must not. Measured against `truth.csv`:

| Syndrome | First attempt: found (sensitivity) | First attempt: right when it says so (PPV) | Worked definitions |
| --- | --- | --- | --- |
| Gastrointestinal | 46% | 100% | 100%, 100% |
| Influenza-like | 38% | 89% | 100%, 100% |
| Respiratory | 37% | 76% | 100%, 100% |
| Rash | 61% | 100% | 100%, 100% |
| Injury | 46% | 100% | 100%, 100% |

The first attempt also gives 1,340 visits two syndromes ("fever and cough" is both influenza-like and respiratory),
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

## Licence

The data and the generator: CC BY 4.0. Made-up data, so nothing here is restricted by anyone's terms.
