"""NSSP's four syndrome definitions, transcribed from their published ESSENCE syntax into Fieldwork's Apply ruleset.

The syntax is in data/nssp/*.syntax.txt as the NSSP Knowledge Repository's definition pages give it (read 2026-11-26).
It is parsed by the rules CDC states in "Free-text Coding in NSSP-ESSENCE" (Parts 1, 2 and 4, read 2026-11-26):

- `^term^` holds the term anywhere, ignoring capitals; a space inside the carets is part of the term.
- ANDNOT binds to the term immediately before it ("Multiple exclusionary statements in a row apply to the inclusionary
  term they immediately follow"); parentheses group; AND binds tighter than OR (Part 4 gives
  ^Fall^,AND,^Injur^,OR,^Fall^,AND,^Face^ as the same visits as (,^Fall^,or,^Fell^,),AND,(,^Injur^,or,^Face^,)).
- Brackets hold one character from a set: [;/ ] a semicolon, slash or space; [018] one of 0, 1, 8; ranges as [0-69]
  = 0 to 6, or 9 (Part 2's own example: [0-24] is "zero through two or four").
- A lone ^ is anything, everything or nothing (Part 1), so it passes a field with nothing in it.

Decisions this script makes, each written to data/nssp/transcription-notes.txt as it makes it:

- `|` inside brackets, as in th[o|r][a|o][a|r]t, is not described by CDC's guide; it is read as "o or r", which is what
  the pattern evidently spells (throat, thraot, ...).
- A code preceded by [;/ ] is a code in a diagnosis list: Fieldwork's "has an item starting with". ICD-9-CM codes are
  left out: the visits are of 2026 and carry none.
- SNOMED CT concept IDs are looked for in the SNOMED CT diagnosis column; text terms in the chief complaint (the visits'
  diagnosis columns hold codes only, so a text term finds nothing there, as it would in ESSENCE's combined field).
- An exclusion on a diagnosis column also passes a visit with no diagnosis recorded there, as ESSENCE's ^ passes an
  empty field.
- Each parenthesised group becomes a column of its own, named after its definition, so the rules keep NSSP's shape.

The ICD-11 ruleset is the same, with each ICD-10 code prefix replaced by its ICD-11 codes from
data/nssp/icd11-translation.csv: Fieldwork's translation, checked against WHO's 2026-01 release, not NSSP's.

python3 scripts/nssp_rules.py   (standard library only)
"""
import csv, itertools, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
NSSP = os.path.join(HERE, '..', 'data', 'nssp')
NOTES = []
note = NOTES.append

CC, ICD10, ICD11, SNOMED = 'fwa:chief_complaint', 'fwa:discharge_diagnosis_icd10', 'fwa:discharge_diagnosis_icd11', \
    'fwa:discharge_diagnosis_snomed'
FIELDS = [{'attribute': 'chief_complaint', 'predicate': CC, 'kind': 'term'},
          {'attribute': 'discharge_diagnosis_icd10', 'predicate': ICD10, 'kind': 'term'},
          {'attribute': 'discharge_diagnosis_icd11', 'predicate': ICD11, 'kind': 'term'},
          {'attribute': 'discharge_diagnosis_snomed', 'predicate': SNOMED, 'kind': 'term'}]
DEFINITIONS = [  # file, short name, column, title as NSSP gives it
    ('ili-ccdd-v1', 'ili', 'ILI CCDD v1'),
    ('cdc-broad-acute-respiratory-dd-v1', 'broad_respiratory', 'CDC Broad Acute Respiratory DD v1'),
    ('norovirus-v1', 'norovirus', 'Norovirus v1'),
    ('cdc-measles-ccdd-v1', 'measles', 'CDC Measles CCDD v1'),
]

# ---- reading the syntax ---------------------------------------------------------------------------------------------

def expand(pattern):
    """Every string a bracketed pattern stands for: [abc] one of a, b, c; [0-69] 0 to 6 or 9; | read as "or"."""
    parts = []
    for literal, bracket in re.findall(r'([^\[]*)(?:\[([^\]]*)\])?', pattern):
        if literal:
            parts.append([literal])
        if bracket:
            chars, body = [], bracket.replace('|', '')
            i = 0
            while i < len(body):
                if i + 2 < len(body) and body[i + 1] == '-':
                    chars += [chr(c) for c in range(ord(body[i]), ord(body[i + 2]) + 1)]; i += 3
                else:
                    chars.append(body[i]); i += 1
            parts.append(chars)
    return [''.join(p) for p in itertools.product(*parts)] if parts else ['']

def tokens(text, name):
    out = []
    for raw in text.split(','):
        t = raw.strip()
        if not t:
            continue
        m = re.match(r'^(or|and|andnot)(\^.*)$', t, re.I)
        if m:  # an operator run into its term: "or^[;/ ]74918002^" in the measles definition
            note(f'{name}: "{t}" has no comma after the operator; read as {m.group(1).lower()} followed by the term.')
            out += [m.group(1).lower(), m.group(2)]
            continue
        out.append(t.lower() if t.lower() in ('or', 'and', 'andnot') else t)
    return out

def parse(toks):
    """expr := and (OR and)* ; and := chain (AND chain)* ; chain := atom (ANDNOT atom)* ; atom := term | ( expr )."""
    pos = 0
    def atom():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == '(':
            e = expr(); assert toks[pos] == ')', toks[pos:pos + 3]; pos += 1
            return ('group', e)
        return ('term', t)
    def chain():
        nonlocal pos
        head, neg = atom(), []
        while pos < len(toks) and toks[pos] == 'andnot':
            pos += 1; neg.append(atom())
        return (head, neg)
    def conj():
        nonlocal pos
        cs = [chain()]
        while pos < len(toks) and toks[pos] == 'and':
            pos += 1; cs.append(chain())
        return cs
    def expr():
        nonlocal pos
        alts = [conj()]
        while pos < len(toks) and toks[pos] == 'or':
            pos += 1; alts.append(conj())
        return alts
    e = expr()
    assert pos == len(toks), toks[pos:]
    return e

def classify(term, name):
    """(field kind, words) for one term; None where the term is left out; ('any', []) for a lone caret."""
    body = term.strip()
    if body.startswith('^'):
        body = body[1:]
    if body.endswith('^'):
        body = body[:-1]
    if body == '':
        return ('any', [])
    if body.lower().startswith('[;/ ]'):
        code = body[5:].strip()
        code = re.sub(r'(;|\[;/ \])$', '', code).strip()
        if re.fullmatch(r'\d{6,}', code):
            return ('snomed', [code])
        if re.match(r'\d', code):
            return None  # ICD-9-CM
        return ('icd10', [c.upper() for c in expand(code)])
    if re.fullmatch(r'\d{6,}', body.strip()):
        return ('snomed', [body.strip()])
    if '^' in body:
        # A caret inside a term is a wildcard (Part 1): "sore ^throat" is "sore ", then anything, then "throat". Each
        # piece must be there; the order between them is not checked here, which ESSENCE's would be.
        note(f'{name}: "{body}" holds a caret inside it, a wildcard: read as every piece present, '
             'without checking their order, which ESSENCE would.')
        return ('text_all', [expand(piece.lower()) for piece in body.split('^') if piece])
    words = expand(body.lower())
    if any('|' in b for b in re.findall(r'\[([^\]]*)\]', body)):
        note(f'{name}: "{body}" holds | inside brackets, read as "or": {len(words)} spellings.')
    return ('text', words)

# ---- writing Fieldwork's rules ----------------------------------------------------------------------------------------

def quoted(word):
    return f'"{word}"' if word != word.strip() else word

class Writer:
    def __init__(self, code_field, translate):
        self.rules, self.columns, self.code_field, self.translate = [], [], code_field, translate

    def condition(self, kind, words, negate=False):
        if kind == 'text':
            return [{'field': CC, 'comparator': 'notContains' if negate else 'contains', 'value': ', '.join(quoted(w) for w in words)}]
        if kind == 'text_all':
            assert not negate, 'an exclusion with a wildcard inside it'
            return [{'field': CC, 'comparator': 'contains', 'value': ', '.join(quoted(w) for w in piece)} for piece in words]
        field = SNOMED if kind == 'snomed' else self.code_field
        if kind == 'icd10':
            words = self.translate(words)
            if not words:
                return None
        return [{'field': field, 'comparator': 'notStartsWith' if negate else 'startsWith', 'value': ', '.join(words)}]

    def column(self, base, label):
        name = base if base not in self.columns else f'{base}_{len(self.columns)}'
        self.columns.append(name)
        return name

    def exclusion_groups(self, negated, name, ctx):
        """The exclusions on one term, as alternatives to choose one from each: all text words in one "contains none of",
        all codes on a field in one "has no item starting with", which also passes where nothing is recorded there."""
        options, by_field = [], {}
        for kind_atom in negated:
            if kind_atom[0] == 'group':
                col = self.emit(kind_atom[1], f'{ctx}_excluded', name)
                if col is None:
                    continue
                options.append([[{'field': f'fwa:{col}', 'comparator': 'notEquals', 'value': 'yes'}]])
                continue
            c = classify(kind_atom[1], name)
            if c is None or c[0] == 'any':
                continue
            cond = self.condition(c[0], c[1], negate=True)
            if cond is None:
                continue
            for one in cond:
                held = by_field.setdefault((one['field'], one['comparator']), [])
                held += [w for w in one['value'].split(', ') if w not in held]
        for (field, comparator), words in by_field.items():
            cond = [{'field': field, 'comparator': comparator, 'value': ', '.join(words)}]
            options.append([cond] if field == CC else [cond, [{'field': f'{field}Known', 'comparator': 'equals', 'value': False}]])
        return options

    def emit(self, expr, base, name):
        """A column holding yes where the expression holds, no otherwise; returns the column's name."""
        col = self.column(base, name)
        groups, simple = [], {}
        for conj in expr:
            alternatives = [[]]
            for (head, negated) in conj:
                head_conds = []
                if head[0] == 'group':
                    sub = self.emit(head[1], f'{col}_part', name)
                    if sub is None:
                        alternatives = None; break
                    head_conds = [{'field': f'fwa:{sub}', 'comparator': 'equals', 'value': 'yes'}]
                else:
                    c = classify(head[1], name)
                    if c is None:
                        alternatives = None; break
                    if c[0] != 'any':
                        cond = self.condition(c[0], c[1])
                        if cond is None:
                            alternatives = None; break
                        head_conds = cond
                ex = self.exclusion_groups(negated, name, col)
                combos = [sum(choice, []) for choice in itertools.product(*ex)] if ex else [[]]
                alternatives = [a + head_conds + c for a in alternatives for c in combos]
            if alternatives is None:
                continue
            for alt in alternatives:
                if len(alt) == 1 and alt[0]['comparator'] in ('contains', 'startsWith'):
                    key = (alt[0]['field'], alt[0]['comparator'])
                    simple.setdefault(key, []).extend(w.strip() and w for w in alt[0]['value'].split(', '))
                else:
                    groups.append({'all': alt})
        for (field, comparator), words in simple.items():
            seen = list(dict.fromkeys(words))
            groups.insert(0, {'all': [{'field': field, 'comparator': comparator, 'value': ', '.join(seen)}]})
        if not groups:
            # Every term in it was left out (ICD-9-CM only): the alternative it stands in falls away with it.
            note(f'{name}: a group holding only codes left out (ICD-9-CM) is dropped, and the alternative it was part of.')
            self.columns.remove(col)
            return None
        self.rules.append({'any': groups, 'then': [{'predicate': f'fwa:{col}', 'value': 'yes'}]})
        return col

def sections(text):
    """Norovirus v1 gives three fields' expressions, which all hold; the others one expression."""
    labelled = re.split(r'^(ChiefComplaints:|CC and DD:|Discharge Diagnosis:)\s*$', text.strip(), flags=re.M)
    if len(labelled) == 1:
        return [('', text.strip())]
    return [(labelled[i].rstrip(':'), labelled[i + 1].strip()) for i in range(1, len(labelled), 2)]

def icd11_translator():
    rows = list(csv.DictReader(open(os.path.join(NSSP, 'icd11-translation.csv'), encoding='utf-8')))
    table = {}
    for r in rows:
        keys = r['icd10cm'].split()
        if 'to' in keys:  # J12 to J18
            a, b = keys[0], keys[2]
            keys = [f'{a[0]}{n}' for n in range(int(a[1:]), int(b[1:]) + 1)]
        for k in keys:
            table.setdefault(k.replace('.', ''), set()).update(r['icd11'].split())
    untranslated = {r['icd10cm'] for r in rows if r['role'] == 'not translated'}
    def translate(prefixes):
        out = []
        for p in prefixes:
            bare = p.replace('.', '')
            if any(bare == u.replace('.', '') for u in untranslated):
                continue
            hits = [codes for k, codes in table.items() if k.startswith(bare) or bare.startswith(k)]
            if not hits:
                raise SystemExit(f'No ICD-11 translation for {p}')
            for codes in hits:
                out += sorted(codes)
        return list(dict.fromkeys(out))
    return translate

# THE GROUPS' NAMES, from each definition's factsheet (Table 1's headings), in the order the groups are met. A trainee
# reading the rules reads NSSP's own words for each part, not a numbered helper column.
GROUP_NAMES = {
    'ili': ['ili_fever_terms', 'ili_respiratory_or_sore_throat_terms', 'ili_influenza_codes_and_terms'],
    'broad_respiratory': ['broad_respiratory_dyspnea_codes', 'broad_respiratory_fever_code'],
    'norovirus': ['norovirus_stomach_with_bug_virus_or_flu', 'norovirus_bug_virus_or_flu'],
    'measles': ['measles_inclusion', 'measles_exclusion'],
}
SECTION_NAMES = {'ChiefComplaints': 'chief_complaint', 'CC and DD': 'cc_and_dd', 'Discharge Diagnosis': 'discharge_diagnosis'}

def ruleset(code_field, translate, title, says):
    w = Writer(code_field, translate)
    rename = {}
    for file, short, label in DEFINITIONS:
        text = open(os.path.join(NSSP, f'{file}.syntax.txt'), encoding='utf-8').read()
        before, parts = len(w.columns), []
        split = sections(text)
        for section, body in split:
            top = f'{short}_{SECTION_NAMES[section]}' if section else short
            parts.append(w.emit(parse(tokens(body, label)), top, label))
        if len(split) > 1:  # Norovirus v1: every field's expression must hold
            w.rules.append({'any': [{'all': [{'field': f'fwa:{p}', 'comparator': 'equals', 'value': 'yes'} for p in parts]}],
                            'then': [{'predicate': f'fwa:{short}', 'value': 'yes'}]})
            w.columns.append(short)
        groups = [c for c in w.columns[before:] if c not in parts and c != short]
        names = GROUP_NAMES[short]
        if len(groups) != len(names):
            raise SystemExit(f'{label}: {len(groups)} groups, {len(names)} names: {groups}')
        rename.update(dict(zip(groups, names)))
    swap = lambda text: re.sub(r'fwa:([a-z0-9_]+)', lambda m: f'fwa:{rename.get(m.group(1), m.group(1))}', text)
    rules = json.loads(swap(json.dumps(w.rules)))
    columns = [rename.get(c, c) for c in w.columns]
    return {'schema': 'fieldwork/authored-ruleset/1', 'title': title,
            'mustNotBeReadAs': 'a diagnosis or a case: a syndrome definition sorts visits by what was written about '
                               'them, before anyone has confirmed anything',
            'description': says,
            'fields': [f for f in FIELDS if f['predicate'] in (CC, code_field, SNOMED)],
            'parameters': [],
            'rules': rules,
            'otherwise': [{'predicate': f'fwa:{c}', 'value': 'no'} for c in columns]}

CREDIT = ('Transcribed from the National Syndromic Surveillance Program (NSSP) Community of Practice\'s definitions on the '
          'NSSP Knowledge Repository: ILI CCDD v1, CDC Broad Acute Respiratory DD v1, Norovirus v1 and CDC Measles CCDD v1. '
          'NSSP and CDC do not endorse Fieldwork or this example.')

def main():
    identity = lambda prefixes: prefixes
    published = ruleset(ICD10, identity, 'NSSP syndromes, as published (ICD-10 and SNOMED CT)',
                        CREDIT + ' Read with ICD-10 codes, as NSSP\'s ICD-10-CM codes are written; ICD-9-CM codes left out.')
    translated = ruleset(ICD11, icd11_translator(), 'NSSP syndromes, with ICD-11 in place of ICD-10 (Fieldwork\'s translation)',
                         CREDIT + ' The ICD-11 codes are Fieldwork\'s translation of NSSP\'s ICD-10-CM codes, checked against '
                         'WHO\'s ICD-11 2026-01 release (data/nssp/icd11-translation.csv); NSSP publishes no ICD-11.')
    for name, rs in (('nssp-syndromes.ruleset.json', published), ('nssp-syndromes-icd11.ruleset.json', translated)):
        with open(os.path.join(HERE, '..', 'data', name), 'w', encoding='utf-8') as f:
            json.dump(rs, f, indent=1, ensure_ascii=False); f.write('\n')
        print(f'{name}: {len(rs["rules"])} rules, {len(rs["otherwise"])} columns')
    with open(os.path.join(NSSP, 'transcription-notes.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(dict.fromkeys(NOTES)) + '\n')
    print('\n'.join(dict.fromkeys(NOTES)))

if __name__ == '__main__':
    main()
