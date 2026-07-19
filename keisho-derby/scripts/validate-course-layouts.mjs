import fs from "node:fs";
import vm from "node:vm";
import assert from "node:assert/strict";

const source=fs.readFileSync(new URL("../course-layout-data.js",import.meta.url),"utf8");
const context={window:{}};vm.createContext(context);vm.runInContext(source,context);
const courses=context.window.COURSE_LAYOUTS;
const expected=["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉","帯広","門別","盛岡","水沢","浦和","船橋","大井","川崎","金沢","笠松","名古屋","園田","姫路","高知","佐賀"];
assert.equal(Object.keys(courses).length,25);
expected.forEach(name=>{
  const c=courses[name];assert.ok(c,`${name} missing`);assert.ok(c.id&&c.category&&c.direction);
  assert.ok(c.surfaces.length&&Object.keys(c.layouts).length);
  assert.ok(c.finishLine&&Number.isFinite(c.finishLine.x)&&Number.isFinite(c.finishLine.y));
  assert.ok(Object.keys(c.startPositions).length,`${name} start positions missing`);
  Object.values(c.layouts).forEach(path=>{assert.ok(path.length>=2);path.flat().forEach(Number.isFinite)});
});
assert.equal(courses["帯広"].direction,"straight");
assert.equal(courses["帯広"].obstacles.length,2);
assert.ok(courses["新潟"].layouts.straight);
assert.equal(courses["大井"].direction,"both");
assert.ok(courses["盛岡"].layouts.turf&&courses["盛岡"].layouts.dirt);
["中山","京都","阪神"].forEach(name=>assert.ok(courses[name].layouts.turf_inner&&courses[name].layouts.turf_outer));
console.log(`course layout validation passed: ${expected.length} venues`);
