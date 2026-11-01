import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const sampleUrl = new URL(
  "../public/samples/demo_long_followup.json",
  import.meta.url
);
const shortSampleUrl = new URL(
  "../public/samples/demo_full_probability.json",
  import.meta.url
);
const appUrl = new URL("../src/App.jsx", import.meta.url);

function seriesValueCount(line) {
  const separator = line.indexOf(":");
  assert.notEqual(separator, -1, line);
  return line
    .slice(separator + 1)
    .replace(/。\s*$/, "")
    .split(",").length;
}

test("default long-followup sample has a complete synthetic data contract", () => {
  const sample = JSON.parse(readFileSync(sampleUrl, "utf8"));
  const serialized = JSON.stringify(sample);
  const followup = sample["followup_series"];
  const labs =
    sample["laboratory_series"];
  const medications =
    sample["medication_series"];

  assert.equal(sample.id, "demo_long_followup");
  assert.equal(Object.hasOwn(sample, "\u6837\u4f8b\u7c7b\u578b"), false);
  assert.ok(sample["basic_information"]);
  assert.ok(Array.isArray(followup));
  assert.ok(Array.isArray(labs));
  assert.ok(Array.isArray(medications));
  assert.equal(followup.length, 3);
  assert.equal(labs.length, 17);
  assert.equal(medications.length, 3);
  assert.equal(sample["clinical_events"].length, 10);
  for (const line of [...followup, ...labs, ...medications]) {
    assert.equal(seriesValueCount(line), 15, line);
  }
  assert.match(followup[0], /1825/);
  assert.equal(serialized.includes("CMV-DNA"), false);
  assert.equal(serialized.includes("EBV-DNA"), false);

  for (const forbiddenField of [
    "\u771f\u5b9e\u6807\u7b7e",
    "\u662f\u5426\u6b7b\u4ea1",
    "\u6b7b\u4ea1\u65f6\u95f4",
    "\u6b7b\u4ea1\u539f\u56e0",
    "\u60a3\u513f\u51fa\u751f\u65e5\u671f",
    "\u624b\u672f\u65e5\u671f",
    "\u968f\u8bbf\u8bb0\u5f55\u6458\u8981",
    "\u968f\u8bbf\u65f6\u95f4",
  ]) {
    assert.equal(serialized.includes(forbiddenField), false, forbiddenField);
  }
  assert.equal(/\b\d{4}-\d{2}-\d{2}\b/.test(serialized), false);
});

test("frontend loads the long-followup demo and retains the short synthetic sample", () => {
  const appSource = readFileSync(appUrl, "utf8");
  const shortSample = JSON.parse(readFileSync(shortSampleUrl, "utf8"));

  assert.match(appSource, /SAMPLE_URL = "\/samples\/demo_long_followup\.json"/);
  assert.match(appSource, /Load sample/);
  assert.equal(shortSample.id, "demo_full_probability");
});

test("both downloadable demo records contain only English/ASCII content", () => {
  for (const url of [sampleUrl, shortSampleUrl]) {
    const data = JSON.parse(readFileSync(url, "utf8"));
    assert.doesNotMatch(JSON.stringify(data), /[^\x00-\x7f]/);
    assert.ok(data.basic_information);
    assert.ok(data.followup_series.length);
    assert.ok(data.laboratory_series.length);
    assert.ok(data.medication_series.length);
  }
});
