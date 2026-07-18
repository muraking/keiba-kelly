import fs from "node:fs";
import vm from "node:vm";

const source=fs.readFileSync(new URL("../app.js",import.meta.url),"utf8");
const start=source.indexOf("const raceCalendar");
const end=source.indexOf("const OFFICIAL_GRADE_LABEL");
if(start<0||end<0)throw new Error("race calendar source not found");
const context={};
vm.runInNewContext(`${source.slice(start,end)};globalThis.__races=raceCalendar`,context);

const horse=classMoney=>({maiden:false,classMoney,races:3});
const cases=[
  [40,900,"オープン"],
  [60,900,"オープン"],
  [97,400,"1勝"],
  [97,900,"2勝"],
  [97,1500,"3勝"],
  [97,2400,"オープン"],
];
for(const [week,classMoney,expectedClass] of cases){
  const eligible=context.__races.filter(r=>r.program&&r.week===week&&r.condition(horse(classMoney)));
  if(!eligible.some(r=>r.raceClass===expectedClass))throw new Error(`${week}週・収得賞金${classMoney}万円: ${expectedClass}がない`);
  if(week>=97&&eligible.some(r=>r.name.includes("2歳")))throw new Error("4歳馬が2歳戦に出走可能");
}
console.log("race eligibility validation passed");
