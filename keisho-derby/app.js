const SAVE_KEY = "dotKeibaTrialV3";
const screens = [...document.querySelectorAll(".game-screen")];
const coats = [["栗毛","#b96e32"],["鹿毛","#74401f"],["黒鹿毛","#3c2a25"],["芦毛","#b9b7ad"]];
const sires = [
  ["ドットキング","GⅡ 1勝","芝1800〜2400m","普通"],["レトロボルト","3勝クラス","ダート1400〜1800m","晩成"],["ピクセルロード","オープン","芝1200〜1600m","早熟"],
  ["エイトスター","2勝クラス","芝2200〜3000m","晩成"],["ファミコンテ","未勝利","ダート1000〜1400m","早熟"]
];
const dams = [
  ["メモリーハート","1勝クラス","芝1600〜2000m","普通"],["グリーンライン","未勝利","ダート1600〜1800m","晩成"],["チップクイーン","2勝クラス","芝1400〜1800m","早熟"],
  ["ブラウンベル","未出走","距離適性不明","普通"],["ドットミスト","1勝クラス","ダート1200〜1600m","晩成"]
];
const defaultGame = () => ({
  horseName:"", week:1, trainingsUsed:0, prize:0, farmPoints:0, equipment:[], classMoney:0, priorityRights:[],
  speed:0, dash:0, gateSkill:450, stamina:0, power:0, guts:0, turf:0, dirt:0, heavyTrack:500, condition:60, fatigue:10,
  conditionDirection:1, conditionPhaseWeeks:4, conditionStability:"普通", conditionPeakWeeks:0,
  weight:0, baseBestWeight:0, growthType:"普通", growthPotential:12,
  generation:1, potentialCaps:null, distanceMin:1400, distanceMax:2000,
  injury:null, legCondition:100,
  temperament:"普通",temperamentValue:50,temperamentKnown:false,
  tackUnlocked:[],equippedTack:null,temperamentObservations:0,
  races:0, wins:0, maiden:true, selectedRace:null, currentRaceWeather:null,
  raceHistory:[], favoriteRaces:[], galleryUnlocks:["stable"], candidate:null,
  reservedRaceId:null, affection:0
});
let game = defaultGame();
let developerMode=localStorage.getItem("dotKeibaDeveloperMode")==="1";
const ABILITY_STATS=["speed","dash","stamina","power","guts","turf","dirt","heavyTrack"];

const raceCalendar = [
  {id:"n1",week:21,name:"2歳新馬",raceClass:"新馬",course:"東京 芝1400m",surface:"芝",distance:1400,baseTime:83100,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n2",week:21,name:"2歳新馬",raceClass:"新馬",course:"東京 芝1600m",surface:"芝",distance:1600,baseTime:95800,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n3",week:21,name:"2歳新馬",raceClass:"新馬",course:"阪神 ダート1400m",surface:"ダート",distance:1400,baseTime:87600,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n4",week:22,name:"2歳新馬",raceClass:"新馬",course:"東京 芝1800m",surface:"芝",distance:1800,baseTime:108500,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"n5",week:22,name:"2歳新馬",raceClass:"新馬",course:"阪神 ダート1800m",surface:"ダート",distance:1800,baseTime:115000,prize:750,difficulty:63,condition:g=>g.races===0},
  {id:"m1",week:22,name:"2歳未勝利",raceClass:"未勝利",course:"東京 芝1400m",surface:"芝",distance:1400,baseTime:82700,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m2",week:22,name:"2歳未勝利",raceClass:"未勝利",course:"阪神 ダート1400m",surface:"ダート",distance:1400,baseTime:87000,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m3",week:23,name:"2歳未勝利",raceClass:"未勝利",course:"東京 芝1600m",surface:"芝",distance:1600,baseTime:95100,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m4",week:23,name:"2歳未勝利",raceClass:"未勝利",course:"阪神 芝1800m",surface:"芝",distance:1800,baseTime:107800,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"m5",week:24,name:"2歳未勝利",raceClass:"未勝利",course:"東京 ダート1600m",surface:"ダート",distance:1600,baseTime:98700,prize:560,difficulty:64,condition:g=>g.races>=1&&g.maiden},
  {id:"o0a",week:22,name:"2歳1勝クラス",raceClass:"1勝",course:"東京 芝1600m",surface:"芝",distance:1600,baseTime:93500,prize:800,difficulty:69,condition:g=>!g.maiden},
  {id:"o0b",week:22,name:"2歳1勝クラス",raceClass:"1勝",course:"阪神 ダート1400m",surface:"ダート",distance:1400,baseTime:85500,prize:800,difficulty:69,condition:g=>!g.maiden},
  {id:"o0c",week:23,name:"2歳1勝クラス",raceClass:"1勝",course:"東京 芝1800m",surface:"芝",distance:1800,baseTime:106900,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o0d",week:24,name:"2歳1勝クラス",raceClass:"1勝",course:"阪神 ダート1800m",surface:"ダート",distance:1800,baseTime:112500,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o0e",week:25,name:"2歳1勝クラス",raceClass:"1勝",course:"福島 芝1800m",surface:"芝",distance:1800,baseTime:108800,prize:800,difficulty:71,condition:g=>!g.maiden},
  {id:"o1",week:26,name:"2歳1勝クラス",raceClass:"1勝",course:"小倉 芝1200m",surface:"芝",distance:1200,baseTime:70800,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o2",week:27,name:"2歳1勝クラス",raceClass:"1勝",course:"新潟 ダート1200m",surface:"ダート",distance:1200,baseTime:73000,prize:800,difficulty:70,condition:g=>!g.maiden},
  {id:"o3",week:40,name:"百日草特別 1勝",raceClass:"1勝",course:"東京 芝2000m",surface:"芝",distance:2000,baseTime:121300,prize:1070,difficulty:71,condition:g=>!g.maiden},
  {id:"g3",week:43,name:"東京スポーツ杯2歳S GⅢ",raceClass:"G3",course:"東京 芝1800m",surface:"芝",distance:1800,baseTime:106500,prize:3300,difficulty:86,condition:g=>!g.maiden&&g.prize>=500},
  {id:"aoba",week:65,name:"青葉賞 GⅡ",raceClass:"G2",course:"東京 芝2400m",surface:"芝",distance:2400,baseTime:145000,prize:5400,difficulty:90,trialRight:{name:"日本ダービー",maxPlace:2},condition:g=>g.classMoney>=400},
  {id:"principal",week:66,name:"プリンシパルS L",raceClass:"オープン",course:"東京 芝2000m",surface:"芝",distance:2000,baseTime:120000,prize:2000,difficulty:84,trialRight:{name:"日本ダービー",maxPlace:1},condition:g=>g.classMoney>=400},
  {id:"derby",week:68,name:"日本ダービー GⅠ",raceClass:"G1",course:"東京 芝2400m",surface:"芝",distance:2400,baseTime:143500,prize:30000,difficulty:96,condition:g=>g.priorityRights.includes("日本ダービー")||g.classMoney>=1600},
];

// 簡易版の開催番組。各週2会場・各12Rを必ず用意し、番組切れを防ぐ。
// 新馬は初出走のみ。未出走馬を含む未勝利馬は未勝利戦へ出走できる。
const PROGRAM_VENUE_PAIRS=[["東京","阪神"],["福島","小倉"],["新潟","札幌"],["中山","中京"],["京都","阪神"]];
const PROGRAM_RACES=[
  [1,"2歳未勝利","未勝利","ダート",1200,560,64,g=>g.maiden],
  [2,"2歳未勝利","未勝利","芝",1400,560,64,g=>g.maiden],
  [3,"2歳未勝利","未勝利","ダート",1400,560,64,g=>g.maiden],
  [4,"2歳未勝利","未勝利","芝",1600,560,64,g=>g.maiden],
  [5,"2歳新馬","新馬","芝",1600,750,63,g=>g.races===0],
  [6,"2歳新馬","新馬","ダート",1800,750,63,g=>g.races===0],
  [7,"2歳1勝クラス","1勝","芝",1400,800,69,g=>!g.maiden&&g.classMoney<=400],
  [8,"2歳1勝クラス","1勝","ダート",1400,800,69,g=>!g.maiden&&g.classMoney<=400],
  [9,"2歳1勝クラス","1勝","芝",1800,800,70,g=>!g.maiden&&g.classMoney<=400],
  [10,"2歳オープン","オープン","ダート",1600,1600,82,g=>g.classMoney>=400],
  [11,"2歳特別","オープン","芝",1800,2000,84,g=>g.classMoney>=400],
  [12,"2歳1勝クラス","1勝","ダート",1800,800,70,g=>!g.maiden&&g.classMoney<=400],
];
for(let week=21;week<=96;week++){
  const venues=PROGRAM_VENUE_PAIRS[Math.floor((week-21)/4)%PROGRAM_VENUE_PAIRS.length];
  venues.forEach(venue=>PROGRAM_RACES.forEach(([number,name,raceClass,surface,distance,prize,difficulty,condition])=>{
    const basePer1000=surface==="芝"?60000:63000;
    raceCalendar.push({id:`p-${week}-${venue}-${number}`,program:true,number,week,name,raceClass,
      course:`${venue} ${surface}${distance}m`,surface,distance,
      baseTime:Math.round(basePer1000*distance/1000),prize,difficulty,condition});
  }));
}
const CLASS_TIME_ADJUST={
  "新馬":{芝:2.6,ダート:3.3},
  "未勝利":{芝:2.2,ダート:3.0},
  "1勝":{芝:1.6,ダート:2.4},
  "2勝":{芝:1.25,ダート:2.0},
  "3勝":{芝:.95,ダート:1.6},
  "オープン":{芝:.72,ダート:1.3},
  "G3":{芝:.55,ダート:1.05},
  "G2":{芝:.4,ダート:.85},
  "G1":{芝:.25,ダート:.65},
};
function raceAgeGroup(){return horseAge()===2?"2歳":"3歳以上"}
function raceVenue(race){return race.course.split(" ")[0]}
function raceTimingRecord(race){
  const master=window.RACE_TIME_MASTER;
  const venue=raceVenue(race),ageGroup=raceAgeGroup();
  const exactKey=`${venue}-${race.surface}-${race.distance}-${ageGroup}`;
  const openKey=`${venue}-${race.surface}-${race.distance}-3歳以上`;
  const exact=master?.records?.[exactKey]??master?.records?.[openKey];
  if(exact)return {time:exact,verified:true};
  const reference=master?.reference?.[`${race.surface}-${race.distance}`]??race.baseTime*.965;
  const venueData=master?.venues?.[venue]||master?.venues?.["東京"]||{turfFactor:1,dirtFactor:1};
  const factor=race.surface==="芝"?venueData.turfFactor:venueData.dirtFactor;
  return {time:Math.round(reference*factor),verified:false};
}
function officialRecordTime(race){return raceTimingRecord(race).time}
function classBenchmarkTime(race){
  const record=officialRecordTime(race);
  const secondsPerKm=CLASS_TIME_ADJUST[race.raceClass]?.[race.surface]??3;
  const twoYearOldExtra=horseAge()===2?race.raceClass==="新馬"?.9:race.raceClass==="未勝利"?.55:.2:0;
  return Math.round(record+(secondsPerKm+twoYearOldExtra)*race.distance);
}

function showScreen(id){ screens.forEach(s=>s.classList.toggle("active",s.id===id)); scrollTo(0,0); }
function saveGame(){ localStorage.setItem(SAVE_KEY,JSON.stringify(game)); }
function loadGame(){
  try{
    const saved=JSON.parse(localStorage.getItem(SAVE_KEY));
    game={...defaultGame(),...saved};
    if(!Number.isFinite(saved?.dash)||saved.dash<=0)game.dash=Math.max(400,Math.min(650,Math.round((game.speed+game.power)/2)-30));
    if(game.candidate&&!Number.isFinite(game.candidate.dash))game.candidate.dash=game.dash;
    if(!Number.isFinite(saved?.baseBestWeight)||saved.baseBestWeight<=0)game.baseBestWeight=rnd(438,492);
    if(!Number.isFinite(saved?.weight)||saved.weight<=0)game.weight=game.baseBestWeight+rnd(-4,6);
    if(!["早熟","普通","晩成"].includes(saved?.growthType))game.growthType="普通";
    if(!Number.isFinite(saved?.growthPotential))game.growthPotential=rnd(9,16);
    if(!saved?.potentialCaps)game.potentialCaps=createPotentialCaps(game);
    if(!Number.isFinite(saved?.distanceMin))game.distanceMin=1400;
    if(!Number.isFinite(saved?.distanceMax))game.distanceMax=2000;
    if(!Number.isFinite(saved?.heavyTrack))game.heavyTrack=rnd(420,680);
    if(!Array.isArray(saved?.raceHistory))game.raceHistory=[];
    if(!Array.isArray(saved?.favoriteRaces))game.favoriteRaces=[];
    if(!Array.isArray(saved?.galleryUnlocks))game.galleryUnlocks=["stable"];
    if(!Number.isFinite(saved?.temperamentValue))game.temperamentValue=rnd(30,75);
    if(!saved?.temperament)game.temperament=temperamentType(game.temperamentValue);
    if(!Array.isArray(saved?.tackUnlocked))game.tackUnlocked=[];
    return !!game.horseName;
  }catch{return false}
}
function rnd(min,max){return Math.floor(Math.random()*(max-min+1))+min}
function temperamentType(value){
  return value>=74?"荒い":value>=60?"前向き":value>=42?"普通":value>=27?"臆病":"穏やか";
}
function inheritTemperament(sire,dam){
  const parentBias=(sire[3]==="早熟"?5:sire[3]==="晩成"?-2:0)+(dam[3]==="早熟"?3:dam[3]==="晩成"?-2:0);
  return Math.max(18,Math.min(88,rnd(32,70)+parentBias+rnd(-7,7)));
}
function inheritGrowthType(sireType,damType){
  const roll=Math.random();
  if(roll<.45)return sireType;
  if(roll<.80)return damType;
  return ["早熟","普通","晩成"][rnd(0,2)];
}
function parentDistanceRange(parent){
  const nums=(parent[2].match(/\d{4}/g)||[]).map(Number);
  return nums.length>=2?[nums[0],nums[1]]:[1200,2200];
}
function createDistanceRange(sire,dam){
  const sr=parentDistanceRange(sire),dr=parentDistanceRange(dam);
  const min=Math.round((sr[0]*.55+dr[0]*.45+rnd(-200,200))/200)*200;
  const max=Math.round((sr[1]*.55+dr[1]*.45+rnd(-200,200))/200)*200;
  return [Math.max(1000,Math.min(min,max-400)),Math.min(3200,Math.max(max,min+400))];
}
function createPotentialCaps(source){
  const caps={};
  ["speed","dash","stamina","power","guts","turf","dirt"].forEach(stat=>{
    const surface=stat==="turf"||stat==="dirt";
    const hardCap=surface?920:950;
    caps[stat]=Math.min(hardCap,source[stat]+rnd(surface?80:90,surface?190:220));
  });
  return caps;
}
function generateCandidate(){
  const coat=Math.random()<.004?["白毛","#eee9dd"]:coats[rnd(0,coats.length-1)], sire=sires[rnd(0,sires.length-1)], dam=dams[rnd(0,dams.length-1)];
  const turf=rnd(400,610), dirt=rnd(400,610);
  const baseBestWeight=rnd(438,492);
  const growthType=inheritGrowthType(sire[3],dam[3]);
  const temperamentValue=inheritTemperament(sire,dam);
  const [distanceMin,distanceMax]=createDistanceRange(sire,dam);
  const parentHeavyBase=(sire[2].includes("ダート")?5:0)+(dam[2].includes("ダート")?5:0);
  const candidate={coat:coat[0],color:coat[1],faceMark:Math.random()<.38,socks:rnd(0,4),eyeType:["優しい","鋭い","好奇心旺盛"][rnd(0,2)],sire,dam,speed:rnd(390,560),dash:rnd(370,540),gateSkill:rnd(380,540),stamina:rnd(390,560),power:rnd(380,550),guts:rnd(370,540),turf,dirt,heavyTrack:Math.max(350,Math.min(800,rnd(430,670)+parentHeavyBase*10)),temperamentValue,temperament:temperamentType(temperamentValue),baseBestWeight,weight:baseBestWeight+rnd(12,20),growthType,growthPotential:rnd(7,15),distanceMin,distanceMax,...createConditionCycle()};
  candidate.potentialCaps=createPotentialCaps(candidate);
  game.candidate=candidate;
  document.querySelector("#candidateTitle").textContent=`${coat[0]}の2歳馬`;
  document.querySelector("#candidateHorse").style.setProperty("--horse-color",coat[1]);
  document.querySelector("#candidatePedigree").innerHTML=
    `父 ${sire[0]}（${sire[1]}）<br>得意 ${sire[2]}／成長型 ${sire[3]}<br>`+
    `母 ${dam[0]}（${dam[1]}）<br>得意 ${dam[2]}／成長型 ${dam[3]}`;
  document.querySelector("#candidateInfo").innerHTML=[
    ["スピード",game.candidate.speed],["ダッシュ",game.candidate.dash],["スタミナ",game.candidate.stamina],["パワー",game.candidate.power],
    ["勝負根性",game.candidate.guts],["馬体重",`${game.candidate.weight}kg`],["芝適性",turf],["ダート適性",dirt],["道悪適性",game.candidate.heavyTrack]
  ].map(([k,v])=>`<span>${k}<b>${typeof v==="number"?(developerMode?`${Math.round(v)} / 1000`:scoutComment(k,v)):v}</b></span>`).join("");
}
function gameYear(){return Math.floor((game.week-1)/48)+1}
function weekLabel(){const yearWeek=(game.week-1)%48,month=Math.floor(yearWeek/4)+1,w=yearWeek%4+1;return `${gameYear()}年目 ${month}月${w}週`;}
function horseAge(){return Math.min(9,2+Math.floor((game.week-1)/48));}
function maturityRate(){
  const age=horseAge()+((game.week-1)%48)/48;
  const curves={
    "早熟":[[2,.82],[3,.97],[4,1],[5,.98],[6,.94],[7,.88]],
    "普通":[[2,.70],[3,.86],[4,.97],[5,1],[6,.98],[7,.93]],
    "晩成":[[2,.58],[3,.72],[4,.87],[5,.97],[6,1],[7,.98]]
  };
  const points=curves[game.growthType]||curves["普通"];
  if(age<=points[0][0])return points[0][1];
  for(let i=1;i<points.length;i++){
    if(age<=points[i][0]){
      const [a0,r0]=points[i-1],[a1,r1]=points[i],t=(age-a0)/(a1-a0);
      return r0+(r1-r0)*t;
    }
  }
  return Math.max(.82,points.at(-1)[1]-(age-points.at(-1)[0])*.04);
}
function growthAbilityBonus(){return game.growthPotential*10*(maturityRate()-.58)/.42;}
function effectiveDistanceRange(){
  // 血統由来の基礎距離を、現在のスタミナで長距離側へ拡張する。
  // スタミナ55を基準に、1ポイントごとに約20m対応距離が伸びる。
  const staminaExtension=Math.max(0,game.stamina-550)*2;
  return {
    min:game.distanceMin,
    max:Math.min(3400,Math.round(game.distanceMax+staminaExtension))
  };
}
function distanceAbilityPenalty(distance){
  const range=effectiveDistanceRange();
  const gap=distance<range.min?range.min-distance:distance>range.max?distance-range.max:0;
  if(gap<=0)return 0;
  // 200m程度なら相手や展開次第で対応可能。大きく外れると急激に厳しくなる。
  if(gap<=200)return gap/100*15;
  if(gap<=400)return 30+(gap-200)/100*20;
  if(gap<=800)return 70+(gap-400)/100*25;
  return Math.min(220,170+(gap-800)/100*12.5);
}
function trainingGain(stat,base,mult,type){
  const cap=game.potentialCaps?.[stat]??1000;
  const remaining=Math.max(0,cap-game[stat]);
  if(remaining<=0||mult<=0)return 0;
  const capFactor=remaining>=120?1:remaining>=70?.72:remaining>=30?.45:.22;
  const equipmentBonus=stat==="power"&&type==="hill"&&game.equipment.includes("treadmill")?5:0;
  return Math.min(remaining,(base*6+equipmentBonus)*mult*(.72+maturityRate()*.33)*capFactor);
}
function bestWeight(){
  const age=horseAge();
  // 成長分は2～4歳を中心に増加し、5歳末で頭打ち。
  const completedYears=Math.max(0,Math.min(4,age-2));
  const currentYearProgress=age<6?((game.week-1)%48)/48:0;
  const yearlyGrowth=[10,7,4,2];
  return Math.round(game.baseBestWeight+
    yearlyGrowth.slice(0,completedYears).reduce((a,b)=>a+b,0)+
    (age<6?(yearlyGrowth[completedYears]||0)*currentYearProgress:0));
}
function weightComment(){
  const diff=game.weight-bestWeight();
  if(diff>=18)return "かなり太目です";
  if(diff>=9)return "まだ太目です";
  if(diff<=-18)return "かなり細すぎます";
  if(diff<=-9)return "少し細い状態です";
  if(Math.abs(diff)<=3)return "ベスト体重です";
  return diff>0?"少し余裕があります":"少し絞れています";
}
function conditionLabel(){return game.condition>=85?"絶好調":game.condition>=68?"好調":game.condition>=45?"普通":game.condition>=28?"不調":"絶不調"}
function createConditionCycle(){
  const stability=["ムラ","普通","安定"][rnd(0,2)];
  return {
    condition:rnd(42,64),
    conditionDirection:Math.random()<.55?1:-1,
    conditionPhaseWeeks:stability==="ムラ"?rnd(2,4):stability==="安定"?rnd(5,8):rnd(3,6),
    conditionStability:stability,
    conditionPeakWeeks:0
  };
}
function conditionTrendComment(){
  if(game.condition>=85&&game.conditionPeakWeeks>0)return "今が一番良い時期でしょう。この状態でレースを迎えたいですね";
  if(game.conditionDirection>0)return game.condition>=75?"調子はかなり上向いてきました。ピークが近そうです":"徐々に調子が上向いてきました";
  if(game.conditionDirection<0)return game.condition<=38?"まだ本調子ではありません。立て直す時間が必要です":"少し調子が下降気味です。疲れを残さないようにしましょう";
  return game.condition>=78?"好調を維持しています":"調子は安定しています";
}
function advanceConditionCycle(actionBonus=0){
  let natural=0;
  if(game.conditionPeakWeeks>0){
    game.conditionPeakWeeks--;
    game.conditionDirection=0;
    natural=rnd(-1,1);
    if(game.conditionPeakWeeks===0){
      game.conditionDirection=-1;
      game.conditionPhaseWeeks=game.conditionStability==="安定"?rnd(5,8):game.conditionStability==="ムラ"?rnd(2,4):rnd(3,6);
    }
  }else{
    const range=game.conditionStability==="ムラ"?[4,8]:game.conditionStability==="安定"?[2,4]:[3,6];
    natural=rnd(range[0],range[1])*game.conditionDirection;
    game.conditionPhaseWeeks--;
    if(game.conditionDirection>0&&game.condition+natural>=86){
      game.conditionPeakWeeks=game.conditionStability==="安定"?rnd(2,4):rnd(1,2);
      game.conditionDirection=0;
    }else if(game.conditionPhaseWeeks<=0){
      game.conditionDirection*=-1;
      game.conditionPhaseWeeks=game.conditionStability==="安定"?rnd(5,8):game.conditionStability==="ムラ"?rnd(2,4):rnd(3,6);
    }
  }
  game.condition=Math.max(20,Math.min(100,game.condition+natural+actionBonus));
}
function classLabel(){return game.maiden?"未勝利":game.classMoney<=400?"1勝クラス":game.classMoney<=1000?"2勝クラス":game.classMoney<=1600?"3勝クラス":"オープン"}
function legLabel(){return game.legCondition>=85?"良好":game.legCondition>=65?"少し張り":game.legCondition>=45?"注意":"危険"}
function raceConditionModifier(){
  if(game.condition>=85)return 30;
  if(game.condition>=68)return 15;
  if(game.condition>=45)return 0;
  if(game.condition>=28)return -30;
  return -60;
}
function abilityBand(value){
  if(value>=900)return "規格外の可能性";
  if(value>=800)return "かなり高い水準";
  if(value>=700)return "水準以上";
  if(value>=600)return "まずまず";
  if(value>=500)return "標準的";
  if(value>=400)return "もう少し欲しい";
  return "まだ力不足";
}
function scoutComment(label,value){
  if(label.includes("芝")||label.includes("ダート"))return value>=700?"かなり向いていそう":value>=580?"適性がありそう":value>=460?"こなせそう":"少し不安があります";
  if(label==="道悪適性")return value>=700?"道悪は歓迎です":value>=520?"特に問題なさそう":"悪い馬場は気になります";
  return abilityBand(value);
}
function statRow(label,value,color){
  if(developerMode){
    const cap=game.potentialCaps?.[{スピード:"speed",ダッシュ:"dash",スタミナ:"stamina",パワー:"power",勝負根性:"guts",芝適性:"turf",ダート適性:"dirt",道悪適性:"heavyTrack"}[label]];
    return `<div class="dev-stat"><span>${label}</span><div class="meter"><i style="width:${value/10}%;background:${color}"></i></div><b>${Math.round(value)}${cap?`/${Math.round(cap)}`:""}</b></div>`;
  }
  return `<div class="trainer-stat"><span>${label}</span><b>${scoutComment(label,value)}</b></div>`;
}
const STAT_LABELS={speed:"スピード",dash:"ダッシュ",stamina:"スタミナ",power:"パワー",guts:"勝負根性",turf:"芝の走り",dirt:"ダートの走り"};
function trainingCoachComment(type,outcome,gains){
  if(outcome==="失敗")return "今日はうまく走りに集中できませんでした。疲れを取って立て直しましょう。";
  const improved=Object.entries(gains).filter(([,gain])=>gain>.1).sort((a,b)=>b[1]-a[1]);
  if(!improved.length)return "動きは悪くありませんが、能力は頭打ちに近いようです。別の調教も試しましょう。";
  const [mainStat,mainGain]=improved[0];
  const value=game[mainStat],cap=game.potentialCaps?.[mainStat]??1000;
  let growth;
  if(outcome==="大成功")growth=`${STAT_LABELS[mainStat]}が大きく良くなりました。今日の動きは素晴らしいです。`;
  else if(mainGain>=8)growth=`${STAT_LABELS[mainStat]}が目に見えて良くなってきました。`;
  else if(mainGain>=4)growth=`${STAT_LABELS[mainStat]}に少し成長が見られます。`;
  else growth=`${STAT_LABELS[mainStat]}はわずかに良くなりました。`;
  let advice;
  if(cap-value<35)advice="この部分はかなり完成に近づいています。";
  else if(value<470)advice=`ただ、${STAT_LABELS[mainStat]}はまだもう少し欲しいですね。`;
  else if(value<620)advice="このまま地道に積み重ねていきましょう。";
  else if(value<760)advice="水準以上の動きになってきました。";
  else advice="かなり高いレベルまで仕上がっています。";
  const secondary=improved[1]&&improved[1][1]>.1?` ${STAT_LABELS[improved[1][0]]}にも良い変化があります。`:"";
  return `${growth}${secondary} ${advice}`;
}
const tackCatalog={
  hood:{name:"メンコ",desc:"音への反応と出遅れを軽減"},
  blinkers:{name:"ブリンカー",desc:"前方へ集中。掛かりには注意"},
  cheekpieces:{name:"チークピーシズ",desc:"馬群での集中力を補助"}
};
function trainerTemperamentComment(){
  if(!game.temperamentKnown)return "まだ性格を見極めている段階です";
  if(game.temperament==="荒い")return "力みやすく、折り合いに注意が必要です";
  if(game.temperament==="前向き")return "前進気勢が強く、序盤に行きたがります";
  if(game.temperament==="臆病")return "周囲の音や他馬を気にするところがあります";
  if(game.temperament==="穏やか")return "落ち着いていますが、反応が鈍い時があります";
  return "気性は安定しています";
}
function renderTack(){
  document.querySelector("#temperamentComment").textContent=trainerTemperamentComment();
  document.querySelector("#tackChoices").innerHTML=game.tackUnlocked.length
    ? `<button data-tack="" class="${!game.equippedTack?"selected":""}">馬具なし</button>`+
      game.tackUnlocked.map(id=>`<button data-tack="${id}" class="${game.equippedTack===id?"selected":""}">${tackCatalog[id].name}<small>${tackCatalog[id].desc}</small></button>`).join("")
    : "";
}
function applyHorseAppearance(el){
  if(!el)return;
  const color=game.candidate?.color||"#b96e32";
  el.style.setProperty("--active-horse-color",color);
  el.style.setProperty("--horse-color",color);
  el.querySelectorAll(".candidate-pixel-horse").forEach(horse=>horse.style.setProperty("--horse-color",color));
  el.classList.toggle("has-face-mark",!!game.candidate?.faceMark);
  el.classList.toggle("has-socks",(game.candidate?.socks||0)>0);
  ["hood","blinkers","cheekpieces"].forEach(id=>el.classList.toggle(`tack-${id}`,game.equippedTack===id));
}
function renderHorseDetail(){
  const stage=document.querySelector("#detailHorseStage");
  applyHorseAppearance(stage);
  document.querySelector("#detailAge").textContent=`${horseAge()}歳・${gameYear()}年目`;
  document.querySelector("#horseDetailInfo").innerHTML=`<h2>${game.horseName}</h2><dl>
    <dt>毛色</dt><dd>${game.candidate?.coat||"栗毛"}${game.candidate?.faceMark?"・額に白い模様":""}</dd>
    <dt>目つき</dt><dd>${game.candidate?.eyeType||"穏やか"}</dd><dt>性格</dt><dd>${trainerTemperamentComment()}</dd>
    <dt>馬体</dt><dd>${game.weight}kg・${weightComment()}</dd><dt>馬具</dt><dd>${game.equippedTack?tackCatalog[game.equippedTack].name:"なし"}</dd>
    <dt>戦績</dt><dd>${game.races}戦${game.wins}勝・${game.prize.toLocaleString()}万円</dd><dt>好感度</dt><dd>${game.affection<3?"まだ少し緊張":game.affection<8?"心を開いてきた":"とても懐いている"}</dd></dl>`;
}
function renderHome(message="今週の予定を決めましょう。"){
  document.querySelector("#homeHorseName").textContent=game.horseName;
  document.querySelector("#homePrize").textContent=`${game.prize.toLocaleString()}万円`;
  document.querySelector("#weekDisplay").textContent=`${horseAge()}歳 ${weekLabel()}`;
  document.querySelector("#turnsLeft").textContent=`${game.trainingsUsed}/2`;
  document.querySelector("#farmPoints").textContent=`${game.farmPoints} FP`;
  document.querySelector("#conditionText").textContent=`調子：${conditionLabel()}／脚元：${legLabel()}／${classLabel()}`;
  const debutWeek=Math.min(...raceCalendar.filter(r=>r.raceClass==="新馬").map(r=>r.week));
  document.querySelector("#debutCountdown").textContent=game.races>0?"初戦出走済み":game.week<debutWeek?`新馬戦開始まであと${debutWeek-game.week}週（${Math.floor((debutWeek-1)/4)+1}月${(debutWeek-1)%4+1}週から）`:"新馬戦へ出走できます";
  document.querySelector("#homeMessage").textContent=message;
  applyHorseAppearance(document.querySelector("#trainingScene"));
  const statsEl=document.querySelector("#horseStats");
  statsEl.hidden=!developerMode;
  statsEl.innerHTML=developerMode
    ? statRow("スピード",game.speed,"#57c8ff")+statRow("ダッシュ",game.dash,"#ff9d43")+statRow("スタミナ",game.stamina,"#55d56b")+
      statRow("パワー",game.power,"#ef8661")+statRow("勝負根性",game.guts,"#e6c354")+
      statRow("芝適性",game.turf,"#72c45e")+statRow("ダート適性",game.dirt,"#c9915b")+
      statRow("道悪適性",game.heavyTrack,"#5aa5c8")+
      statRow("ゲート習熟",game.gateSkill,"#c7a9ef")+
      `<div class="trainer-stat"><span>調子の波</span><b>${game.condition}／${game.conditionDirection>0?"上向き":game.conditionDirection<0?"下降中":"維持"}・${game.conditionStability}型（残り${game.conditionPeakWeeks||game.conditionPhaseWeeks}週）</b></div>`
    : "";
  document.querySelector("#horseWeight").textContent=`${game.weight}kg`;
  document.querySelector("#horseWeightCondition").textContent=weightComment();
  document.querySelector("#fatigueBar").style.width=`${game.fatigue}%`;
  document.querySelector("#fatigueValue").textContent=game.fatigue<20?"元気":game.fatigue<45?"少し疲れ":game.fatigue<70?"疲れている":"かなり疲労";
  renderTack();
  const injured=!!game.injury;
  document.querySelectorAll("[data-action]").forEach(b=>b.disabled=injured||game.trainingsUsed>=2);
  document.querySelector("#goRaceSelectButton").disabled=injured;
  document.querySelector("#nextWeekButton").disabled=injured;
  document.querySelector("#pastureButton").hidden=!injured;
  if(injured)document.querySelector("#pastureWeeks").textContent=`${game.injury.name}・${game.injury.weeks}週間を一括進行`;
  saveGame();
}
const training={
  turfSolo:{label:"芝・単走",fatigue:8,stats:{speed:1,turf:1}},
  turfPair:{label:"芝・併せ馬",fatigue:17,stats:{speed:1,guts:1,turf:1}},
  dirtSolo:{label:"ダート・単走",fatigue:10,stats:{stamina:1,dirt:1}},
  dirtPair:{label:"ダート・併せ馬",fatigue:19,stats:{power:1,guts:1,dirt:1}},
  hill:{label:"坂路",fatigue:15,stats:{power:2}},
  pool:{label:"プール",fatigue:3,stats:{stamina:1}},
  gate:{label:"ゲート訓練",fatigue:7,stats:{dash:1}},
};
const injuries=[
  {name:"骨膜炎",minWeeks:6,maxWeeks:10,weight:44,lossChance:.18,maxLoss:1},
  {name:"軽度の管骨骨折",minWeeks:12,maxWeeks:18,weight:25,lossChance:.32,maxLoss:2},
  {name:"繋靭帯炎",minWeeks:16,maxWeeks:24,weight:19,lossChance:.45,maxLoss:3},
  {name:"浅屈腱炎",minWeeks:24,maxWeeks:36,weight:12,lossChance:.60,maxLoss:4},
];
function weightedInjury(){
  const total=injuries.reduce((sum,x)=>sum+x.weight,0);
  let roll=Math.random()*total;
  return injuries.find(x=>(roll-=x.weight)<=0)||injuries[0];
}
function injuryRisk(type){
  const intensity={turfSolo:.55,turfPair:1,dirtSolo:.65,dirtPair:1.08,hill:1.15,pool:.08,gate:.35}[type]||0;
  if(game.fatigue<55||intensity===0)return 0;
  const fatigueRisk=Math.pow((game.fatigue-50)/50,2);
  const legRisk=game.legCondition>=65?1:game.legCondition>=45?1.45:2.1;
  return Math.min(.05,(.001+fatigueRisk*.032*intensity)*legRisk);
}
function sufferInjury(type){
  if(Math.random()>=injuryRisk(type))return null;
  const injury=weightedInjury();
  game.injury={...injury,weeks:rnd(injury.minWeeks,injury.maxWeeks)};
  return game.injury;
}
function sendToPasture(){
  if(!game.injury)return;
  const injury=game.injury;
  const weeks=injury.weeks;
  game.week+=weeks;
  game.trainingsUsed=0;
  game.fatigue=0;
  game.legCondition=Math.min(100,game.legCondition+rnd(28,45));
  game.condition=Math.max(35,Math.min(70,game.condition+rnd(-5,8)));
  game.weight=Math.min(600,bestWeight()+rnd(10,22));
  const lost=[];
  ["speed","dash","stamina","power","guts"].forEach(stat=>{
    if(Math.random()<injury.lossChance){
      const amount=rnd(1,injury.maxLoss)*10;
      game[stat]=Math.max(1,Math.round((game[stat]-amount)*10)/10);
      lost.push(`${stat==="speed"?"スピード":stat==="dash"?"ダッシュ":stat==="stamina"?"スタミナ":stat==="power"?"パワー":"勝負根性"}-${amount}`);
    }
  });
  game.injury=null;
  renderHome(`${injury.name}から復帰しました。${weeks}週間の放牧${lost.length?`で能力が低下（${lost.join("、")}）`:"を経て、能力低下はありませんでした"}。`);
}
const equipmentCatalog=[
  {id:"treadmill",name:"高性能トレッドミル",cost:120,grade:"改良型",desc:"坂路調教のパワー上昇量+1"},
  {id:"walker",name:"ウォーキングマシン",cost:90,grade:"標準設備",desc:"翌週開始時の疲労回復+8"},
  {id:"gps",name:"GPS計測装置",cost:70,grade:"標準設備",desc:"調教失敗率を25%軽減"},
];
const galleryCatalog=[
  {id:"stable",title:"はじめての入厩",trophy:"bronze",condition:()=>true,desc:"厩舎で始まった育成の日々"},
  {id:"debut",title:"ターフへ",trophy:"bronze",condition:g=>g.races>=1,desc:"記念すべき初出走"},
  {id:"firstWin",title:"初勝利",trophy:"silver",condition:g=>g.wins>=1,desc:"初めて先頭で駆け抜けた日"},
  {id:"mudWin",title:"泥んこの勲章",trophy:"silver",condition:g=>g.raceHistory.some(x=>x.place===1&&["重","不良"].includes(x.going)),desc:"道悪を克服して勝利"},
  {id:"graded",title:"重賞ウイナー",trophy:"gold",condition:g=>g.raceHistory.some(x=>x.place===1&&["G1","G2","G3"].includes(x.raceClass)),desc:"重賞のタイトルを獲得"},
  {id:"g1",title:"夢の頂点",trophy:"grand",condition:g=>g.raceHistory.some(x=>x.place===1&&x.raceClass==="G1"),desc:"GⅠ制覇"},
  {id:"record",title:"時代を超えた脚",trophy:"record",condition:g=>g.raceHistory.some(x=>x.isRecord),desc:"レコードタイムを更新"},
  {id:"veteran",title:"歴戦の相棒",trophy:"gold",condition:g=>g.races>=10,desc:"10戦を共に戦った証"}
];
function refreshGalleryUnlocks(){
  galleryCatalog.forEach(item=>{
    if(item.condition(game)&&!game.galleryUnlocks.includes(item.id))game.galleryUnlocks.push(item.id);
  });
}
function renderHistory(){
  const totalPrize=game.raceHistory.reduce((sum,x)=>sum+x.earned,0);
  document.querySelector("#historySummary").textContent=`${game.races}戦${game.wins}勝　${totalPrize.toLocaleString()}万円`;
  const favorites=game.favoriteRaces.length
    ? `<h2 class="archive-caption">★ お気に入りレース</h2>${[...game.favoriteRaces].map((x,index)=>({x,index})).reverse().map(({x,index})=>`<article class="history-card favorite">
        <div class="history-place"><b>★</b></div>
        <div><small>${x.course}　${x.weather}／${x.going}</small><h3>${x.raceName}</h3>
        <p>勝ちタイム ${x.winnerTime}　勝ち馬 ${x.order?.[0]?.name||"--"}</p></div>
        <button class="favorite-play" data-favorite-replay="${index}">再生</button>
      </article>`).join("")}`
    : "";
  const history=game.raceHistory.length
    ? `<h2 class="archive-caption">全戦歴</h2>${[...game.raceHistory].reverse().map((x,i)=>`<article class="history-card ${x.place===1?"winner":""}">
        <div class="history-place"><b>${x.place}</b><small>着</small></div>
        <div><small>${x.age}歳 ${x.date}　${x.course}</small><h3>${x.raceName}</h3>
        <p>${x.weather}／${x.going}　${x.time}${x.isRecord?"　NEW RECORD":""}${x.favorite?"　★お気に入り":""}</p></div>
        <strong>+${x.earned.toLocaleString()}万</strong>
      </article>`).join("")}`
    : `<p class="empty-archive">まだ出走記録がありません。</p>`;
  document.querySelector("#historyList").innerHTML=favorites+history;
}
function replayFavoriteRace(index){
  const saved=game.favoriteRaces[index];
  if(!saved?.setup)return;
  const setup={...saved.setup,replaySeed:saved.seed,archiveReplay:true};
  document.querySelector("#raceCourseTitle").textContent=saved.course;
  document.querySelector("#raceNameTitle").textContent=`${saved.raceName}・保存リプレイ`;
  showScreen("raceScreen");
  dispatchEvent(new CustomEvent("dotkeiba:prepare",{detail:setup}));
}
function renderGallery(){
  refreshGalleryUnlocks();
  const unlocked=galleryCatalog.filter(x=>game.galleryUnlocks.includes(x.id)).length;
  document.querySelector("#gallerySummary").textContent=`${unlocked} / ${galleryCatalog.length}`;
  document.querySelector("#galleryGrid").innerHTML=galleryCatalog.map(item=>{
    const open=game.galleryUnlocks.includes(item.id);
    const winningRace=open?game.raceHistory.find(x=>x.place===1&&(item.id==="record"?x.isRecord:item.id==="graded"?["G1","G2","G3"].includes(x.raceClass):item.id==="g1"?x.raceClass==="G1":true)):null;
    return `<article class="gallery-card ${open?"unlocked":"locked"}">
      <div class="gallery-art ${open?item.trophy:""}">
        <div class="pixel-trophy"><i class="cup"></i><i class="handle left"></i><i class="handle right"></i><i class="stem"></i><i class="base"></i></div>
        <div class="pixel-winner"><i class="head"></i><i class="cap"></i><i class="body"></i><i class="arm left"></i><i class="arm right"></i><i class="leg left"></i><i class="leg right"></i></div>
        <div class="gallery-podium"></div>
        ${open?"":'<b class="gallery-lock">?</b>'}
      </div>
      <h3>${open?item.title:"？？？？"}</h3><p>${open?item.desc:"条件を達成すると解放"}</p>
      ${open&&winningRace?`<small class="trophy-winner">勝馬 ${game.horseName}<br>${winningRace.raceName}</small>`:""}
    </article>`;
  }).join("");
  saveGame();
}
function train(type){
  if(game.injury)return renderHome(`${game.injury.name}のため調教できません。長期放牧が必要です。`);
  if(game.trainingsUsed>=2)return renderHome("今週の調教は2回終了しました。レースか翌週を選びましょう。");
  if(type==="rest"){
    game.trainingsUsed++;
    game.fatigue=Math.max(0,game.fatigue-22);
    game.condition=Math.min(100,game.condition+4);
    game.weight=Math.min(600,game.weight+rnd(4,7));
    game.legCondition=Math.min(100,game.legCondition+rnd(8,14));
    playTrainingAnimation("rest","休養","回復");
    return renderHome(`調教師「${conditionTrendComment()}」 休養しました。現在${game.weight}kg、${weightComment()}。`);
  }
  const t=training[type];
  const beforeStats=Object.fromEntries(Object.keys(t.stats).map(stat=>[stat,game[stat]]));
  const roll=Math.random(),failChance=(.05+game.fatigue*.004)*(game.equipment.includes("gps")?.75:1);
  let outcome,mult;
  if(roll<failChance){outcome="失敗";mult=0}
  else if(roll>.94-game.condition*.0005){outcome="大成功";mult=2}
  else{outcome="成功";mult=1}
  Object.entries(t.stats).forEach(([stat,value])=>{
    game[stat]=Math.round((game[stat]+trainingGain(stat,value,mult,type))*10)/10;
  });
  if(type==="gate"&&mult>0)game.gateSkill=Math.min(1000,game.gateSkill+rnd(mult===2?24:12,mult===2?40:22));
  const gains=Object.fromEntries(Object.keys(t.stats).map(stat=>[stat,game[stat]-beforeStats[stat]]));
  game.trainingsUsed++; game.fatigue=Math.min(100,game.fatigue+t.fatigue);
  const legLoad={turfSolo:3,turfPair:8,dirtSolo:4,dirtPair:9,hill:10,pool:-5,gate:2}[type]||0;
  game.legCondition=Math.max(0,Math.min(100,game.legCondition-legLoad+rnd(-1,1)));
  const weightLoss=type==="pool"?rnd(1,2):type==="gate"?rnd(1,2):type.includes("Pair")||type==="hill"?rnd(3,5):rnd(2,4);
  game.weight=Math.max(330,game.weight-weightLoss);
  game.condition=Math.max(20,Math.min(100,game.condition+(outcome==="大成功"?5:outcome==="失敗"?-10:-1)));
  const injury=sufferInjury(type);
  if(injury){
    playTrainingAnimation(type,t.label,"故障");
    return renderHome(`${t.label}中に${injury.name}を発症しました。復帰には${injury.weeks}週間の長期放牧が必要です。`);
  }
  playTrainingAnimation(type,t.label,outcome);
  game.temperamentObservations++;
  let tackMessage="";
  if(!game.temperamentKnown&&game.temperamentObservations>=2){
    game.temperamentKnown=true;
    tackMessage=` 調教師「${trainerTemperamentComment()}」`;
  }
  const proposed=game.temperament==="荒い"||game.temperament==="前向き"?"blinkers":game.temperament==="臆病"?"hood":game.temperamentObservations>=4?"cheekpieces":null;
  if(proposed&&!game.tackUnlocked.includes(proposed)&&Math.random()<.38){
    game.tackUnlocked.push(proposed);
    tackMessage+=` 調教師から${tackCatalog[proposed].name}を試す提案がありました。`;
  }
  const coachComment=trainingCoachComment(type,outcome,gains);
  renderHome(`調教師「${coachComment} ${conditionTrendComment()}」 現在${game.weight}kg、${weightComment()}。${tackMessage}`);
}
function playTrainingAnimation(type,label,outcome){
  const popup=document.querySelector("#trainingPopup");
  const stage=document.querySelector("#trainingPopupStage");
  document.querySelector("#trainingPopupTitle").textContent=label;
  document.querySelector("#trainingPopupResult").textContent=outcome==="失敗"?"うまく走れなかった…":outcome==="大成功"?"大成功！":`${outcome}！`;
  popup.style.setProperty("--popup-horse-color",game.candidate?.color||"#b96e32");
  popup.classList.add("show");
  popup.setAttribute("aria-hidden","false");
  stage.className=`training-popup-stage ${type}`;
  clearTimeout(playTrainingAnimation.timer);
  playTrainingAnimation.timer=setTimeout(()=>{
    popup.classList.remove("show");
    popup.setAttribute("aria-hidden","true");
  },2200);
}
function advanceWeek(rest=false){
  game.week++; game.trainingsUsed=0;
  const walker=game.equipment.includes("walker")?8:0;
  game.fatigue=Math.max(0,game.fatigue-(rest?38:14)-walker);
  game.legCondition=Math.min(100,game.legCondition+(rest?rnd(12,20):rnd(4,8)));
  advanceConditionCycle(rest?5:0);
  game.weight=Math.min(600,game.weight+(rest?rnd(6,10):rnd(2,4)));
  const reserved=raceCalendar.find(r=>r.id===game.reservedRaceId);
  const notice=reserved&&reserved.week===game.week?` 予約していた「${reserved.name}」の開催週です。`:reserved&&reserved.week-game.week===1?` 来週は予約した「${reserved.name}」です。`:"";
  renderHome(`${rest?"休養して翌週へ進みました。":"翌週へ進みました。"}${notice} 調教師「${conditionTrendComment()}」`);
}
function renderShop(){
  document.querySelector("#shopPoints").textContent=`${game.farmPoints} FP`;
  document.querySelector("#equipmentCards").innerHTML=equipmentCatalog.map(item=>{
    const owned=game.equipment.includes(item.id),canBuy=game.farmPoints>=item.cost;
    return `<article class="equipment-card ${owned?"owned":""}">
      <div class="equipment-icon">${item.id==="treadmill"?"走":item.id==="walker"?"歩":"測"}</div>
      <div><small>${item.grade}</small><h3>${item.name}</h3><p>${item.desc}</p></div>
      <button data-equipment="${item.id}" ${owned||!canBuy?"disabled":""}>${owned?"所有中":`${item.cost} FP`}</button>
    </article>`;
  }).join("");
}
function buyEquipment(id){
  const item=equipmentCatalog.find(x=>x.id===id);
  if(!item||game.equipment.includes(id)||game.farmPoints<item.cost)return;
  game.farmPoints-=item.cost; game.equipment.push(id); saveGame(); renderShop();
}
function renderRaces(){
  document.querySelector("#selectTurn").textContent=weekLabel();
  if(!window.selectedRacePeriod)window.selectedRacePeriod="current";
  const futureStart=Math.min(...raceCalendar.filter(r=>r.week>game.week&&r.program).map(r=>r.week));
  const periodRaces=raceCalendar.filter(r=>(window.selectedRacePeriod==="current"?r.week===game.week:(r.week>=futureStart&&r.week<=futureStart+3))&&(r.program||["G1","G2","G3","オープン"].includes(r.raceClass)));
  const venues=["すべて",...new Set(periodRaces.map(raceVenue))];
  if(!venues.includes(window.selectedRaceVenue))window.selectedRaceVenue=venues[1]||"すべて";
  document.querySelectorAll("[data-period]").forEach(b=>b.classList.toggle("selected",b.dataset.period===window.selectedRacePeriod));
  document.querySelector("#raceVenueTabs").innerHTML=venues.map(v=>`<button data-venue="${v}" class="${window.selectedRaceVenue===v?"selected":""}">${v}</button>`).join("");
  const shown=periodRaces.filter(r=>window.selectedRaceVenue==="すべて"||raceVenue(r)===window.selectedRaceVenue).sort((a,b)=>a.week-b.week||raceVenue(a).localeCompare(raceVenue(b))||(a.number||11)-(b.number||11));
  document.querySelector("#raceChoices").innerHTML=shown.map(r=>{
    const arrived=r.week===game.week,eligible=arrived&&r.condition(game),surfaceAbility=r.surface==="芝"?game.turf:game.dirt;
    const raceYear=Math.floor((r.week-1)/48)+1,raceYearWeek=(r.week-1)%48;
    const date=`${raceYear}年目 ${Math.floor(raceYearWeek/4)+1}月${raceYearWeek%4+1}週`;
    let reason="出走条件外";
    if(eligible)reason="出走する";
    else if(!arrived)reason="未来の予定";
    else if(r.raceClass==="新馬"&&game.races>0)reason="新馬戦は初戦のみ";
    else if(r.raceClass==="未勝利"&&game.races===0)reason="新馬戦出走後";
    else if(r.raceClass==="未勝利"&&!game.maiden)reason="勝ち上がり済み";
    else if(r.id==="derby")reason="優先権・収得賞金不足";
    else if(game.maiden)reason="未勝利馬条件";
    else reason="獲得賞金不足";
    const reserved=game.reservedRaceId===r.id;
    const wonBefore=game.raceHistory.some(x=>x.raceName===r.name&&x.place===1);
    return `<article class="race-choice ${eligible?"":"locked"} ${reserved?"reserved":""}"><b class="race-number">${r.number||11}R</b><div><small>${date}　${r.course}${reserved?"　★出走予定":""}</small>
    <h3>${wonBefore?"🏆 ":""}${r.name}</h3><p>1着賞金 ${r.prize.toLocaleString()}万円　${r.surface} ${developerMode?surfaceAbility:scoutComment(`${r.surface}適性`,surfaceAbility)}</p></div>
    <div class="race-choice-buttons"><button ${eligible?"":"disabled"} data-race="${r.id}">${reason}</button>${!arrived?`<button data-reserve="${r.id}">${reserved?"予約を解除":"出走予約"}</button>`:""}</div></article>`;
  }).join("")||`<p class="empty-races">${window.selectedRacePeriod==="current"?"今週、この条件で開催されるレースはありません。未来の予定から予約できます。":"今後の登録レースはありません。"}</p>`;
}
function playerAbility(race){
  const surface=race.surface==="芝"?game.turf:game.dirt;
  const speed=game.speed,dash=game.dash,stamina=game.stamina,power=game.power,guts=game.guts;
  const distanceWeight=race.distance>=2000?stamina:speed;
  const weightPenalty=Math.min(80,Math.abs(game.weight-bestWeight())*2.2);
  const fatiguePenalty=game.fatigue<=25?0:game.fatigue<=45?(game.fatigue-25)*.6:game.fatigue<=70?12+(game.fatigue-45)*1.2:42+(game.fatigue-70)*1.3;
  const distancePenalty=distanceAbilityPenalty(race.distance);
  const raw=distanceWeight*.28+speed*.18+dash*.08+stamina*.14+power*.11+guts*.07+surface*.14+
    growthAbilityBonus()+raceConditionModifier()-weightPenalty-fatiguePenalty-distancePenalty;
  return Math.round(Math.min(game.generation===1?840:1000,raw));
}
function seededRaceRandom(race,salt=0){
  const text=`${game.horseName}-${race.id}-${game.week}-${salt}`;
  let hash=2166136261;
  for(let i=0;i<text.length;i++){hash^=text.charCodeAt(i);hash=Math.imul(hash,16777619)}
  return (hash>>>0)/4294967296;
}
const VENUE_WEATHER_REGION={
  "札幌":"north","函館":"north",
  "福島":"east","新潟":"east",
  "東京":"kanto","中山":"kanto",
  "中京":"central","京都":"kansai","阪神":"kansai","小倉":"west"
};
const MONTHLY_RAIN_CHANCE={
  north:[.18,.17,.19,.22,.25,.28,.27,.30,.31,.28,.24,.20],
  east:[.17,.18,.22,.27,.31,.38,.36,.34,.38,.28,.20,.17],
  kanto:[.14,.16,.21,.27,.31,.43,.35,.30,.39,.28,.17,.13],
  central:[.16,.18,.23,.28,.33,.42,.37,.32,.40,.29,.18,.15],
  kansai:[.17,.19,.23,.28,.32,.40,.36,.31,.38,.27,.18,.15],
  west:[.19,.21,.25,.29,.32,.39,.36,.34,.38,.27,.20,.18]
};
function raceCalendarMonth(race){
  return Math.floor(((race.week-1)%48)/4)+1;
}
function raceDayWeather(race){
  const venue=raceVenue(race),month=raceCalendarMonth(race);
  const region=VENUE_WEATHER_REGION[venue]||"kanto";
  let rainChance=MONTHLY_RAIN_CHANCE[region][month-1];
  // 梅雨と秋雨は雨が増えるが、連続して極端な道悪ばかりにはしない。
  if(month===6&&(region==="kanto"||region==="central"||region==="kansai"))rainChance+=.04;
  const weatherRoll=seededRaceRandom(race,1);
  const heavyRainChance=month>=7&&month<=9?.16:.09;
  const snowChance=region!=="north"&&(month===1||month===2||month===12)
    // 1レース単位ではごく低確率。複数年プレイして約3年に1度見る程度のレア演出。
    ? (region==="east"||region==="kanto"?.006:.004)
    : 0;
  const snow=seededRaceRandom(race,5)<snowChance;
  const weather=snow?"雪":weatherRoll<rainChance
    ? (seededRaceRandom(race,3)<heavyRainChance?"大雨":"雨")
    : weatherRoll<rainChance+.27?"曇":"晴";
  const goingRoll=seededRaceRandom(race,2);
  const priorMoisture=seededRaceRandom(race,4);
  let going;
  if(weather==="晴"){
    const damp=priorMoisture<rainChance*.38;
    going=damp?(goingRoll<.62?"良":"稍重"):(goingRoll<.94?"良":"稍重");
  }else if(weather==="曇"){
    const damp=priorMoisture<rainChance*.65;
    going=damp?(goingRoll<.40?"良":goingRoll<.84?"稍重":"重"):(goingRoll<.72?"良":"稍重");
  }else if(weather==="雪"){
    going=goingRoll<.42?"稍重":goingRoll<.86?"重":"不良";
  }else if(weather==="雨"){
    going=goingRoll<.08?"良":goingRoll<.48?"稍重":goingRoll<.86?"重":"不良";
  }else{
    going=goingRoll<.12?"稍重":goingRoll<.57?"重":"不良";
  }
  return {weather,going,month,region};
}
function prepareRace(race){
  if(!race)return;
  document.querySelector("#raceCourseTitle").textContent=`${race.course}・左`;
  document.querySelector("#raceNameTitle").textContent=race.name;
  document.querySelector("#newspaperDate").textContent=weekLabel();
  document.querySelector("#newspaperCourse").textContent=race.course;
  document.querySelector("#newspaperRaceName").textContent=race.name;
  document.querySelector("#newspaperEntries").innerHTML='<p class="newspaper-loading">出走各馬を取材中……</p>';
  showScreen("newspaperScreen");
  try{
    const timingRecord=raceTimingRecord(race),benchmarkTime=classBenchmarkTime(race),recordTime=timingRecord.time;
    const raceWeather=raceDayWeather(race);
    // condition関数を含むカレンダー本体ではなく、結果処理に必要な値だけを保存する。
    game.selectedRace={
      id:race.id,name:race.name,raceClass:race.raceClass,course:race.course,
      surface:race.surface,distance:race.distance,prize:race.prize,
      trialRight:race.trialRight||null
    };
    game.currentRaceWeather=raceWeather;
    saveGame();
    dispatchEvent(new CustomEvent("dotkeiba:prepare",{detail:{horseName:game.horseName,raceName:race.name,ability:playerAbility(race),dash:game.dash,gateSkill:game.gateSkill,condition:game.condition,fatigue:game.fatigue,difficulty:race.difficulty*10,raceClass:race.raceClass,venue:raceVenue(race),distance:race.distance,surface:race.surface,heavyTrack:game.heavyTrack,temperament:game.temperament,temperamentValue:game.temperamentValue,equippedTack:game.equippedTack,weather:raceWeather.weather,going:raceWeather.going,raceMonth:raceWeather.month,baseTime:benchmarkTime,benchmarkTime,recordTime,recordVerified:timingRecord.verified,horizontalLayout:!!race.horizontalTest,layoutV2:!!race.horizontalTest2}}));
  }catch(error){
    console.error("race preparation failed",error);
    document.querySelector("#commentary").textContent="レースの読み込みを再試行しています。";
    dispatchEvent(new CustomEvent("dotkeiba:prepare",{detail:{
      horseName:game.horseName,raceName:race.name,ability:playerAbility(race),dash:game.dash,gateSkill:game.gateSkill,
      condition:game.condition,fatigue:game.fatigue,difficulty:race.difficulty*10,
      raceClass:race.raceClass,venue:raceVenue(race),distance:race.distance,
      surface:race.surface,heavyTrack:game.heavyTrack,weather:"晴",going:"良",
      raceMonth:raceCalendarMonth(race),baseTime:race.baseTime,
      benchmarkTime:race.baseTime,recordTime:race.baseTime*.965,recordVerified:false
    }}));
  }
}
function postRaceTrainerComment(){
  const comments=[];
  if(game.injury)return `調教師「レース後に${game.injury.name}が判明しました。無理はできません。${game.injury.weeks}週間の長期放牧が必要です。」`;
  if(game.fatigue>=75)comments.push("かなり疲れが残っています。次週は休養を優先した方がいいでしょう");
  else if(game.fatigue>=52)comments.push("レースの疲れが見えます。強い調教は避けたいところです");
  else comments.push("レース後としては疲れも軽く、回復は早そうです");

  const weightDiff=game.weight-bestWeight();
  if(weightDiff<=-12)comments.push("馬体が細くなっています。しっかり食べさせて戻しましょう");
  else if(weightDiff>=12)comments.push("まだ馬体には余裕があります");
  else comments.push("馬体重は良い範囲に収まっています");

  if(game.legCondition<45)comments.push("脚元に強い張りがあります。念のため慎重に見ていきます");
  else if(game.legCondition<70)comments.push("脚元に少し張りがあるので、軽めの調整がよさそうです");
  else comments.push("脚元に大きな問題はありません");

  comments.push(conditionTrendComment());
  return `調教師「${comments.join("。")}。」`;
}
function sufferPostRaceInjury(race,going){
  let risk=.0005;
  if(game.fatigue>=70)risk+=.0012;
  if(game.legCondition<70)risk+=.0010;
  if(game.legCondition<45)risk+=.0025;
  if(["重","不良"].includes(going))risk+=.0008;
  if(race.surface==="ダート")risk+=.0003;
  if(Math.random()>=Math.min(.007,risk))return null;
  const injury=weightedInjury();
  game.injury={...injury,weeks:rnd(injury.minWeeks,injury.maxWeeks)};
  return game.injury;
}
function showResult(detail){
  const player=detail.order.find(h=>h.player),place=detail.order.findIndex(h=>h.player)+1,r=game.selectedRace;
  const earned=place===1?r.prize:place===2?Math.round(r.prize*.4):place===3?Math.round(r.prize*.25):place<=5?Math.round(r.prize*.1):0;
  game.prize+=earned;game.races++;if(place===1){game.wins++;game.maiden=false}
  if(game.reservedRaceId===r.id)game.reservedRaceId=null;
  const classMoneyAdd=place===1
    ? (r.raceClass==="新馬"||r.raceClass==="未勝利"?400:r.raceClass==="1勝"?500:r.raceClass==="2勝"?600:r.raceClass==="3勝"?900:r.raceClass==="G3"?1600:r.raceClass==="G2"||r.raceClass==="G1"?Math.round(r.prize*.5):1000)
    : ((["G1","G2","G3"].includes(r.raceClass)&&place===2)?Math.round(r.prize*.2):0);
  game.classMoney+=classMoneyAdd;
  if(r.trialRight&&place<=r.trialRight.maxPlace&&!game.priorityRights.includes(r.trialRight.name))game.priorityRights.push(r.trialRight.name);
  const fpTable=[45,32,24,18,14,11,9,7];
  const fpEarned=fpTable[Math.min(7,place-1)]+5;
  game.farmPoints+=fpEarned;
  const weather=game.currentRaceWeather||{weather:"晴",going:"良"};
  const playerTrouble=player.temperamentTrouble;
  if(playerTrouble==="掛かり"&&!game.tackUnlocked.includes("blinkers"))game.tackUnlocked.push("blinkers");
  if((playerTrouble==="出遅れ"||playerTrouble==="物見")&&!game.tackUnlocked.includes("hood"))game.tackUnlocked.push("hood");
  game.raceHistory.push({
    raceName:r.name,raceClass:r.raceClass,course:r.course,place,time:player.finishTime,
    earned,weather:weather.weather,going:weather.going,isRecord:!!player.isRecord,
    age:horseAge(),date:weekLabel(),favorite:false
  });
  refreshGalleryUnlocks();
  game.fatigue=Math.min(100,game.fatigue+28);advanceConditionCycle(-8);
  game.legCondition=Math.max(0,game.legCondition-rnd(4,9));
  game.weight=Math.max(330,game.weight-rnd(4,7));
  sufferPostRaceInjury(r,weather.going);
  game.week++;game.trainingsUsed=0;saveGame();
  document.querySelector("#resultPlace").textContent=`${place}着`;document.querySelector("#resultHorseName").textContent=game.horseName;
  document.querySelector("#resultFrame").textContent=player.id;document.querySelector("#resultFrame").style.background=player.color;
  document.querySelector("#resultTime").textContent=player.finishTime;document.querySelector("#resultPrize").textContent=`${earned.toLocaleString()}万円／+${fpEarned} FP${classMoneyAdd?`／収得+${classMoneyAdd}`:""}`;
  document.querySelector("#resultComment").textContent=(place===1?"見事な勝利です！":place<=3?"好走しました。次は勝利を狙いましょう。":"調教を重ねて巻き返しましょう。")+
    (playerTrouble?` 調教師「今日は${playerTrouble}がありました。馬具を検討しましょう」`:"");
  document.querySelector("#postRaceCondition").textContent=postRaceTrainerComment();
  document.querySelector("#resultOrder").innerHTML=detail.order.slice(0,5).map((h,i)=>`<div><span>${i+1}</span><b>${h.name}</b><small>${h.odds.toFixed(1)}倍</small></div>`).join("");
  showScreen("resultScreen");
}

document.querySelector("#continueButton").disabled=!localStorage.getItem(SAVE_KEY);
document.querySelector("#devModeButton").textContent=developerMode?"開発表示 ON":"開発表示";
document.querySelector("#newGameButton").onclick=()=>{game=defaultGame();generateCandidate();showScreen("nameScreen")};
document.querySelector("#raceTestButton").onclick=()=>{
  game=defaultGame();generateCandidate();
  const c=game.candidate;game={...game,horseName:"ドットスター",week:21,speed:650,dash:620,gateSkill:600,stamina:640,power:610,guts:600,turf:660,dirt:520,heavyTrack:560,baseBestWeight:c.baseBestWeight,weight:c.baseBestWeight,condition:72,candidate:c,potentialCaps:c.potentialCaps};
  prepareRace({...raceCalendar.find(r=>r.id==="n2"),horizontalTest:true});
  showScreen("raceScreen");
  dispatchEvent(new CustomEvent("dotkeiba:auto-start"));
};
document.querySelector("#raceTest2Button").onclick=()=>{
  game=defaultGame();generateCandidate();
  const c=game.candidate;game={...game,horseName:"ドットスター",week:21,speed:650,dash:620,gateSkill:600,stamina:640,power:610,guts:600,turf:660,dirt:520,heavyTrack:560,baseBestWeight:c.baseBestWeight,weight:c.baseBestWeight,condition:72,candidate:c,potentialCaps:c.potentialCaps};
  prepareRace({...raceCalendar.find(r=>r.id==="n2"),horizontalTest2:true});
  showScreen("raceScreen");
  dispatchEvent(new CustomEvent("dotkeiba:auto-start"));
};
document.querySelector("#rerollHorseButton").onclick=generateCandidate;
document.querySelector("#continueButton").onclick=()=>{if(loadGame()){renderHome();showScreen("homeScreen")}};
document.querySelector("#confirmNameButton").onclick=()=>{
  const input=document.querySelector("#horseNameInput"),name=input.value.trim();
  const blocked=["チンコ","マンコ","セックス","シネ","コロス"];
  if(!/^[ァ-ヶー]{2,10}$/.test(name)||blocked.some(word=>name.includes(word))){
    document.querySelector("#nameScreen .hint").textContent="馬名はカタカナ2〜10文字で、使用できない表現を含まない名前にしてください。";
    input.focus();return;
  }
  const c=game.candidate;game={...defaultGame(),horseName:name,speed:c.speed,dash:c.dash,gateSkill:c.gateSkill,stamina:c.stamina,power:c.power,guts:c.guts,turf:c.turf,dirt:c.dirt,heavyTrack:c.heavyTrack,temperament:c.temperament,temperamentValue:c.temperamentValue,baseBestWeight:c.baseBestWeight,weight:c.weight,growthType:c.growthType,growthPotential:c.growthPotential,potentialCaps:c.potentialCaps,distanceMin:c.distanceMin,distanceMax:c.distanceMax,condition:c.condition,conditionDirection:c.conditionDirection,conditionPhaseWeeks:c.conditionPhaseWeeks,conditionStability:c.conditionStability,conditionPeakWeeks:c.conditionPeakWeeks,candidate:c};
  renderHome(`入厩しました。現在${game.weight}kg、${weightComment()}。まずは馬体を整えましょう。`);showScreen("homeScreen");
};
document.querySelectorAll("[data-back]").forEach(b=>b.onclick=()=>showScreen(b.dataset.back));
document.querySelectorAll("[data-action]").forEach(b=>b.onclick=()=>train(b.dataset.action));
document.querySelector("#pastureButton").onclick=sendToPasture;
document.querySelector("#nextWeekButton").onclick=()=>advanceWeek(false);
document.querySelector("#shopButton").onclick=()=>{renderShop();showScreen("shopScreen")};
document.querySelector("#historyButton").onclick=()=>{renderHistory();showScreen("historyScreen")};
document.querySelector("#historyList").onclick=e=>{
  const button=e.target.closest("[data-favorite-replay]");
  if(button)replayFavoriteRace(Number(button.dataset.favoriteReplay));
};
document.querySelector("#galleryButton").onclick=()=>{renderGallery();showScreen("galleryScreen")};
const openHorseDetail=()=>{renderHorseDetail();showScreen("horseDetailScreen")};
document.querySelector("#homeHorse").onclick=e=>{e.stopPropagation();openHorseDetail()};
document.querySelector("#homeHorse").onkeydown=e=>{
  if(e.key!=="Enter"&&e.key!==" ")return;
  e.preventDefault();e.stopPropagation();openHorseDetail();
};
document.querySelector("#trainingScene").onclick=()=>{
  game.affection=Math.min(99,game.affection+1);
  const reactions=["嬉しそうに首を振りました。","こちらへ駆け寄ってきました。","小さく跳ねて喜んでいます。","鼻を寄せて甘えています。"];
  renderHome(reactions[rnd(0,reactions.length-1)]);
};
document.querySelector("#detailHorseStage").onclick=()=>{
  game.affection=Math.min(99,game.affection+1);
  const reactions=["ブルルッ、と嬉しそうです。","撫でると目を細めました。","もっと遊んでほしそうに見ています。","尻尾を振って応えてくれました。"];
  document.querySelector("#horseReaction").textContent=reactions[rnd(0,reactions.length-1)];
  document.querySelector("#detailHorseStage").classList.remove("horse-happy");void document.querySelector("#detailHorseStage").offsetWidth;document.querySelector("#detailHorseStage").classList.add("horse-happy");
  saveGame();
};
document.querySelector("#devModeButton").onclick=()=>{
  developerMode=!developerMode;
  localStorage.setItem("dotKeibaDeveloperMode",developerMode?"1":"0");
  document.querySelector("#devModeButton").textContent=developerMode?"開発表示 ON":"開発表示";
  renderHome(developerMode?"内部能力と素質上限を表示しています。":"調教師コメント表示に戻しました。");
};
document.querySelector("#equipmentCards").onclick=e=>{if(e.target.dataset.equipment)buyEquipment(e.target.dataset.equipment)};
document.querySelector("#tackChoices").onclick=e=>{
  const button=e.target.closest("[data-tack]");
  if(!button)return;
  game.equippedTack=button.dataset.tack||null;
  renderHome(game.equippedTack?`${tackCatalog[game.equippedTack].name}を装着しました。`:"馬具を外しました。");
};
document.querySelector("#goRaceSelectButton").onclick=()=>{window.selectedRacePeriod="current";window.selectedRaceVenue="";renderRaces();showScreen("raceSelectScreen")};
document.querySelector("#raceChoices").onclick=e=>{
  const reserve=e.target.closest("[data-reserve]");
  if(reserve){game.reservedRaceId=game.reservedRaceId===reserve.dataset.reserve?null:reserve.dataset.reserve;saveGame();renderRaces();return}
  const button=e.target.closest("[data-race]");if(button)prepareRace(raceCalendar.find(r=>r.id===button.dataset.race));
};
document.querySelector("#raceVenueTabs").onclick=e=>{const b=e.target.closest("[data-venue]");if(b){window.selectedRaceVenue=b.dataset.venue;renderRaces()}};
document.querySelector(".race-period-tabs").onclick=e=>{const b=e.target.closest("[data-period]");if(b){window.selectedRacePeriod=b.dataset.period;window.selectedRaceVenue="";renderRaces()}};
document.querySelector("#newspaperRaceButton").onclick=()=>{showScreen("raceScreen");dispatchEvent(new CustomEvent("dotkeiba:auto-start"))};
addEventListener("dotkeiba:preview-ready",e=>{
  if(!game.selectedRace)return;
  const marks=["◎","○","▲","△","△","☆","",""];
  document.querySelector("#newspaperBias").textContent=`${e.detail.weather}・${e.detail.going}　${e.detail.bias}`;
  document.querySelector("#newspaperEntries").innerHTML=e.detail.entries.map(h=>{
    const mark=marks[h.popularity-1]||"";
    return `<article class="newspaper-entry ${h.player?"player":""}">
      <span class="news-number frame-${h.id}">${h.id}</span><b class="news-mark">${mark}</b>
      <div><h3>${h.name}${h.player?' <small>愛馬</small>':""}</h3><p>${h.style}　調子 ${h.condition}</p><small>${h.comment}</small></div>
      <strong>${h.odds.toFixed(1)}<small>倍</small></strong>
    </article>`;
  }).join("");
});
document.querySelector("#resetGameButton").onclick=()=>{if(confirm("育成データを消しますか？")){localStorage.removeItem(SAVE_KEY);game=defaultGame();showScreen("titleScreen")}};
document.querySelector("#returnHomeButton").onclick=()=>{renderHome("レースを終えて翌週になりました。");showScreen("homeScreen")};
addEventListener("dotkeiba:finished",e=>showResult(e.detail));
addEventListener("dotkeiba:favorite",e=>{
  const favorite={...e.detail,savedAt:Date.now()};
  game.favoriteRaces.push(favorite);
  saveGame();
  const button=document.querySelector("#favoriteRaceButton");
  if(button){button.textContent="★ 保存済み";button.disabled=true}
});
addEventListener("dotkeiba:archive-close",()=>{
  renderHistory();
  showScreen("historyScreen");
});
