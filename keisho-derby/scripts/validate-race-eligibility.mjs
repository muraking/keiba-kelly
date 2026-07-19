import fs from "node:fs";
import vm from "node:vm";

const source=fs.readFileSync(new URL("../app.js",import.meta.url),"utf8");
const programSource=fs.readFileSync(new URL("../race-program-2026.js",import.meta.url),"utf8");
const start=source.indexOf("const raceCalendar");
const end=source.indexOf("const CLASS_TIME_ADJUST");
if(start<0||end<0)throw new Error("race calendar source not found");
const context={window:{}};
vm.runInNewContext(programSource,context);
vm.runInNewContext(`const CAREER_MAX_WEEKS=384;${source.slice(start,end)};globalThis.__races=raceCalendar`,context);

const horse=classMoney=>({maiden:false,classMoney,races:3,candidate:{sex:"牡馬"}});
const cases=[
  [40,900,"オープン"],
  [60,900,"オープン"],
  [97,400,"1勝"],
  [97,900,"2勝"],
  [97,1500,"3勝"],
  [97,2400,"オープン"],
  [241,400,"1勝"],
  [288,1500,"3勝"],
];
for(const [week,classMoney,expectedClass] of cases){
  const eligible=context.__races.filter(r=>r.program&&r.week===week&&r.condition(horse(classMoney)));
  if(!eligible.some(r=>r.raceClass===expectedClass))throw new Error(`${week}週・収得賞金${classMoney}万円: ${expectedClass}がない`);
  if(week>=97&&eligible.some(r=>r.name.includes("2歳")))throw new Error("4歳馬が2歳戦に出走可能");
}
const olderThreeWin=horse(1500);
const olderGraded=context.__races.filter(r=>r.official&&r.week>=97&&r.condition(olderThreeWin));
if(olderGraded.length)throw new Error(`3勝クラス馬が古馬重賞へ出走可能: ${olderGraded[0].name}`);
const ageLimitedGraded=context.__races.find(r=>r.official&&/^(2歳|3歳)(?!以上)/.test(r.age||"")&&r.condition(horse(400)));
if(!ageLimitedGraded)throw new Error("勝ち上がり馬が2・3歳限定重賞へ出走できない");
for(let week=1;week<=384;week++){
  const jraVenues=new Set(["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"]);
  const venues=[...new Set(context.__races.filter(r=>r.program&&r.week===week).map(r=>r.course.split(" ")[0]).filter(v=>jraVenues.has(v)))];
  for(const venue of venues){
    const card=context.__races.filter(r=>r.program&&r.week===week&&r.course.startsWith(`${venue} `));
    if(card.length!==12)throw new Error(`${week}週 ${venue}: ${card.length}競走（12競走ではない）`);
    const turf=card.filter(r=>r.surface==="芝").length,dirt=card.filter(r=>r.surface==="ダート").length;
    if(Math.abs(turf-dirt)>2)throw new Error(`${week}週 ${venue}: 芝${turf}・ダート${dirt}で偏り過ぎ`);
  }
}
console.log("race eligibility validation passed");
