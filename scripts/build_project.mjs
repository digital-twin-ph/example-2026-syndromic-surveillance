// The Fieldwork project, brought up to the visits with discharge diagnoses and given NSSP's definitions (2026-11-26).
//
// Built with Fieldwork's own modules, so the table, its key and each workflow's manifest are what the application makes:
// the visits read by Fieldwork's CSV reader, keyed by tableDataKey, each workflow's inventory by syncProjectManifest, and
// every workflow run headless by executeWorkflow before the file is written. Open the project in Fieldwork afterwards
// to see it as a reader does.
//
// The first three workflows are kept, their table brought up to the new columns. Their own keyword definitions gain the
// norovirus outbreak's new wording (stomach bug, stomach virus, norov, noro v), which those complaints now use. Two
// workflows are added:
//   4. Which NSSP syndromes does each visit match? NSSP's four definitions as published, and with ICD-11.
//   5. Does NSSP's norovirus definition find the outbreak? Its visits by day, and CUSUM over the first four weeks.
//
// node scripts/build_project.mjs <a Fieldwork checkout, built>
import {readFileSync, writeFileSync} from 'node:fs';
import {gunzipSync, gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {join, dirname} from 'node:path';

const fieldwork = process.argv[2];
if (!fieldwork) throw new Error('Give the path of a built Fieldwork checkout.');
const from = path => import(pathToFileURL(join(fieldwork, 'build', path)).href);
const {parseCSV} = await from('input-data.js');
const {dataTable} = await from('data-table.js');
const {tableDataKey} = await from('project.js');
const {syncProjectManifest} = await from('project-manifest.js');
const {executeWorkflow, validateWorkflow} = await from('core.js');

const here = dirname(new URL(import.meta.url).pathname), root = join(here, '..');
const bundlePath = join(root, 'fieldwork-project.json.gz');
const bundle = JSON.parse(gunzipSync(readFileSync(bundlePath)));
const json = path => JSON.parse(readFileSync(join(root, path), 'utf8'));

// THE VISITS, as Tabular data reads a file: one row per visit, every column but the value a key, age the value.
const bytes = readFileSync(join(root, 'data', 'visits.csv')), text = bytes.toString('utf8');
const csv = parseCSV(text, 250_000, 40_000_000), valueField = 'age_years';
const keys = csv.headers.filter(h => h !== valueField);
const source = {filename: 'visits.csv', bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'), rows: csv.rows.length};
const data = {...dataTable(csv, {keys, valueField}), source};
const tableParams = {label: 'Emergency department visits, January to June 2026', keys, valueField, source, dataRef: tableDataKey(data), data};

// THE EXAMPLE'S OWN KEYWORDS meet the outbreak's new wording.
const GI_BEFORE = 'vomit, n/v, nausea, diarrh, gastro, stomach flu, throwing up, emesis, gi upset';
const GI_AFTER = GI_BEFORE + ', stomach bug, stomach virus, norov, noro v';
const widen = rules => JSON.parse(JSON.stringify(rules).replaceAll(JSON.stringify(GI_BEFORE), JSON.stringify(GI_AFTER)));

const stamp = 1796000000000;
let next = 0;
const id = type => `${type}-${stamp + (next++) * 1000}`;
const edge = (from, to, port) => ({id: `e-${stamp + (next++) * 1000}`, from, to, port});
const writtenHere = {id: 'urn:fieldwork:ruleset:written-in-this-workflow', version: '1.0.0', title: 'Rules written in this workflow',
  inputs: [['subjects', 'table']], output: 'table'};
const ruleStep = (file, label, x, y) => {
  const r = json(`data/${file}`);
  return {type: 'apply_ruleset', id: id('apply_ruleset'), x, y, params: {label, parameters: {}, ruleset: writtenHere,
    authored: {title: r.title, mustNotBeReadAs: r.mustNotBeReadAs, fields: r.fields, parameters: [], rules: r.rules, otherwise: r.otherwise}}};
};

const project = bundle.project.id;
function workflow(n, name, nodes, edges) {
  return {key: `${project}/w${n}`, document: {schema: 'fieldwork/workflow/1', name, nodes, edges, projectId: project,
    workflowKey: `${project}/w${n}`}};
}

// 1 to 3, brought up to date.
for (const w of bundle.workflows) {
  for (const node of w.document.nodes) {
    if (node.type === 'table_input') node.params = {...tableParams};
    if (node.type === 'apply_ruleset' && node.params.authored) node.params.authored.rules = widen(node.params.authored.rules);
  }
}

// 4. Which NSSP syndromes does each visit match?
{
  const table = {type: 'table_input', id: id('table_input'), x: 40, y: 40, params: {...tableParams}};
  const published = ruleStep('nssp-syndromes.ruleset.json', 'NSSP definitions, as published (ICD-10, SNOMED CT)', 340, 40);
  const translated = ruleStep('nssp-syndromes-icd11.ruleset.json', 'NSSP definitions, with ICD-11 (Fieldwork’s translation)', 340, 300);
  const out1 = {type: 'table_output', id: id('table_output'), x: 640, y: 40, params: {label: 'Each visit and the definitions it matches, ICD-10'}};
  const out2 = {type: 'table_output', id: id('table_output'), x: 640, y: 300, params: {label: 'Each visit and the definitions it matches, ICD-11'}};
  bundle.workflows.push(workflow(4, 'Which NSSP syndromes does each visit match?', [table, published, translated, out1, out2],
    [edge(table.id, published.id, 'subjects'), edge(table.id, translated.id, 'subjects'),
     edge(published.id, out1.id, 'table'), edge(translated.id, out2.id, 'table')]));
}

// 5. Does NSSP's norovirus definition find the outbreak?
{
  const table = {type: 'table_input', id: id('table_input'), x: 40, y: 40, params: {...tableParams}};
  const rules = ruleStep('nssp-syndromes.ruleset.json', 'NSSP definitions, as published (ICD-10, SNOMED CT)', 340, 40);
  const select = {type: 'select_rows', id: id('select_rows'), x: 640, y: 40, params: {label: 'Norovirus v1 only', keyColumn: 'norovirus', values: ['yes']}};
  const series = {type: 'case_series', id: id('case_series'), x: 940, y: 40, params: {label: 'Norovirus visits by day', dateField: 'date',
    dateKind: 'other', period: 'day', source: 'table', rowAsCase: true, caseId: 'visit_id'}};
  const detect = {type: 'detect_unusual_counts', id: id('detect_unusual_counts'), x: 1240, y: 40, params: {label: 'Unusual days, CUSUM over the first four weeks',
    timeField: 'period', method: 'cusum', baselinePeriods: 28, reset: true}};
  const chart = {type: 'chart_output', id: id('chart_output'), x: 1540, y: 40, params: {label: 'Norovirus visits against the threshold',
    figure: 'series', renderer: 'vega-lite', panelsBy: 'measure', seriesMarks: {observed: 'bar', threshold: 'dashed'},
    chartTitle: 'Visits matching NSSP’s Norovirus v1 by day, against the CUSUM threshold', signals: {from: 'signal', on: 'observed', label: 'signal'}}};
  const out = {type: 'table_output', id: id('table_output'), x: 1540, y: 300, params: {label: 'Each day: observed, expected, threshold and signal'}};
  bundle.workflows.push(workflow(5, 'Does NSSP’s norovirus definition find the outbreak?', [table, rules, select, series, detect, chart, out],
    [edge(table.id, rules.id, 'subjects'), edge(rules.id, select.id, 'records'), edge(select.id, series.id, 'cases'),
     edge(series.id, detect.id, 'records'), edge(detect.id, chart.id, 'records'), edge(detect.id, out.id, 'table')]));
}

bundle.project.workflows = bundle.workflows.map(w => w.key);
bundle.project.subject = 'Made-up emergency department visits: syndromes from chief complaints and discharge diagnoses, '
  + 'NSSP’s definitions among them, and unusual days';
bundle.project.changedAt = bundle.exportedAt = new Date().toISOString();

// Every workflow validated and run before anything is written.
const reasoner = {reason: async () => ({conclusions: []})};
for (const w of bundle.workflows) {
  syncProjectManifest(w.document, true);
  validateWorkflow(w.document);
  const run = await executeWorkflow(structuredClone(w.document), reasoner);
  const failed = run.unfinished?.length ? run.unfinished.map(u => `${u.nodeId}: ${u.message}`).join('; ') : '';
  if (failed) throw new Error(`${w.document.name}: ${failed}`);
  console.log(`ran: ${w.document.name}`);
}
writeFileSync(bundlePath, gzipSync(JSON.stringify(bundle)));
console.log(`wrote ${bundlePath}: ${bundle.workflows.length} workflows`);
