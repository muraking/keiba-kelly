const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const source=fs.readFileSync(path.join(__dirname,"..","race.js"),"utf8");
const neutral=source.match(/function neutral1000mSplit\(\)\{[\s\S]*?\n\}/)?.[0];
const analyze=source.match(/function analyzePace\(entries\) \{[\s\S]*?\n\}/)?.[0];
const classify=source.match(/function classify1000mPace\(milliseconds\) \{[\s\S]*?\n\}/)?.[0];
assert.ok(neutral&&analyze&&classify,"pace functions must remain testable");

const context={TOTAL:1600,raceSurface:"芝",playerSetup:{raceClass:"G1",age:3,baseTime:94000},raceRandom:()=>.5};
vm.createContext(context);vm.runInContext(`${neutral}\n${analyze}\n${classify}`,context);
assert.equal(context.neutral1000mSplit(),58800);
assert.equal(context.classify1000mPace(58800),"平均ペース");
assert.equal(context.classify1000mPace(57800),"ハイペース");

context.TOTAL=3600;context.playerSetup={raceClass:"G3",age:3,baseTime:228000};
assert.equal(context.neutral1000mSplit(),63700);
const longHigh=context.analyzePace([{style:"逃げ"},{style:"逃げ"},{style:"逃げ"}]);
assert.equal(longHigh.targetSplit,62250);
assert.ok(longHigh.targetSplit>=62000,"3600mの1000m通過が短距離並みにならないこと");

context.TOTAL=1800;context.raceSurface="ダート";context.playerSetup={raceClass:"G3",age:3,baseTime:110000};
assert.equal(context.neutral1000mSplit(),61500);

context.TOTAL=1600;context.raceSurface="芝";context.playerSetup={raceClass:"未勝利",age:2,baseTime:97000};
assert.equal(context.neutral1000mSplit(),60550);

// ゲーム内で使う全距離帯を芝・ダート、古馬重賞・2歳未勝利で総点検する。
const distances=[1000,1150,1200,1300,1400,1500,1600,1700,1800,1900,2000,2100,2200,2300,2400,2500,2600,3000,3200,3400,3600];
for(const surface of ["芝","ダート"]){
  for(const profile of [{raceClass:"G1",age:4},{raceClass:"未勝利",age:2}]){
    let previous=0;
    for(const distance of distances){
      context.TOTAL=distance;context.raceSurface=surface;
      context.playerSetup={...profile,baseTime:distance===1000?(surface==="芝"?55000:58000):distance*62};
      const split=context.neutral1000mSplit();
      assert.ok(split>=54000&&split<=68000,`${surface}${distance}mの基準1000mが現実的な範囲に入ること`);
      assert.ok(split>=previous-1,`${surface}は距離延長で基準1000mが速くならないこと`);
      previous=split;
      assert.equal(context.classify1000mPace(split),"平均ペース");
      const high=context.analyzePace([{style:"逃げ"},{style:"逃げ"},{style:"逃げ"}]);
      const expectedDrop=distance===1000?1200:1450;
      assert.ok(high.targetSplit<=split-expectedDrop+50&&high.targetSplit>=split-expectedDrop-50,`${surface}${distance}mの逃げ競り合いをハイペース化すること`);
    }
  }
}

console.log("race pace balance: OK");
