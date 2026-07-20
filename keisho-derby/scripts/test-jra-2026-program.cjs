const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const context={window:{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,"..","race-program-2026.js"),"utf8"),context);
const races=context.window.OFFICIAL_JRA_GRADED_2026;
const counts=Object.fromEntries(["G1","G2","G3"].map(grade=>[grade,races.filter(r=>r.grade===grade).length]));

assert.equal(races.length,130,"JRA平地重賞は130競走");
assert.deepEqual(counts,{G1:24,G2:38,G3:68});
assert.equal(races.filter(r=>r.surface==="障害"||String(r.grade).startsWith("J")).length,0,"障害重賞を含めない");
assert.equal(new Set(races.map(r=>`${r.date}|${r.name}`)).size,races.length,"重賞ID相当の日付＋名称が重複しない");
assert.equal(new Set(races.map(r=>r.name)).size,races.length,"同一重賞を複数週へ置かない");
assert.equal(new Set(races.map(r=>r.id)).size,races.length,"重賞IDが重複しない");
races.forEach(r=>{
  assert.match(r.date,/^2026-\d{2}-\d{2}$/);
  assert.ok(r.name&&r.venue&&r.surface&&r.distance&&r.grade);
  assert.ok(["sat","sun","holiday"].includes(r.dayType));
  assert.ok(r.sexCondition&&r.weightCondition&&r.raceNumber);
});

const first=Date.UTC(2026,0,4);
const weeks=new Set(races.map(r=>Math.floor((Date.parse(`${r.date}T00:00:00Z`)-first)/604800000)+1));
assert.ok([...weeks].every(week=>week>=1&&week<=52));
assert.ok([...weeks].some(week=>week>=27&&week<=36),"夏競馬の重賞が存在する");
const satsuki=races.find(r=>r.name==="皐月賞");
assert.ok(satsuki,"皐月賞が存在する");
assert.equal(satsuki.venue,"中山");
assert.equal(satsuki.surface,"芝");
assert.equal(satsuki.distance,2000);
assert.equal(satsuki.sexCondition,"牡牝");

const app=fs.readFileSync(path.join(__dirname,"..","app.js"),"utf8");
assert.match(app,/const YEAR_WEEKS = 52/);
const venueBlock=app.match(/const JRA_2026_VENUES=\[([\s\S]*?)\]\.map/);
assert.ok(venueBlock,"52週開催場テーブルが存在する");
assert.equal((venueBlock[1].match(/"[^"\r\n]+"/g)||[]).length,52,"全52週の開催場を登録する");

console.log(`JRA 2026 program: OK (G1 ${counts.G1}, G2 ${counts.G2}, G3 ${counts.G3}, total ${races.length})`);
